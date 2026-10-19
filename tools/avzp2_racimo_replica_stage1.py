#!/usr/bin/env python3
r"""AVZP2-RACIMO-GRILLA etapa 1 (36 definiciones de racimo) (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md): desenlaces desde la formación del racimo, real vs pseudo apareado por ocupación.
Por contrato (env AVCL_CONTRACTS, separados por coma): ticks -> barras 50t -> footprint NT8 -> run_full (parámetros
congelados de VOL-1). Guarda en /kaggle/working: <c>_bars.npz, <c>_blocks.parquet, <c>_zones.parquet."""
from __future__ import annotations

import dataclasses
import gc
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists()
HOLDOUT_FIRST_TRADE_DATE = 20261001
HOLDOUT_FIRST_TS_NS = 1_790_805_600_000_000_000        # 2026-09-30T22:00:00Z: apertura CME de la sesión del 2026-10-01
if KAGGLE:                                              # kernel de Kaggle: código del dataset edgelab-code-avcl-fast + release como dataset
    OUT = Path(os.environ.get("AVCL_OUT", "/kaggle/working"))
    _inp = Path("/kaggle/input")
    _code = next((p.parent.parent for r in [_inp, *_inp.glob("datasets/*")] for p in r.glob("edgelab-code-avcl-fast/**/edgelab/__init__.py")), None)
    if _code is None:
        raise RuntimeError("STOP: no se encontró el dataset de código edgelab-code-avcl-fast")
    sys.path.insert(0, str(_code))
    _rel = os.environ.get("RELEASE_DIR")
    RELEASE = Path(_rel) if _rel else next((p.parent for p in sorted(_inp.rglob("release_manifest.json"))), None)
    if RELEASE is None:
        raise RuntimeError("STOP: no se encontró release_manifest.json en /kaggle/input")
