"""Controles de la etapa PERSIST: ruido puro sin persistencia, persistencia plantada encontrada, calidad estática separada por el
desfase, y la etapa corre de punta a punta sobre sintéticos."""
import numpy as np

from edgelab.research import persistencia as PE


def _M(meses=36, celdas=2000, regimen=0.0, estatica=0.0, seed=0):
    r = np.random.default_rng(seed); C = np.full((meses, celdas), 12.0)
    base = estatica * r.normal(size=celdas)                                   # calidad fija por celda
    estado = np.zeros((meses, celdas)); e = r.normal(size=celdas)
    for t in range(meses):                                                     # régimen: AR(1) mensual por celda
        e = 0.8 * e + 0.6 * r.normal(size=celdas); estado[t] = regimen * e
    mu = base + estado
    S = (mu + r.normal(size=(meses, celdas)) * 3 / np.sqrt(C)) * C
    Q = S ** 2 / C + 9 * C
    return dict(S=S.astype(np.float32), Q=Q.astype(np.float32), C=C.astype(np.float32), meses=[f"m{i:02d}" for i in range(meses)])


def test_ruido_sin_persistencia_ni_canasta():
    M = _M()
    p = PE.persistencia(M, 3, 1, 10)
    assert abs(p["resumen"]["rho"]["media"]) < 0.03
    m = PE.meta_regla(M, 3, 100, 20)
    assert abs(m["resumen"]["neto_por_op"]["t"]) < 3


def test_regimen_plantado_se_encuentra_y_desaparece_con_desfase():
    M = _M(regimen=1.0, seed=1)
    p0, p12 = PE.persistencia(M, 3, 1, 10, desfase=0), PE.persistencia(M, 3, 1, 10, desfase=12)
    assert p0["resumen"]["rho"]["media"] > 0.2 and abs(p12["resumen"]["rho"]["media"]) < 0.05
    assert PE.meta_regla(M, 3, 100, 20)["resumen"]["neto_por_op"]["media"] > 0


def test_calidad_estatica_persiste_con_desfase():
    M = _M(estatica=1.0, seed=2)
    p0, p12 = PE.persistencia(M, 3, 1, 10, desfase=0), PE.persistencia(M, 3, 1, 10, desfase=12)
    assert p0["resumen"]["rho"]["media"] > 0.2 and p12["resumen"]["rho"]["media"] > 0.2      # estática: no es régimen


def test_etapa_persist_corre_sobre_sinteticos(monkeypatch):
    from edgelab.research import etapas as ET, grilla_generica as GG, sintetico, u1_indaga as U
    monkeypatch.setattr(U, "INDICADORES", ["LUX-IMB"], raising=False)
    ctx = GG.contexto_m1(sintetico.bloques(dias=90, planta=False, seed=3), tick=0.25)
    r = ET.ejecutar("PERSIST", U, ctx, friccion=1.0, extra_adverso=0.5, log=lambda s: None)
    assert r["celdas"] == GG.n_celdas(U, r["cortes"]) and len(r["meses"]) >= 3 and r["persistencia"] and r["meta_regla"]
