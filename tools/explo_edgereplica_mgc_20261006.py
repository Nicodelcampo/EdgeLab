"""Exploración (decisión de Nico 2026-10-06, sin custodia de holdout): EdgeReplica en MNQ 12-26 y celda MGC 04:15
desde la publicación (2026-09-11) hasta hoy, con ticks de NT8 (E:\\DatosNT8\\tick_history_explo_20261006).

Semántica espejo de EdgeReplica.cs (barras de 1 min, sello = cierre, Calculate=OnBarClose):
- b1 = barra que abre en HHMM (CT); señal = signo(close b1 − close de la última barra con cierre <= cierre_b1 − 15 min).
- La entrada se envía al cierre de b2 (HHMM+2) y se llena en la apertura de la barra siguiente; HOLD cuenta desde
  HHMM+2; la salida se envía en la primera barra con cierre >= envío + HOLD y se llena en la apertura siguiente.
- Una entrada en sentido contrario cierra las posiciones lógicas opuestas al mismo precio (libro neto de NT8).
- Sólo se permite la regla si quedan >= HOLD minutos hasta el fin de sesión 16:00 CT.
Costos: 1 tick de slippage por lado + comisión USD 1,90 por ida y vuelta (micro).
"""
import glob, os, json
import numpy as np, pandas as pd

ROOT = r"E:\DatosNT8\tick_history_explo_20261006"
CT = "America/Chicago"
RULES = [(1,4,115,1,15,-1),(2,4,1015,-1,15,1),(3,1,445,1,30,-1),(4,1,1700,-1,60,0),(5,2,1030,1,30,-1),(6,4,400,1,30,-1),
 (7,1,1715,-1,30,-1),(8,1,145,1,60,0),(9,4,100,1,30,0),(10,4,815,-1,30,0),(11,5,1500,-1,30,0),(12,3,1830,1,60,0),
 (13,4,745,-1,60,1),(14,2,730,-1,15,1),(15,1,200,1,60,0),(16,0,1445,1,60,-1),(17,3,915,1,15,1),(18,4,1445,1,60,-1),
 (19,5,330,-1,15,0),(20,1,1730,-1,60,-1),(21,1,130,1,60,1),(22,0,45,1,60,1),(23,3,1845,1,60,-1),(24,2,2215,1,60,-1),
 (25,1,700,1,60,0),(26,3,1145,1,15,0),(27,0,1145,1,60,1),(28,3,1945,1,60,-1),(29,2,2030,1,15,-1),(30,1,230,1,15,-1),
 (31,1,715,1,60,1),(32,4,645,-1,15,1),(33,1,1430,1,30,1),(34,0,1345,-1,60,1),(35,2,1830,1,15,0),(36,3,1900,1,60,0),
 (37,4,1330,-1,60,1),(38,2,1230,1,30,1),(39,1,730,1,30,-1),(40,1,1415,1,60,-1),(41,4,800,-1,30,0),(42,5,1145,1,60,1),
 (43,1,415,1,15,1),(44,3,1315,1,30,-1),(45,1,215,1,30,0),(46,1,645,-1,15,1),(47,2,1745,1,60,0),(48,5,1515,-1,15,0),
 (49,2,2145,-1,15,-1),(50,3,600,1,15,1),(51,1,630,-1,30,1),(52,4,2230,-1,15,1),(53,4,2330,-1,30,-1),(54,5,315,-1,30,1),
 (55,5,1300,-1,60,1),(56,4,30,1,60,0),(57,0,1300,-1,15,1),(58,5,430,1,15,-1),(59,2,1800,1,60,1),(60,5,445,-1,30,-1)]


def minute_bars(contract):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, contract, "*.Last.utc.txt"))):
        d = pd.read_csv(f, sep=";", header=None, names=["t", "last", "bid", "ask", "vol"], usecols=[0, 1])
        ts = pd.to_datetime(d.t.str[:15], format="%Y%m%d %H%M%S", utc=True) + pd.to_timedelta(d.t.str[16:].astype(np.int64) * 100, unit="ns")
        close_t = ts.dt.ceil("min")                              # NT8: tick exactamente en :00 cierra esa barra
        g = pd.DataFrame({"c": close_t, "p": d["last"].astype(float)}).groupby("c")["p"]
        out.append(pd.DataFrame({"open": g.first(), "close": g.last()}))
    b = pd.concat(out)
    b = b[~b.index.duplicated()].sort_index()
    b.index = b.index.tz_convert(CT)
    return b


def session_of(t):
    return (t + pd.Timedelta(hours=7)).date()                    # sesión CME 17:00-16:00 CT -> fecha de cierre


