from fastapi import HTTPException
from psycopg.types.json import Jsonb
from historical_replay import play
from correction_job import KIND_ALIASES as CORRECTION_KINDS, run_correction


def run_job(cx, kind, payload):
    if kind in CORRECTION_KINDS:
        return run_correction(cx, payload)
    if kind != "rehearsal-history":
        raise ValueError(kind)
    cx.execute("SELECT pg_advisory_xact_lock(54020)")
    key = payload["hold"]
    hold = cx.execute("SELECT * FROM practice_holds WHERE code=%s", (key,)).fetchone()
    if not hold or hold["state"] != "held":
        raise HTTPException(409, "只可对待回放的预留时段试算")
    days = {}
    for row in cx.execute("SELECT * FROM historical_blocks WHERE on_day<=%s ORDER BY on_day,half_from", (hold["on_day"],)):
        days.setdefault(row["on_day"], {})[row["half_from"]] = row
    result = play(hold, days, payload["neighbors"], payload["percentile"])
    cx.execute('''
      INSERT INTO analog_replays VALUES(%s,%s,%s,%s,%s)
      ON CONFLICT(code) DO UPDATE SET percentile=excluded.percentile,neighbors=excluded.neighbors,
      replay_window=excluded.replay_window,backtest=excluded.backtest
    ''', (key,payload["percentile"],payload["neighbors"],
            Jsonb(result["window"]),Jsonb(result["backtest"]|{"analogs":result["analogs"]})))
    return result
