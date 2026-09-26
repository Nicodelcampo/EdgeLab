"""G2 — verificación contra datos sintéticos con VERDAD CONOCIDA.

Una prueba estadística que nadie verificó es peor que no tenerla: da una
sensación de rigor sin el rigor. Cada test acá construye un caso donde la
respuesta correcta se sabe de antemano y exige que G2 la dé.

Los dos casos que importan en cada prueba:
  - **ruido puro** → el gate debe RECHAZAR (o al menos no aprobar);
  - **efecto real plantado** → el gate debe APROBAR.

Un gate que solo pasa el primero es un gate que dice "no" a todo, y no sirve
para encontrar edges.

## Enmienda G2-A1 (2026-08-10)

`mcpt()` se renombró `temporal_concentration_test()` y salió de los gates
duros — ver el docstring de `edgelab.research.g2` y
`docs/incidents/AMENDMENT_G2-A1_2026-08-10.md`. La clase de fixture que
faltaba (auditoría, ítem 6) está al final de este archivo: un edge
**genuinamente estable**, el caso que el viejo `evaluar()` rechazaba y que
`g2_decision.PrimaryCI` aprueba correctamente.
"""
import math

import pytest

from edgelab.research import g2
from edgelab.stats.cluster_estimand import (
    SessionAggregate, aggregate_sessions, studentized_stationary_interval,
)


def _ruido(n, seed=7, amp=1.0):
    """Serie determinista sin señal: media cero por construcción."""
    rng = g2._lcg(seed)
    return [amp * (((next(rng) >> 8) % 2001) - 1000) / 1000.0 for _ in range(n)]


# --------------------------------------------------------------------------- #
# 1. Concentración temporal (ex-MCPT) — DIAGNÓSTICO, no gate. Ver enmienda G2-A1.
# --------------------------------------------------------------------------- #
def test_concentracion_exige_el_minimo_de_permutaciones_del_contrato():
    with pytest.raises(ValueError):
        g2.temporal_concentration_test([1.0, -1.0], ["s1", "s2"], n_perm=999)


