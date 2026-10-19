import collections, pathlib, json
from datetime import datetime, timezone
base = pathlib.Path(r"C:\Users\nicoc\OneDrive\Documentos\DataNT8")
CS = ("GC 12-25","GC 02-26","GC 04-26","GC 06-26","GC 08-26")
DST_i = int(datetime(2026,3,8,8,0,tzinfo=timezone.utc).timestamp())
DST_o = int(datetime(2025,11,2,7,0,tzinfo=timezone.utc).timestamp())
def sesion(s):
    t = int(datetime(int(s[0:4]),int(s[4:6]),int(s[6:8]),int(s[9:11]),int(s[11:13]),int(s[13:15]),tzinfo=timezone.utc).timestamp())
    off = -5*3600 if (t < DST_o or t >= DST_i) else -6*3600
    return datetime.fromtimestamp(t+off+7*3600, tz=timezone.utc).strftime("%Y%m%d")
vol = {}
for c in CS:
    d = collections.Counter()
    with open(base/f"{c}.Last.txt", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = ln.split(";")
            if len(p) >= 5: d[sesion(p[0])] += int(p[4])
    vol[c] = d; print("  %s: %d sesiones  %s -> %s" % (c,len(d),min(d),max(d)), flush=True)
fechas = sorted({f for c in CS for f in vol[c] if f <= "20260630"})
front = CS[0]; conf = 0; asign = {}; rolls = []
for f in fechas:
    v = {c: vol[c].get(f,0) for c in CS}
    if max(v.values()) < 5000: continue
    i = CS.index(front)
    if i+1 < len(CS):
        suc = CS[i+1]
        if v[suc] > v[front]:
            conf += 1
            if conf >= 2:
                rolls.append({"desde":front,"hacia":suc,"efectivo":f,
                    "vol_pred":v[front],"vol_suc":v[suc],"razon":round(v[suc]/max(v[front],1),1)})
                front = suc; conf = 0
        else: conf = 0
    asign[f] = front
print("\n  ROLLS (regla congelada: 2 confirmaciones -> efectivo la sesion siguiente):")
for r in rolls:
    print("    %s  %s -> %s   vol %s vs %s  (%.0fx)" % (r["efectivo"],r["desde"].split()[1],r["hacia"].split()[1],
          f'{r["vol_pred"]:,}', f'{r["vol_suc"]:,}', r["razon"]))
print("\n  CADENA:")
tot=0
for c in CS:
    ds = sorted(k for k,v in asign.items() if v==c)
    if ds: print("    %-10s %3d sesiones   %s -> %s"%(c,len(ds),ds[0],ds[-1])); tot+=len(ds)
print("    %-10s %3d"%("TOTAL",tot))
r0 = rolls[0]["efectivo"] if rolls else None
n_rb = sum(1 for f in asign if f >= r0) if r0 else 0
print("\n  ARRANQUE RULE-BASED: primer roll determinado por la regla = %s"%r0)
print("    cadena desde ese roll (100%% rule-based): %d sesiones"%n_rb)
print("    cadena completa incluyendo 12-25 pre-roll : %d sesiones"%tot)
json.dump({"rolls":rolls,"asignacion":asign,"n_total":tot,"n_rule_based":n_rb,"primer_roll":r0},
    open(r"C:\ProyectosQuant\EdgeLab\docs\research\CADENA_FRONTMONTH_GC.json","w",encoding="utf-8"),indent=2,ensure_ascii=False)
