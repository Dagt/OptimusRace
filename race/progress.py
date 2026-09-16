import hashlib,json

def comparison_key(test):
    parameters=test.get('parameters',{})
    protocol={key:parameters.get(key) for key in ['metric','duration_seconds','distance_meters','laps','load_mode','load_value','bar_weight','load_step','round_mode','instructions','equipment']}
    data={'name':test['name'],'unit':test['unit'],'higher':test['higher'],'parameters':protocol}
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def comparison_label(test):
    p=test.get('parameters',{});parts=[test['name'],test['unit']]
    if p.get('duration_seconds'):parts.append(f"{p['duration_seconds']:g} s de esfuerzo")
    if p.get('distance_meters'):parts.append(f"{p['distance_meters']:g} m × {p.get('laps') or 1:g}")
    if p.get('load_mode')=='body_percent':parts.append(f"carga {p['load_value']:g}% corporal")
    elif p.get('load_mode')=='fixed':parts.append(f"carga {p['load_value']:g} kg")
    return ' · '.join(parts)
