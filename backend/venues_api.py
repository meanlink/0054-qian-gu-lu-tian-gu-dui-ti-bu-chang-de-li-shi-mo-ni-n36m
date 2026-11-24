from fastapi import APIRouter,Depends
from core import db,require
from hold_board import context
router=APIRouter(prefix="/venues")
@router.get("")
def read(_=Depends(require())):
    with db() as cx:
        return context(cx)
