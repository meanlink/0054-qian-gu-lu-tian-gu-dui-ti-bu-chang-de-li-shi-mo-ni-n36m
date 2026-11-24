def context(cx):
    venues = cx.execute("SELECT * FROM rehearsal_venues ORDER BY code").fetchall()
    holds = cx.execute("SELECT * FROM practice_holds ORDER BY on_day,code").fetchall()
    batches = cx.execute(
        """SELECT id,batch_key,status,correction_from
             FROM correction_batches
            WHERE status IN ('queued','running','failed')
            ORDER BY id"""
    ).fetchall()

    paused_codes = []
    for hold in holds:
        batch = next((b for b in batches if b["correction_from"] <= hold["on_day"]), None)
        hold["ticketing_paused"] = batch is not None
        if batch:
            hold["pause_batch_id"] = batch["id"]
            hold["pause_batch_key"] = batch["batch_key"]
            hold["pause_status"] = batch["status"]
            hold["pause_reason"] = "气象订正批次处理中，暂停出票"
            paused_codes.append(hold["code"])
        else:
            hold["pause_batch_id"] = None
            hold["pause_batch_key"] = None
            hold["pause_status"] = None
            hold["pause_reason"] = None

    return {
        "venues": venues,
        "holds": holds,
        "active_corrections": batches,
        "paused_codes": paused_codes,
    }
