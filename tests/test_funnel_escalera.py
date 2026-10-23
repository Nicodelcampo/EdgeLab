"""Escalera del embudo y monitor secuencial contra verdad conocida, en los dos sentidos: ruido no se confirma y un edge plantado
SÍ se confirma (un gate que sólo sabe decir "no" no sirve para encontrar edges, contrato G2)."""
import numpy as np
import pytest

from edgelab.funnel import escalera as E
from edgelab.funnel.secuencial import EProceso, MonitorCandidato, combinar_e


def _ops(n_ses, por_ses, media, sd, seed):
    rng = np.random.default_rng(seed); s = np.repeat(np.arange(n_ses), por_ses)
    return rng.normal(media, sd, len(s)), s


def test_tamiz_fdr_controla_fraccion_y_conserva_potencia():
    rng = np.random.default_rng(1); fdp, pot = [], []
    for _ in range(200):
        m1 = 20; z = np.r_[rng.normal(3.0, 1, m1), rng.normal(0, 1, 480)]
        from statistics import NormalDist
        p = [1 - NormalDist().cdf(v) for v in z]
        nom = set(E.tamiz_fdr(p, 0.10, "bh")["nominadas"])
        fdp.append(len([i for i in nom if i >= m1]) / max(len(nom), 1)); pot.append(len([i for i in nom if i < m1]) / m1)
    assert np.mean(fdp) <= 0.12                     # FDR ~ q·pi0
    assert np.mean(pot) > 0.45                      # con Bonferroni (0,10/500) la potencia sería ~0,25


def test_tamiz_rechaza_p_invalidos():
    with pytest.raises(ValueError):
        E.tamiz_fdr([0.1, float("nan")])


def test_lordpp_controla_fdr_y_no_se_agota():
    rng = np.random.default_rng(7); fdps, ult = [], []
    from statistics import NormalDist
    for _ in range(150):
        L = E.LordPP(); falsos = verdaderos = 0
        for t in range(300):
            real = rng.random() < 0.1; z = rng.normal(3.0 if real else 0.0, 1)
            r = L.probar(1 - NormalDist().cdf(z))
            if r["rechazo"]: verdaderos += real; falsos += (not real)
        fdps.append(falsos / max(falsos + verdaderos, 1)); ult.append(L.nivel())
    assert np.mean(fdps) <= 0.06
    assert np.median(ult) > 1e-4                    # tras 300 pruebas sigue teniendo nivel (el alpha-investing actual quedó en ~1e-3 tras 8)
    assert E.LordPP.from_dict(L.to_dict()).nivel() == pytest.approx(L.nivel())


