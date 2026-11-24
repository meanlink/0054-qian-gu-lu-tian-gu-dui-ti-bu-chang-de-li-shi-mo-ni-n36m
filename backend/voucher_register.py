from fastapi import HTTPException
from pydantic import BaseModel,Field
from rental_tally import charge

class Voucher(BaseModel):
    from_block:int=Field(ge=0,le=47)
    to_block:int=Field(ge=1,le=48)
    memo:str=Field(min_length=4,max_length=160)
class Settlement(BaseModel):
    paid_cents:int=Field(ge=0)

def open_ticket(cx,key,data,actor):
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    hold=cx.execute("SELECT * FROM practice_holds WHERE code=%s",(key,)).fetchone()
    model=cx.execute("SELECT * FROM analog_replays WHERE code=%s",(key,)).fetchone()
    if not hold or hold["state"]!="held" or not model:
        raise HTTPException(409,"等预留登记与回放结果齐备后调整")
    site=cx.execute("SELECT * FROM rehearsal_venues WHERE code=%s",(hold["backup"],)).fetchone()
    total=charge(cx,hold,site,data,model["replay_window"])
    cx.execute('''
      INSERT INTO adjustment_vouchers(hold,from_block,to_block,moved_to,estimate_cents,memo,reviewed_by) VALUES(%s,%s,%s,%s,%s,%s,%s)
    ''',(key,data.from_block,data.to_block,hold["backup"],total,data.memo,actor))
    cx.execute("UPDATE practice_holds SET state='proposed' WHERE code=%s",(key,))
    return {"hold":key,"estimate_cents":total,"state":"proposed"}

def close_ticket(cx,key,paid,actor):
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    row=cx.execute("SELECT * FROM adjustment_vouchers WHERE hold=%s",(key,)).fetchone()
    if not row or row["settled_at"]:
        raise HTTPException(409,"调整票不存在或已锁档")
    if row["estimate_cents"]!=paid:
        raise HTTPException(409,"实收金额须与冻结后的场租一致")
    cx.execute("UPDATE adjustment_vouchers SET settled_by=%s,settled_at=now() WHERE hold=%s",(actor,key))
    cx.execute("UPDATE practice_holds SET state='closed' WHERE code=%s",(key,))
    return {"hold":key,"paid_cents":paid,"state":"closed"}
