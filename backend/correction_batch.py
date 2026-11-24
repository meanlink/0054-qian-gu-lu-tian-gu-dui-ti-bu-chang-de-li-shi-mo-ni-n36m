"""Queue weather corrections and publish their replay effects as one batch."""
from datetime import date
from typing import Any

from fastapi import HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, ValidationError

from core import enqueue

KIND = "weather-correction"
KIND_ALIASES = {
    "weather-correction", "weather-corrections", "correction-batch",
    "correction-rebatch", "weather-revision", "weather-revisions",
    "historical-log", "historical-log-correction", "weather-recompute",
}
ACTIVE_STATES = ("queued", "running", "failed")


class Block(BaseModel):
    on_day: date
    half_from: int = Field(ge=0, le=47)
    temp_c: float = Field(ge=-15, le=55, allow_inf_nan=False)
    humidity: int = Field(ge=0, le=100)
    source: str = Field(min_length=4, max_length=100)


def _model_block(item: Any) -> dict[str, Any]:
    try:
        if isinstance(item, Block):
            model = item
        elif isinstance(item, BaseModel) and hasattr(item, "model_dump"):
            model = Block.model_validate(item.model_dump())
        else:
            model = Block.model_validate(item)
    except ValidationError as exc:
        messages = "; ".join(
            f"{'.'.join(str(part) for part in error.get('loc', ()))} {error.get('msg', '')}".strip()
            for error in exc.errors()
        )
        raise HTTPException(422, messages or "气象订正字段不合法") from exc
    return model.model_dump(mode="json")


def parse_corrections(data: Any, idempotency_key: str | None = None):
    """Accept the legacy single form and explicit batch envelopes."""
    supplied_key = idempotency_key
    raw_items: Any = data

    if isinstance(data, BaseModel):
        raw_items = _model_block(data)
    elif isinstance(data, dict):
        supplied_key = (
            idempotency_key
            or data.get("idempotency_key")
            or data.get("batch_key")
            or data.get("key")
            or data.get("batch_no")
            or data.get("request_id")
            or data.get("reference")
            or data.get("Idempotency-Key")
        )
        if not supplied_key and isinstance(data.get("batch_id"), str):
            supplied_key = data["batch_id"]
        for container in (data.get("batch"), data.get("payload"), data.get("data")):
            if isinstance(container, dict):
                supplied_key = supplied_key or container.get("batch_key") or container.get("idempotency_key")
                if any(k in container for k in ("corrections", "blocks", "items", "records")):
                    data = container
                    break
        if isinstance(data, dict):
            for name in (
                "corrections", "blocks", "items", "records", "entries",
                "data", "weather", "readings", "rows", "payload",
            ):
                if isinstance(data.get(name), list):
                    raw_items = data[name]
                    break
            else:
                raw_items = data
    elif isinstance(data, list):
        raw_items = data

    if isinstance(raw_items, dict):
        items = [raw_items]
    else:
        items = list(raw_items or [])
    if not items:
        raise HTTPException(422, "请至少提供一条气象订正")

    merged: dict[tuple[str, int], dict[str, Any]] = {}
    for item in items:
        block = _model_block(item)
        merged[(block["on_day"], block["half_from"])] = block
    corrections = [merged[key] for key in sorted(merged)]
    key = str(supplied_key).strip() if supplied_key else None
    if key == "":
        key = None
    if key and len(key) > 100:
        raise HTTPException(422, "批次标识不能超过 100 个字符")
    return corrections, key


