#!/usr/bin/env python3
r"""Estudio paramétrico de efectos por franja horaria (CT) con nulo de signos y Holm. La configuración llega por STUDY_CFG (JSON) y debe figurar TEXTUALMENTE en el pre-registro
(el autopilot lo verifica antes de lanzar). Modos:
  idm        retorno «resto del día» (cierre previo 15:00 CT → 14:30 CT) vs última media hora (14:30 → 15:00 CT); corr; unilateral positiva (momentum). Opcional: diferencia de corr con gamma bajo (DIX/GEX, causal) en la fuente `gamma_source`.
  idm_jump   descompone el «resto del día» (cierre previo 15:00 CT → 14:30 CT) en componente de SALTOS (retornos de 5 min con |r| > 4σ, σ = 1,4826·mediana(|r|) de las 20 sesiones previas, causal) y el resto continuo;
             OLS LH ~ 1 + ROD_salto + ROD_cont; prueba unilateral b_salto > 0 con nulo de signo sobre LH; `reference_sources` se informan pero NO entran en Holm.
  slot_scan  barrido de franjas por familia (descubrimiento → réplica): celdas = franja de 30 min (07:00-14:30 CT) × horizonte h ∈ {15,30,60} × predictor ∈ {retorno de los h min previos, «resto del día» desde el cierre previo 15:00 CT};
             estadístico corr(predictor, retorno de los h min siguientes), BILATERAL (momentum +, reversión −). Descubrimiento: nulo de MÁXIMO por permutación conjunta de sesiones (misma permutación en todas las celdas); réplica: las 3 mejores celdas del
             descubrimiento, con el signo fijado, unilateral, nulo de signo. El descubrimiento usa `disc` (spot largo o 60 % inicial de los futuros) y la réplica `rep` (futuros 2025-26 o 40 % final).
  strategy_pnl  evalúa REGLAS OPERABLES fijas (entrada y salida por reloj, 1 operación/día, dirección = signo del predictor) con P&L NETO de costos en USD por contrato, por muestra (descubrimiento / fuera de muestra / descriptivas):
             media neta por operación, desvío, aciertos, P&L por trimestre, parte de los 5 mejores días, resistencia a costos × 1,5, frecuencia, drawdown; prueba confirmatoria SOLO en la muestra fuera de muestra (nulo de dirección aleatoria por operación,
             unilateral; p = 1 si la media neta ≤ 0). Guarda el P&L diario para simular challenges (control sin ventaja incluido) fuera del kernel.
  slot_corr  corr(r previo, r siguiente) de `horizon_min` minutos en cada franja de `slots`; unilateral negativa (reversión).
Fuentes: futuros por load_m1 (2025-07-01→2026-09-30) o spot Dukascopy (spot_ranges). Precio = apertura del minuto indicado. Sin holdout.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    OUT = Path("/kaggle/working")
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docs/data_catalog"))
    OUT = Path(os.environ.get("STUDY_OUT", "/tmp/study_out"))
OUT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("EDGELAB_ALLOW_MISSING", "1")
SYNTH = os.environ.get("STUDY_SYNTH") == "1"
if not SYNTH:
    import edgelab_data as ed  # noqa: E402

CFG = json.loads(os.environ["STUDY_CFG"]) if "STUDY_CFG" in os.environ else {}
CT = "America/Chicago"
SEED = int(CFG.get("seed", 20261013))
NPERM = int(os.environ.get("STUDY_NPERM", CFG.get("nperm", 20000)))
BLOCK = 20


def load_source(name):
    if SYNTH:
        return synth_jump(CFG.get("synth_jump_effect", 0.0)) if CFG.get("mode") in ("idm_jump", "slot_scan", "strategy_pnl") else synth(CFG.get("synth_gamma_effect", 0.0))
    if name in CFG.get("spot_ranges", {}):
        inst, a, b = CFG["spot_ranges"][name]
        t = ed.load_spot(inst, a, b, "m1"); mid = ((t.bid_open + t.ask_open) / 2).to_numpy()
        return pd.DataFrame(dict(ts=t.time_utc_ns.to_numpy(), open=mid))
    m = ed.load_m1(name, *CFG.get("futures_range", ["2025-07-01", "2026-09-30"])); k = float(m.attrs["tick_size"])
    return pd.DataFrame(dict(ts=m.minute.to_numpy(), open=m.open.to_numpy() * k))


def synth(gamma_effect=0.0, n_days=600, seed=3):
    """RW intradiaria; si gamma_effect>0, en días de «gamma bajo» (de a bloques) el último 30 min sigue al resto del día."""
    rng = np.random.default_rng(seed); rows = []; d0 = pd.Timestamp("2018-01-02")
    for d in range(n_days):
        day = d0 + pd.Timedelta(days=d)
        if day.dayofweek >= 5: continue
        low = (d // 40) % 3 == 0
        r = rng.standard_normal(24 * 60) * 1e-4
        lp = np.cumsum(r)
        i1430, i1500 = (14 * 60 + 30), 15 * 60                       # minutos desde 00:00 CT del día
        rod = lp[i1430] - lp[0]
        if gamma_effect and low: lp[i1500:] += gamma_effect * rod
        ts = (pd.Timestamp(day, tz=CT) + pd.to_timedelta(np.arange(24 * 60), unit="m")).tz_convert("UTC").tz_localize(None).values.astype("datetime64[ns]").astype("int64")
        rows.append(pd.DataFrame(dict(ts=ts, open=100 * np.exp(lp))))
    return pd.concat(rows, ignore_index=True)


def synth_jump(effect=0.0, n_days=420, seed=5):
    """M1 sintético 24 h: ruido gaussiano + algunos saltos de 5 min; si effect>0, LH sigue al ROD_salto."""
    rng = np.random.default_rng(seed); rows = []; d0 = pd.Timestamp("2022-01-03")
    for d in range(n_days):
        day = d0 + pd.Timedelta(days=d)
        if day.dayofweek >= 5: continue
        r = rng.standard_normal(24 * 60) * 1e-4; jumps = np.zeros(24 * 60)
        for _ in range(rng.integers(0, 3)):
            k = int(rng.integers(0, 14 * 60 + 25)); jumps[k] = rng.choice([-1, 1]) * rng.uniform(15, 40) * 1e-4
        lp = np.cumsum(r + jumps); i1430, i1500 = 870, 900
        lp[i1500:] += effect * jumps[:i1430].sum()
        se = float(CFG.get("synth_slot_effect", 0.0))
        if se: lp[10 * 60 + 30:] += se * (lp[10 * 60] - lp[9 * 60 + 30])           # el tramo 10:30 sigue al tramo 09:30-10:00 (momentum sintético en la celda 10:00_h30_prev)
        ts = (pd.Timestamp(day, tz=CT) + pd.to_timedelta(np.arange(24 * 60), unit="m")).tz_convert("UTC").tz_localize(None).values.astype("datetime64[ns]").astype("int64")
        rows.append(pd.DataFrame(dict(ts=ts, open=100 * np.exp(lp))))
    return pd.concat(rows, ignore_index=True)


def sessions_table(df, times):
    """DataFrame por fecha local CT con el precio (apertura del minuto) en cada hh:mm de `times` ('prev15' = 15:00 de la sesión anterior)."""
    loc = pd.DatetimeIndex(pd.to_datetime(df.ts.to_numpy(), utc=True)).tz_convert(CT)
    mod = loc.hour * 60 + loc.minute; want = {int(t[:2]) * 60 + int(t[3:]): t for t in times}
    sel = np.isin(mod, list(want))
    t = pd.DataFrame(dict(date=loc[sel].strftime("%Y-%m-%d"), hm=[want[m] for m in mod[sel]], p=df.open.to_numpy()[sel]))
    t = t.drop_duplicates(["date", "hm"]).pivot(index="date", columns="hm", values="p").sort_index()
    return t


def holm(ps):
    o = np.argsort(ps); adj = np.empty(len(ps)); mx = 0.0
    for rank, i in enumerate(o):
        mx = max(mx, min(1.0, (len(ps) - rank) * ps[i])); adj[i] = mx
    return adj


def signflip_p(x, y, rng, sign):
    """p unilateral de corr(x,y) con nulo de signo aleatorio sobre y. sign=+1: H1 corr>0; -1: H1 corr<0."""
    c = float(np.corrcoef(x, y)[0, 1]); xs = (x - x.mean()) / x.std(); ys = y - y.mean()
    nul = np.empty(NPERM)
    for i in range(NPERM):
        s = rng.choice([-1.0, 1.0], len(y)); z = ys * s; nul[i] = (xs * (z - z.mean())).mean() / z.std()
    return c, float((1 + np.sum(sign * nul >= sign * c)) / (1 + NPERM)), float(nul.std())


def gamma_labels(dates):
    if SYNTH:
        low = np.array([(i // 40) % 3 == 0 for i in range(len(dates))]); return low
    p = Path("/kaggle/working/dix.csv") if KAGGLE else Path(CFG.get("dix_path", "/tmp/dix.csv"))
    if KAGGLE: urllib.request.urlretrieve("https://squeezemetrics.com/monitor/static/DIX.csv", p)
    g = pd.read_csv(p, dtype={"date": str}).set_index("date").gex.sort_index(); idx, vals = g.index.to_numpy(), g.to_numpy(); low = []
    for d in dates:
        k = int(np.searchsorted(idx, d, side="left"))
        low.append(bool(k >= 251 and vals[k - 1] < np.quantile(vals[:k - 1 + 1], 0.20)) if k >= 251 else np.nan)
    return np.array(low, dtype=object)


def grid5(df):
    """Apertura por rejilla de 5 min en hora local CT (NaN donde no hay mercado)."""
    loc = pd.DatetimeIndex(pd.to_datetime(df.ts.to_numpy(), utc=True)).tz_convert(CT).tz_localize(None)
    return pd.Series(df.open.to_numpy(), index=loc).sort_index().resample("5min").first().dropna()


def jump_table(df):
    """Por fecha local d: ROD, ROD_salto, ROD_cont, LH. Retornos sucesivos entre puntos de rejilla disponibles; una brecha (mantenimiento/fin de semana) cuenta como un retorno."""
    g = grid5(df); lp = np.log(g.to_numpy()); idx = g.index; days = sorted(set(idx.normalize()))
    pos = {d: (np.searchsorted(idx, d + pd.Timedelta(hours=14, minutes=30)), np.searchsorted(idx, d + pd.Timedelta(hours=15))) for d in days}
    rows = []; hist = []                                              # hist: |r| de las sesiones previas
    prev15 = {}
    for d in days:
        a = np.searchsorted(idx, d + pd.Timedelta(hours=15)); prev15[d] = a if a < len(idx) and idx[a] == d + pd.Timedelta(hours=15) else None
    last = None
    for d in days:
        i1430, i1500 = pos[d]
        ok = (i1430 < len(idx) and idx[i1430] == d + pd.Timedelta(hours=14, minutes=30) and i1500 < len(idx) and idx[i1500] == d + pd.Timedelta(hours=15))
        if ok and last is not None:
            r = np.diff(lp[last:i1430 + 1])
            if len(r) >= 20:
                sig = 1.4826 * np.median(np.abs(np.concatenate(hist[-20:]))) if len(hist) >= 5 else np.nan
                if np.isfinite(sig) and sig > 0:
                    jump = np.abs(r) > 4 * sig; rod = float(r.sum()); rj = float(r[jump].sum())
                    rows.append(dict(date=d.strftime("%Y-%m-%d"), rod=rod, rod_jump=rj, rod_cont=rod - rj, lh=float(lp[i1500] - lp[i1430]), has_jump=bool(jump.any())))
                hist.append(np.abs(r))
            else: hist.append(np.abs(r)) if len(r) else None
        if ok: last = i1500
    return pd.DataFrame(rows)


def mode_idm_jump(rng):
    out, ps, rows = [], [], []; refs = set(CFG.get("reference_sources", []))
    for name in CFG["sources"] + list(refs):
        t = jump_table(load_source(name))
        if len(t) < 150: out.append(dict(test=f"idmj/{name}", n=int(len(t)), evaluable=False)); continue
        X = np.c_[np.ones(len(t)), t.rod_jump.to_numpy(), t.rod_cont.to_numpy()]; y = t.lh.to_numpy(); W = np.linalg.pinv(X)
        b = W @ y; wj = W[1]; nul = np.empty(NPERM)
        for i in range(NPERM): nul[i] = wj @ (y * rng.choice([-1.0, 1.0], len(y)))
        p = float((1 + np.sum(nul >= b[1])) / (1 + NPERM)); q = pd.PeriodIndex(pd.to_datetime(t.date), freq="Q").astype(str).to_numpy()
        loo = {}
        for qq in sorted(set(q)):                                        # sin cada trimestre (descriptivo)
            m = q != qq
            if m.sum() > 100: loo[qq] = float((np.linalg.pinv(X[m]) @ y[m])[1])
        r = dict(test=f"idmj/{name}", source=name, n=int(len(t)), share_jump_sessions=float(t.has_jump.mean()), b_jump=float(b[1]), b_cont=float(b[2]), null_sd=float(nul.std()), p=p, evaluable=True,
                 reference_only=name in refs, leave_one_quarter_out_b_jump_min=min(loo.values()) if loo else None, leave_one_quarter_out_b_jump_max=max(loo.values()) if loo else None)
        out.append(r); print(r, flush=True)
        if name not in refs: ps.append(p); rows.append(r)
    return out, ps, rows


SCAN_SLOTS = [f"{m // 60:02d}:{m % 60:02d}" for m in range(7 * 60, 14 * 60 + 31, 30)]; SCAN_H = (15, 30, 60)


def scan_matrices(df):
    """Fechas (n) y matrices X, Y (n × celdas) con X = predictor y Y = retorno siguiente; precio = apertura del minuto, ffill dentro del día; se descartan fechas con datos faltantes."""
    times = [f"{m // 60:02d}:{m % 60:02d}" for m in range(6 * 60, 15 * 60 + 31, 15)] + ["15:00"]
    t = sessions_table(df, sorted(set(times))); t = t.ffill(axis=1); prev = t["15:00"].shift(1)
    ok = t.notna().all(axis=1) & prev.notna(); t, prev = t[ok], prev[ok]
    X, Y, labels = [], [], []
    for sl in SCAN_SLOTS:
        hh, mm = map(int, sl.split(":")); m0 = hh * 60 + mm; lab = lambda m: f"{m // 60:02d}:{m % 60:02d}"
        for h in SCAN_H:
            if m0 + h > 15 * 60 + 30: continue
            nxt = np.log(t[lab(m0 + h)] / t[sl]).to_numpy()
            X.append(np.log(t[sl] / t[lab(m0 - h)]).to_numpy()); Y.append(nxt); labels.append(f"{sl}_h{h}_prev")
            X.append(np.log(t[sl] / prev).to_numpy()); Y.append(nxt); labels.append(f"{sl}_h{h}_rod")
    return list(t.index), np.column_stack(X), np.column_stack(Y), labels


def _std(a):
    return (a - a.mean(0)) / a.std(0)


def mode_slot_scan(rng):
    out, ps, rows, desc = [], [], [], []; B = int(os.environ.get("STUDY_NPERM", CFG.get("nperm", 5000)))
    for sc in CFG["scans"]:
        name = sc["name"]; d_disc, X, Y, labels = scan_matrices(load_source(sc["disc"]))
        if sc["rep"] == sc["disc"] or sc.get("split"):
            k = int(len(d_disc) * float(sc.get("split", 0.6))); d0, X0, Y0, d1, X1, Y1 = d_disc[:k], X[:k], Y[:k], d_disc[k:], X[k:], Y[k:]
        else:
            d0, X0, Y0 = d_disc, X, Y; d1, X1, Y1, lab1 = scan_matrices(load_source(sc["rep"])); assert lab1 == labels
        n0 = len(d0)
        if n0 < 150 or len(d1) < 100: out.append(dict(test=f"scan/{name}/max_disc", evaluable=False, n_disc=n0, n_rep=len(d1))); continue
        Xs, Ys = _std(X0), _std(Y0); c0 = (Xs * Ys).mean(0); z0 = c0 * np.sqrt(n0); obs = float(np.abs(z0).max())
        mx = np.empty(B)
        for i in range(B): mx[i] = np.abs((Xs * Ys[rng.permutation(n0)]).mean(0)).max() * np.sqrt(n0)      # misma permutación en todas las celdas
        p_max = float((1 + np.sum(mx >= obs)) / (1 + B)); top = np.argsort(-np.abs(z0))[:3]
        r = dict(test=f"scan/{name}/max_disc", source=name, n_disc=n0, n_cells=len(labels), max_abs_z=obs, null_q95=float(np.quantile(mx, 0.95)), p=p_max, evaluable=True, disc=f"{sc['disc']} {d0[0]}..{d0[-1]}")
        out.append(r); ps.append(p_max); rows.append(r); print(r, flush=True)
        for j in top:
            sgn = 1.0 if c0[j] > 0 else -1.0; x1, y1 = X1[:, j], Y1[:, j]; c1, p1, sd1 = signflip_p(x1, y1, rng, sgn)
            r2 = dict(test=f"scan/{name}/rep/{labels[j]}", source=name, cell=labels[j], n_rep=int(len(x1)), corr_disc=float(c0[j]), corr_rep=c1, direction="momentum" if sgn > 0 else "reversion", null_sd=sd1, p=p1, evaluable=True, rep=f"{sc['rep']} {d1[0]}..{d1[-1]}")
            out.append(r2); ps.append(p1); rows.append(r2); print(r2, flush=True)
        o = np.argsort(-np.abs(z0))[:10]; desc.append(dict(scan=name, top_cells=[dict(cell=labels[j], corr_disc=float(c0[j]), corr_rep=float(np.corrcoef(X1[:, j], Y1[:, j])[0, 1])) for j in o]))
    CFG["_descriptive"] = desc
    return out, ps, rows


COSTS = {"GC": dict(mult=100.0, cost_rt=24.8), "ES": dict(mult=50.0, cost_rt=30.0), "NQ": dict(mult=20.0, cost_rt=32.0), "YM": dict(mult=5.0, cost_rt=24.0)}     # USD por punto de precio y costo de ida y vuelta por contrato (supuestos de edgelab.autopilot.universe)


def rule_trades(df, rule, inst):
    """Operaciones diarias de una regla: entrada y salida a la apertura del minuto indicado. pred = 'prev_h' (retorno de h min antes de la entrada) o 'rod' (desde el cierre previo 15:00 CT)."""
    em = int(rule["entry"][:2]) * 60 + int(rule["entry"][3:]); xm = em + int(rule["hold_min"]); lab = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    times = {rule["entry"], lab(xm), "15:00"}
    if rule["pred"].startswith("prev_"): times.add(lab(em - int(rule["pred"][5:])))
    t = sessions_table(df, sorted(times)).ffill(axis=1); prev15 = t["15:00"].shift(1)
    pred = np.log(t[rule["entry"]] / (prev15 if rule["pred"] == "rod" else t[lab(em - int(rule["pred"][5:]))]))
    ok = pred.notna() & t[lab(xm)].notna() & t[rule["entry"]].notna(); t, pred = t[ok], pred[ok]; a = np.abs(pred.to_numpy())
    keep = np.ones(len(a), bool)
    if rule.get("filter") == "bigmove_q67":                                     # |pred| ≥ cuantil 2/3 expansivo de las sesiones previas (causal, mínimo 60)
        keep = np.array([len(a[:i]) >= 60 and a[i] >= np.quantile(a[:i], 2 / 3) for i in range(len(a))])
    sgn = np.sign(pred.to_numpy()) * (1.0 if rule["dir"] == "momentum" else -1.0); mult = COSTS[inst]["mult"]
    gross = sgn * (t[lab(xm)].to_numpy() - t[rule["entry"]].to_numpy()) * mult
    return pd.DataFrame(dict(date=t.index[keep], sign=sgn[keep], gross=gross[keep], entry=t[rule["entry"]].to_numpy()[keep]))


def trade_metrics(tr, inst, stress=1.5):
    cost = COSTS[inst]["cost_rt"]; net = tr.gross.to_numpy() - cost; q = pd.PeriodIndex(pd.to_datetime(tr.date), freq="Q").astype(str).to_numpy(); n = len(net)
    qp = {k: float(net[q == k].sum()) for k in sorted(set(q))}; best5 = float(np.sort(net)[::-1][:5].sum() / net.sum()) if net.sum() > 0 else None
    cum = np.cumsum(net); dd = float((np.maximum.accumulate(cum) - cum).max()) if n else 0.0; months = max(1.0, (pd.to_datetime(tr.date.iloc[-1]) - pd.to_datetime(tr.date.iloc[0])).days / 30.4) if n else 1.0
    return dict(n=int(n), mean_net_usd=float(net.mean()) if n else None, sd_usd=float(net.std()) if n else None, hit_rate=float((net > 0).mean()) if n else None, mean_gross_usd=float(tr.gross.mean()) if n else None,
                total_net_usd=float(net.sum()), total_net_cost_x1_5_usd=float((tr.gross - cost * stress).sum()) if n else None, quarterly_net_usd=qp, frac_positive_quarters=float(np.mean([v > 0 for v in qp.values()])) if qp else None,
                best5_days_share_of_pnl=best5, max_drawdown_usd=dd, trades_per_month=float(n / months), first=str(tr.date.iloc[0]) if n else None, last=str(tr.date.iloc[-1]) if n else None)


def mode_strategy_pnl(rng):
    out, ps, rows, desc = [], [], [], []; B = int(os.environ.get("STUDY_NPERM", CFG.get("nperm", 20000))); daily = {}
    for rule in CFG["rules"]:
        inst = rule["inst"]
        for role in ("discovery", "oos", "descriptive"):
            for src in rule.get(role, []):
                tr = rule_trades(load_source(src), rule, inst)
                if len(tr) < 60: out.append(dict(test=f"pnl/{rule['name']}/{role}/{src}", evaluable=False, n=int(len(tr)))); continue
                m = trade_metrics(tr, inst)
                daily[f"{rule['name']}|{role}|{src}"] = dict(date=list(tr.date), gross=[float(x) for x in tr.gross], sign=[float(x) for x in tr.sign])
                r = dict(test=f"pnl/{rule['name']}/{role}/{src}", rule=rule["name"], role=role, source=src, **m, evaluable=role == "oos")
                if role == "oos":                                                  # confirmatoria: media neta > 0 y mayor que la del control de dirección aleatoria
                    g = tr.gross.to_numpy(); cost = COSTS[inst]["cost_rt"]; obs = float((g - cost).mean()); nul = np.empty(B)
                    for i in range(B): nul[i] = float((g * rng.choice([-1.0, 1.0], len(g)) - cost).mean())
                    praw = float((1 + np.sum(nul >= obs)) / (1 + B)); r.update(p_placebo_raw=praw, null_mean_net_usd=float(nul.mean()), null_sd=float(nul.std()), p=praw if obs > 0 else 1.0)
                    ps.append(r["p"]); rows.append(r)
                out.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in ("test", "n", "mean_net_usd", "hit_rate", "p", "frac_positive_quarters", "best5_days_share_of_pnl")}, flush=True)
    CFG["_descriptive"] = dict(daily=daily)
    return out, ps, rows


def block_perm(v, rng):
    blocks = [v[i:i + BLOCK] for i in range(0, len(v), BLOCK)]; return np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])


def mode_idm(rng):
    out, ps, rows = [], [], []
    for name in CFG["sources"]:
        t = sessions_table(load_source(name), ["14:30", "15:00"]); p15 = t["15:00"]; prev = p15.shift(1)
        ok = t["14:30"].notna() & p15.notna() & prev.notna()
        rod, lh = np.log(t["14:30"][ok] / prev[ok]).to_numpy(), np.log(p15[ok] / t["14:30"][ok]).to_numpy()
        if len(rod) < 100: out.append(dict(source=name, n=int(len(rod)), evaluable=False)); continue
        c, p, sd = signflip_p(rod, lh, rng, +1); r = dict(test=f"idm/{name}", source=name, n=int(len(rod)), corr=c, null_sd=sd, p=p, evaluable=True)
        out.append(r); ps.append(p); rows.append(r); print(r, flush=True)
        if name == CFG.get("gamma_source"):
            dates = list(t.index[ok]); low = gamma_labels(dates); good = np.array([x is not np.nan and x == x for x in low]) if low.dtype == object else np.ones(len(low), bool)
            lowb = low[good].astype(bool); a, b = rod[good], lh[good]
            if lowb.sum() >= 30 and (~lowb).sum() >= 30:
                diff = lambda m: np.corrcoef(a[m], b[m])[0, 1] - np.corrcoef(a[~m], b[~m])[0, 1]
                obs = float(diff(lowb)); nul = np.array([diff(block_perm(lowb, rng)) for _ in range(NPERM)])
                pp = float((1 + np.sum(nul >= obs)) / (1 + NPERM))
                r2 = dict(test=f"idm_gamma_diff/{name}", source=name, n_low=int(lowb.sum()), n_high=int((~lowb).sum()), diff=obs, null_sd=float(nul.std()), p=pp, evaluable=True)
                out.append(r2); ps.append(pp); rows.append(r2); print(r2, flush=True)
            else: out.append(dict(test=f"idm_gamma_diff/{name}", evaluable=False, n_low=int(lowb.sum())))
    return out, ps, rows


def mode_slot_corr(rng):
    out, ps, rows = [], [], []; h = int(CFG.get("horizon_min", 15))
    for name in CFG["sources"]:
        df = load_source(name)
        for slot in CFG["slots"]:
            hh, mm = map(int, slot.split(":")); t0 = hh * 60 + mm
            lab = lambda m: f"{(m // 60) % 24:02d}:{m % 60:02d}"
            t = sessions_table(df, [lab(t0 - h), lab(t0), lab(t0 + h)]); ok = t.notna().all(axis=1)
            x = np.log(t[lab(t0)][ok] / t[lab(t0 - h)][ok]).to_numpy(); y = np.log(t[lab(t0 + h)][ok] / t[lab(t0)][ok]).to_numpy()
            if len(x) < 100: out.append(dict(test=f"slot/{name}/{slot}", n=int(len(x)), evaluable=False)); continue
            c, p, sd = signflip_p(x, y, rng, -1); r = dict(test=f"slot/{name}/{slot}", source=name, slot=slot, n=int(len(x)), corr=c, null_sd=sd, p=p, evaluable=True)
            out.append(r); ps.append(p); rows.append(r); print(r, flush=True)
    return out, ps, rows


def main():
    t0 = time.time(); rng = np.random.default_rng(SEED); mode = CFG["mode"]
    out, ps, rows = {"idm": mode_idm, "idm_jump": mode_idm_jump, "slot_corr": mode_slot_corr, "slot_scan": mode_slot_scan, "strategy_pnl": mode_strategy_pnl}[mode](rng)
    m = int(CFG.get("n_planned", len(ps)))
    for r, h in zip(rows, holm(np.array(ps)) if ps else []): r["p_holm_%d" % m] = float(min(1.0, h * 1.0))
    # Holm con m planeado (≥ evaluables): reajusta usando m en el denominador
    o = np.argsort(ps); mx = 0.0
    for rank, i in enumerate(o):
        mx = max(mx, min(1.0, (m - rank) * ps[i])); rows[i]["p_holm_%d" % m] = mx
    res = dict(campaign=CFG.get("campaign", "study_slot_effect"), descriptive=CFG.pop("_descriptive", None), cfg=CFG, nperm=NPERM, results_flat=out, n_planned=m, seconds=round(time.time() - t0))
    (OUT / "STUDY_RESULTS.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print("listo en %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
