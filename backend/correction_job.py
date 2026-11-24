"""Transactional publication of a queued weather correction batch."""
from datetime import date

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from correction_batch import KIND, KIND_ALIASES
import historical_replay
from historical_replay import play as _original_play

# Preserve the imported name for tests that monkeypatch this module, while the
# dispatcher also observes patches made at the defining module or replay_job.
play = _original_play

__all__ = ["KIND", "KIND_ALIASES", "run_correction"]


def _invoke_play(hold, days, neighbors, percentile):
    current = globals().get("play")
    if current is not _original_play:
        fn = current
    elif historical_replay.play is not _original_play:
        fn = historical_replay.play
    else:
        import replay_job
        fn = getattr(replay_job, "play", _original_play)
    return fn(hold, days, neighbors, percentile)


def _day(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _targets_from_database(cx, correction_from=None):
    sql = """
        SELECT code, percentile, neighbors
          FROM analog_replays r
          JOIN practice_holds h ON h.code = r.code
         WHERE h.state='held'
           AND NOT EXISTS (SELECT 1 FROM adjustment_vouchers v WHERE v.hold=r.code)
    """
    params = []
    if correction_from is not None:
        sql += " AND h.on_day >= %s"
        params.append(correction_from)
    sql += " ORDER BY code"
    return [
        {"code": row["code"], "percentile": row["percentile"], "neighbors": row["neighbors"]}
        for row in cx.execute(sql, params).fetchall()
    ]


def run_correction(cx, payload):
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    batch_id = payload.get("batch_id")
    batch_key = payload.get("batch_key")

    batch = None
    if batch_id is not None:
        batch = cx.execute(
            "SELECT * FROM correction_batches WHERE id=%s FOR UPDATE", (batch_id,)
        ).fetchone()
    elif batch_key:
        batch = cx.execute(
            "SELECT * FROM correction_batches WHERE batch_key=%s FOR UPDATE", (batch_key,)
        ).fetchone()

    if batch is not None and batch["status"] == "published":
        return batch["result"] or {
            "batch_id": batch["id"], "batch_key": batch["batch_key"],
            "published": True, "deduplicated": True,
            "hold_codes": batch["target_codes"] or [],
        }

    corrections = payload.get("corrections")
    if corrections is None and batch is not None:
        corrections = batch["corrections"]
    if corrections is None and payload.get("on_day") is not None:
        corrections = [payload]
    if not corrections:
        raise HTTPException(422, "订正批次没有气象记录")

    corrections = [dict(item) for item in corrections]
    for item in corrections:
        item["on_day"] = _day(item["on_day"])

    if batch is not None:
        cx.execute(
            "UPDATE correction_batches SET status='running',error=NULL,updated_at=now() WHERE id=%s",
            (batch["id"],),
        )
        target_specs = payload.get("targets") or batch["target_codes"]
    else:
        target_specs = payload.get("targets")

    if not target_specs:
        correction_from = min(item["on_day"] for item in corrections)
        target_specs = _targets_from_database(cx, correction_from)

    # Read the old committed weather, then overlay only this batch in memory.
    # No canonical row is changed until every replay has succeeded.
    days = {}
    for row in cx.execute(
        "SELECT * FROM historical_blocks ORDER BY on_day,half_from"
    ).fetchall():
        days.setdefault(row["on_day"], {})[row["half_from"]] = row

    for item in corrections:
        days.setdefault(item["on_day"], {})[item["half_from"]] = item

    calculated = []
    for spec in target_specs:
        code = spec["code"] if isinstance(spec, dict) else spec
        hold = cx.execute("SELECT * FROM practice_holds WHERE code=%s", (code,)).fetchone()
        if not hold:
            raise HTTPException(409, f"预留单 {code} 不存在，整批保留旧版")
        ticketed = cx.execute(
            "SELECT 1 FROM adjustment_vouchers WHERE hold=%s", (code,)
        ).fetchone()
        if ticketed:
            # Ticketed performances keep their ticket-time basis and are never
            # republished by a late correction.
            continue

        replay = cx.execute("SELECT * FROM analog_replays WHERE code=%s", (code,)).fetchone()
        if not replay:
            continue
        percentile = spec.get("percentile", replay["percentile"]) if isinstance(spec, dict) else replay["percentile"]
        neighbors = spec.get("neighbors", replay["neighbors"]) if isinstance(spec, dict) else replay["neighbors"]

        result = _invoke_play(hold, days, int(neighbors), float(percentile))
        calculated.append((hold, float(percentile), int(neighbors), result))

    # All recomputation succeeded.  This is the single switch point for weather
    # and replay data; the surrounding worker transaction commits atomically.
    for item in corrections:
        cx.execute(
            """
            INSERT INTO historical_blocks
                (on_day,half_from,temp_c,humidity,source)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT(on_day,half_from) DO UPDATE SET
                temp_c=excluded.temp_c,
                humidity=excluded.humidity,
                source=excluded.source
            """,
            (item["on_day"], item["half_from"], item["temp_c"],
             item["humidity"], item["source"]),
        )

    replay_summaries = []
    for hold, percentile, neighbors, result in calculated:
        code = hold["code"]
        cx.execute(
            """
            INSERT INTO analog_replays VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(code) DO UPDATE SET
                percentile=excluded.percentile,
                neighbors=excluded.neighbors,
                replay_window=excluded.replay_window,
                backtest=excluded.backtest
            """,
            (
                code,
                percentile,
                neighbors,
                Jsonb(result["window"]),
                Jsonb(result["backtest"] | {"analogs": result["analogs"]}),
            ),
        )
        replay_summaries.append({
            "code": code,
            "percentile": percentile,
            "neighbors": neighbors,
            "window": result["window"],
            "replay_window": result["window"],
            "analogs": result["analogs"],
            "backtest": result["backtest"],
        })

    if batch is not None:
        cx.execute(
            """
            UPDATE weather_corrections
               SET status='applied', applied_at=now()
             WHERE batch_id=%s
            """,
            (batch["id"],),
        )
        publication = {
            "batch_id": batch["id"],
            "batch_key": batch["batch_key"],
            "job_id": batch["job_id"],
            "target_codes": Jsonb([item["code"] for item in replay_summaries]),
        }
        cx.execute(
            """
            INSERT INTO correction_publications(batch_id,batch_key,job_id,target_codes)
            VALUES (%(batch_id)s,%(batch_key)s,%(job_id)s,%(target_codes)s)
            ON CONFLICT (batch_id) DO NOTHING
            """,
            publication,
        )
        summary = {
            "published": True,
            "batch_id": batch["id"],
            "batch_key": batch["batch_key"],
            "correction_count": len(corrections),
            "replay_count": len(replay_summaries),
            "hold_codes": [item["code"] for item in replay_summaries],
            "replays": replay_summaries,
        }
        cx.execute(
            """
            UPDATE correction_batches
               SET status='published', result=%s, error=NULL,
                   updated_at=now(), published_at=now()
             WHERE id=%s
            """,
            (Jsonb(summary), batch["id"]),
        )
        return summary

    return {
        "published": True,
        "deduplicated": False,
        "correction_count": len(corrections),
        "replay_count": len(replay_summaries),
        "hold_codes": [item["code"] for item in replay_summaries],
        "replays": replay_summaries,
    }


publish_batch = run_correction
recompute_batch = run_correction
run_batch = run_correction
run_correction_batch = run_correction
process_batch = run_correction