def test_concentracion_sobre_ruido_no_declara_significancia():
    r = _ruido(400)
    ses = ["s%03d" % (i // 20) for i in range(400)]
    p, _ = g2.temporal_concentration_test(r, ses, n_perm=1000)
    assert p > 0.05, (
        "sobre ruido puro dio p=%.4f: estaria marcando concentracion en azar" % p)


def test_concentracion_detecta_un_efecto_concentrado_y_real():
    # el efecto vive en la primera mitad de las sesiones: la permutación de
    # bloques debe encontrar improbable esa concentración
    r, ses = [], []
    for s in range(20):
        for i in range(20):
            r.append(1.0 if s < 10 else -1.0)
            ses.append("s%03d" % s)
    p, obs = g2.temporal_concentration_test(r, ses, n_perm=1000)
    assert p <= 0.05, "no detecto un efecto concentrado plantado (p=%.4f)" % p
    assert obs > 0


def test_concentracion_es_reproducible():
    r = _ruido(200)
    ses = ["s%03d" % (i // 10) for i in range(200)]
    a, _ = g2.temporal_concentration_test(r, ses, n_perm=1000, seed=42)
    b, _ = g2.temporal_concentration_test(r, ses, n_perm=1000, seed=42)
    assert a == b, "el p-valor debe ser determinista con la misma semilla"


def test_concentracion_con_una_sola_sesion_no_finge_significancia():
    p, _ = g2.temporal_concentration_test([1.0] * 50, ["unica"] * 50, n_perm=1000)
    assert p == 1.0, "sin bloques que permutar no se puede afirmar nada"


def test_concentracion_sobre_edge_ESTABLE_no_es_significativa_YESO_ESTA_BIEN():
    """El caso que la enmienda G2-A1 existe para documentar.

    Un edge parejo en el tiempo -exactamente lo que G1 exige, cero
    concentración- da p ALTO acá, porque el estadístico mide concentración,
    no presencia de señal. Si esto todavía fuera un gate duro, RECHAZARÍA a
    un candidato que cumple G1. Ver `test_edge_estable_...` en la sección de
    fixtures cruzados: la MISMA serie, evaluada con el gate real (PrimaryCI),
    aprueba.
    """
    r, ses = [], []
    for s in range(200):
        # parejo en el tiempo, con ruido -- sin concentracion en ninguna mitad
        r.append(1.0 + (((s * 2654435761) % 1000) - 500) / 2000.0)
        ses.append("s%03d" % s)
    p, _ = g2.temporal_concentration_test(r, ses, n_perm=1000)
    assert p > 0.30, (
        "un edge parejo en el tiempo dio p=%.4f: si esto gateara, rechazaria "
        "casi cualquier edge que cumpla la estabilidad de G1" % p)


# --------------------------------------------------------------------------- #
# 2. PBO vía CSCV
# --------------------------------------------------------------------------- #
def test_pbo_sobre_ruido_esta_centrado_en_un_medio():
    """Si nada tiene señal, el ganador in-sample rankea al azar OOS ⇒ PBO ≈ 0.5.

    Se mide sobre MUCHAS matrices, no sobre una: una sola matriz 40x12 de ruido
    da PBO entre 0.03 y 0.91 según la semilla. Afirmar algo sobre un solo sorteo
    sería testear el ruido, no la herramienta.
    """
    T, C = 40, 12
    vals = []
    for seed in range(30):
        rng = g2._lcg(1000 + seed)
        m = [[(((next(rng) >> 8) % 2001) - 1000) / 1000.0 for _ in range(C)]
             for _ in range(T)]
        vals.append(g2.pbo_cscv(m, s=8)[0])
    vals.sort()
    mediana = vals[len(vals) // 2]
    assert 0.35 <= mediana <= 0.65, (
        "con puro ruido la mediana del PBO dio %.2f; la teoria dice ~0.5" % mediana)


def test_pbo_genera_todas_las_particiones_cscv():
    T, C = 40, 12
    rng = g2._lcg(99)
    m = [[(((next(rng) >> 8) % 2001) - 1000) / 1000.0 for _ in range(C)]
         for _ in range(T)]
    _, lam = g2.pbo_cscv(m, s=8)
    assert len(lam) == math.comb(8, 4) == 70


def test_pbo_bajo_cuando_un_config_es_genuinamente_mejor():
    """Un config con ventaja real y estable debe dar PBO bajo."""
    T, C = 40, 12
    rng = g2._lcg(5)
    m = []
    for _ in range(T):
        fila = [(((next(rng) >> 8) % 2001) - 1000) / 1000.0 for _ in range(C)]
        fila[3] += 3.0                      # ventaja real, presente en TODO el tiempo
        m.append(fila)
    pbo, _ = g2.pbo_cscv(m, s=8)
    assert pbo <= g2.PBO_MAX, (
        "con una ventaja real y estable el PBO dio %.2f: el gate rechazaria un "
        "edge verdadero" % pbo)


def test_pbo_rechaza_matrices_degeneradas():
    with pytest.raises(ValueError):
        g2.pbo_cscv([[1.0, 2.0]] * 4, s=8)          # menos filas que S
    with pytest.raises(ValueError):
        g2.pbo_cscv([[1.0] for _ in range(40)], s=8)  # un solo config


# --------------------------------------------------------------------------- #
# 3. Deflated Sharpe Ratio
# --------------------------------------------------------------------------- #
def test_dsr_castiga_el_numero_de_intentos():
    """El MISMO Sharpe vale menos si se probaron más variantes.

    OJO: `sharpe` es **por observación**, no anualizado. Un SR/trade de 0.1 ya
    es fuerte; con 0.5 el DSR satura en 1.0 y el test no mediria nada.
    """
    base = dict(n_obs=500, skew=0.0, kurt=3.0)
    d1 = g2.deflated_sharpe(0.1, n_trials=1, **base)
    d48 = g2.deflated_sharpe(0.1, n_trials=48, **base)
    d1000 = g2.deflated_sharpe(0.1, n_trials=1000, **base)
    assert d1 > d48 > d1000, "el DSR debe caer al crecer N_eff"
    assert d1 > 0.95 and d1000 < 0.25


def test_dsr_satura_con_un_sharpe_por_trade_irreal():
    """Documenta la trampa: SR/trade=0.5 sobre 500 trades es descomunal.

    Si alguien ve DSR=1.0 y lo celebra, el problema esta en la escala del
    Sharpe que le paso, no en la estrategia.
    """
    assert g2.deflated_sharpe(0.5, n_obs=500, n_trials=1000) > 0.9999


def test_dsr_bajo_para_un_sharpe_mediocre_con_muchos_intentos():
    assert g2.deflated_sharpe(0.1, n_obs=300, n_trials=48) < 0.5


def test_dsr_castiga_la_cola_izquierda_gruesa():
    """Mismo Sharpe, peor asimetría y curtosis ⇒ menos DSR."""
    limpio = g2.deflated_sharpe(0.8, n_obs=500, n_trials=48, skew=0.0, kurt=3.0)
    feo = g2.deflated_sharpe(0.8, n_obs=500, n_trials=48, skew=-2.0, kurt=12.0)
    assert feo < limpio


def test_expected_max_sharpe_crece_con_los_intentos():
    v = 1.0 / 499
    assert (g2.expected_max_sharpe(2, v) < g2.expected_max_sharpe(48, v)
            < g2.expected_max_sharpe(1000, v))


# --------------------------------------------------------------------------- #
# 4. Walk-forward
# --------------------------------------------------------------------------- #
FOLDS = ["f1", "f2", "f3", "f4"]


def test_wf_no_evalua_el_primer_fold():
    per = {"A": {f: 1.0 for f in FOLDS}}
    tot, det = g2.walk_forward(per, FOLDS)
    assert [d["fold"] for d in det] == ["f2", "f3", "f4"], (
        "el primer fold no tiene historia previa: no es evaluable OOS")
    assert tot == 3.0


def test_wf_selecciona_solo_con_folds_ANTERIORES():
    # 'trampa' es el mejor SOLO en el ultimo fold: si el WF mirara el futuro,
    # lo elegiria; eligiendo con el pasado, nunca lo hace.
    per = {"solido": {"f1": 1.0, "f2": 1.0, "f3": 1.0, "f4": 1.0},
           "trampa": {"f1": -5.0, "f2": -5.0, "f3": -5.0, "f4": 99.0}}
    tot, det = g2.walk_forward(per, FOLDS)
    assert all(d["ganador_in_sample"] == "solido" for d in det)
    assert tot == 3.0, "el WF no debe capturar el 99 del futuro"


def test_wf_negativo_cuando_el_ganador_no_generaliza():
    per = {"A": {"f1": 10.0, "f2": -3.0, "f3": -3.0, "f4": -3.0},
           "B": {"f1": -1.0, "f2": 0.5, "f3": 0.5, "f4": 0.5}}
    tot, _ = g2.walk_forward(per, FOLDS)
    assert tot < 0, "un ganador que no generaliza debe dar WF-OOS negativo"


# --------------------------------------------------------------------------- #
# 5. Sensibilidad paramétrica
# --------------------------------------------------------------------------- #
def test_sensibilidad_detecta_un_pico_aislado():
    exp = {"g": 5.0, "v1": -1.0, "v2": -2.0, "v3": -0.5, "v4": -3.0}
    med, pos, n = g2.parameter_sensitivity(exp, "g", ["v1", "v2", "v3", "v4"])
    assert med < 0 and pos == 0 and n == 4, "un acantilado debe reprobar"


def test_sensibilidad_acepta_una_meseta():
    exp = {"g": 5.0, "v1": 4.0, "v2": 3.5, "v3": 4.2, "v4": 3.0}
    med, pos, n = g2.parameter_sensitivity(exp, "g", ["v1", "v2", "v3", "v4"])
    assert med > 0 and pos == 4


def test_sensibilidad_sin_vecinos_no_inventa_un_valor():
    med, pos, n = g2.parameter_sensitivity({"g": 1.0}, "g", ["no_existe"])
    assert med is None and n == 0


# --------------------------------------------------------------------------- #
# Fixture cruzado — el hallazgo central de la enmienda G2-A1, verificado
# --------------------------------------------------------------------------- #
def _edge_estable_200_sesiones():
    """200 sesiones, 2 trades c/u, expectativa positiva pareja en el tiempo —
    ni concentrada en la primera mitad ni en la segunda. Exactamente el perfil
    que G1 exige (ningún fold aporta > 80% del P&L).

    La varianza tiene que estar ENTRE sesiones, no sólo adentro de cada una:
    un primer intento con `(0.5+j, 0.5-j)` sumaba siempre 1.0 exacto por
    sesión -- varianza HAC nula, degenerado, no "estable". Acá el total por
    sesión varía de verdad (positivo en promedio, con sesiones perdedoras
    incluidas, como cualquier edge real).
    """
    trades = {}
    for s in range(200):
        # determinista, en aprox [-1.5, 1.5), sin tendencia con s
        total = 0.5 + (((s * 2654435761) % 3000) - 1500) / 1000.0
        intra = 0.1                                    # como se reparte entre los 2 trades
        sid = "s%03d" % s
        trades[sid] = (total / 2 + intra, total / 2 - intra)
    return trades


def test_edge_estable_lo_rechazaria_la_concentracion_pero_PrimaryCI_lo_aprueba():
    """El hallazgo central de la auditoría, como regresión permanente.

    Misma serie que `test_concentracion_sobre_edge_ESTABLE...`: acá se prueba
    el otro lado. El gate REAL (bootstrap estacionario-t por sesión,
    `lower > 0`, la máquina de `g2_decision.PrimaryCI`) sobre este edge
    genuinamente estable debe APROBAR — al revés de lo que el viejo
    `evaluar()` habría hecho con un p de concentración alto.
    """
    trades = _edge_estable_200_sesiones()
    calendario = sorted(trades)
    clusters = aggregate_sessions(calendario, trades)

    # el mismo dato, visto como concentracion temporal: p alto, "no significativo"
    returns = [v for sid in calendario for v in trades[sid]]
    session_ids = [sid for sid in calendario for _ in trades[sid]]
    p_concentracion, _ = g2.temporal_concentration_test(returns, session_ids, n_perm=1000)
    assert p_concentracion > 0.30, "el fixture no es estable como se pretendia"

    # el mismo dato, visto con el gate real: aprueba
    ic = studentized_stationary_interval(clusters, n_replicates=2000, seed=20260810,
                                         confidence=0.95)
    assert ic.lower > 0, (
        "PrimaryCI deberia aprobar un edge parejo y positivo -- lower=%.4f" % ic.lower)

# La exclusividad de cada umbral (un solo gate en rojo reprueba todo G2) ya
# esta cubierta -para la definicion UNICA vigente tras la enmienda G2-A1- por
# `test_ic_y_gate_bloquean` en test_g2_decision.py.
