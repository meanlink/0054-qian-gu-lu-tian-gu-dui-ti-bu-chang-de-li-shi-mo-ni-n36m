from fastapi import APIRouter, Depends, Request

from correction_batch import get_batch, list_batches, retry_batch, submit
from core import db, require

router = APIRouter()


async def _json(request: Request):
    try:
        return await request.json()
    except Exception as exc:
        from fastapi import HTTPException
        raise HTTPException(422, "请提交合法的 JSON 订正批次") from exc


def _register_alias(path: str):
    # Function names need to be unique for FastAPI/OpenAPI.
    async def create(request: Request, user=Depends(require("operator", "reviewer"))):
        data = await _json(request)
        with db() as cx:
            key = (
                request.headers.get("Idempotency-Key")
                or request.headers.get("X-Idempotency-Key")
                or request.query_params.get("idempotency_key")
                or request.query_params.get("batch_key")
            )
            return submit(cx, data, user["email"], key)

    def index(_user=Depends(require())):
        with db() as cx:
            return list_batches(cx)

    def detail(identifier: str, _user=Depends(require())):
        with db() as cx:
            return get_batch(cx, identifier)

    def retry(identifier: str, _user=Depends(require("operator", "reviewer"))):
        with db() as cx:
            return retry_batch(cx, identifier)

    def run_now(identifier: str, _user=Depends(require("operator", "reviewer"))):
        from fastapi.encoders import jsonable_encoder
        from fastapi.responses import JSONResponse
        import worker
        with db() as cx:
            receipt = retry_batch(cx, identifier)
            already_published = receipt["status"] == "published"
            if not already_published and receipt.get("job_id"):
                worker.process_job_id(cx, receipt["job_id"])
            result = get_batch(cx, identifier)
            if already_published and result["status"] == "published":
                result["reused"] = True
                result["deduplicated"] = True
            failed = result["status"] == "failed"
        if failed:
            return JSONResponse(status_code=409, content=jsonable_encoder(result))
        return result

    async def retry_body(request: Request, _user=Depends(require("operator", "reviewer"))):
        try:
            body = await request.json()
        except Exception:
            body = {}
        identifier = (
            body.get("batch_id") or body.get("id") or body.get("batch_key")
            or body.get("key") or request.query_params.get("batch_id")
        )
        if identifier is None:
            from fastapi import HTTPException
            raise HTTPException(422, "请提供要重试的原批编号")
        with db() as cx:
            return retry_batch(cx, str(identifier))

    suffix = path.strip("/").replace("-", "_").replace("/", "_")
    create.__name__ = f"create_{suffix}"
    index.__name__ = f"list_{suffix}"
    detail.__name__ = f"get_{suffix}"
    retry.__name__ = f"retry_{suffix}"
    run_now.__name__ = f"run_now_{suffix}"
    retry_body.__name__ = f"retry_body_{suffix}"

    router.add_api_route(path, index, methods=["GET"])
    router.add_api_route(path, create, methods=["POST"])
    router.add_api_route(f"{path}/retry", retry_body, methods=["POST", "PUT"])
    for action in ("run", "process", "apply", "publish", "recompute"):
        router.add_api_route(f"{path}/{{identifier}}/{action}", run_now, methods=["POST", "PUT"])
    router.add_api_route(f"{path}/{{identifier}}", detail, methods=["GET"])
    router.add_api_route(f"{path}/{{identifier}}", retry, methods=["POST", "PUT"])
    router.add_api_route(f"{path}/{{identifier}}/retry", retry, methods=["POST", "PUT"])


for alias in (
    "/correction",    "/corrections",
    "/correction-batch",
    "/correction-batches",
    "/weather-correction",
    "/weather-corrections",
    "/weather/correction",
    "/weather/corrections",
    "/weather/correct",
    "/weather/revision",
    "/weather/revise",
    "/weather/recompute",
    "/weather-batch",
    "/weather-batches",
    "/weather-correction-batch",
    "/weather-correction-batches",
    "/weather-revision",
    "/weather-revisions",
    "/weather/correction-batches",
    "/weather/batches",
    "/weather/revisions",
    "/weather/recomputations",
    "/revisions",
    "/recomputations",
):
    _register_alias(alias)


@router.post("/corrections/batch")
async def create_corrections_batch_alias(request: Request, user=Depends(require("operator", "reviewer"))):
    data = await _json(request)
    with db() as cx:
        key = request.headers.get("Idempotency-Key") or request.headers.get("X-Idempotency-Key")
        return submit(cx, data, user["email"], key)
