"""Calendario de noticias USD y filtro de operaciones (`edgelab/noticias.py`)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from edgelab import noticias

ROOT = Path(__file__).resolve().parents[1]
NS_MIN = 60 * 1_000_000_000


def ns(s: str) -> int:
    return pd.Timestamp(s, tz="UTC").value


@pytest.fixture()
def chico(tmp_path):
    p = tmp_path / "cal.csv"
    p.write_text("ts_utc,evento,fuente_url,impacto\n"
                 "2024-03-12T12:30Z,CPI,https://www.bls.gov/schedule/2024/home.htm,tier1\n"
                 "2024-03-14T12:30Z,INITIAL_JOBLESS_CLAIMS,https://example.org/claims,tier2\n"
                 "2024-03-20T18:00Z,FOMC_DECISION,https://www.federalreserve.gov/x,tier1\n"
                 "2024-03-20T18:30Z,FOMC_PRESS_CONFERENCE,https://www.federalreserve.gov/x,tier1\n",
                 encoding="utf-8")
    return p


# ---------------------------------------------------------------- calendario real
def test_csv_ordenado_sin_duplicados_y_con_fuente():
    raw = pd.read_csv(noticias.RUTA, dtype=str, keep_default_na=False)
    assert list(raw.columns) == list(noticias.COLUMNAS)
    assert raw["ts_utc"].is_monotonic_increasing
    assert not raw.duplicated(["ts_utc", "evento"]).any()
    assert (raw["fuente_url"].str.startswith("https://")).all()
    assert set(raw["impacto"]) <= set(noticias.IMPACTOS)
    assert raw["ts_utc"].str.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\dZ").all()
    assert raw["ts_utc"].min() >= "2023-01-01" and raw["ts_utc"].max() < "2027-01-01"


def test_csv_reproducible_desde_las_transcripciones():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "noticias_calendario.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_dst_cpi_marzo_y_noviembre():
    df = noticias.cargar()
    cpi = set(df.loc[df["evento"] == "CPI", "ts_utc"].dt.strftime("%Y-%m-%dT%H:%MZ"))
    # 08:30 ET: EDT (UTC-4) después del 2.º domingo de marzo; EST (UTC-5) después del 1.º domingo de noviembre
    assert "2024-03-12T12:30Z" in cpi       # DST desde el 2024-03-10
    assert "2024-11-13T13:30Z" in cpi       # EST desde el 2024-11-03
    assert "2023-03-14T12:30Z" in cpi       # DST desde el 2023-03-12
    assert "2023-11-14T13:30Z" in cpi       # EST desde el 2023-11-05
    et = df.loc[df["evento"] == "CPI", "ts_utc"].dt.tz_convert("America/New_York")
    assert (et.dt.strftime("%H:%M") == "08:30").all()


def test_horas_locales_por_evento():
    df = noticias.cargar()
    hora = df["ts_utc"].dt.tz_convert("America/New_York").dt.strftime("%H:%M")
    for ev, h in [("FOMC_DECISION", "14:00"), ("FOMC_PRESS_CONFERENCE", "14:30"), ("FOMC_MINUTES", "14:00"),
                  ("NFP_EMPLOYMENT_SITUATION", "08:30"), ("ISM_MANUFACTURING_PMI", "10:00"),
                  ("ISM_SERVICES_PMI", "10:00"), ("JOLTS", "10:00"), ("RETAIL_SALES", "08:30")]:
        assert (hora[df["evento"] == ev] == h).all(), ev


def test_cobertura_minima_por_evento_y_anio():
    df = noticias.cargar()
    y = df["ts_utc"].dt.year
    for ev in ["CPI", "NFP_EMPLOYMENT_SITUATION", "ISM_MANUFACTURING_PMI", "ISM_SERVICES_PMI", "RETAIL_SALES"]:
        for anio in (2023, 2024, 2026):
            assert ((df["evento"] == ev) & (y == anio)).sum() >= 12, (ev, anio)
    assert ((df["evento"] == "FOMC_DECISION") & (y == 2025)).sum() == 8
    assert (df.loc[df["evento"] == "INITIAL_JOBLESS_CLAIMS", "impacto"] == "tier2").all()


# ---------------------------------------------------------------- intervalos (fixture chico)
def test_ventanas_fusionan_y_respetan_impacto(chico):
    w1 = noticias.ventanas_bloqueadas(1, 1, ruta=chico)
    assert len(w1) == 3                                        # claims (tier2) fuera
    w30 = noticias.ventanas_bloqueadas(30, 30, ruta=chico)
    assert len(w30) == 2                                       # FOMC 14:00 y 14:30 ET se funden
    assert w30.iloc[1]["eventos"] == "FOMC_DECISION+FOMC_PRESS_CONFERENCE"
    assert len(noticias.ventanas_bloqueadas(1, 1, impactos=("tier1", "tier2"), ruta=chico)) == 4


@pytest.mark.parametrize("entrada,salida,esperado", [
    ("2024-03-12T12:00", "2024-03-12T12:28:59", False),    # sale antes de la ventana
    ("2024-03-12T12:00", "2024-03-12T12:29:00", True),     # toca el borde izquierdo (cerrado)
    ("2024-03-12T12:29:30", "2024-03-12T12:29:45", True),  # adentro
    ("2024-03-12T12:31:00", "2024-03-12T13:00", True),     # entra en el borde derecho
    ("2024-03-12T12:31:01", "2024-03-12T13:00", False),    # entra después
    ("2024-03-12T10:00", "2024-03-12T15:00", True),        # envuelve la ventana
    ("2024-03-14T12:00", "2024-03-14T13:00", False),       # claims es tier2: no bloquea por defecto
    ("2024-03-20T18:31:01", "2024-03-20T18:31:30", False),  # entre FOMC y conferencia con ±1
])
def test_cruza_noticia_bordes(chico, entrada, salida, esperado):
    r = noticias.cruza_noticia([ns(entrada)], [ns(salida)], ruta=chico)
    assert r.tolist() == [esperado]


def test_cruza_vectorizado_igual_a_fuerza_bruta(chico):
    rng = np.random.default_rng(7)
    base = ns("2024-03-11T00:00")
    a = base + rng.integers(0, 11 * 24 * 60, 4000) * NS_MIN // 4
    b = a + rng.integers(0, 120, 4000) * NS_MIN // 3
    w = noticias.ventanas_bloqueadas(2, 3, impactos=("tier1", "tier2"), ruta=chico)
    rapido = noticias.cruza_noticia(a, b, ventanas=w)
    lento = np.array([((w["inicio_ns"] <= bi) & (w["fin_ns"] >= ai)).any() for ai, bi in zip(a, b)])
    assert (rapido == lento).all() and rapido.any() and not rapido.all()


def test_acepta_datetime_y_falla_cerrado(chico):
    e = pd.Series(pd.to_datetime(["2024-03-12T12:30:00Z"]))
    assert noticias.cruza_noticia(e, e, ruta=chico).tolist() == [True]
    with pytest.raises(ValueError):
        noticias.cruza_noticia([ns("2024-03-12T13:00")], [ns("2024-03-12T12:00")], ruta=chico)
    with pytest.raises(noticias.FueraDeCobertura):
        noticias.cruza_noticia([ns("2022-12-30T13:00")], [ns("2022-12-30T14:00")], ruta=chico)
    assert noticias.cruza_noticia([ns("2022-12-30T13:00")], [ns("2022-12-30T14:00")], ruta=chico,
                                  exigir_cobertura=False).tolist() == [False]


def test_minutos_bloqueados_del_dia(chico):
    m = noticias.minutos_bloqueados_del_dia("2024-03-12", ruta=chico)
    assert m.tolist() == [7 * 60 + 29, 7 * 60 + 30, 7 * 60 + 31]      # 08:30 ET = 07:30 CT, ±1 min
    m_et = noticias.minutos_bloqueados_del_dia("2024-03-12", 0, 0, tz="America/New_York", ruta=chico)
    assert m_et.tolist() == [8 * 60 + 30]
    assert noticias.minutos_bloqueados_del_dia("2024-03-13", ruta=chico).size == 0
