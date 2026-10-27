"""Descargador autónomo de Dukascopy: decodifica bi5, escribe por día, retoma, y lee lo mismo que la estrategia de JForex."""
import datetime as dt
import importlib.util
import lzma
import struct
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location("dk", Path(__file__).resolve().parents[1] / "tools/dukascopy_descarga.py")
DK = importlib.util.module_from_spec(spec); spec.loader.exec_module(DK)


def _bi5(regs):
    return lzma.compress(b"".join(struct.pack(">IIIff", *r) for r in regs), format=lzma.FORMAT_ALONE)


def test_decodifica_bi5():
    df = DK.decodificar(_bi5([(500, 20001250, 20001000, 1.5, 2.0), (1500, 20002000, 20001500, 1.0, 1.0)]), 1_790_000_000_000, 1000.0)
    assert list(df.bid) == [20001.0, 20001.5] and list(df.ask) == [20001.25, 20002.0]
    assert df.time_utc_ns.iloc[0] == (1_790_000_000_000 + 500) * 1_000_000 and df.bid_vol.iloc[0] == 2.0


def test_bajar_dia_retoma_y_no_escribe_dias_vacios(tmp_path):
    llamadas = []
    def falso(sim, t): llamadas.append(t.hour); return _bi5([(10, 1000, 990, 1.0, 1.0)]) if t.hour == 3 else b""
    f = DK.bajar_dia("USATECHIDXUSD", dt.date(2026, 10, 2), tmp_path, bajar=falso)
    assert f.exists() and len(pd.read_parquet(f)) == 1 and len(llamadas) == 24
    DK.bajar_dia("USATECHIDXUSD", dt.date(2026, 10, 2), tmp_path, bajar=falso); assert len(llamadas) == 24        # ya estaba: no baja
    assert DK.bajar_dia("USATECHIDXUSD", dt.date(2026, 10, 3), tmp_path, bajar=lambda s, t: b"") is None


def test_lee_el_binario_de_jforex(tmp_path):
    a = np.array([(1_790_900_000_000, 25000.5, 25000.75, 1.0, 2.0)], dtype=[("ms", ">i8"), ("bid", ">f8"), ("ask", ">f8"), ("bv", ">f4"), ("av", ">f4")])
    a.tofile(tmp_path / "2026-10-02.bin")
    df = DK.leer_jforex_bin(tmp_path / "2026-10-02.bin")
    assert df.bid.iloc[0] == 25000.5 and df.ask_vol.iloc[0] == 2.0


def test_lector_sellado_lee_jforex_y_rechaza_desarrollo(tmp_path):
    from edgelab.research import fuentes_ticks as F
    d = tmp_path / "USATECHIDXUSD" / "ticks"; d.mkdir(parents=True)
    ms = 1_790_900_000_000 + np.arange(100) * 1000
    a = np.zeros(100, dtype=[("ms", ">i8"), ("bid", ">f8"), ("ask", ">f8"), ("bv", ">f4"), ("av", ">f4")]); a["ms"] = ms; a["bid"] = 25000; a["ask"] = 25000.5
    a.tofile(d / "2026-10-02.bin")
    b = pd.concat(F.bloques_spot_sellado("USATECHIDXUSD", 20261001, 20261031, tmp_path))
    assert len(b) == 100 and b.px.iloc[0] == 25000.25
    with pytest.raises(ValueError): next(F.bloques_spot_sellado("USATECHIDXUSD", 20260901, 20261031, tmp_path))


def test_lector_sellado_lee_el_parquet_plano_de_kaggle(tmp_path):
    from edgelab.research import fuentes_ticks as F
    ms = 1_790_900_000_000 + np.arange(50) * 1000
    pd.DataFrame(dict(time_utc_ns=ms * 1_000_000, bid=25000.0, ask=25000.5, bid_vol=1.0, ask_vol=1.0)).to_parquet(tmp_path / "USATECHIDXUSD_ticks.parquet")
    b = pd.concat(F.bloques_spot_sellado("USATECHIDXUSD", 20261001, 20261031, tmp_path))
    assert len(b) == 50 and b.px.iloc[0] == 25000.25
