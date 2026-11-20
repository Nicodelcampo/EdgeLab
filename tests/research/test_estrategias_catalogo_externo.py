"""Pruebas de contrato, causalidad estricta, ejecución y fricción para las 28 estrategias traducidas del catálogo externo."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.research import analizador as A
from edgelab.research.estrategias import catalogo_externo as CE


class RegStub:
    def __init__(self) -> None:
        self.filas: list[tuple[str, str, int]] = []

    def ensure(self, cid: str, fam: str, n: int, nota: str = "") -> bool:
        self.filas.append((cid, fam, n))
        return True


def _barras_sinteticas(dias: int = 30, seed: int = 17) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    filas = []
    t0 = pd.Timestamp("2025-03-03 14:30", tz="UTC")
    for d in range(dias):
        p = 20000.0 + rng.normal() * 50.0
        for m in range(390):
            o = p
            p = p + rng.normal() * 3.0
            h = max(o, p) + abs(rng.normal())
            l = min(o, p) - abs(rng.normal())
            ts = t0 + pd.Timedelta(days=d, minutes=m + 1)
            filas.append(dict(ts=int(ts.value // 10**6), o=o, h=h, l=l, c=p, v=100.0 + abs(rng.normal() * 20.0), ses=d))
    return pd.DataFrame(filas)


_BARRAS_CACHE: pd.DataFrame | None = None


def _barras() -> pd.DataFrame:
    global _BARRAS_CACHE
    if _BARRAS_CACHE is None:
        _BARRAS_CACHE = _barras_sinteticas(dias=30, seed=17)
    return _BARRAS_CACHE


def test_catalogo_completo_y_contrato() -> None:
    assert len(CE.ESTRATEGIAS_EXTERNAS) == 28
    assert len(CE.MAPA_ESTRATEGIAS) == 28
    cat = CE.listar_catalogo()
    assert len(cat) == 28
    for mod in CE.ESTRATEGIAS_EXTERNAS:
        for attr in ("NOMBRE", "FAMILIA", "INSTRUMENTO", "PARAMETROS", "senales"):
            assert hasattr(mod, attr), f"{mod.__name__} no expone {attr}"


@pytest.mark.parametrize("mod", CE.ESTRATEGIAS_EXTERNAS, ids=lambda m: m.NOMBRE)
def test_estrategia_es_estrictamente_causal(mod) -> None:
    B = _barras()
    vs = A.variantes(mod)
    assert len(vs) >= 1
    err = A.causal(mod, B, vs[0], cortes=3)
    assert err == [], f"{mod.NOMBRE} falló causalidad: {err}"


@pytest.mark.parametrize("mod", CE.ESTRATEGIAS_EXTERNAS, ids=lambda m: m.NOMBRE)
def test_estrategia_corre_registra_y_genera_operaciones(mod) -> None:
    B = _barras()
    reg = RegStub()
    out = A.analizar(mod, 20250303, 20250430, registro=reg, B=B, tick=0.25, friccion_pts=1.0, resolucion="m1")
    assert "error" not in out, f"{mod.NOMBRE} devolvió error: {out}"
    assert reg.filas and reg.filas[0][1] == mod.FAMILIA and reg.filas[0][2] == out["variantes"]
    assert "EXPLORATORIO" in out["aviso"]

    mejor_n = max(r["n"] for r in out["resultados"])
    assert mejor_n > 0, f"{mod.NOMBRE} no generó operaciones en 30 días sintéticos"

    p0 = out["resultados"][0]["parametros"]
    T = A.simular(B, mod.senales(B, **p0), 0.25, out["friccion_pts"])
    if len(T):
        assert np.allclose(T.neto_pts, T.bruto_pts - out["friccion_pts"])


def test_correr_todas_por_lote() -> None:
    B = _barras()
    reg = RegStub()
    reps = CE.correr_todas(20250303, 20250430, registro=reg, B=B, tick=0.25, friccion_pts=1.0, resolucion="m1")
    assert len(reps) == 28
    assert len(reg.filas) == 28
    assert all("error" not in r for r in reps)
