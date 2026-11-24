from math import ceil

def nearest(reference,days,starting,ending,k):
    # The two hours start record provides two half-hour temperatures and humidities.
    blocks=range(starting-2,starting)
    required=range(starting-2,ending)
    result=[]
    for day,measurements in days.items():
        if any(h not in measurements for h in required):
            continue
        distance=sum(abs(reference[h]["temp_c"]-measurements[h]["temp_c"])+
                     abs(reference[h]["humidity"]-measurements[h]["humidity"])/10 for h in blocks)
        result.append((distance,day,measurements))
    return sorted(result,key=lambda row:(row[0],row[1]))[:k]

def percentile_upper(values,frac):
    return round(sorted(values)[max(0,ceil(len(values)*frac)-1)],2)