def test_edge_plantado_llega_a_lista_para_holdout_y_ruido_no():
    x, s = _ops(240, 3, 0.25, 2.0, 11); d = E.resumen_sesiones(x, s)
    xr, sr = _ops(200, 3, 0.25, 2.0, 12); r = E.resumen_sesiones(xr, sr)
    eco = E.economia(x, x - 0.05, s, periodos=np.repeat(np.arange(4), len(x) // 4 + 1)[:len(x)])
    v = E.evaluar(descubrimiento=d, nominada=True, n_pruebas_familia=40, replica=r, alfa_replica=0.02, economico=eco, n_esperado_holdout=900)
    assert v.estado == "LISTA_PARA_HOLDOUT", v.motivos
    xn, sn = _ops(240, 3, 0.0, 2.0, 13); rn = E.resumen_sesiones(*_ops(200, 3, 0.0, 2.0, 14))
    vn = E.evaluar(descubrimiento=E.resumen_sesiones(xn, sn), nominada=True, n_pruebas_familia=40, replica=rn, alfa_replica=0.02)
    assert vn.estado in ("SIN_POTENCIA", "REFUTADA")


def test_sin_potencia_no_es_refutada():
    """Un efecto real chico con pocas operaciones queda VIVO (con cuántas operaciones faltan), no muerto."""
    x, s = _ops(30, 1, 0.3, 2.0, 21); d = E.resumen_sesiones(x, s)
    v = E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=10)
    assert v.estado == "SIN_POTENCIA" and "operaciones" in v.siguiente_paso


def test_refutada_cuando_la_cota_optimista_no_llega_a_lo_util():
    x, s = _ops(300, 3, -0.4, 1.0, 31)
    v = E.evaluar(descubrimiento=E.resumen_sesiones(x, s), nominada=False, n_pruebas_familia=5)
    assert v.estado == "REFUTADA"


def test_recorte_es_no_lineal():
    fuerte, marginal = E.recorte_t(6.0, 1000), E.recorte_t(3.0, 1000)
    assert fuerte["conservado"] > 0.7 and marginal["conservado"] < 0.3


def test_n_efectivo_cuenta_variantes_correlacionadas_como_pocas():
    rng = np.random.default_rng(3); base = rng.normal(size=(500, 1))
    casi_iguales = base + 0.05 * rng.normal(size=(500, 20)); indep = rng.normal(size=(500, 20))
    assert E.n_efectivo(casi_iguales) < 4 and E.n_efectivo(indep) > 15


def test_economia_marca_concentracion_y_colapso():
    x = np.r_[np.full(95, -0.1), np.full(5, 10.0)]
    eco = E.economia(x, x - 1.0, periodos=["a"] * 50 + ["b"] * 50)
    assert not eco["duros"]["sin_top5_positivo"] and not eco["pasa"]


def test_eproceso_tipo_I_mirando_siempre():
    """Bajo H0 (media 0) y mirando después de CADA operación, la tasa de falsos rechazos queda <= alfa (Ville)."""
    rng = np.random.default_rng(5); rech = 0; sims = 400
    for _ in range(sims):
        e = EProceso(0.0, -1.2, 5.2)
        for x in rng.choice([-1.0, 5.0], p=[5 / 6, 1 / 6], size=600) + rng.uniform(-0.2, 0.2, 600):
            if e.agregar(float(x)) >= 20: rech += 1; break
    assert rech / sims <= 0.05


def test_monitor_confirma_edge_real_y_refuta_futil():
    rng = np.random.default_rng(9)
    m = MonitorCandidato(piso=-1.3, techo=5.3, mu_util=0.15)
    st = m.agregar((rng.choice([-1.0, 5.0], p=[0.75, 0.25], size=1500) - 0.05).tolist())   # media 0,45 R
    assert st["estado"] == "EDGE_CONFIRMADO"
    f = MonitorCandidato(piso=-1.3, techo=5.3, mu_util=0.3)
    st = f.agregar((rng.choice([-1.0, 5.0], p=[5 / 6, 1 / 6], size=3000) - 0.05).tolist())   # media -0,05 R
    assert st["estado"] == "REFUTADO_FUTILIDAD"
    with pytest.raises(ValueError, match="LIMITE_VIOLADO"):
        MonitorCandidato(piso=-1.3, techo=5.3, mu_util=0.3).agregar(-3.0)
    assert combinar_e(2.0, 3.0) == 6.0


def test_salida_compatible_con_el_autopilot():
    out = E.para_autopilot([dict(test="NQ/regla/disc", p=0.01, effect=0.3), dict(test="NQ/regla/rep/1", p=0.02, effect=0.2)])
    import sys, types
    if "fcntl" not in sys.modules:                   # analyze importa fdr.py, que usa fcntl (Debian); acá sólo se usa Holm
        try: import fcntl  # noqa: F401
        except ImportError: sys.modules["fcntl"] = types.ModuleType("fcntl")
    from edgelab.autopilot import analyze
    recs = analyze.records(out)
    assert [r["test"] for r in recs] == ["NQ/regla/disc", "NQ/regla/rep/1"]
    assert analyze.decide(out, 0.05, 2)["hit"] is True


def test_economia_regimen_reciente_no_mata_lo_actual_pero_si_lo_viejo():
    x = np.r_[np.full(60, -0.05), np.full(20, 2.0)]                              # gana sólo al final
    per = ["202508"] * 20 + ["202509"] * 20 + ["202510"] * 20 + ["202511"] * 20
    eco = E.economia(x, x - 0.1, periodos=per)
    assert eco["regimen_reciente"] and eco["duros"]["ningun_periodo_80pct"]
    viejo = E.economia(x[::-1], x[::-1] - 0.1, periodos=per)                     # mismo P&L pero ganado al principio
    assert not viejo["regimen_reciente"] and not viejo["duros"]["ningun_periodo_80pct"]
