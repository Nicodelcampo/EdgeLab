"""En el holdout (SELLADO=1) con el almacén de desarrollo montado, U1-ZONAS-GRILLA tiene que usar las zonas de desarrollo anteriores a la
frontera MÁS las armadas con los ticks sellados (bug del 2026-11-17: devolvía sólo el desarrollo y el holdout de YM quedaba con 0 disparos)."""
import pandas as pd

from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS
from edgelab.research import u1_zonas_grilla as G


def test_sellado_concatena_desarrollo_y_holdout(tmp_path, monkeypatch):
    dev = pd.DataFrame(dict(t_ns=[HOLDOUT_APERTURA_UTC_NS - 10, HOLDOUT_APERTURA_UTC_NS + 10], lo=[1.0, 2.0], hi=[1.5, 2.5], zona=[17, 17]))
    dev.to_parquet(tmp_path / "ZONAS_AVZG_YM.parquet")
    sel = pd.DataFrame(dict(t_ns=[HOLDOUT_APERTURA_UTC_NS + 5], lo=[3.0], hi=[3.5], zona=[17]))
    monkeypatch.setattr(G, "_zonas_avzg_selladas", lambda inst, ent: sel)
    monkeypatch.setenv("SELLADO", "1"); monkeypatch.setenv("ENTRADA", str(tmp_path))
    Z = G._cargar("YM")
    assert list(Z.t_ns) == [HOLDOUT_APERTURA_UTC_NS - 10, HOLDOUT_APERTURA_UTC_NS + 5]   # el del almacén posterior a la frontera no entra


def test_desarrollo_sin_sellado_usa_el_almacen(tmp_path, monkeypatch):
    pd.DataFrame(dict(t_ns=[1, 2], lo=[1.0, 2.0], hi=[1.5, 2.5], zona=[0, 0])).to_parquet(tmp_path / "ZONAS_AVZG_YM.parquet")
    monkeypatch.delenv("SELLADO", raising=False); monkeypatch.setenv("ENTRADA", str(tmp_path))
    assert len(G._cargar("YM")) == 2
