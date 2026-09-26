#!/usr/bin/env python3
r"""HFT-REV-EXP: ¿una zona HFTZonesNQPureV4 anticipa la reversión cuando el precio vuelve a ella? (exploratorio)

Pre-registro: docs/research/HFT_REVERSION_EXPLORATORIA_MNQ_20260926.md. Sólo describe: no elige parámetros ni
direcciones por P&L, publica todas las celdas y siempre al lado de dos controles.

Evento (por zona): la zona queda disponible (`ts_avail`) → el precio se ALEJA D ticks del borde cercano → VUELVE al
borde cercano (primer toque) → desde ahí se sigue el camino hasta que pasa una de dos cosas:
  - reversión: el precio se aleja R ticks del borde cercano en la dirección esperada;
  - ruptura: cruza el borde lejano por B ticks.
Verde (HFT_BUY, barrido comprador): borde cercano = techo, reversión esperada ALCISTA.
Roja  (HFT_SELL, barrido vendedor): borde cercano = piso, reversión esperada BAJISTA.

Controles, con el MISMO seguidor de camino:
  - NIVEL: por cada zona real, K zonas falsas de igual ancho, polaridad y hora, con el borde cercano en un precio que
    el mercado operó en los 30 min previos. Responde «¿revierte más que cualquier nivel reciente de la misma forma?».
  - POLARIDAD: la misma zona real leída con el color opuesto. Responde «¿importa el color?».
  - Caminata aleatoria: P(reversión) = (W + B) / (R + W + B), la referencia sin memoria.

Uso (máquina con los parquets; nada del holdout — corta en 2026-04-01):
    python tools/hft_reversion_explore.py --parquet data/nt8_research_v2/MNQ_parquet/MNQ_09-25_ticks.parquet \
        --instrument MNQ --contract "MNQ 09-25" --out artifacts/research/hft_rev_exp/MNQ_09-25
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from numba import njit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

HOLDOUT_NS = 1_775_001_600_000_000_000          # 2026-04-01T00:00Z: confirmación y holdout quedan fuera
D_GRID = (8, 20, 40)                            # alejamiento previo, ticks
R_GRID = (16, 40, 80, 160)                      # tamaño de la reversión, ticks
B_BREAK = 2                                     # ruptura: borde lejano + B ticks
HORIZONS_S = (300, 900, 3600)                   # MFE/MAE tras el toque
K_LEVEL = 3                                     # zonas falsas por zona real
LOOKBACK_S = 1800
NS = 1_000_000_000
# estados
DEPART_NONE, TOUCHED, INVALID = 0, 1, 2
OUT_REV, OUT_BREAK, OUT_CENS = 1, 2, 3


@njit(cache=True)
def follow(ts, y, i0, i_end, near, far, D, R, B, horizons_ns, out_ext):
    """Camino de UNA zona en coordenadas orientadas (y = pol · precio; se espera que y suba).
    near > far en y. Devuelve (estado, i_touch, desenlace, penetración máx, i_desenlace).
    out_ext[h, 0/1] = MFE / MAE (ticks, respecto del borde cercano) en la ventana h tras el toque."""
    departed = False
    i_t = -1
    for i in range(i0, i_end):
        v = y[i]
        if not departed:
            if v <= far - B:                         # se rompió antes de alejarse: no hay retorno que medir
                return INVALID, -1, 0, 0.0, -1
            if v >= near + D:
                departed = True
        elif v <= near:
            i_t = i
            break
    if i_t < 0:
        return DEPART_NONE, -1, 0, 0.0, -1
    t0 = ts[i_t]
    lo = near - y[i_t]
    outcome = OUT_CENS
    i_out = i_end - 1
    for i in range(i_t, i_end):
        v = y[i]
        if near - v > lo:
            lo = near - v
        if v >= near + R:
            outcome = OUT_REV; i_out = i; break
        if v <= far - B:
            outcome = OUT_BREAK; i_out = i; break
    for h in range(horizons_ns.shape[0]):
        mfe = -1e18; mae = 1e18
        for i in range(i_t, i_end):
            if ts[i] - t0 > horizons_ns[h]:
                break
            d = y[i] - near
            if d > mfe:
                mfe = d
            if d < mae:
                mae = d
        out_ext[h, 0] = mfe
        out_ext[h, 1] = mae
    return TOUCHED, i_t, outcome, lo, i_out


def run_zones(ts, px, zones, D, R, B=B_BREAK, horizons_s=HORIZONS_S):
    """zones: lista de dicts con `i_avail`, `top`, `bot` (ticks), `pol` (+1 verde, −1 roja), `i_end`.
    Devuelve una fila por zona."""
    hz = np.asarray(horizons_s, np.int64) * NS
    rows = []
    ext = np.zeros((len(hz), 2))
    y_pos = px.astype(np.float64)
    y_neg = -y_pos
    for z in zones:
        if z["pol"] > 0:
            y, near, far = y_pos, float(z["top"]), float(z["bot"])
        else:
            y, near, far = y_neg, -float(z["bot"]), -float(z["top"])
        st, it, oc, pen, io = follow(ts, y, z["i_avail"], z["i_end"], near, far, float(D), float(R), float(B), hz, ext)
        w = float(z["top"] - z["bot"])
        r = dict(zid=z.get("zid"), pol=z["pol"], W=w, estado=int(st), desenlace=int(oc), pen=float(pen),
                 pen_frac=float(pen / w) if w > 0 else float("nan"), rw=(w + B) / (R + w + B))
        if st == TOUCHED:
            r.update(t_toque_s=(ts[it] - ts[z["i_avail"]]) / NS, t_desenlace_s=(ts[io] - ts[it]) / NS,
                     mfe={h: float(ext[k, 0]) for k, h in enumerate(horizons_s)},
                     mae={h: float(ext[k, 1]) for k, h in enumerate(horizons_s)})
        rows.append(r)
    return rows


def level_nulls(ts, px, zones, rng, k=K_LEVEL, lookback_s=LOOKBACK_S):
    """Zonas falsas: mismo ancho, polaridad y hora; borde cercano en un precio operado en los 30 min previos."""
    out = []
    lb = lookback_s * NS
    for z in zones:
        i1 = z["i_avail"]
        i0 = int(np.searchsorted(ts, ts[i1] - lb))
        if i1 - i0 < 2:
            continue
        w = z["top"] - z["bot"]
        for _ in range(k):
            lvl = int(px[rng.integers(i0, i1)])
            top, bot = (lvl, lvl - w) if z["pol"] > 0 else (lvl + w, lvl)
            out.append(dict(z, top=top, bot=bot, zid=f"{z.get('zid')}~n"))
    return out


def polarity_swap(zones):
    return [dict(z, pol=-z["pol"], zid=f"{z.get('zid')}~p") for z in zones]


def summarize(rows):
    t = [r for r in rows if r["estado"] == TOUCHED]
    res = [r for r in t if r["desenlace"] != OUT_CENS]
    rev = [r for r in res if r["desenlace"] == OUT_REV]
    pen = np.array([r["pen"] for r in rev]) if rev else np.array([np.nan])
    penf = np.array([r["pen_frac"] for r in rev if r["pen_frac"] == r["pen_frac"]]) if rev else np.array([np.nan])
    out = dict(zonas=len(rows), se_alejan_y_vuelven=len(t), resueltas=len(res), reversiones=len(rev),
               tasa_reversion=len(rev) / len(res) if res else float("nan"),
               tasa_caminata_aleatoria=float(np.mean([r["rw"] for r in res])) if res else float("nan"),
               pen_media_t=float(np.nanmean(pen)), pen_mediana_t=float(np.nanmedian(pen)),
               pen_p90_t=float(np.nanpercentile(pen, 90)), pen_media_frac_W=float(np.nanmean(penf)),
               t_toque_mediana_s=float(np.median([r["t_toque_s"] for r in t])) if t else float("nan"))
    for h in HORIZONS_S:
        if t:
            out[f"mfe_{h}s_media_t"] = float(np.mean([r["mfe"][h] for r in t]))
            out[f"mae_{h}s_media_t"] = float(np.mean([r["mae"][h] for r in t]))
    return out


def boot_diff(a_rows, b_rows, key_session, n=1000, seed=20260926):
    """IC 95 % de (tasa real − tasa control), bootstrap por sesión (las zonas de una sesión no son independientes)."""
    rng = np.random.default_rng(seed)

    def per_session(rows):
        d = {}
        for r in rows:
            if r["estado"] == TOUCHED and r["desenlace"] != OUT_CENS:
                s = d.setdefault(r[key_session], [0, 0]); s[0] += r["desenlace"] == OUT_REV; s[1] += 1
        return d
    A, Bc = per_session(a_rows), per_session(b_rows)
    ses = sorted(set(A) | set(Bc))
    if not ses:
        return (float("nan"),) * 3
    a = np.array([A.get(s, [0, 0]) for s in ses], float); b = np.array([Bc.get(s, [0, 0]) for s in ses], float)
    idx = rng.integers(0, len(ses), (n, len(ses)))
    ra = a[idx, 0].sum(1) / np.maximum(a[idx, 1].sum(1), 1)
    rb = b[idx, 0].sum(1) / np.maximum(b[idx, 1].sum(1), 1)
    d = ra - rb
    pt = a[:, 0].sum() / max(a[:, 1].sum(), 1) - b[:, 0].sum() / max(b[:, 1].sum(), 1)
    return float(pt), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def load_zones(parquet, instrument, contract, max_sessions=None):
    """Sesión por sesión, igual que el constructor del visor: ticks, zonas SCALED_FUNNEL_V1 y su índice de disponibilidad."""
    import pyarrow.parquet as pq
    from edgelab.bridge.indicators import hftzones_universal as hft
    from edgelab.bridge.ticks import load_canonical_parquet
    from edgelab.kaggle.sessions_cme import is_maintenance_break, trade_date_ymd

    tab = pq.read_table(parquet, columns=["ts_utc_ns"])
    ts_all = tab["ts_utc_ns"].to_numpy()
    ts_all = ts_all[ts_all < HOLDOUT_NS]
    tds = trade_date_ymd(ts_all)
    ok = ~is_maintenance_break(ts_all)
    thr = hft.profile(hft.SCALED, instrument)
    carry = None
    for n, td in enumerate(sorted(np.unique(tds[ok]))):
        if max_sessions and n >= max_sessions:
            break
        m = np.where((tds == td) & ok)[0]
        if len(m) < 100:
            continue
        tk = load_canonical_parquet(parquet, contract=contract, instrument=instrument,
                                    start_utc_ns=int(ts_all[m[0]]), end_utc_ns=int(ts_all[m[-1]]) + 1)
        ts = np.asarray(tk.ts_ns, np.int64); px = np.asarray(tk.price_ticks, np.int64)
        cands = hft.detect_candidates(tk.ts_ns, tk.price_ticks, tk.volume, prev_session_close_ticks=carry)
        zs, _ = hft.accept_all(cands, thr)
        carry = int(px[-1])
        zones = []
        for j, z in enumerate(zs):
            ia = int(np.searchsorted(ts, int(z["ts_avail"])))
            if ia >= len(ts) - 1:
                continue
            zones.append(dict(zid=f"{td}:{j}", sesion=int(td), i_avail=ia, i_end=len(ts),
                              top=int(z["sw_hi_tk"]), bot=int(z["sw_lo_tk"]),
                              pol=1 if int(z["direction"]) > 0 else -1, bucket=z["bucket"],
                              vol=float(z["total_vol"]), avg_ms=float(z["avg_ms"])))
        yield int(td), ts, px, zones


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True); ap.add_argument("--instrument", default="MNQ")
    ap.add_argument("--contract", default="MNQ 09-25"); ap.add_argument("--out", required=True)
    ap.add_argument("--max-sessions", type=int)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(20260926)
    acc = {(D, R): dict(real=[], nivel=[], polaridad=[]) for D in D_GRID for R in R_GRID}
    n_zonas = n_ses = 0
    for td, ts, px, zones in load_zones(a.parquet, a.instrument, a.contract, a.max_sessions):
        n_ses += 1; n_zonas += len(zones)
        nulls = level_nulls(ts, px, zones, rng); swap = polarity_swap(zones)
        for (D, R), c in acc.items():
            for tag, zz in (("real", zones), ("nivel", nulls), ("polaridad", swap)):
                for r, z in zip(run_zones(ts, px, zz, D, R), zz):
                    r.update(sesion=td, bucket=z.get("bucket"))
                    c[tag].append(r)
        print(f"{td}: {len(zones)} zonas", flush=True)
    celdas = []
    for (D, R), c in acc.items():
        fila = dict(D=D, R=R, **{f"{k}": summarize(v) for k, v in c.items()})
        for ctrl in ("nivel", "polaridad"):
            fila[f"real_menos_{ctrl}"] = boot_diff(c["real"], c[ctrl], "sesion")
        fila["por_color"] = {col: summarize([r for r in c["real"] if r["pol"] == p]) for col, p in (("verde", 1), ("roja", -1))}
        fila["por_bucket"] = {b: summarize([r for r in c["real"] if r["bucket"] == b])
                              for b in sorted({r["bucket"] for r in c["real"] if r["bucket"]})}
        celdas.append(fila)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rep = dict(instrumento=a.instrument, contrato=a.contract, sesiones=n_ses, zonas=n_zonas,
               corte_holdout_ns=HOLDOUT_NS, perfil="SCALED_FUNNEL_V1", B=B_BREAK, celdas=celdas)
    (out / "reporte.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    L = [f"# HFT-REV-EXP — {a.contract} ({n_ses} sesiones, {n_zonas} zonas)", "",
         "| D | R | tocadas | reversión real | nivel | caminata | real − nivel [IC 95 %] | real − polaridad [IC 95 %] | pen. mediana (t) | pen. media (%W) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for f in celdas:
        r, n = f["real"], f["nivel"]
        dn, dp = f["real_menos_nivel"], f["real_menos_polaridad"]
        L.append(f"| {f['D']} | {f['R']} | {r['se_alejan_y_vuelven']} | {r['tasa_reversion']:.3f} | {n['tasa_reversion']:.3f} | "
                 f"{r['tasa_caminata_aleatoria']:.3f} | {dn[0]:+.3f} [{dn[1]:+.3f}, {dn[2]:+.3f}] | "
                 f"{dp[0]:+.3f} [{dp[1]:+.3f}, {dp[2]:+.3f}] | {r['pen_mediana_t']:.1f} | {100 * r['pen_media_frac_W']:.0f} % |")
    (out / "reporte.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
