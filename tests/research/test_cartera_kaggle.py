"""Motor de Kaggle de la cartera viva (2026-11-01): espera con verificación de versión, régimen en dos tramos (desarrollo en caché +
sellado), seguimiento sellado con acta y sin almacenes de zonas, lectura de varios parquets sellados (manda el diario) y etapa DIARIO."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from edgelab.cartera import motor_kaggle as MK, papel as PA


class _Kaggle:
    """Runner falso: cada handle pasa por estados; `res` decide el resultado por (etapa, periodo)."""
    def __init__(self, estados=("running", "complete"), sellado=None):
        self.estados, self.dataset_sellado, self.lanzados, self.n = list(estados), sellado, [], {}
    def lanzar(self, spec, etapa, params, periodo):
        h = f"{spec['cid']}/{etapa}/{periodo[0]}"; self.lanzados.append((spec, etapa, params, periodo)); self.n[h] = 0; self.per = periodo; return h
    def estado(self, h):
        i = min(self.n[h], len(self.estados) - 1); self.n[h] += 1; return self.estados[i]
    def traer(self, h):
        spec, etapa, params, periodo = [x for x in self.lanzados if f"{x[0]['cid']}/{x[1]}/{x[3][0]}" == h][-1]
        if etapa == "DIARIO":
            f = [periodo[0], periodo[1]]
            return dict(desde=periodo[0], hasta=periodo[1], diario=dict(fecha=f, h=[2.0, 3.0], l=[1.0, 1.5], c=[1.5, 2.5]))
        return dict(desde=periodo[0], hasta=periodo[1], operaciones=dict(ses=[periodo[0] - 1, periodo[0], periodo[0]], neto=[9.0, 4.0, 2.0]))


def test_espera_rechaza_la_version_anterior_y_corta_por_tiempo():
    k = _Kaggle(estados=("complete",)); reloj = iter(range(0, 10_000, 10))
    e = MK.Espera(k, espera_s=50, cada_s=0, dormir=lambda s: None, reloj=lambda: next(reloj))
    h = e.lanzar(dict(cid="X"), "DIARIO", {}, [20261001, 20261103])
    assert e.traer(h)["hasta"] == 20261103
    viejo = k.traer; k.traer = lambda h: dict(viejo(h), hasta=20261102)                           # el slug reusado devuelve la versión de ayer
    with pytest.raises(TimeoutError): e.traer(h)
    k2 = _Kaggle(estados=("error",)); e2 = MK.Espera(k2, cada_s=0, dormir=lambda s: None)
    with pytest.raises(RuntimeError, match="error"): e2.traer(e2.lanzar(dict(cid="Y"), "DIARIO", {}, [1, 2]))


def test_diarios_cachea_el_desarrollo_y_suma_el_sellado(tmp_path):
    dev, sel = MK.Espera(_Kaggle(), cada_s=0, dormir=lambda s: None), MK.Espera(_Kaggle(sellado="ds"), cada_s=0, dormir=lambda s: None)
    err = []
    d = MK.traer_diarios(MK.lanzar_diarios(["NQ"], 20261103, 20250805, sel, dev, tmp_path, err))["NQ"]
    assert d.fecha.tolist() == [20250805, 20260930, 20261001, 20261103] and not err
    assert sel.run.lanzados[0][2]["acta"]["preregistro"] == MK.ACTA_REGIMEN                        # el sellado siempre con acta
    MK.traer_diarios(MK.lanzar_diarios(["NQ"], 20261104, 20250805, sel, dev, tmp_path, err))
    assert len(dev.run.lanzados) == 1                                                              # el desarrollo no se relanza


def test_seguimiento_sellado_usa_acta_periodo_forward_y_saltea_zonas(tmp_path):
    from edgelab.cartera.ficha import Cartera, Ficha
    (tmp_path / "PRE.md").write_text("x"); c = Cartera(tmp_path / "c.json", libro_ventanas=tmp_path / "v.jsonl")
    base = dict(instrumento="NQ", preregistro="PRE.md", perdida_max_pts=50.0, ganancia_max_pts=50.0, margen_hueco_pts=0.0, friccion_pts=0.5,
                mu_util=1.0, sd_desarrollo=5.0, desde=20261102)
    c.alta(Ficha(id="A", familia="FA", cid="CA", regla=dict(spec=dict(experimento="x", sensor="NQ"), celdas=[[0], [1]], cortes={}, tope=None), **base), tmp_path)
    c.alta(Ficha(id="Z", familia="FZ", cid="CZ", regla=dict(spec=dict(experimento="x", sensor="NQ", datasets_extra=["zonas"]), celdas=[[0]],
                                                             cortes={}, tope=None), **base), tmp_path)
    k = _Kaggle(sellado="ds"); r = PA.actualizar(c, MK.Espera(k, cada_s=0, dormir=lambda s: None), 20261103)
    assert [x[3] for x in k.lanzados] == [[20261102, 20261103]] and k.lanzados[0][2]["acta"]["preregistro"] == "PRE.md"
    assert c.fichas["A"].ops == [[20261102, 3.0]]                                                  # (4 + 2) / 2 celdas; lo previo no entra
    assert any("zonas" in x.get("error", "") for x in r)


def test_sellado_de_varios_archivos_manda_el_diario(tmp_path):
    from edgelab.research.fuentes_ticks import _leer_sellado_futuro
    def pq(nombre, td, n):
        pd.DataFrame(dict(ts_utc_ns=np.arange(n, dtype=np.int64), price_ticks=np.ones(n, np.int64), volume=np.ones(n, np.int64),
                          trade_date=np.full(n, td, np.int64), contract=["NQ 12-26"] * n)).to_parquet(tmp_path / nombre)
        return str(tmp_path / nombre)
    a = pq("NQ_12-26_ticks.parquet", 20261026, 5); pq("NQ_12-26b_ticks.parquet", 20261027, 3)
    b = pq("NQ_20261026_ticks.parquet", 20261026, 7)
    t = _leer_sellado_futuro([a, b, str(tmp_path / "NQ_12-26b_ticks.parquet")])
    assert t.groupby("trade_date").size().to_dict() == {20261026: 7, 20261027: 3}


def test_etapa_diario():
    from edgelab.research import etapas as ET
    ctx = dict(ses=np.array([1, 1, 2]), h=np.array([5.0, 6, 7]), l=np.array([1.0, 2, 3]), c=np.array([4.0, 5, 6]))
    r = ET.ejecutar("DIARIO", None, ctx, friccion=0, extra_adverso=0)
    assert r["diario"] == dict(fecha=[1, 2], h=[6.0, 7.0], l=[1.0, 3.0], c=[5.0, 6.0])
