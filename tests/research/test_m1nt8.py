"""Lector de M1 de futuros de NT8 (`fuentes_ticks.bloques_m1nt8`, 2026-11-17): el archivo llega hasta la fecha del export con el holdout
adentro; el lector nunca entrega nada desde la frontera única, asigna la sesión CME (18:00 NY → día siguiente), descarta fines de semana
y usa la convención calibrada de 4 ticks por vela."""
import numpy as np
import pandas as pd
import pytest

from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS
from edgelab.research import fuentes_ticks as F


def _parquet(tmp_path, idx):
    n = len(idx)
    D = pd.DataFrame(dict(open=np.full(n, 100.0), high=np.full(n, 101.0), low=np.full(n, 99.0), close=np.full(n, 100.5),
                          volume=np.full(n, 8, np.int64)), index=pd.DatetimeIndex(idx, name="datetime"))
    D.to_parquet(tmp_path / "NQ_M1_nonadj_utc.parquet")


def test_corta_en_la_frontera_y_asigna_sesion(tmp_path):
    frontera = pd.Timestamp(HOLDOUT_APERTURA_UTC_NS)
    idx = [pd.Timestamp("2026-09-29 14:00"),            # martes 10:00 NY → sesión 20260929
           pd.Timestamp("2026-09-29 22:30"),            # 18:30 NY → sesión 20260930
           frontera - pd.Timedelta(minutes=1),          # última vela antes de la frontera
           frontera, frontera + pd.Timedelta(days=10)]  # holdout: nunca sale
    _parquet(tmp_path, idx)
    B = list(F.bloques_m1nt8("NQ", 20260901, 20260930, str(tmp_path)))
    ts = np.concatenate([b.ts_ns.to_numpy() for b in B])
    assert ts.max() < HOLDOUT_APERTURA_UTC_NS
    assert sorted({int(s) for b in B for s in b.sesion}) == [20260929, 20260930]
    assert len(ts) == 3 * 4                                                              # 3 velas válidas × 4 ticks
    assert list(B[0].px[:4]) == [100.0, 99.0, 101.0, 100.5]                               # sube: apertura, mínimo, máximo, cierre


def test_ventana_que_toca_el_holdout_falla(tmp_path):
    _parquet(tmp_path, [pd.Timestamp("2026-09-29 14:00")])
    with pytest.raises(ValueError):
        list(F.bloques_m1nt8("NQ", 20260901, 20261015, str(tmp_path)))


def test_fin_de_semana_y_resolver(tmp_path):
    _parquet(tmp_path, [pd.Timestamp("2025-03-08 15:00"), pd.Timestamp("2025-03-10 15:00")])   # sábado (fuera) y lunes
    B = list(F.bloques_m1nt8("NQ", 20250301, 20250331, str(tmp_path)))
    assert [int(b.sesion.iloc[0]) for b in B] == [20250310]
    lector, tick = F.resolver("M1NT8:NQ"); assert tick == 0.25
    from edgelab.research.embudo_runners import datasets, friccion
    assert datasets("M1NT8:NQ", 20250101, 20250131) == ([], [F.M1NT8_DATASET])
    assert friccion("M1NT8:NQ") == friccion("NQ")


def test_leer_m1nt8_hora_ny_y_frontera(tmp_path):
    from edgelab.research.m1_intradia import leer_m1nt8
    frontera = pd.Timestamp(HOLDOUT_APERTURA_UTC_NS)
    _parquet(tmp_path, [pd.Timestamp("2025-07-15 13:30"), frontera, frontera + pd.Timedelta(hours=1)])
    D = leer_m1nt8(tmp_path / "NQ_M1_nonadj_utc.parquet")
    assert list(D.index) == [pd.Timestamp("2025-07-15 09:30")]                 # 13:30 UTC = 09:30 NY (verano); nada desde la frontera
