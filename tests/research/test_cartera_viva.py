"""Cartera viva (edgelab/cartera): régimen causal, afinidad con contracción, ciclo de vida (alta abre la ventana, futilidad retira,
e-proceso promueve), asignación dentro del presupuesto de la cuenta, cola con plazos y ciclo diario con modo seguro."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from edgelab.cartera import afinidad as AF, asignacion as AS, ciclo as CI, investigacion as IV, regimen as RG
from edgelab.cartera.ficha import Cartera, Ficha


def _diario(n=200, seed=0, drift=0.0):
    rng = np.random.default_rng(seed); r = rng.normal(drift, 0.01, n); c = 100 * np.exp(np.cumsum(r))
    rg = np.abs(rng.normal(0, 1, n)) + 0.5
    f = pd.date_range("2025-01-01", periods=n, freq="B")
    return pd.DataFrame(dict(fecha=f.year * 10000 + f.month * 100 + f.day, h=c + rg, l=c - rg, c=c))


def _ficha(id_="A", inst="NQ", **kw):
    base = dict(id=id_, familia=f"FAM_{id_}", cid=f"C-{id_}", instrumento=inst, regla=dict(spec=dict(experimento="x", sensor=inst), celda=[0],
                cortes={}, tope=None), preregistro="PRE.md", perdida_max_pts=10.0, ganancia_max_pts=20.0, margen_hueco_pts=2.0,
                friccion_pts=0.5, mu_util=1.0, sd_desarrollo=8.0, desde=20261102)
    base.update(kw); return Ficha(**base)


@pytest.fixture
def cart(tmp_path):
    (tmp_path / "PRE.md").write_text("pre-registro")
    return Cartera(tmp_path / "cartera.json", libro_ventanas=tmp_path / "ventanas.jsonl"), tmp_path


def test_regimen_es_causal_y_etiqueta_con_cortes_congelados():
    d = _diario()
    r1 = RG.rasgos_diarios(d); r2 = RG.rasgos_diarios(d.iloc[:150])
    pd.testing.assert_frame_equal(r1.iloc[:150].reset_index(drop=True), r2.reset_index(drop=True))     # truncar no cambia el pasado
    d2 = d.copy(); d2.loc[149, ["h", "l", "c"]] *= 1.5                                                       # cambiar el día 149 ...
    assert RG.rasgos_diarios(d2).iloc[149].equals(r1.iloc[149])                                             # ... no cambia sus rasgos
    cortes = RG.congelar_cortes(r1, int(d.fecha.iloc[120]))
    et = RG.etiquetar(r1, cortes)
    assert et.dropna().str.match(r"^(BAJA|MEDIA|ALTA)\|(BAJISTA|RANGO|ALCISTA)$").all()
    assert RG.t_newey_west(np.r_[np.ones(30) * 0.01 + np.random.default_rng(1).normal(0, 0.001, 30)]) > 5


def test_regimen_siguiente_usa_solo_lo_cerrado():
    d = _diario(); cortes = RG.congelar_cortes(RG.rasgos_diarios(d), int(d.fecha.iloc[120]))
    s, m, x = CI.regimen_siguiente(d, cortes)
    assert len(s) == len(d) and m is not None and np.isfinite(x["rv_rel"])


def test_afinidad_contrae_y_suspende():
    reg = pd.Series({1: "A", 2: "A", 3: "B", 4: "B"})
    ops = pd.DataFrame(dict(ses=[1, 2, 3, 4] * 10, neto=[5.0, 5.0, -3.0, -3.0] * 10))
    t = AF.tabla(ops, reg).set_index("reg")
    assert t.loc["A", "mult"] > 1 and t.loc["B", "mult"] == 0.0
    assert AF.multiplicador(ops, reg, "B") == 0.0 and AF.multiplicador(ops, reg, None) == 1.0
    assert AF.multiplicador(ops, reg, "Z") == 1.0                                                          # régimen nunca visto: neutro


def test_alta_exige_preregistro_y_abre_la_ventana(cart):
    c, tmp = cart
    with pytest.raises(ValueError, match="pre-registro"):
        c.alta(_ficha(preregistro="NO_EXISTE.md"), tmp)
    f = c.alta(_ficha(), tmp)
    assert f.nivel == "PAPEL" and json.loads((tmp / "ventanas.jsonl").read_text().splitlines()[0])["familia"] == "FAM_A"
    with pytest.raises(ValueError, match="ya existe"):
        c.alta(_ficha(), tmp)


def test_futilidad_retira_y_no_resucita(cart):
    c, tmp = cart; c.alta(_ficha(), tmp)
    r = c.agregar_ops("A", [(20261102 + i, -3.0) for i in range(80)])
    assert r["estado"] == "RETIRADA" and ("futilidad" in r["motivo"] or "drawdown" in r["motivo"])
    c2 = Cartera(tmp / "cartera.json", libro_ventanas=tmp / "otro.jsonl")
    with pytest.raises(ValueError, match="retirada"):
        c2.alta(_ficha(id_="A2", familia="FAM_A", cid="C-A"), tmp)


def test_e_proceso_promueve_a_real_y_agregar_es_idempotente(cart):
    c, tmp = cart; c.alta(_ficha(), tmp)
    filas = [(20261102 + i, 8.0 if i % 4 else -2.0) for i in range(60)]
    r = c.agregar_ops("A", filas)
    assert r["nivel"] == "REAL"
    n = len(c.fichas["A"].ops); c.agregar_ops("A", filas)
    assert len(c.fichas["A"].ops) == n


def test_asignacion_respeta_presupuesto_y_habilitacion():
    f1, f2, f3 = _ficha("A", "NQ", nivel="REAL"), _ficha("B", "ES", nivel="REAL"), _ficha("C", "NQ")
    demo = dict(id="demo", tipo="demo", perdida_dia_max_usd=1000, drawdown_max_usd=2000)
    a = AS.asignar(demo, [f1, f2, f3], {"A": 1.0, "B": 2.0, "C": 0.0})
    assert a["operar"] and a["riesgo_asignado_usd"] <= a["presupuesto_usd"] + 1e-9
    assert {p["estrategia"] for p in a["posiciones"] if p["contratos"]} <= {"A", "B"}                   # C suspendida por régimen
    real = dict(id="axi", tipo="propio", perdida_dia_max_usd=500, drawdown_max_usd=2000)
    assert not AS.asignar(real, [f1], {"A": 1.0})["operar"]                                              # sin habilitar por una persona
    a2 = AS.asignar(dict(real, habilitada=True), [f1, f3], {"A": 1.0, "C": 1.0})
    assert {p["estrategia"] for p in a2["posiciones"]} == {"A"}                                          # sólo nivel REAL en cuentas reales


def test_cola_prioriza_retiros_y_huecos():
    f = _ficha("A", "NQ")
    emb = [dict(cid="X", familia="FX", instrumento="NQ", fase="PISTAS_VIVAS", p_canasta=0.05, media_canasta=3.0, estado=""),
           dict(cid="Y", familia="FY", instrumento="ES", fase="BLOQUEADA", p_canasta=None, media_canasta=None, estado="")]
    q = IV.cola([f], {"NQ": "MEDIA|RANGO"}, {"A": 1.0}, [dict(id="Z", motivo="futilidad")], emb, objetivo_por_instrumento=2, instrumentos=("NQ",))
    assert [x["accion"] for x in q[:2]] == ["REEMPLAZAR", "HUECO_DE_REGIMEN"]
    assert {x["accion"] for x in q} >= {"ALTA_FORWARD", "DESTRABAR"}


class _Runner:
    def __init__(self, filas): self.filas = filas
    def lanzar(self, spec, etapa, params, periodo): assert etapa == "ANALIZAR_REGLA" and params["operaciones"]; return "h"
    def traer(self, h): return dict(operaciones=dict(ses=[s for s, _ in self.filas], neto=[x for _, x in self.filas]))


def test_ciclo_completo_y_modo_seguro(cart, tmp_path):
    c, tmp = cart; c.alta(_ficha(nivel="PAPEL"), tmp)
    d = _diario(); d["fecha"] = d.fecha  # NQ diario sintético
    cortes = RG.congelar_cortes(RG.rasgos_diarios(d), int(d.fecha.iloc[120]))
    cfg = dict(cartera=str(tmp / "cartera.json"), libro_ventanas=str(tmp / "ventanas.jsonl"), salida=str(tmp / "planes"), alertas=str(tmp / "alertas.jsonl"),
               cortes_regimen={"NQ": cortes}, instrumentos=["NQ"], objetivo_por_instrumento=1,
               cuentas=[dict(id="demo", tipo="demo", perdida_dia_max_usd=1000, drawdown_max_usd=2000)])
    plan = CI.correr(cfg, 20261105, {"NQ": d}, runner=_Runner([(20261103, 4.0), (20261104, -1.0)]), repo=tmp)
    assert "modo_seguro" not in plan and plan["cuentas"][0]["operar"] and (tmp / "planes" / "20261105" / "PLAN.md").exists()
    assert plan["cartera"][0]["n_forward"] == 2
    roto = CI.correr(dict(cfg, cuentas=[dict(id="x", firma="NoExiste", plan="P")]), 20261106, {"NQ": d}, repo=tmp)
    assert "modo_seguro" in roto and "alertas.jsonl" in str(cfg["alertas"]) and (tmp / "alertas.jsonl").read_text()


def test_sesion_cerrada_salta_fin_de_semana():
    from datetime import datetime, timezone
    assert CI.sesion_cerrada(datetime(2026, 11, 1, 12, tzinfo=timezone.utc)) == 20261030                # domingo -> viernes
    assert CI.sesion_cerrada(datetime(2026, 11, 2, 22, tzinfo=timezone.utc)) == 20261102                # lunes después del cierre
