from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from core import db,require,enqueue
router=APIRouter(prefix="/scenarios")
class Replay(BaseModel):
    hold:str
    percentile:float=Field(ge=.5,le=.99)
    neighbors:int=Field(ge=2,le=10)
@router.get("")
def register(_=Depends(require())):
    with db() as cx:
        return cx.execute("SELECT * FROM analog_replays ORDER BY code").fetchall()
@router.post("")
def work(data:Replay,_=Depends(require("operator","reviewer"))):
    with db() as cx:
        return {"job_id":enqueue(cx,"rehearsal-history",data.model_dump())}
