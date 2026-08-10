"""Calibración sintética preregistrada para session_hac_bartlett_v2.

Los sobres se fijan antes de mirar el resultado del CI. No demuestran validez
universal: buscan fallos gruesos bajo IID, dependencia positiva, colas pesadas,
sesiones sin trades y un efecto plantado. El IC bootstrap-t sigue siendo la
inferencia primaria; DSR es un veto complementario.
"""
from __future__ import annotations

import json
import math

from edgelab.research import g2

N = 160
REPLICATES = 400
CALENDAR = "d" * 64


class SplitMixNormal:
    MASK = (1 << 64) - 1

    def __init__(self, seed):
        self.state = seed & self.MASK

    def uint64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & self.MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & self.MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & self.MASK
        return (z ^ (z >> 31)) & self.MASK

    def uniform(self):
        return (self.uint64() + 0.5) / float(1 << 64)

    def normal(self):
        u1 = self.uniform()
        u2 = self.uniform()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def iid(rng, mean=0.0):
    return [mean + rng.normal() for _ in range(N)]


def ar1(rng, rho=0.5, mean=0.0):
    scale = math.sqrt(1.0 - rho * rho)
    value = mean + rng.normal()
    out = []
    for _ in range(N):
        value = mean + rho * (value - mean) + scale * rng.normal()
        out.append(value)
    return out


def student_t5(rng):
    out = []
    for _ in range(N):
        numerator = rng.normal()
        chi_square = sum(rng.normal() ** 2 for _ in range(5))
        out.append(numerator / math.sqrt(chi_square / 5.0))
    return out


def zero_inflated(rng, inactive_probability=0.40):
    return [
        0.0 if rng.uniform() < inactive_probability else rng.normal()
        for _ in range(N)
    ]


def measure(generator, *, seed, n_trials=1):
    rng = SplitMixNormal(seed)
    passes = 0
    errors = 0
    effective = []
    for _ in range(REPLICATES):
        values = generator(rng)
        zero_count = sum(value == 0.0 for value in values)
        try:
            result = g2.deflated_sharpe_sessions(
                values,
                n_trials=n_trials,
                calendar_sha256=CALENDAR,
                zero_trade_sessions=zero_count,
            )
        except g2.G2SemanticError:
            errors += 1
            continue
        passes += result.probability >= g2.DSR_MIN
        effective.append(result.n_effective)
    return {
        "passes": passes,
        "replicates": REPLICATES,
        "errors_fail_closed": errors,
        "rate": passes / REPLICATES,
        "mean_n_effective": sum(effective) / len(effective) if effective else 0.0,
    }


def calibration_report():
    return {
        "method": g2.DSR_DEPENDENCE_METHOD,
        "method_sha256": g2.DSR_METHOD_SHA256_V2,
        "implementation_sha256": g2.DSR_IMPLEMENTATION_SHA256,
        "n_sessions": N,
        "replicates_per_scenario": REPLICATES,
        "scenarios": {
            "iid_gaussian_null": measure(iid, seed=101),
            "iid_gaussian_null_n48": measure(iid, seed=101, n_trials=48),
            "ar1_rho_050_null": measure(ar1, seed=202),
            "student_t5_null": measure(student_t5, seed=303),
            "zero_trade_40pct_null": measure(zero_inflated, seed=404),
            "iid_gaussian_signal_020": measure(
                lambda rng: iid(rng, mean=0.20), seed=505
            ),
            "ar1_rho_050_signal_030": measure(
                lambda rng: ar1(rng, mean=0.30), seed=606
            ),
        },
    }


def assert_calibration(report):
    s = report["scenarios"]
    assert all(row["errors_fail_closed"] == 0 for row in s.values())

    # Tamaño nominal: estricto en IID, tolerancia explícita en los nulos duros.
    assert 0.01 <= s["iid_gaussian_null"]["rate"] <= 0.09
    assert s["ar1_rho_050_null"]["rate"] <= 0.11
    assert s["student_t5_null"]["rate"] <= 0.11
    assert s["zero_trade_40pct_null"]["rate"] <= 0.11

    # La multiplicidad sólo puede volver más conservador al mismo panel.
    assert (
        s["iid_gaussian_null_n48"]["rate"]
        <= s["iid_gaussian_null"]["rate"]
    )

    # Poder mínimo para efectos deliberadamente grandes y verificables.
    assert s["iid_gaussian_signal_020"]["rate"] >= 0.70
    assert s["ar1_rho_050_signal_030"]["rate"] >= 0.60

    # El estimador de dependencia debe reconocer clustering positivo en promedio.
    assert (
        s["ar1_rho_050_null"]["mean_n_effective"]
        < s["iid_gaussian_null"]["mean_n_effective"]
    )


def test_calibracion_sintetica_preregistrada():
    report = calibration_report()
    assert_calibration(report)


if __name__ == "__main__":
    result = calibration_report()
    assert_calibration(result)
    print(json.dumps(result, indent=2, sort_keys=True))
