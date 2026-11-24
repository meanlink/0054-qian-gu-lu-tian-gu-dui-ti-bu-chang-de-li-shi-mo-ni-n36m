from fastapi import APIRouter,Depends
from core import db,require
from voucher_register import Settlement,Voucher,open_ticket,close_ticket
router=APIRouter(prefix="/vouchers")
@router.get("")
def receipts(_=Depends(require())):
    with db() as cx:
        return cx.execute("SELECT v.*,h.on_day,h.title,h.state FROM adjustment_vouchers v JOIN practice_holds h ON h.code=v.hold ORDER BY h.on_day,h.code").fetchall()
@router.post("/{hold}")
def create(hold:str,data:Voucher,u=Depends(require("reviewer"))):
    with db() as cx:
        return open_ticket(cx,hold,data,u["email"])
@router.post("/{hold}/settle")
def close(hold:str,data:Settlement,u=Depends(require("reviewer"))):
    with db() as cx:
        return close_ticket(cx,hold,data.paid_cents,u["email"])
