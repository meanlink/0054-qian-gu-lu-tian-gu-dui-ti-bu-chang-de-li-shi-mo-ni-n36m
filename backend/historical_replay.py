from statistics import mean
from fastapi import HTTPException
from analog_dates import nearest,percentile_upper

# Fixed archival supervisor aid, not a live exposure or personal limit.
ARCHIVE_CUTOFF=35

def play(holds,days,k,q):
    first,last=holds["from_block"],holds["to_block"]
    key=holds["on_day"]
    pilot=days.get(key,{})
    if first<2 or any(h not in pilot for h in range(first-2,first)):
        raise HTTPException(409,"目标日缺少演前连续两段气象窗，须转人工查档")
    history={day:records for day,records in days.items() if day<key}
    selected=nearest(pilot,history,first,last,k)
    if len(selected)<k:
        raise HTTPException(409,"没有足够连续的相似日")
    window=[]
    for half in range(first,last):
        value=percentile_upper([r[half]["temp_c"] for _,_,r in selected],q)
        window.append({"half":half,"value":value,"backup":value>=ARCHIVE_CUTOFF})
    errors=[]
    same_or_higher=[]
    targets=sorted(history)[-3:]
    for day in targets:
        value=history[day]
        # A pseudo-prediction uses only records strictly before its test date.
        if any(h not in value for h in range(first-2,last)):
            continue
        prev={d:record for d,record in history.items() if d<day}
        trials=nearest(value,prev,first,last,k)
        if len(trials)<k:
            continue
        for half in range(first,last):
            pred=percentile_upper([r[half]["temp_c"] for _,_,r in trials],q)
            errors.append(abs(pred-value[half]["temp_c"]))
            same_or_higher.append(pred>=value[half]["temp_c"])
    backtest={"comparison_blocks":len(errors),"mae":round(mean(errors),3) if errors else None,
              "exceeded_or_equal_rate":round(mean(same_or_higher),3) if errors else None}
    return {"window":window,"backtest":backtest,"analogs":[str(day) for _,day,_ in selected]}
