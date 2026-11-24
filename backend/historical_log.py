from datetime import date
from fastapi import HTTPException
from pydantic import BaseModel,Field

class Block(BaseModel):
    on_day:date
    half_from:int=Field(ge=0,le=47)
    temp_c:float=Field(ge=-15,le=55,allow_inf_nan=False)
    humidity:int=Field(ge=0,le=100)
    source:str=Field(min_length=4,max_length=100)

def add(cx,data):
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    used=cx.execute("SELECT 1 FROM practice_holds WHERE on_day>=%s AND state IN ('proposed','closed')",(data.on_day,)).fetchone()
    if used:
        raise HTTPException(409,"先前气象证据已纳入调整票，禁止覆盖")
    cx.execute('''
        INSERT INTO historical_blocks VALUES(%(on_day)s,%(half_from)s,%(temp_c)s,%(humidity)s,%(source)s)
        ON CONFLICT(on_day,half_from) DO UPDATE SET temp_c=excluded.temp_c,humidity=excluded.humidity,source=excluded.source
    ''',data.model_dump())
    cx.execute("DELETE FROM analog_replays r USING practice_holds h WHERE r.code=h.code AND h.on_day>=%s AND h.state='held'",(data.on_day,))
    return {"message":"历史气象已登记，相关回放待重新计算"}