else:                                                   # local: repo + release descargada de Kaggle
    RELEASE = Path(os.environ.get("RELEASE_DIR", r"D:\edgelab_release_work\dl_check"))
    OUT = Path(os.environ.get("AVCL_OUT", "D:/edgelab_release_work/avzp2_replica_v3"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT.mkdir(parents=True, exist_ok=True)
from scipy.stats import norm  # noqa: E402
from edgelab.bridge import bars as B  # noqa: E402
from edgelab.bridge import ticks as T  # noqa: E402
from edgelab.bridge.sessions import session_end_ns  # noqa: E402
import hashlib  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402


def preflight_footer(pf):
    """COPIA de edgelab.data.liquid_release.release_reader.preflight_footer (un test verifica que se comportan igual).
    STOP de custodia ANTES de leer cualquier payload: ambos relojes en TODOS los row groups; sin estadísticas, con nulls o con
    fecha/timestamp reservados se detiene."""
    names = pf.schema_arrow.names
    cols = {}
    for col in ("trade_date", "ts_utc_ns"):
        if col not in names:
            raise RuntimeError(f"STOP: el archivo no tiene columna {col}")
        cols[col] = names.index(col)
    for g in range(pf.metadata.num_row_groups):
        rg = pf.metadata.row_group(g)
        for col, ci in cols.items():
            st = rg.column(ci).statistics
            if st is None or not st.has_min_max:
                raise RuntimeError(f"STOP: row group {g} sin estadísticas de {col}")
            if st.null_count:
                raise RuntimeError(f"STOP: row group {g} con nulls en {col}")
            limit = HOLDOUT_FIRST_TRADE_DATE if col == "trade_date" else HOLDOUT_FIRST_TS_NS
            if int(st.max) >= limit:
                raise RuntimeError(f"STOP: row group {g} contiene {col} reservado (max {int(st.max)} >= {limit})")


def read_asset(release_dir, asset, start_trade_date, end_trade_date, *, columns=None, verify_hash=True, purpose=None):
    """Lector mínimo equivalente al de la release: manifiesto, ruta relativa, tamaño, SHA-256, preflight de footers y sólo los row
    groups pedidos por trade_date (STOP si un grupo cruza el borde del rango). `purpose` obligatorio y distinto de 'research'."""
    if purpose not in ("audit", "provisional_research"):
        raise RuntimeError("STOP: declarar purpose='audit' o 'provisional_research' (research exige aprobación externa de Nico)")
    root = Path(release_dir)
    man = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    if man.get("schema") != "edgelab_liquid_release_v1":
        raise RuntimeError("STOP: esquema de manifiesto desconocido")
    if end_trade_date >= HOLDOUT_FIRST_TRADE_DATE:
        raise RuntimeError("STOP: el rango pedido alcanza el holdout")
    e = man["assets"][asset]
    rel = e["file"]
    if os.path.isabs(rel) or ".." in Path(rel).parts:
        raise RuntimeError("STOP: ruta del manifiesto no relativa")
    f = root / rel
    if f.stat().st_size != int(e["bytes"]):
        raise RuntimeError("STOP: tamaño distinto al del manifiesto")
    if verify_hash:
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            while True:
                b = fh.read(16 << 20)
                if not b:
                    break
                h.update(b)
        if h.hexdigest() != e["sha256"]:
            raise RuntimeError("STOP: SHA-256 distinto al del manifiesto")
    pf = pq.ParquetFile(f)
    preflight_footer(pf)
    ci = pf.schema_arrow.names.index("trade_date")
    keep = []
    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(ci).statistics
        lo, hi = int(st.min), int(st.max)
        if hi < start_trade_date or lo > end_trade_date:
            continue
        if lo < start_trade_date or hi > end_trade_date:
            raise RuntimeError("STOP: row group cruza el borde del rango pedido")
        keep.append(g)
    return pf.read_row_groups(keep, columns=columns) if keep else pf.schema_arrow.empty_table().select(columns)

END_NS = pd.Timestamp("2026-09-30 22:00", tz="UTC").value
CT = "America/Chicago"
INST = os.environ.get("AVCL_INST", "ES")
TICK_SIZE = {"ES": 0.25, "NQ": 0.25, "MES": 0.25, "MNQ": 0.25}[INST]
WARMUP_SESSIONS = 20
TICKS_BAR = 50


def ct_minute_of_day(ts_ns):
    """Minuto del día en hora de Chicago; convierte una vez por minuto único (mismo resultado que por tick)."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    um, inv = np.unique(ts // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT)
    return np.asarray(c.hour * 60 + c.minute)[inv]


def session_end_vec(end_ns):
    """Igual que session_end_ns(int(x)) por barra (verificado en 200.000 instantes 2025-06 → 2026-09): próximo cierre
    16:00 CT lun-vie estrictamente posterior."""
    end = np.asarray(end_ns, dtype=np.int64)
    d0 = pd.Timestamp(int(end.min()), tz="UTC").tz_convert(CT).normalize() - pd.Timedelta(days=1)
    d1 = pd.Timestamp(int(end.max()), tz="UTC").tz_convert(CT).normalize() + pd.Timedelta(days=8)
    days = pd.date_range(d0.tz_localize(None), d1.tz_localize(None), freq="D")
    days = days[days.weekday < 5]
    closes = np.sort((days + pd.Timedelta(hours=16)).tz_localize(CT).tz_convert("UTC").asi8)
    return closes[np.searchsorted(closes, end, side="right")]


def load_contract(c):
    """Ticks del contrato c desde la release (sólo sus sesiones seleccionadas) sin la pausa CME 16:00-17:00 CT."""
    si = pd.read_parquet(RELEASE / "metadata" / "session_index.parquet")
    d_ = si[(si.instrument == INST) & (si.contract == c) & (si.status == "SELECTED")].trade_date
    t = read_asset(RELEASE, INST, int(d_.min()), int(d_.max()), verify_hash=os.environ.get("VERIFY_HASH", "1") == "1", purpose="provisional_research",
                   columns=["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "contract", "trade_date"])
    import pyarrow.compute as pc
    m = pc.equal(t.column("contract").cast("string"), c).to_numpy(zero_copy_only=False)
    ts = t.column("ts_utc_ns").to_numpy()[m]; px = t.column("price_ticks").to_numpy()[m]; vol = t.column("volume").to_numpy()[m]
    bid = t.column("bid_ticks").to_numpy(zero_copy_only=False)[m]; ask = t.column("ask_ticks").to_numpy(zero_copy_only=False)[m]
    td = t.column("trade_date").to_numpy()[m]
    del t
    o = np.argsort(ts, kind="stable") if len(ts) > 1 and (np.diff(ts) < 0).any() else None
    if o is not None:
        ts, px, vol, bid, ask, td = ts[o], px[o], vol[o], bid[o], ask[o], td[o]
    mod = ct_minute_of_day(ts)
    keep = ~((mod >= 960) & (mod < 1020))
    ts, px, vol, bid, ask, td = ts[keep], px[keep], vol[keep], bid[keep], ask[keep], td[keep]
    tk = T.TickSeries(ts_ns=ts, price_ticks=px.astype(np.int64), volume=vol.astype(np.int64),
                      bid_ticks=np.nan_to_num(bid.astype(float), nan=-1).astype(np.int64),
                      ask_ticks=np.nan_to_num(ask.astype(float), nan=1 << 40).astype(np.int64), sequence=np.arange(len(ts), dtype=np.int64),
                      tick_size=TICK_SIZE, instrument=INST, contract=c)
    return tk, np.unique(td)


import numba  # noqa: E402
import zlib  # noqa: E402
from edgelab.bridge.indicators.avolzonepoi2 import run as zp2_run, _racimo  # noqa: E402

SPEC = int(os.environ.get("AVCL_SPEC", 25))      # ticks (operaciones) por barra; ES/MNQ 25; NQ-normalizada 3 (manifiesto REPLICA-NQ-BARRA)
ZP2_PARAMS = dict(ob_away_heights=6.0, ob_max_inside_pct=4.0, racimo_min=0, racimo_bars=500, racimo_altura_ticks=30)
CELLS = [(6, 500, 30)] + [(m, 1000, a) for m in (4, 5, 6) for a in (30, 45)]   # congeladas en el manifiesto REPLICA


def pseudo_box(c_b0, dl, dh, tr_real, tr_pseudo):
    """Caja [L, H] de un pseudo-racimo ubicado en una barra con cierre c_b0, copiando los desplazamientos (dl, dh) del racimo real.
    Si las tendencias previas (signo) son opuestas se espeja: [dl, dh] -> [-dh, -dl]. Así la distancia al borde del lado de la tendencia
    del pseudo es igual a la del real (H-03)."""
    if tr_real != 0 and tr_pseudo != 0 and tr_pseudo != tr_real:
        return int(c_b0 - dh), int(c_b0 - dl)
    return int(c_b0 + dl), int(c_b0 + dh)


def racimos_de(zones, m, w, a):
    """Misma regla que _racimo de avolzonepoi2, aplicada a las zonas ya detectadas (las zonas no dependen del racimo)."""
    p = dict(racimo_min=m, racimo_bars=w, racimo_altura_ticks=a)
    zs, clusters = [], []
    for z in zones:
        nz = dict(bar=z["bar"], low_tick=z["low_tick"], high_tick=z["high_tick"], racimo_bar=-1, rac=None)
        _racimo(nz, zs, clusters, z["bar"], p)
        zs.append(nz)
    return clusters
EXIT_MAX, HPOST, TREND, OCC, NPSEUDO = 2000, 200, 500, 500, 5


@numba.njit(cache=True)
def outcomes(hi, lo, cl, send, t0, L, H, n):
    """Desenlaces desde t0+1 (misma sesión). Devuelve
    te, dir_salida, o2_seguimiento, o3a_retest, o3b_rebote, max_excursion_h (antes de volver a cerrar dentro, en h)."""
    h = H - L + 1
    te = -1
    d = 0
    for t in range(t0 + 1, min(t0 + EXIT_MAX, n - 1) + 1):
        if send[t] != send[t0]:
            break
        if cl[t] > H:
            te = t; d = 1
            break
        if cl[t] < L:
            te = t; d = -1
            break
    if te < 0:
        return -1, 0, -1, -1, -1, -1.0, -1
    edge = H if d == 1 else L
    # O2: llega a edge + d*h antes de volver a cerrar dentro de [L, H]; excursión máxima hasta volver
    o2 = -1
    mx = 0.0
    for t in range(te + 1, min(te + EXIT_MAX, n - 1) + 1):
        if send[t] != send[te]:
            break
        exc = (hi[t] - edge) if d == 1 else (edge - lo[t])
        if exc > mx:
            mx = exc
        if o2 < 0 and exc >= h:
            o2 = 1
        if cl[t] >= L and cl[t] <= H:
            if o2 < 0:
                o2 = 0
            break
    # O3: retest del borde por el que salió, luego rebote (edge + d*h) vs ruptura (edge - d*h)
    o3a = 0
    o3b = -1
    tr = -1
    for t in range(te + 1, min(te + EXIT_MAX, n - 1) + 1):
        if send[t] != send[te]:
            break
        if (lo[t] <= edge) if d == 1 else (hi[t] >= edge):
            tr = t
            o3a = 1
            break
    if tr >= 0:
        up = edge + d * h
        dn = edge - d * h
        for t in range(tr + 1, min(tr + EXIT_MAX, n - 1) + 1):
            if send[t] != send[tr]:
                break
            r = (hi[t] >= up) if d == 1 else (lo[t] <= up)
            bk = (lo[t] <= dn) if d == 1 else (hi[t] >= dn)
            if r and bk:
                o3b = -2
                break
            if r:
                o3b = 1
                break
            if bk:
                o3b = 0
                break
    # O6 (reversión interna al centro M = (L+H)/2 vs continuación externa a igual distancia d_in desde cl[te], en <=200 barras de la misma sesión)
    o6_rev = -1
    mid = 0.5 * (L + H)
    d_in = abs(cl[te] - mid)
    if d_in >= 1.0:
        lvl_rev = mid
        lvl_cont = cl[te] + d * d_in
        for t in range(te + 1, min(te + HPOST, n - 1) + 1):
            if send[t] != send[te]:
                break
            hit_rev = (lo[t] <= lvl_rev) if d == 1 else (hi[t] >= lvl_rev)
            hit_cont = (hi[t] >= lvl_cont) if d == 1 else (lo[t] <= lvl_cont)
            if hit_rev and hit_cont:
                o6_rev = -2
                break
            if hit_rev:
                o6_rev = 1
                break
            if hit_cont:
                o6_rev = 0
                break
    return te, d, o2, o3a, o3b, mx / h, o6_rev


def run_contract(c):
    t0_ = time.time()
    tk, dates = load_contract(c)
    dates = [int(d) for d in dates]
    ok_dates = set(dates[WARMUP_SESSIONS:])          # sólo sesiones con >= 20 previas del mismo contrato en la release
    bars = B.build_tick_bars(tk, SPEC)
    fps = B.build_total_footprint_csr_nt8(tk, bars)
    del tk
    gc.collect()
    hi = np.asarray(bars.high_t, np.int64); lo = np.asarray(bars.low_t, np.int64); cl = np.asarray(bars.close_t, np.int64)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    n = len(cl)
    send = session_end_vec(end)
    r = zp2_run(bars, fps, send, ZP2_PARAMS)
    del fps, bars
    gc.collect()
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    clock = ct_minute_of_day(end) // 30
    appr = np.isin(sdate, list(ok_dates))
    rng200 = (pd.Series(hi).rolling(HPOST).max() - pd.Series(lo).rolling(HPOST).min()).to_numpy()
    rng_fwd = (pd.Series(hi[::-1]).rolling(HPOST).max() - pd.Series(lo[::-1]).rolling(HPOST).min()).to_numpy()[::-1]  # [t, t+199]
    csum_cache = {}

    def occ(t0, L, H):
        a_ = max(0, t0 - OCC + 1)
        x = cl[a_:t0 + 1]
        return float(((x >= L) & (x <= H)).mean())

    def row(kind, t0, L, H, start0):
        te, d, o2, o3a, o3b, mx, o6_rev = outcomes(hi, lo, cl, send, t0, L, H, n)
        tr = np.sign(cl[t0] - cl[max(0, t0 - TREND)])
        pre_end = start0 - 1
        exp = np.nan
        exp_t0 = np.nan
        # H-04: la ventana post-salida [te+1, te+HPOST] y la previa [pre_end-HPOST+1, pre_end] deben ser intra-sesión
        if (te >= 0 and te + HPOST < n and pre_end >= HPOST and rng200[pre_end] > 0
                and send[te + HPOST] == send[te] and send[pre_end] == send[pre_end - HPOST + 1]):
            exp = float(np.log(max(rng_fwd[te + 1], 1) / rng200[pre_end]))
        # H-06: mismo numerador contra el rango de las 200 barras que terminan en t0 (separa compresión de regresión a la media desde start0)
        if (te >= 0 and te + HPOST < n and t0 >= HPOST and rng200[t0] > 0
                and send[te + HPOST] == send[te] and send[t0] == send[t0 - HPOST + 1]):
            exp_t0 = float(np.log(max(rng_fwd[te + 1], 1) / rng200[t0]))
        pos = 0 if L <= cl[t0] <= H else (1 if cl[t0] > H else -1)
        return (c, kind, int(t0), int(L), int(H), int(H - L + 1), int(sdate[t0]), int(clock[t0]), occ(t0, L, H),
                float(rng200[t0]) if t0 >= HPOST else np.nan, int(tr), pos, int(te), int(d), int(o2), int(o3a), int(o3b),
                float(mx), float(np.log(te - t0)) if te > 0 else np.nan, exp, exp_t0, int(o6_rev),
                float(cl[t0] - cl[max(0, t0 - TREND)]) / (H - L + 1), float(cl[t0] - cl[max(0, t0 - 100)]) / (H - L + 1),
                int(end[te]) if te >= 0 else -1, int(end[t0]), int(cl[te]) if te >= 0 else -1,
                # auditoría externa (H-03/H-04/H-06): cierre en el evento, componentes de O5 y banderas de misma sesión
                int(cl[t0]), float(rng200[pre_end]) if pre_end >= HPOST else np.nan,
                float(rng_fwd[te + 1]) if (te >= 0 and te + 1 < n and not np.isnan(rng_fwd[te + 1])) else np.nan,
                bool(pre_end >= HPOST and send[pre_end - HPOST + 1] == send[pre_end]),
                bool(te >= 0 and te + HPOST < n and send[te + HPOST] == send[te]))

    rows = []
    for (cm, cw, ca) in CELLS:
        cell = "%d_%d_%d" % (cm, cw, ca)
        clus = racimos_de(r["zones"], cm, cw, ca)
        reals = [k for k in clus if appr[k["bar"]] and k["bar"] < n - 2]
        for k in reals:
            rows.append((cell,) + row("real", k["bar"], k["low0"], k["high0"], k["start0"]))
        rng = np.random.default_rng(zlib.crc32((c + "|" + cell).encode()))  # semilla estable (hash() cambia por proceso)
        pool = np.flatnonzero(appr)
        pool = pool[(pool > max(OCC, HPOST) + 600) & (pool < n - 2)]
        pclock = clock[pool]
        for k in reals:
            t0 = k["bar"]
            cand = pool[pclock == clock[t0]]
            if len(cand) == 0:
                continue
            dl, dh, span = k["low0"] - cl[t0], k["high0"] - cl[t0], t0 - k["start0"]
            tr_r = int(np.sign(cl[t0] - cl[max(0, t0 - TREND)]))
            occ_r = occ(t0, k["low0"], k["high0"])
            # NULO ESPEJADO (primario; H-03 de la auditoría externa): apareamiento por ocupación y por orientación relativa al signo de la
            # tendencia: si sign(trend(b0)) != sign(trend(t0)) se espeja [dl, dh] -> [-dh, -dl], preservando la distancia al borde del lado de la tendencia.
            got = 0
            for b0 in rng.choice(cand, min(200, 40 * NPSEUDO), replace=True):
                b0_i = int(b0)
                if b0_i - span - 1 < HPOST:
                    continue
                tr_b = int(np.sign(cl[b0_i] - cl[max(0, b0_i - TREND)]))
                L_, H_ = pseudo_box(int(cl[b0_i]), dl, dh, tr_r, tr_b)
                if abs(occ(b0_i, L_, H_) - occ_r) > 0.05:
                    continue
                rows.append((cell,) + row("pseudo", b0_i, L_, H_, int(b0_i - span)))
                got += 1
                if got >= NPSEUDO:
                    break
            # NULO LEGACY (sensibilidad; idéntico al de las actas del 14-oct): copia (dl, dh) sin tener en cuenta el signo de la tendencia del pseudo.
            # Se genera en la MISMA corrida para medir directamente cuánto del efecto de O1 depende del nulo.
            rng2 = np.random.default_rng(zlib.crc32((c + "|" + cell + "|k%d" % t0).encode()))
            got = 0
            for b0 in rng2.choice(cand, min(200, 40 * NPSEUDO), replace=True):
                L_, H_ = int(cl[b0] + dl), int(cl[b0] + dh)
                if abs(occ(int(b0), L_, H_) - occ_r) > 0.05:
                    continue
                rows.append((cell,) + row("pseudo_legacy", int(b0), L_, H_, int(b0 - span)))
                got += 1
                if got >= NPSEUDO:
                    break
    t = pd.DataFrame(rows, columns=["cell", "contract", "kind", "t0", "L", "H", "h", "session", "clock", "occ", "amp", "trend", "pos",
                                    "te", "dir", "o2", "o3a", "o3b", "mx_h", "o4", "o5", "o5_t0", "o6_rev", "trend_h", "mom100_h", "te_end_ns", "t0_end_ns", "close_te",
                                    "c0", "rng_pre", "rng_post", "pre_same_session", "post_same_session"])
    t.to_parquet(OUT / ("%s_%s%s_avzp2racgrid.parquet" % (INST, c.replace(" ", "_"), "" if SPEC == 25 else "_s%d" % SPEC)))
    print(c, "sesiones", len(dates), "evaluables", len(ok_dates), "velas", n, "zonas", len(r["zones"]), "filas", len(t),
          "%.0f s" % (time.time() - t0_), flush=True)


def _contract_order(k):
    mm, yy = k.split()[-1].split("-")
    return int(yy), int(mm)


def pin_check():
    """Si EXPECT_MANIFEST_SHA256 está definido, el manifiesto de la release visible debe tener EXACTAMENTE ese SHA-256 (pin por contenido:
    no depende del número de versión de Kaggle)."""
    exp = os.environ.get("EXPECT_MANIFEST_SHA256", "").strip().lower()
    if exp:
        got = hashlib.sha256((RELEASE / "release_manifest.json").read_bytes()).hexdigest()
        if got != exp:
            raise RuntimeError("STOP: el manifiesto de la release (%s...) no es el esperado (%s...)" % (got[:12], exp[:12]))
        print("manifiesto verificado:", got, flush=True)


def main():
    pin_check()
    cs = [x.strip() for x in os.environ.get("AVCL_CONTRACTS", "").split(",") if x.strip()]
    if not cs:                                           # por defecto: todos los contratos del activo con sesiones seleccionadas
        si = pd.read_parquet(RELEASE / "metadata" / "session_index.parquet")
        cs = sorted(si[(si.instrument == INST) & (si.status == "SELECTED")].contract.unique(), key=_contract_order)
    for c in cs:
        run_contract(c)
        gc.collect()
    fn = globals().get("run_analysis")                   # lo agrega el constructor del kernel (build_avzp2_replica_kernel.py)
    if fn and os.environ.get("AVCL_ANALYZE", "1") == "1":
        fn()


if __name__ == "__main__":
    main()