def run_edgereplica(b, tick=0.25, usd_pt=2.0, comm=1.90):
    times = b.index; idx = {t: i for i, t in enumerate(times)}
    closes = b.close.to_numpy(); opens = b.open.to_numpy()
    sched = {}
    for r in RULES: sched.setdefault(r[2], []).append(r)
    pos, pend, sub, trades, fired = {}, [], [], [], set()
    for i, now in enumerate(times):
        if i == 0: continue
        # 1) fills al open de esta barra
        for kind, r, sig in sub:
            px = opens[i]
            if kind == "x":
                p = pos.pop(r[0], None)
                if p: trades.append(dict(rule=r[0], dir=r[3], entry_t=p["t"], entry=p["px"], exit_t=now, exit=px - r[3] * tick))
            else:
                for rid in [k for k, p in pos.items() if p["r"][3] != r[3]]:
                    p = pos.pop(rid)
                    trades.append(dict(rule=rid, dir=p["r"][3], entry_t=p["t"], entry=p["px"], exit_t=now, exit=px - p["r"][3] * tick, netted=True))
                pos[r[0]] = dict(r=r, px=px + r[3] * tick, t=now, sub=sig)
        sub = []
        # 2) salidas por HOLD
        for rid, p in list(pos.items()):
            if now >= p["sub"] + pd.Timedelta(minutes=p["r"][4]): sub.append(("x", p["r"], None))
        # 3) entradas pendientes
        for r in pend: sub.append(("e", r, now))
        pend = []
        # 4) señales
        local = now - pd.Timedelta(minutes=1)
        if local.weekday() >= 5: continue
        hm = local.hour * 100 + local.minute
        for r in sched.get(hm, []):
            if r[1] != 0 and r[1] != local.isoweekday(): continue
            key = (r[0], local.date())
            if key in fired: continue
            j = times.searchsorted(now - pd.Timedelta(minutes=15), side="right") - 1
            has = j >= 0 and j < i
            sign = int(np.sign(closes[i] - closes[j])) if has else 0
            send = pd.Timestamp(session_of(now), tz=CT) + pd.Timedelta(hours=16)
            if (send - now).total_seconds() / 60 >= r[4] and (r[5] == 0 or (has and sign == r[5])):
                pend.append(r); fired.add(key)
    t = pd.DataFrame(trades)
    t["pts"] = (t.exit - t.entry) * t.dir
    t["usd"] = t.pts * usd_pt - comm
    return t


def run_gold(b, tick=0.10, usd_pt=10.0, comm=1.90, slot=(4, 15), hold=15, cond=True):
    rows = []
    for day, g in b.groupby(b.index.date):
        if pd.Timestamp(day).weekday() >= 5: continue
        base = pd.Timestamp(day, tz=CT) + pd.Timedelta(hours=slot[0], minutes=slot[1])
        def at(t):                                               # barra con cierre exacto t
            return g.loc[t] if t in g.index else None
        b1 = at(base + pd.Timedelta(minutes=1)); ref = g[g.index <= base + pd.Timedelta(minutes=1 - 15)]
        if b1 is None or ref.empty: continue
        up = b1.close - ref.close.iloc[-1] > 0
        if cond and not up: continue
        after_e = g[g.index > base + pd.Timedelta(minutes=2)]; after_x = g[g.index > base + pd.Timedelta(minutes=2 + hold)]
        if after_e.empty or after_x.empty: continue
        e = after_e.open.iloc[0] - tick; x = after_x.open.iloc[0] + tick          # corto
        pts = e - x
        rows.append(dict(day=str(day), entry_t=after_e.index[0], exit_t=after_x.index[0], pts=pts, usd=pts * usd_pt - comm))
    return pd.DataFrame(rows)


def boot(t, col, key, n=20000, seed=20261006):
    s = t.groupby(key)[col].agg(["sum", "size"])
    rng = np.random.default_rng(seed); k = len(s)
    ii = rng.integers(0, k, (n, k))
    m = s["sum"].to_numpy()[ii].sum(1) / s["size"].to_numpy()[ii].sum(1)
    return [round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3)]


def summ(t, key, cut):
    res = {}
    for nm, sub in (("11sep-30sep", t[t[key] < cut]), ("01oct-06oct", t[t[key] >= cut]), ("total", t)):
        if sub.empty: res[nm] = None; continue
        res[nm] = dict(trades=len(sub), sesiones=int(sub[key].nunique()), usd_total=round(float(sub.usd.sum()), 2),
                       usd_por_op=round(float(sub.usd.mean()), 2), pts_por_op=round(float(sub.pts.mean()), 3),
                       ic95_usd_por_op=boot(sub, "usd", key), pct_ganadoras=round(float((sub.usd > 0).mean() * 100), 1))
    return res


if __name__ == "__main__":
    out = {}
    mnq = minute_bars("MNQ_12-26")
    t = run_edgereplica(mnq); t["ses"] = t.entry_t.map(lambda x: str(session_of(x)))
    t = t[t.ses >= "2026-09-11"]
    out["EdgeReplica_MNQ"] = summ(t, "ses", "2026-10-01")
    out["EdgeReplica_MNQ_por_dia"] = t.groupby("ses").usd.sum().round(2).to_dict()
    t.to_csv(os.path.join(ROOT, "edgereplica_mnq_trades.csv"), index=False)
    del mnq
    mgc = minute_bars("MGC_12-26")
    for nm, c in (("MGC_0415_corto_tras_subida", True), ("MGC_0415_corto_sin_condicion", False)):
        g = run_gold(mgc, cond=c); g["ses"] = g.day
        out[nm] = summ(g, "ses", "2026-10-01")
        if c: out["MGC_0415_operaciones"] = g[["day", "pts", "usd"]].round(2).to_dict("records")
    print(json.dumps(out, indent=1, default=str))
    json.dump(out, open(os.path.join(ROOT, "RESULTADOS_EXPLO_20261006.json"), "w"), indent=1, default=str)
