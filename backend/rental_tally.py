from fastapi import HTTPException

def charge(cx,hold,backup,data,window):
    if not backup["covered"] or hold["heads"]>backup["max_heads"]:
        raise HTTPException(409,"替补场地的遮蔽或人数容量不满足")
    interval=range(data.from_block,data.to_block)
    values={r["half"] for r in window if r["backup"]}
    if not interval or not values or not set(interval)<=values:
        raise HTTPException(409,"调整票须位于回放达到替场口径的时窗")
    if cx.execute('''
      SELECT 1 FROM adjustment_vouchers a JOIN practice_holds h ON h.code=a.hold
      WHERE h.on_day=%s AND a.moved_to=%s AND a.from_block<%s AND a.to_block>%s
    ''',(hold["on_day"],backup["code"],data.to_block,data.from_block)).fetchone():
        raise HTTPException(409,"替补场地在同日存在重叠票据")
    return len(interval)*backup["rate_per_half"]
