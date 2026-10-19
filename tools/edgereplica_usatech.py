"""EdgeReplica (60 reglas) sobre USATECH CFD Dukascopy M1 bid/ask. Pre-registro: docs/research/edgereplica_usatech/PREREG.md.
Uso: python tools/edgereplica_usatech.py RUTA_M1.parquet [salida.json]"""
import json, sys
import numpy as np, pandas as pd

CT = "America/Chicago"
from pathlib import Path
RULES = json.loads((Path(__file__).resolve().parents[1] / "docs/research/edgereplica_usatech/rules_v1.json").read_text())["rules"]
STALE = pd.Timedelta(minutes=5)


def load(path):
    d = pd.read_parquet(path)
    t = pd.to_datetime(d.time_utc_ns, unit="ns", utc=True) + pd.Timedelta(minutes=1)   # sello = cierre de la vela (convención NT8)
    b = pd.DataFrame({"open": (d.bid_open.values + d.ask_open.values) / 2, "close": (d.bid_close.values + d.ask_close.values) / 2,
                      "bo": d.bid_open.values, "ao": d.ask_open.values}, index=t).sort_index()
    b = b[~b.index.duplicated()]
    b.index = b.index.tz_convert(CT)
    return b


def session_of(t):
    return (t + pd.Timedelta(hours=7)).date()


def run(b, slip=0.0):
    times = b.index; closes = b.close.to_numpy(); bo = b.bo.to_numpy(); ao = b.ao.to_numpy()
    sched = {}
    for r in RULES: sched.setdefault(r[2], []).append(r)
    pos, pend, sub, trades, fired = {}, [], [], [], set()
    skipped = {"stale_ref": 0, "late_fill": 0}
    for i, now in enumerate(times):
        if i == 0: continue
        for kind, r, sig in sub:
            if now - sig > STALE + pd.Timedelta(minutes=1):          # barra de fill demasiado lejos del envío
                skipped["late_fill"] += 1
                if kind == "x": pos.pop(r[0], None)
                continue
            if kind == "x":
                p = pos.pop(r[0], None)
                if p:
                    px = bo[i] if r[3] == 1 else ao[i]
                    trades.append(dict(rule=r[0], dir=r[3], entry_t=p["t"], entry=p["px"], exit_t=now, exit=px))
            else:
                for rid in [k for k, p in pos.items() if p["r"][3] != r[3]]:
                    p = pos.pop(rid); px = bo[i] if p["r"][3] == 1 else ao[i]
                    trades.append(dict(rule=rid, dir=p["r"][3], entry_t=p["t"], entry=p["px"], exit_t=now, exit=px, netted=True))
                pos[r[0]] = dict(r=r, px=ao[i] if r[3] == 1 else bo[i], t=now, sub=sig)
        sub = []
        for rid, p in list(pos.items()):
            if now >= p["sub"] + pd.Timedelta(minutes=p["r"][4]): sub.append(("x", p["r"], now))
        for r in pend: sub.append(("e", r, now))
        pend = []
        local = now - pd.Timedelta(minutes=1)
        if local.weekday() >= 5: continue
        hm = local.hour * 100 + local.minute
        for r in sched.get(hm, []):
            if r[1] != 0 and r[1] != local.isoweekday(): continue
            key = (r[0], local.date())
            if key in fired: continue
            j = times.searchsorted(now - pd.Timedelta(minutes=15), side="right") - 1
            has = 0 <= j < i
            if has and (now - pd.Timedelta(minutes=15)) - times[j] > STALE:
                skipped["stale_ref"] += 1; has = False
                if r[5] != 0: continue
            sign = int(np.sign(closes[i] - closes[j])) if has else 0
            send = pd.Timestamp(session_of(now), tz=CT) + pd.Timedelta(hours=16)
            if (send - now).total_seconds() / 60 >= r[4] and (r[5] == 0 or (has and sign == r[5])):
                pend.append(r); fired.add(key)
    t = pd.DataFrame(trades)
    t["pts"] = (t.exit - t.entry) * t.dir - slip
    t["ses"] = t.entry_t.map(lambda x: str(session_of(x)))
    return t, skipped


def boot(t, col="pts", key="ses", n=20000, seed=20261018):
    s = t.groupby(key)[col].agg(["sum", "size"]); rng = np.random.default_rng(seed); k = len(s)
    ii = rng.integers(0, k, (n, k)); m = s["sum"].to_numpy()[ii].sum(1) / s["size"].to_numpy()[ii].sum(1)
    return [round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3)]


def summ(t):
    if t.empty: return None
    return dict(ops=len(t), ses=int(t.ses.nunique()), pts_op=round(float(t.pts.mean()), 3), ic95=boot(t),
                pct_gan=round(float((t.pts > 0).mean() * 100), 1), pts_total=round(float(t.pts.sum()), 1))


if __name__ == "__main__":
    b = load(sys.argv[1]); out = {}
    for nm, slip in (("primaria_spread_real", 0.0), ("sensib_slip_1pt", 1.0)):
        t, sk = run(b, slip)
        t = t[t.ses <= "2026-09-30"]
        out[nm] = {"total": summ(t), "pre_pub(<=2026-09-10)": summ(t[t.ses <= "2026-09-10"]), "post_pub": summ(t[t.ses > "2026-09-10"]),
                   "por_ano": {y: summ(g) for y, g in t.groupby(t.ses.str[:4])}, "descartes": sk,
                   "largos": summ(t[t.dir == 1]), "cortos": summ(t[t.dir == -1])}
        if slip == 0.0:
            t0 = t
            out["spread_medio_pts"] = round(float(((b.ao - b.bo)).median()), 3)
            out["por_regla_top_bottom"] = None
            pr = t.groupby("rule").pts.agg(["size", "mean"]).round(2)
            out["reglas_pos"] = int((pr["mean"] > 0).sum()); out["reglas_n"] = int(len(pr))
            out["por_dia_post"] = t[t.ses > "2026-09-10"].groupby("ses").pts.sum().round(1).to_dict()
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else "/dev/stdout", "w"), indent=1, default=str)
