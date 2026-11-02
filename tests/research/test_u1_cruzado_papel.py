"""U1-CRUZADO en papel: la etapa OPERAR corre la regla congelada (E1A/T3/S3, tope 3×) con el código del descubrimiento y filtra por
sesión de evaluación; el seguimiento usa la etapa declarada en la ficha."""
import numpy as np
import pandas as pd

from edgelab.research import etapas as ET, u1_cruzado as U1C, u1_cruzado_papel as P


def test_operar_filtra_regla_tope_y_desde(monkeypatch):
    llamado = {}
    def falso(cu, cn, tope=None):
        llamado["tope"] = tope
        return pd.DataFrame(dict(ejecucion=["E1A/T3/S3", "E1A/T1/S3", "E1A/T3/S3", "E1A/T3/S3"], bruto=[10.0, 99.0, np.nan, -4.0],
                                 ses=[20261102, 20261102, 20261103, 20261030], t=[3.0, 1.0, 2.0, 0.0]))
    monkeypatch.setattr(U1C, "operar", falso)
    r = ET.ejecutar("OPERAR", P, dict(desde_eval=20261101), friccion=1.5, extra_adverso=0, cx_ej={})
    assert llamado["tope"] == ("mult", 3.0) and r["operaciones"]["ses"] == [20261102] and r["operaciones"]["neto"] == [8.5]


def test_papel_usa_la_etapa_de_la_ficha(tmp_path):
    from edgelab.cartera import papel as PA
    from edgelab.cartera.ficha import Cartera, Ficha
    (tmp_path / "PRE.md").write_text("x"); c = Cartera(tmp_path / "c.json", libro_ventanas=tmp_path / "v.jsonl")
    c.alta(Ficha(id="U", familia="F", cid="U1-CRUZADO", instrumento="NQ", regla=dict(spec=dict(experimento="x", sensor="DK:USATECHIDXUSD",
           ejecucion="NQ"), celda=[0], cortes={}, tope=None, etapa="OPERAR"), preregistro="PRE.md", perdida_max_pts=300.0,
           ganancia_max_pts=300.0, margen_hueco_pts=0.0, friccion_pts=1.5, mu_util=5.0, sd_desarrollo=60.0, desde=20261102), tmp_path)
    vistos = []
    class R:
        def lanzar(self, spec, etapa, params, periodo): vistos.append(etapa); return "h"
        def traer(self, h): return dict(operaciones=dict(ses=[20261102], neto=[12.0]))
    PA.actualizar(c, R(), 20261103)
    assert vistos == ["OPERAR"] and c.fichas["U"].ops == [[20261102, 12.0]] and c.fichas["U"].evaluada_hasta == 20261103
