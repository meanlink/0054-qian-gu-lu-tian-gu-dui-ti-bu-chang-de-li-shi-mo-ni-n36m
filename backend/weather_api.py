from fastapi import APIRouter,Depends
from historical_log import Block,add
from core import db,require
router=APIRouter(prefix="/weather")
@router.get("")
def all_weather(_=Depends(require())):
    with db() as cx:
        return cx.execute("SELECT * FROM historical_blocks ORDER BY on_day DESC,half_from").fetchall()
@router.post("")
def put(data:Block,_=Depends(require("operator","reviewer"))):
    with db() as cx:
        return add(cx,data)
