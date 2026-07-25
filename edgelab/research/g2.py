"""G2 — Robustez estadística. Implementa `docs/edge_validation_contract.md` §G2.

Se construye **antes** de tener un candidato positivo, a propósito: escribir el
test estadístico después de ver un resultado bueno invita a ajustarlo hasta que
lo apruebe. Acá los umbrales vienen del contrato sellado y las funciones se
verifican contra datos sintéticos con verdad conocida.

Cinco pruebas duras (§G2):

1. `mcpt`             — permutación por bloques de sesión, p ≤ 0.05, ≥1000 perms.
2. `pbo_cscv`         — PBO ≤ 0.50 vía CSCV con S = 8.
3. `deflated_sharpe`  — DSR > 0 con nº de trials = N_eff del manifiesto.
4. `walk_forward`     — re-selección por contrato; agregado WF-OOS neto > 0.
5. `parameter_sensitivity` — vecinos ±1 paso: mediana de expectancies netas > 0.

Sin dependencias nuevas: `statistics.NormalDist` (stdlib) cubre Φ y Φ⁻¹.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from statistics import NormalDist

# --- umbrales DUROS del contrato (no se tocan sin enmienda aprobada) --------
MCPT_MAX_P = 0.05
MCPT_MIN_PERMS = 1000
PBO_MAX = 0.50
CSCV_S = 8
DSR_MIN = 0.0

_N = NormalDist()
_EULER = 0.5772156649015329


@dataclass
class G2Result:
    name: str
    value: float
    threshold: float
    passed: bool
    detail: str = ""

    def __str__(self):
        return "%-22s %10.4f  (umbral %.4f)  %s%s" % (
            self.name, self.value, self.threshold,
            "PASS" if self.passed else "FAIL",
            ("  — " + self.detail) if self.detail else "")


# --------------------------------------------------------------------------- #
# 1. MCPT — permutación por bloques de SESIÓN
# --------------------------------------------------------------------------- #
def _lcg(seed):
    """Generador determinista propio: el resultado no puede depender de la
    versión de numpy ni del estado global de random."""
    x = seed & 0xFFFFFFFF
    while True:
        x = (1664525 * x + 1013904223) & 0xFFFFFFFF
        yield x


def _shuffle(seq, rng):
    """Fisher-Yates con el LCG: reproducible entre corridas y máquinas."""
    a = list(seq)
    for i in range(len(a) - 1, 0, -1):
        j = next(rng) % (i + 1)
        a[i], a[j] = a[j], a[i]
    return a


def mcpt(returns, session_ids, n_perm=MCPT_MIN_PERMS, seed=12345):
    """p-valor por permutación de BLOQUES DE SESIÓN (§G2).

    `returns[i]` es el neto del trade i y `session_ids[i]` su sesión. La hipótesis
    nula permuta el orden de las **sesiones completas**, no de los trades
    individuales: eso preserva la autocorrelación intradía, que es justamente lo
    que una permutación ingenua destruiría (inflando la significancia).

    El estadístico es la **suma neta**. p = (1 + #{perm ≥ observado}) / (1 + n_perm),
    la forma sesgada-conservadora: nunca devuelve p = 0.
    """
    if n_perm < MCPT_MIN_PERMS:
        raise ValueError("el contrato exige >= %d permutaciones, no %d"
                         % (MCPT_MIN_PERMS, n_perm))
    if len(returns) != len(session_ids):
        raise ValueError("returns y session_ids deben tener el mismo largo")
    if not returns:
        return 1.0, 0.0

    bloques = {}
    for r, s in zip(returns, session_ids):
        bloques.setdefault(s, []).append(r)
    claves = sorted(bloques)
    if len(claves) < 2:
        # Con una sola sesión no hay nada que permutar: se declara, no se finge.
        return 1.0, float(sum(returns))

    # Estadístico observado. Bajo permutación de bloques la SUMA total no cambia,
    # así que el estadístico es la suma de los k primeros bloques (la mitad
    # temporal): mide si el resultado se concentra donde realmente ocurrió.
    k = max(1, len(claves) // 2)
    obs = sum(sum(bloques[c]) for c in claves[:k])

    rng = _lcg(seed)
    peores = 0
    for _ in range(n_perm):
        perm = _shuffle(claves, rng)
        stat = sum(sum(bloques[c]) for c in perm[:k])
        if stat >= obs:
            peores += 1
    return (1.0 + peores) / (1.0 + n_perm), float(obs)


# --------------------------------------------------------------------------- #
# 2. PBO vía CSCV
# --------------------------------------------------------------------------- #
def pbo_cscv(matrix, s=CSCV_S):
    """Probability of Backtest Overfitting (Bailey et al.), CSCV con S bloques.

    `matrix[t][c]` = performance del config `c` en el sub-período `t`.

    Para cada partición del tiempo en mitad train / mitad test: se elige el mejor
    config **in-sample** y se mide su **rango relativo out-of-sample**. Si el
    ganador in-sample cae sistemáticamente por debajo de la mediana OOS, el
    procedimiento de selección está sobreajustando.

    PBO = fracción de particiones con logit λ ≤ 0.
    """
    T = len(matrix)
    if T < s:
        raise ValueError("hacen falta al menos S=%d filas de tiempo, hay %d" % (s, T))
    n_cfg = len(matrix[0])
    if n_cfg < 2:
        raise ValueError("PBO necesita al menos 2 configs para rankear")

    corte = [round(i * T / s) for i in range(s + 1)]
    bloques = [list(range(corte[i], corte[i + 1])) for i in range(s)]

    lambdas = []
    for comb in itertools.combinations(range(s), s // 2):
        tr = [i for b in comb for i in bloques[b]]
        te = [i for b in range(s) if b not in comb for i in bloques[b]]
        if not tr or not te:
            continue
        perf_tr = [sum(matrix[t][c] for t in tr) for c in range(n_cfg)]
        perf_te = [sum(matrix[t][c] for t in te) for c in range(n_cfg)]
        best = max(range(n_cfg), key=lambda c: perf_tr[c])
        # rango relativo OOS del ganador in-sample (1 = el mejor)
        orden = sorted(range(n_cfg), key=lambda c: perf_te[c])
        rango = orden.index(best) + 1
        w = rango / (n_cfg + 1.0)
        w = min(max(w, 1e-9), 1 - 1e-9)
        lambdas.append(math.log(w / (1 - w)))

    if not lambdas:
        raise ValueError("no se generaron particiones CSCV")
    pbo = sum(1 for x in lambdas if x <= 0) / len(lambdas)
    return pbo, lambdas


# --------------------------------------------------------------------------- #
# 3. Deflated Sharpe Ratio
# --------------------------------------------------------------------------- #
def expected_max_sharpe(n_trials, var_sharpe):
    """SR esperado del MEJOR de `n_trials` intentos bajo la nula (Bailey/LdP)."""
    if n_trials < 2:
        return 0.0
    sd = math.sqrt(max(var_sharpe, 0.0))
    a = _N.inv_cdf(1 - 1.0 / n_trials)
    b = _N.inv_cdf(1 - 1.0 / (n_trials * math.e))
    return sd * ((1 - _EULER) * a + _EULER * b)


def deflated_sharpe(sharpe, n_obs, n_trials, skew=0.0, kurt=3.0,
                    var_sharpe=None):
    """DSR: probabilidad de que el Sharpe observado supere al esperado por azar
    tras cobrar **todas** las variantes probadas (`n_trials` = N_eff, §G2).

    Corrige por el número de intentos y por los momentos de orden superior: una
    estrategia con cola izquierda gruesa necesita más Sharpe para el mismo DSR.
    """
    if n_obs < 2:
        return 0.0
    if var_sharpe is None:
        # varianza del estimador de Sharpe bajo no-normalidad
        var_sharpe = (1 - skew * sharpe + (kurt - 1) / 4.0 * sharpe ** 2) / (n_obs - 1)
    sr0 = expected_max_sharpe(n_trials, var_sharpe)
    den = math.sqrt(max(var_sharpe, 1e-18))
    return _N.cdf((sharpe - sr0) / den)


# --------------------------------------------------------------------------- #
# 4. Walk-forward por contrato
# --------------------------------------------------------------------------- #
def walk_forward(per_fold, folds_ordenados, seleccionar=None):
    """WF-OOS por contrato (§G2).

    `per_fold[config][fold]` = neto de ese config en ese fold. Para cada fold `k`
    (k ≥ 1) se re-elige el ganador usando **sólo** los folds anteriores y se
    evalúa en `k`. El fold 0 no es evaluable: no tiene historia previa.

    Devuelve (agregado_oos, detalle_por_fold).
    """
    if seleccionar is None:
        def seleccionar(cands):
            return max(cands, key=lambda kv: kv[1])[0]

    detalle, total = [], 0.0
    for i in range(1, len(folds_ordenados)):
        prev = folds_ordenados[:i]
        test = folds_ordenados[i]
        cands = [(c, sum(per_fold[c].get(f, 0.0) for f in prev)) for c in per_fold]
        gan = seleccionar(cands)
        oos = per_fold[gan].get(test, 0.0)
        total += oos
        detalle.append(dict(fold=test, ganador_in_sample=gan, oos_neto=oos,
                            entrenado_con=list(prev)))
    return total, detalle


# --------------------------------------------------------------------------- #
# 5. Sensibilidad paramétrica
# --------------------------------------------------------------------------- #
def parameter_sensitivity(expectancies, ganador, vecinos):
    """Mediana de las expectancies netas de los vecinos ±1 paso de grilla (§G2).

    Un ganador rodeado de vecinos negativos es un pico aislado — la firma de un
    acantilado de sobreajuste, no de un efecto real.
    """
    vals = [expectancies[v] for v in vecinos if v in expectancies]
    if not vals:
        return None, 0, 0
    vals.sort()
    n = len(vals)
    mediana = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    return mediana, sum(1 for v in vals if v > 0), n


# --------------------------------------------------------------------------- #
# Evaluación conjunta
# --------------------------------------------------------------------------- #
def evaluar(*, mcpt_p=None, pbo=None, dsr=None, wf_oos=None,
            sensibilidad_mediana=None):
    """Aplica los umbrales DUROS del contrato. Todo lo que falte queda FAIL:
    un gate no evaluado nunca cuenta como aprobado."""
    out = [
        G2Result("MCPT p", mcpt_p if mcpt_p is not None else 1.0,
                 MCPT_MAX_P, mcpt_p is not None and mcpt_p <= MCPT_MAX_P,
                 "" if mcpt_p is not None else "no evaluado"),
        G2Result("PBO", pbo if pbo is not None else 1.0,
                 PBO_MAX, pbo is not None and pbo <= PBO_MAX,
                 "" if pbo is not None else "no evaluado"),
        G2Result("DSR", dsr if dsr is not None else -1.0,
                 DSR_MIN, dsr is not None and dsr > DSR_MIN,
                 "" if dsr is not None else "no evaluado"),
        G2Result("WF-OOS neto", wf_oos if wf_oos is not None else -1.0,
                 0.0, wf_oos is not None and wf_oos > 0.0,
                 "" if wf_oos is not None else "no evaluado"),
        G2Result("sensibilidad (mediana)",
                 sensibilidad_mediana if sensibilidad_mediana is not None else -1.0,
                 0.0, sensibilidad_mediana is not None and sensibilidad_mediana > 0.0,
                 "" if sensibilidad_mediana is not None else "no evaluado"),
    ]
    return out, all(r.passed for r in out)
