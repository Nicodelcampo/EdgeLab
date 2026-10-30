"""U1-RACIMOS-GRILLA (2026-10-26, nivel 1 del diseño aprobado por Nico: «optimizalo bien y usá las variantes que valen la pena»).

Los racimos de aVolZonePOI2 como zonas de la gramática de U1, con la DEFINICIÓN de zona y de racimo como perillas: zona (36 definiciones
del indicador) × racimo (12 definiciones) del almacén `ZONAS_AVZRG_<INST>` (`tools/kaggle_grilla/almacen_zonas_main.py`, GRILLA_ZONA y
GRILLA_RACIMO). Para que el tamiz tenga potencia, U1 se reduce a su vecindario: N (2) × x (3) × A/H (3) × 6 ejecuciones, escala 1
(el racimo ya trae su tamaño en ticks). 2·3·3·36·12·6 = 46.656 celdas por canal. El nivel 2 (gramática completa) corre sólo sobre las
definiciones que salgan como pistas, en su réplica.
Pre-registro: `docs/research/u1_zonas_20261025/PREREGISTRO_U1_ZONAS_BT2_AVZR.md`.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from edgelab.research import areas_expansion as AX
from edgelab.research import u1_indaga as U
from edgelab.research import u1_oro as UO
from edgelab.research import u1_zonas as Z
from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_indaga import niveles  # noqa: F401

NOMBRE = "U1-RACIMOS-GRILLA"
INDICADORES = ["aVolZonePOI2"]
FUENTE = "AVZRG"
N_ZONA, N_RACIMO = 36, 12
VARIABLES = list(U.VARIABLES[:3]) + [Variable("def_zona", "zt", "grupo", categoria=N_ZONA),
                                     Variable("def_racimo", "rt", "grupo", categoria=N_RACIMO)]
EJES_ORDINALES = (1, 2)
EJECUCIONES = [(e, o, "S3", 0) for e in ("E1A", "RET10", "VOL_VUELTA") for o in ("T1", "T2")]
VACIO = ["m", "k", "xi", "ciclo", "lado", "lo", "hi", "H", "E", "A", "D", "ni", "A_H", "zt", "rt"]
BASE = {"N": 0, "x": 1, "A/H": 1, "def_zona": 17, "def_racimo": 4, "ejecución": 0}   # zona 95/2/10/3 (pc·12+mm·4+wb·2+mc), racimo 6/500/30 (m·4+w·2+a)


GRILLA_ZONA = [dict(detection_percentile=pc, median_multiplier=mm, window_bars=wb, min_cluster_ticks=mc)
               for pc in (90.0, 95.0, 98.0) for mm in (1.5, 2.0, 3.0) for wb in (10, 20) for mc in (2, 3)]
GRILLA_RACIMO = [dict(racimo_min=m, racimo_bars=w, racimo_altura_ticks=a) for m in (4, 6, 8) for w in (500, 1000) for a in (30, 45)]


def _racimos_sellados(inst: str, entrada: str) -> pd.DataFrame:
    """En el holdout (`SELLADO=1`), calcula los racimos AVZRG sobre los ticks sellados de `inst` (si `PARAMS` congela celdas,
    corre sólo las definiciones `zona` presentes en `celdas` para no repetir las 36 definiciones innecesariamente)."""
    import glob
    import json
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolzonepoi2 import _racimo, run
    from edgelab.bridge.ticks import TickSeries
    from edgelab.research import fuentes_ticks as F
    r = glob.glob(f"{entrada}/**/{inst}_*ticks.parquet", recursive=True)
    if not r: raise FileNotFoundError(f"sin ticks sellados de {inst} en {entrada}")
    acta = os.environ.get("ACTA_HOLDOUT_RUTA") or os.path.abspath("ACTA_HOLDOUT.json"); hasta = int(os.environ.get("HASTA", 20991231)); tick = F.TICK_FUTURO[inst]
    bl = list(F.bloques_nq_sellado(F.HOLDOUT_PRIMERA_SESION_INT, hasta, r[0], acta, tick))
    if not bl: return pd.DataFrame(columns=["t_ns", "lo", "hi", "zona", "racimo"])
    ts = np.concatenate([b.ts_ns.to_numpy() for b in bl]); px = np.concatenate([b.px.to_numpy() for b in bl])
    vol = np.concatenate([b.vol.to_numpy() for b in bl])
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / tick).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick)
    bars = B.build_tick_bars(tk, 25); fps = B.build_total_footprint_csr_nt8(tk, bars)
    end = np.asarray(bars.end_ns, np.int64); ses = B.session_ids(end); filas = []
    p_base = dict(ob_away_heights=6.0, ob_max_inside_pct=4.0, racimo_min=0, racimo_bars=500, racimo_altura_ticks=30)
    celdas = (json.loads(os.environ.get("PARAMS") or "{}")).get("celdas") or []
    zts = sorted({int(c[3]) for c in celdas if len(c) > 3}) or list(range(len(GRILLA_ZONA)))
    for iz in zts:
        zs = sorted(run(bars, fps, ses, dict(p_base, **GRILLA_ZONA[iz], racimo_min=0))["zones"], key=lambda z: z["bar"])
        for ir, pr in enumerate(GRILLA_RACIMO):
            hechas, clusters = [], []
            for z in zs:
                nz = dict(bar=z["bar"], low_tick=z["low_tick"], high_tick=z["high_tick"], racimo_bar=-1, rac=None)
                _racimo(nz, hechas, clusters, nz["bar"], pr); hechas.append(nz)
            filas += [(int(end[c["bar"]]), c["low0"] * tick, c["high0"] * tick, iz, ir) for c in clusters]
    return pd.DataFrame(filas, columns=["t_ns", "lo", "hi", "zona", "racimo"])


def _cargar(inst):
    import glob
    ent = os.environ.get("ENTRADA", "/kaggle/input")
    f = glob.glob(f"{ent}/**/ZONAS_{FUENTE}_{inst}.parquet", recursive=True)
    if not f:
        if os.environ.get("SELLADO") == "1": return _racimos_sellados(inst, ent)
        raise FileNotFoundError(f"sin almacén {FUENTE}/{inst}: nunca se cae a otra fuente")
    return pd.read_parquet(f[0], columns=["t_ns", "lo", "hi", "zona", "racimo"])


def disparos(ctx, r_ref: float | None = None) -> pd.DataFrame:
    """Un llamado de la gramática de U1 (escala 1, como `u1_oro`) por definición (zona, racimo) con esas zonas del almacén. Sin almacén
    ni zonas en el contexto (preflight, tests sintéticos) usa las de LUX-IMB del contexto como definición (0, 0)."""
    if "zonas" in ctx: Zs = ctx["zonas"][FUENTE]
    elif os.environ.get("SENSOR"): Zs = _cargar(os.environ["SENSOR"])
    else: Zs = None
    mes, f = UO.escala_por_mes(ctx, r_ref or UO.R_USATECH)
    cx = dict(ctx, seg=mes, escala_seg=f)
    grupos = [((0, 0), None)] if Zs is None else list(Zs.groupby(["zona", "racimo"], sort=True))
    out = []
    for (zt, rt), Zi in grupos:
        previo = U.AX; U.AX = Z._AXConZonas(Zi) if Zi is not None else AX
        try: D = U.disparos(cx)
        finally: U.AX = previo
        if len(D): out.append(D.assign(zt=int(zt), rt=int(rt)))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=VACIO)
