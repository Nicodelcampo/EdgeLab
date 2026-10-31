"""Auditoría del 2026-10-31 (pedido heredado de gonzasib-claude: «AVZP2 tiene t_ns antes de la decisión de la zona; las reglas U1 usan
t_ns: ¿lookahead?»). La creación de la zona (t_ns = cierre de la barra que la crea), sus bordes y los racimos se conocen en t_ns:
truncar la serie de ticks después de t no cambia ninguna zona ni racimo creado hasta t. La decisión posterior sólo clasifica la zona
(estado 1/2) y las reglas U1 no la usan (`u1_zonas.zonas_almacen` lee t_ns, lo, hi, t_fin_ns). Acta:
docs/research/AUDITORIA_T_NS_AVZP2_20261031.md."""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import sintetico

ROOT = Path(__file__).resolve().parents[2]
SUELTO = dict(detection_percentile=30.0, median_multiplier=1.0, min_samples=5, lookback_sessions=5)   # el sintético no llega a los umbrales reales
RAC = dict(racimo_min=2, racimo_bars=500, racimo_altura_ticks=45)


def _almacen():
    spec = importlib.util.spec_from_file_location("almacen_causal", ROOT / "tools/kaggle_grilla/almacen_zonas_main.py")
    m = importlib.util.module_from_spec(spec); sys.modules["almacen_causal"] = m
    src = (ROOT / "tools/kaggle_grilla/almacen_zonas_main.py").read_text(encoding="utf-8").replace('if __name__ == "__main__":\n    main()', "")
    exec(compile(src, "almacen_causal", "exec"), m.__dict__)
    return m


def _zonas(A, bls):
    from edgelab.bridge import bars as B
    from edgelab.bridge.indicators.avolzonepoi2 import run
    from edgelab.bridge.ticks import TickSeries
    ts = np.concatenate([b.ts_ns for b in bls]); px = np.concatenate([b.px for b in bls]); vol = np.concatenate([b.vol for b in bls])
    tk = TickSeries(ts_ns=ts, price_ticks=np.round(px / 0.25).astype(np.int64), volume=vol.astype(np.int64), bid_ticks=None, ask_ticks=None,
                    sequence=np.arange(len(ts), dtype=np.int64), tick_size=0.25)
    spec = A.INDICADORES["AVZP2"][1]; bars = B.build_tick_bars(tk, spec); fps = B.build_total_footprint_csr_nt8(tk, bars)
    end = np.asarray(bars.end_ns, np.int64); zs = run(bars, fps, B.session_ids(end), dict(A.PARAMS, **SUELTO))["zones"]
    Z = pd.DataFrame([(z["end_ns"], z["low_tick"], z["high_tick"]) for z in zs], columns=["t", "lo", "hi"])
    R = pd.DataFrame([(int(end[c["bar"]]), c["low"], c["high"]) for c in A.racimos_de(sorted(zs, key=lambda z: z["bar"]), RAC)], columns=["t", "lo", "hi"])
    return Z, R


def test_creacion_y_racimos_de_avzp2_no_dependen_del_futuro():
    A = _almacen(); bl = list(sintetico.bloques(dias=30, seed=3, planta=False))
    Zf, Rf = _zonas(A, bl)
    assert len(Zf) >= 10 and len(Rf) >= 1
    for corte in (16, 27):
        T = int(bl[corte - 1].ts_ns.iloc[-1]); Zp, Rp = _zonas(A, bl[:corte])
        assert Zf[Zf.t <= T].reset_index(drop=True).equals(Zp[Zp.t <= T].reset_index(drop=True))
        assert Rf[Rf.t <= T].reset_index(drop=True).equals(Rp[Rp.t <= T].reset_index(drop=True))


def test_u1_no_usa_el_estado_ni_la_decision():
    src = (ROOT / "edgelab/research/u1_zonas.py").read_text(encoding="utf-8")
    assert "estado" not in src and "t_decidida" not in src
