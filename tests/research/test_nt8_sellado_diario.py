"""Conversor del logger en vivo de NT8 al dataset sellado (2026-11-01): sesión CME armada desde dos días UTC, sesión incompleta no
subida, roll con el contrato de más volumen, inmutabilidad y lectura por el lector sellado de los kernels."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "tools"))
import nt8_sellado_diario as S  # noqa: E402


def _txt(carpeta: Path, desde_ct: str, hasta_ct: str, px=21000.0, vol=1, cada="1min"):
    """Un tick por minuto entre dos horas de Chicago, repartido en archivos por día UTC (como el logger)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    t = pd.date_range(pd.Timestamp(desde_ct, tz="America/Chicago"), pd.Timestamp(hasta_ct, tz="America/Chicago"), freq=cada).tz_convert("UTC")
    for dia, g in pd.Series(t).groupby(t.strftime("%Y%m%d")):
        with open(carpeta / f"{dia}.Last.utc.txt", "a") as fh:
            for x in g: fh.write(f"{x:%Y%m%d %H%M%S} 0000000;{px};{px - 0.25};{px};{vol}\n")


@pytest.fixture
def espejo(tmp_path):
    e = tmp_path / "espejo"; e.mkdir(); (e / "SELLADO.txt").write_text("sellado"); return e


def test_sesion_completa_incompleta_y_roll(tmp_path, espejo):
    live = tmp_path / "live"
    _txt(live / "NQ_12-26", "2026-11-01 17:00", "2026-11-02 15:59")                  # sesión 2026-11-02 completa
    _txt(live / "NQ_03-27", "2026-11-01 17:00", "2026-11-02 15:59", vol=0)           # contrato siguiente, sin volumen
    _txt(live / "ES_12-26", "2026-11-01 19:30", "2026-11-02 15:59")                  # ES arrancó 2,5 h tarde: incompleta
    ahora = pd.Timestamp("2026-11-02 16:30", tz="America/Chicago").value
    h = {(f["instrumento"], f["sesion"]): f for f in S.convertir(espejo, [live], ahora_ns=ahora)}
    assert h[("NQ", 20261102)]["estado"] == "OK" and h[("NQ", 20261102)]["contrato"] == "NQ 12-26"
    assert h[("ES", 20261102)]["estado"] == "INCOMPLETA_NO_SUBIDA" and not (espejo / "ES_20261102_ticks.parquet").exists()
    t = pd.read_parquet(espejo / "NQ_20261102_ticks.parquet")
    assert len(t) == 23 * 60 and set(t.trade_date) == {20261102} and t.price_ticks.iloc[0] == 84000 and t.bid_ticks.iloc[0] == 83999
    assert S.convertir(espejo, [live], ahora_ns=ahora) == [] or all(f["instrumento"] == "ES" for f in S.convertir(espejo, [live], ahora_ns=ahora))
    f = S.convertir(espejo, [live], forzar={20261102}, ahora_ns=ahora)
    assert [x["estado"] for x in f] == ["FORZADA"]


def test_sesion_abierta_no_se_sube_y_lo_lee_el_kernel(tmp_path, espejo):
    from edgelab.research import fuentes_ticks as F
    live = tmp_path / "live"; _txt(live / "NQ_12-26", "2026-11-01 17:00", "2026-11-02 15:59")
    assert S.convertir(espejo, [live], ahora_ns=pd.Timestamp("2026-11-02 15:00", tz="America/Chicago").value) == []
    S.convertir(espejo, [live], ahora_ns=pd.Timestamp("2026-11-03 09:00", tz="America/Chicago").value)
    (tmp_path / "acta.json").write_text("{}")
    b = list(F.bloques_nq_sellado(20261102, 20261102, sorted(str(p) for p in espejo.glob("NQ_*_ticks.parquet")), str(tmp_path / "acta.json")))
    assert len(b) == 1 and len(b[0]) == 23 * 60 and b[0].px.iloc[0] == 21000.0
