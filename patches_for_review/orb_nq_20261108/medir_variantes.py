"""ORB-VARIANTES (2026-11-08, pedido de Nico: «variantes, filtros, distintos RR, diversificación»). Pre-registro:
docs/research/orb_nq_20261108/PREREGISTRO_VARIANTES.md. Reutiliza señales, calendario, noticias y fills de `medir_exploratorio`.

Familia cerrada, sin filtros de día/hora/ATR (no nominaron en ORB-NQ-FILTROS): instrumento (NQ, ES, YM) × caja (5/15/30) × stop
(extremo opuesto O / mitad de caja M) × salida (cierre 15:55 C / objetivo 1R, 2R, 3R con cierre 15:55 si no llega) = 72 reglas, más
las 24 canastas igual ponderadas por sesión entre los tres instrumentos = 96 pruebas.
DESC 2025-08-05 → 2026-03-31: nominación FDR q 0,10 (p por inversión de signo por sesión) con m = 96 + 720 + 705 heredadas.
RÉPLICA 2026-04-01 → 2026-09-30 SÓLO para lo congelado al terminar el DESC: las nominadas y las 3 ORB base de NQ (O, C) pre-registradas.
Sin holdout (el lector corta en la frontera). Objetivo: orden límite; se llena si el last lo atraviesa (estrictamente), sin slippage.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import medir_exploratorio as ME
from senales_orb import disparos
from conciliar_calendario import conciliar

RR = ME.RR
INSTR = {"NQ": (0.25, 5.0), "ES": (0.25, 12.5), "YM": (1.0, 5.0)}   # tick, USD por tick (edgelab/costos.py)
COMISION_USD = 5.76
CAJAS = (5, 15, 30); STOPS = ("O", "M"); SALIDAS = ("C", 1.0, 2.0, 3.0)
DESC = (20250805, 20260331); REP = (20260401, 20260618)   # 2026-11-08: el calendario CME versionado termina el 18/06/2026
B = 10000; SEED = 20261108; Q = .10; M_HEREDADO = 720 + 705; NMIN = 30
BASE_PRE = [("NQ", d, "O", "C") for d in CAJAS]
SERIES = False


def preparar(df, tick):
    """`ME.prep` con el tamaño de tick del instrumento (ME.prep tiene fijo 0,25 de NQ)."""
    df = df.loc[~df.outside_regular].reset_index(drop=True)
    if df.empty or df.trade_date.nunique() != 1 or df.regime_id.nunique() != 1: return None
    if np.any(np.diff(df.ts_utc_ns.to_numpy(np.int64)) < 0): raise ValueError("ticks desordenados")
    df["t"] = (df.ts_utc_ns // ME.MIN + 1) * 60
    m = df.groupby("t", sort=True).agg(h=("price_ticks", "max"), l=("price_ticks", "min"), c=("price_ticks", "last"),
                                       ses=("trade_date", "first"), seg=("regime_id", "first")).reset_index()
    base = ME.midnight(int(df.trade_date.iloc[0]))
    esperado = base // 1_000_000_000 + np.arange(571, 956) * 60
    if not np.isin(esperado, m.t.to_numpy(np.int64)).all(): return None
    if not ((df.ts_utc_ns >= base + 955 * ME.MIN) & (df.ts_utc_ns < base + 960 * ME.MIN)).any(): return None
    ctx = {k: m[k].to_numpy(np.int64) for k in ("t", "ses", "seg")}
    ctx.update({k: m[k].to_numpy(float) * tick for k in ("h", "l", "c")})
    s = disparos(ctx)
    if len(s): s["signal_ns"] = m.t.to_numpy(np.int64)[s.k.to_numpy(np.int64)] * 1_000_000_000
    return df, s


def llenar(t, last, bid, ask, senal, cierre, limite, lado, stop, slip, tick, com_pts, objetivo_r):
    """Como `ME.fill` (entrada en bid/ask + slippage, stop por last) con objetivo opcional en múltiplos del riesgo inicial."""
    i = int(np.searchsorted(t, senal, side="right"))
    if i >= len(t) or t[i] >= cierre: return None
    entrada = (ask[i] if lado == 1 else bid[i]) * tick + lado * slip * tick
    riesgo = lado * (entrada - stop)
    if riesgo <= 0: return None
    fin = int(np.searchsorted(t, limite, side="left")); tt = t[i + 1:fin]; lp = last[i + 1:fin] * tick
    tp = entrada + lado * objetivo_r * riesgo if objetivo_r else None
    cond = (tt >= cierre) | (lado * (lp - stop) <= 0)
    if tp is not None: cond |= lado * (lp - tp) > 0
    h = np.flatnonzero(cond)
    if not len(h): raise ValueError("posición sin salida durante sesión")
    j = i + 1 + int(h[0])
    if tp is not None and t[j] < cierre and lado * (last[j] * tick - tp) > 0 and lado * (last[j] * tick - stop) > 0:
        salida = tp                                                            # límite atravesado: se llena al precio límite
    else:
        salida = (bid[j] if lado == 1 else ask[j]) * tick - lado * slip * tick
    return (lado * (salida - entrada) - com_pts) / riesgo


def operaciones(root, inst, d0, d1, files, allowed, events):
    tick, usd_tick = INSTR[inst]; com_pts = COMISION_USD / (usd_tick / tick)
    pf = pq.ParquetFile(files[inst].path); ix = pf.schema_arrow.names.index("trade_date"); por_dia = {}
    for g in RR.select_row_groups(pf, d0, d1):
        st = pf.metadata.row_group(g).column(ix).statistics
        if int(st.min) != int(st.max): raise RR.ReleaseStop("row group mezcla sesiones")
        por_dia.setdefault(int(st.min), []).append(g)
    cols = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "trade_date", "regime_id", "outside_regular"]; filas = []
    for dia, gs in sorted(por_dia.items()):
        if dia not in allowed: continue
        raw = pf.read_row_groups(gs, columns=cols).to_pandas()
        if (raw.trade_date != dia).any() or (raw.ts_utc_ns >= RR.HOLDOUT_FIRST_TS_NS).any(): raise RR.ReleaseStop("fecha o timestamp no permitido")
        p = preparar(raw, tick)
        if p is None: continue
        tk, senales = p; base = ME.midnight(dia); cierre = base + 955 * ME.MIN; lim = base + 960 * ME.MIN
        t = tk.ts_utc_ns.to_numpy(np.int64); last = tk.price_ticks.to_numpy(float); bid = tk.bid_ticks.to_numpy(float); ask = tk.ask_ticks.to_numpy(float)
        for s in senales.itertuples():
            if ME.blocked(s.signal_ns, cierre, events): continue
            for sp in STOPS:
                stop = (s.lo if s.lado == 1 else s.hi) if sp == "O" else (s.lo + s.hi) / 2.0
                for sa in SALIDAS:
                    obj = None if sa == "C" else sa
                    a = llenar(t, last, bid, ask, s.signal_ns, cierre, lim, int(s.lado), stop, 1, tick, com_pts, obj)
                    z = llenar(t, last, bid, ask, s.signal_ns, cierre, lim, int(s.lado), stop, 2, tick, com_pts, obj)
                    if a is None or z is None: continue
                    filas.append(dict(ses=dia, inst=inst, caja=int(s.duracion), stop=sp, salida=str(sa), r=a, r_adv=z))
    return pd.DataFrame(filas)


def resumir(O):
    reglas = {}
    for k, g in O.groupby(["inst", "caja", "stop", "salida"]):
        reglas[k] = g
    for (c, s, sa), g in O.groupby(["caja", "stop", "salida"]):                   # canasta igual ponderada entre instrumentos
        pi = g.groupby(["ses", "inst"]).r.mean().unstack()
        reglas[("CANASTA", c, s, sa)] = pd.DataFrame(dict(ses=pi.index, r=pi.mean(1).to_numpy(), r_adv=np.nan))
    return reglas


def evaluar(reglas, dias, seed):
    rng = np.random.default_rng(seed); S = rng.choice((-1., 1.), size=(B, len(dias))); pos = {d: i for i, d in enumerate(dias)}
    res = {}
    for k, g in reglas.items():
        x = g.groupby("ses").r.sum(); idx = np.array([pos[d] for d in x.index]); v = x.to_numpy(float)
        n = len(g); mu = float(g.r.mean()); T = v.sum() / np.sqrt((v * v).sum()) if (v * v).sum() > 0 else np.nan
        p = float((1 + ((S[:, idx] * v).sum(1) / np.sqrt((v * v).sum()) >= T).sum()) / (B + 1)) if np.isfinite(T) else 1.0
        res[k] = dict(n=n, sesiones=len(v), media_r=mu, media_r_adv=float(g.r_adv.mean()) if g.r_adv.notna().any() else None,
                      p=p, evaluable=bool(n >= NMIN and np.isfinite(T)))
    return res


def bh(res, m_total):
    ev = sorted([(v["p"], k) for k, v in res.items() if v["evaluable"]]); nom = set()
    for r, (p, k) in enumerate(ev, 1):
        if p <= Q * r / m_total: nom = {kk for _, kk in ev[:r]}
    return nom


def run(root, out=Path("/kaggle/working")):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    if RR.sha256_file(root / "release_manifest.json") != ME.H or RR.sha256_file(ME.CAL) != ME.CAL_SHA or RR.sha256_file(ME.NEWS) != ME.NEWS_SHA:
        raise RR.ReleaseStop("SHA distinto")
    files = RR.load_manifest(root, verify_hash=True, purpose="research")
    cal = json.loads(ME.CAL.read_text())["sessions"]
    news = pd.read_csv(ME.NEWS); events = pd.to_datetime(news.ts_utc, utc=True).dt.as_unit("ns").astype("int64").to_numpy()
    def permitidas(inst, d0, d1):
        meta = pd.read_parquet(root / "metadata/session_index.parquet", filters=[("instrument", "==", inst), ("trade_date", ">=", d0), ("trade_date", "<=", d1)])
        rec = conciliar(cal, json.loads(meta[["trade_date", "prev_trade_date", "status"]].to_json(orient="records")), d0, d1)
        return {x["trade_date"] for x in rec["filas"] if x["clase_cme"] == "NORMAL" and x["revision"] == "ANTERIOR_COINCIDE"}
    # ---- DESC
    O = pd.concat([operaciones(root, i, *DESC, files, permitidas(i, *DESC), events) for i in INSTR], ignore_index=True)
    reglas = resumir(O); dias = np.sort(O.ses.unique()); res = evaluar(reglas, dias, SEED)
    m_total = len(res) + M_HEREDADO; nom = bh(res, m_total)
    congeladas = sorted(set(nom) | {k for k in reglas if k in BASE_PRE}, key=str)
    (out / "ORB_VARIANTES_CONGELADAS.json").write_text(json.dumps([list(map(str, k)) for k in congeladas]))   # antes de la réplica
    desc = {"|".join(map(str, k)): dict(v, nomina=k in nom) for k, v in res.items()}
    base = dict(estado="EXPLORATORIO_DESC_Y_REPLICA_CONGELADA", m_total=m_total, q=Q, reglas_desc=len(res), nominadas=len(nom),
                congeladas=["|".join(map(str, k)) for k in congeladas], desc=desc)
    (out / "ORB_VARIANTES_DESC.json").write_text(json.dumps(base, indent=1, default=float))
    if SERIES:                                                          # 2026-11-08: series diarias por regla (CANASTA-ORB)
        ser = {"|".join(map(str, k)): g.groupby("ses").r.sum().round(6).to_dict() for k, g in resumir(O).items()}
        (out / "ORB_SERIES_DESC.json").write_text(json.dumps({k: {str(d): v for d, v in x.items()} for k, x in ser.items()}))   # 2026-11-08: el DESC no se pierde si falla la réplica
    # ---- RÉPLICA sólo para lo congelado (por instrumento; un error queda registrado con su traza)
    import traceback
    partes, errores = [], {}
    for i in INSTR:
        try: partes.append(operaciones(root, i, *REP, files, permitidas(i, *REP), events))
        except Exception as e: errores[i] = traceback.format_exc()[-1500:]
    Or = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=["ses", "inst", "caja", "stop", "salida", "r", "r_adv"])
    rr = resumir(Or) if len(Or) else {}; rr = {k: v for k, v in rr.items() if k in set(congeladas)}
    rep = {"|".join(map(str, k)): v for k, v in evaluar(rr, np.sort(Or.ses.unique()), SEED + 1).items()} if rr else {}
    (out / "ORB_VARIANTES_RESULTADOS.json").write_text(json.dumps(dict(base, replica=rep, errores_replica=errores), indent=1, default=float))
    print("ORB_VARIANTES_COMPLETA", len(res), len(nom), flush=True)


if __name__ == "__main__":
    import glob, os
    run(Path(os.environ.get("RELEASE_DIR") or Path(sorted(glob.glob("/kaggle/input/**/release_manifest.json", recursive=True))[0]).parent))
