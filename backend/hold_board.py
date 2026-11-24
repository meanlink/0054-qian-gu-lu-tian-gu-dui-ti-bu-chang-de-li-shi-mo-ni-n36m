def context(cx):
    return {"venues":cx.execute("SELECT * FROM rehearsal_venues ORDER BY code").fetchall(),
            "holds":cx.execute("SELECT * FROM practice_holds ORDER BY on_day,code").fetchall()}