def _receipt(cx, row, *, reused=False, retried=False, message=None):
    if row is None:
        raise HTTPException(404, "没有这条订正批次")
    targets = row["target_codes"] or []
    if isinstance(targets, str):
        # Defensive only; psycopg returns jsonb as Python values.
        import json
        targets = json.loads(targets)
    codes = [item["code"] if isinstance(item, dict) else item for item in targets]
    job_status = None
    if row["job_id"] is not None:
        job = cx.execute(
            "SELECT status FROM app_jobs WHERE id=%s", (row["job_id"],)
        ).fetchone()
        job_status = job["status"] if job else None
    status_text = {
        "queued": "排队中",
        "running": "重算中",
        "failed": "失败，旧版仍在工作台显示，可按原批重试",
        "published": "已一次性切换气象与回放",
        "cancelled": "已取消",
    }.get(row["status"], row["status"])
    receipt = {
        "id": row["id"],
        "batch_id": row["id"],
        "batch_key": row["batch_key"],
        "job_id": row["job_id"],
        "job_status": job_status,
        "status": row["status"],
        "state": row["status"],
        "status_text": status_text,
        "pending": row["status"] in ("queued", "running"),
        "queued": row["status"] == "queued",
        "running": row["status"] == "running",
        "failed": row["status"] == "failed",
        "published": row["status"] == "published",
        "completed": row["status"] == "published",
        "correction_from": row["correction_from"],
        "corrections": row["corrections"],
        "targets": targets,
        "target_codes": codes,
        "hold_codes": codes,
        "holds": codes,
        "result": row["result"],
        "error": row["error"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "published_at": row["published_at"],
        "reused": reused,
        "deduplicated": reused,
        "retried": retried,
        "message": message or (
            "原批已发布，未重复发布" if reused and row["status"] == "published"
            else "订正已排队；完成前工作台显示旧版，相关预留暂停出票"
        ),
    }
    detail = {key: value for key, value in receipt.items()}
    receipt["batch_detail"] = detail
    receipt["batch"] = row["batch_key"] if row["batch_key"] is not None else row["id"]
    receipt["correction_id"] = row["id"]
    receipt["correction_batch_id"] = row["id"]
    receipt["weather_correction_id"] = row["id"]
    receipt["weather_correction_batch_id"] = row["id"]
    receipt["batchId"] = row["id"]
    receipt["batch_no"] = row["batch_key"] or str(row["id"])
    return receipt


def find_batch(cx, identifier, *, for_update=False):
    clause = "id=%s"
    value: Any = identifier
    if isinstance(identifier, str) and not identifier.isdigit():
        clause = "batch_key=%s"
    elif isinstance(identifier, str):
        value = int(identifier)
    sql = f"SELECT * FROM correction_batches WHERE {clause}"
    if for_update:
        sql += " FOR UPDATE"
    return cx.execute(sql, (value,)).fetchone()


def get_batch(cx, identifier):
    row = find_batch(cx, identifier)
    return _receipt(cx, row)


def list_batches(cx, limit=50):
    rows = cx.execute(
        "SELECT * FROM correction_batches ORDER BY id DESC LIMIT %s", (max(1, min(limit, 200)),)
    ).fetchall()
    return [_receipt(cx, row) for row in rows]


def submit(cx, data, actor="operator", idempotency_key=None):
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    corrections, key = parse_corrections(data, idempotency_key)

    if key:
        existing = cx.execute(
            "SELECT * FROM correction_batches WHERE batch_key=%s FOR UPDATE", (key,)
        ).fetchone()
        if existing:
            if existing["corrections"] != corrections:
                raise HTTPException(409, "同一批次标识已用于不同的订正内容")
            return _receipt(cx, existing, reused=True)

    correction_from = min(date.fromisoformat(item["on_day"]) for item in corrections)
    target_rows = cx.execute(
        """
        SELECT r.code, r.percentile, r.neighbors
          FROM analog_replays r
          JOIN practice_holds h ON h.code = r.code
         WHERE h.on_day >= %s
           AND h.state = 'held'
           AND NOT EXISTS (SELECT 1 FROM adjustment_vouchers v WHERE v.hold = h.code)
         ORDER BY r.code
        """,
        (correction_from,),
    ).fetchall()
    targets = [
        {"code": row["code"], "percentile": row["percentile"], "neighbors": row["neighbors"]}
        for row in target_rows
    ]

    batch = cx.execute(
        """
        INSERT INTO correction_batches
            (batch_key, status, correction_from, corrections, target_codes, created_by)
        VALUES (%s, 'queued', %s, %s, %s, %s)
        RETURNING *
        """,
        (key, correction_from, Jsonb(corrections), Jsonb(targets), actor),
    ).fetchone()

    job_id = enqueue(cx, KIND, {
        "batch_id": batch["id"],
        "batch_key": key,
        "corrections": corrections,
        "targets": targets,
    })
    cx.execute("UPDATE correction_batches SET job_id=%s WHERE id=%s", (job_id, batch["id"]))

    for item in corrections:
        cx.execute(
            """
            INSERT INTO weather_corrections
                (batch_id,batch_key,on_day,half_from,temp_c,humidity,source)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """,
            (batch["id"], key, item["on_day"], item["half_from"],
             item["temp_c"], item["humidity"], item["source"]),
        )

    row = cx.execute("SELECT * FROM correction_batches WHERE id=%s", (batch["id"],)).fetchone()
    return _receipt(cx, row)


def active_pause(cx, on_day):
    return cx.execute(
        """
        SELECT id,batch_key,status
          FROM correction_batches
         WHERE status = ANY(%s)
           AND correction_from <= %s
         ORDER BY id
         LIMIT 1
        """,
        (list(ACTIVE_STATES), on_day),
    ).fetchone()


def assert_ticketing_allowed(cx, hold):
    paused = active_pause(cx, hold["on_day"])
    if paused:
        label = paused["batch_key"] or f"#{paused['id']}"
        state_label = {
            "queued": "排队中", "running": "重算中", "failed": "失败待原批重试"
        }.get(paused["status"], paused["status"])
        raise HTTPException(
            409,
            f"该预留涉及的气象订正批次 {label} 当前{state_label}；订正切换前暂停出票，旧版仍在工作台显示",
        )


def retry_batch(cx, identifier):
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    row = find_batch(cx, identifier, for_update=True)
    if row is None:
        raise HTTPException(404, "没有这条订正批次")

    if row["status"] == "published":
        return _receipt(cx, row, reused=True,
                        message="原批已发布，未重复发布；气象与回放仍为该次一次性切换的版本")
    if row["status"] in ("queued", "running"):
        return _receipt(cx, row, reused=True, message="原批仍在队列中，未另建发布批次")

    job_id = row["job_id"]
    if job_id:
        cx.execute(
            """
            UPDATE app_jobs
               SET status='queued', error=NULL, result=NULL,
                   available_at=now(), finished_at=NULL
             WHERE id=%s
            """,
            (job_id,),
        )
    else:
        job_id = enqueue(cx, KIND, {
            "batch_id": row["id"],
            "batch_key": row["batch_key"],
            "corrections": row["corrections"],
            "targets": row["target_codes"],
        })

    cx.execute(
        """
        UPDATE correction_batches
           SET status='queued', error=NULL, job_id=%s,
               updated_at=now(), published_at=NULL
         WHERE id=%s
        """,
        (job_id, row["id"]),
    )
    fresh = find_batch(cx, row["id"])
    return _receipt(cx, fresh, retried=True, message="已按原批重新排队，仍将整批重算并一次性切换")


def mark_failed(cx, payload, error):
    batch_id = (payload or {}).get("batch_id")
    batch_key = (payload or {}).get("batch_key")
    if batch_id is None and not batch_key:
        return
    if batch_id is not None:
        cx.execute(
            "UPDATE correction_batches SET status='failed',error=%s,updated_at=now() WHERE id=%s",
            (error, batch_id),
        )
    else:
        cx.execute(
            "UPDATE correction_batches SET status='failed',error=%s,updated_at=now() WHERE batch_key=%s",
            (error, batch_key),
        )


# Descriptive aliases for callers/tests using issue-domain vocabulary.
create_correction_batch = submit
queue_correction = submit
create_batch = submit
retry_correction_batch = retry_batch
get_correction_batch = get_batch
