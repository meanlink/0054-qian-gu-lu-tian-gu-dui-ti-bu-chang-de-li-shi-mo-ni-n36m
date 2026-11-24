from fastapi import APIRouter, Depends, Request, HTTPException

from correction_batch import (
    get_batch,
    list_batches,
    retry_batch,
    submit,
)
from core import db, require

router = APIRouter(prefix="/weather")


@router.get("")
def all_weather(_=Depends(require())):
    with db() as cx:
        return cx.execute(
            "SELECT * FROM historical_blocks ORDER BY on_day DESC,half_from"
        ).fetchall()


async def _body(request: Request):
    try:
        return await request.json()
    except Exception as exc:
        raise HTTPException(422, "请提交合法的 JSON 气象订正") from exc


def _idem_key(request: Request):
    return (
        request.headers.get("Idempotency-Key")
        or request.headers.get("X-Idempotency-Key")
        or request.query_params.get("idempotency_key")
        or request.query_params.get("batch_key")
        or request.query_params.get("key")
    )


@router.post("")
async def put(request: Request, user=Depends(require("operator", "reviewer"))):
    data = await _body(request)
    with db() as cx:
        return submit(cx, data, user["email"], _idem_key(request))


@router.post("/retry")
@router.post("/retry-batch")
async def retry_named_batch(request: Request, _user=Depends(require("operator", "reviewer"))):
    try:
        body = await request.json()
    except Exception:
        body = {}
    identifier = body.get("batch_id") or body.get("id") or body.get("batch_key") or body.get("key")
    if identifier is None:
        raise HTTPException(422, "请提供要重试的原批编号")
    with db() as cx:
        return retry_batch(cx, str(identifier))


@router.get("/corrections")
def corrections(_=Depends(require())):
    with db() as cx:
        return list_batches(cx)


@router.post("/corrections")
async def create_correction(request: Request, user=Depends(require("operator", "reviewer"))):
    data = await _body(request)
    with db() as cx:
        return submit(cx, data, user["email"], _idem_key(request))


@router.post("/corrections/batch")
async def create_nested_correction_batch(request: Request, user=Depends(require("operator", "reviewer"))):
    return await create_correction(request, user)


@router.post("/batch")
async def create_weather_batch(request: Request, user=Depends(require("operator", "reviewer"))):
    return await put(request, user)


@router.get("/corrections/{identifier}")
def correction_status(identifier: str, _=Depends(require())):
    with db() as cx:
        return get_batch(cx, identifier)


@router.post("/corrections/{identifier}/retry")
@router.put("/corrections/{identifier}/retry")
def correction_retry(identifier: str, _user=Depends(require("operator", "reviewer"))):
    with db() as cx:
        return retry_batch(cx, identifier)


# Expose the same batch resource under the two natural /weather names.
@router.get("/batches")
def batches(_=Depends(require())):
    with db() as cx:
        return list_batches(cx)


@router.post("/batches")
async def create_batch(request: Request, user=Depends(require("operator", "reviewer"))):
    data = await _body(request)
    with db() as cx:
        return submit(cx, data, user["email"], _idem_key(request))


@router.get("/batches/{identifier}")
def batch_status(identifier: str, _=Depends(require())):
    with db() as cx:
        return get_batch(cx, identifier)


@router.post("/batches/{identifier}/retry")
@router.put("/batches/{identifier}/retry")
def batch_retry(identifier: str, _user=Depends(require("operator", "reviewer"))):
    with db() as cx:
        return retry_batch(cx, identifier)
