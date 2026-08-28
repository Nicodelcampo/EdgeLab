# -*- coding: utf-8 -*-
"""Potencia de la carrera simetrica L3, con la aritmetica exacta del spec.

r en {-1,0,+1}; f = fraccion resuelta; p = P(revert | resuelta).
    mean(r) = f*(2p-1)
    Var(r)  = f - f^2*(2p-1)^2   ->  bajo H0 (p=0.5): sd = sqrt(f)
    SE      = sqrt(f/n)
MDE a potencia 80% y dos colas alfa: (z_{1-a/2} + 0.8416) * SE
Split equivalente: p = 0.5 + mean/(2f)

Con f=0.6 y n=210 esto reproduce el SE~0.054 y el MDE~0.15 del spec.
"""
import json
import math

F = 0.6
Z80 = 0.8416


def z_two_sided(alpha):
    target = 1.0 - alpha / 2.0
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0))) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def se(n, f=F):
    return math.sqrt(f / n)


def mde(n, f=F, alpha=0.05):
    return (z_two_sided(alpha) + Z80) * se(n, f)


def split(mean, f=F):
    return 0.5 + mean / (2.0 * f)


def mean_of(p, f=F):
    return f * (2.0 * p - 1.0)


def zval(p, n, f=F):
    return mean_of(p, f) / se(n, f)


def n_needed(p, f=F, alpha=0.05):
    m = abs(mean_of(p, f))
    return math.ceil(f * ((z_two_sided(alpha) + Z80) / m) ** 2) if m else None


out = {}

out["un_activo_210"] = dict(
    n=210, se=round(se(210), 5), mde=round(mde(210), 4),
    split_detectable=round(split(mde(210)), 4),
    claim_58=dict(mean=round(mean_of(0.58), 4), z=round(zval(0.58, 210), 3),
                  ci95=[round(mean_of(0.58) - 1.96 * se(210), 4),
                        round(mean_of(0.58) + 1.96 * se(210), 4)],
                  etiqueta="PRERANGE_NO_EDGE" if mean_of(0.58) - 1.96 * se(210) <= 0 else "emitible"),
    claim_62=dict(mean=round(mean_of(0.62), 4), z=round(zval(0.62, 210), 3),
                  ci95=[round(mean_of(0.62) - 1.96 * se(210), 4),
                        round(mean_of(0.62) + 1.96 * se(210), 4)],
                  etiqueta="PRERANGE_NO_EDGE" if mean_of(0.62) - 1.96 * se(210) <= 0 else "emitible"),
    n_para_55_45=n_needed(0.55), n_para_58_42=n_needed(0.58),
)

# pooling con la dependencia que declara el propio spec:
# ES/NQ/YM ~ 1.3 activos independientes (sincronizacion 51% vs 36% esperado)
for label, k_eff, n_ses in (("indices_solos_1.3", 1.3, 201),
                            ("indices_mas_GC_2.3", 2.3, 201),
                            ("ingenuo_4_activos", 4.0, 201)):
    n_eff = int(round(k_eff * n_ses))
    out["pool_" + label] = dict(
        k_efectivo=k_eff, sesiones_por_activo=n_ses, n_efectivo=n_eff,
        se=round(se(n_eff), 5), mde=round(mde(n_eff), 4),
        split_detectable=round(split(mde(n_eff)), 4),
        z_si_58=round(zval(0.58, n_eff), 3))

n_eff = int(round(2.3 * 201))
for m in (1, 3, 12, 25):
    a = 0.05 / m
    out["multiplicidad_%d_tests" % m] = dict(
        alpha_bonferroni=round(a, 5), z_critico=round(z_two_sided(a), 3),
        mde=round(mde(n_eff, alpha=a), 4),
        split_detectable=round(split(mde(n_eff, alpha=a)), 4))

for c in (0.5, 0.3, 0.2, 0.1):
    n_c = int(round(n_eff * c))
    out["cond_bigtrap2_c%.1f" % c] = dict(
        tasa_coocurrencia=c, n_condicional=n_c, se=round(se(n_c), 4),
        mde=round(mde(n_c), 4), split_detectable=round(split(mde(n_c)), 4))

for n6 in (66, 39, 11):
    out["6E_%d_sesiones" % n6] = dict(
        n=n6, se=round(se(n6), 4), mde=round(mde(n6), 4),
        split_detectable=round(split(mde(n6)), 4), gate_sessions_ge_30=n6 >= 30)

out["cuello_de_botella"] = dict(
    ticks_en_kaggle=1_078_414_656, sesiones_por_activo_aprox=201,
    observaciones_utiles_por_sesion=1,
    nota="la carrera produce UNA observacion por sesion: el n no escala con ticks",
    ticks_por_observacion=round(1_078_414_656 / (201 * 11)))

print(json.dumps(out, indent=2))
with open("power_l3.json", "w") as fh:
    json.dump(out, fh, indent=2)
