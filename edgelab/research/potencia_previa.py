"""Potencia prevista de una campaña (2026-10-26, pedido de Nico: que el agente del Debian lance corridas que puedan concluir).

Dos momentos, los dos INFORMATIVOS (no matan: una regla del régimen actual con pocas operaciones sigue viva, sólo se sabe antes
cuánto va a tardar en poder confirmarse):
  - PREFLIGHT: si la campaña declara `potencia_previa = {ops_mes, sd_op, efecto_util}` (de una familia vecina o de E0), se publica
    el MDE de cada ventana (DESC, OOS, holdout a N fijo) y los meses que harían falta para detectar `efecto_util`.
  - Fin del DESC: por candidata, con su n y su IC90 reales, el MDE proyectado en el OOS y en el holdout (se ~ 1/sqrt(n)).
Las fórmulas son las de `edgelab.funnel.escalera` (mde, potencia, ops_necesarias); acá sólo se proyectan a las ventanas.
"""
from __future__ import annotations

import math

from edgelab.funnel.escalera import ALFA_CONFIRMACION, mde, ops_necesarias, potencia

Z90 = 1.6448536


def se_de_ic90(ic90) -> float:
    return (float(ic90[1]) - float(ic90[0])) / (2 * Z90)


def ventana(n: float, sd_op: float, efecto: float | None = None) -> dict:
    """MDE (y potencia contra `efecto`) de una ventana con n operaciones de desvío sd_op (se = sd/sqrt(n), sin agrupación)."""
    if n <= 0 or sd_op <= 0: return dict(n=float(n), mde=float("inf"), potencia=0.0 if efecto else None)
    se = sd_op / math.sqrt(n)
    return dict(n=round(float(n), 1), se=se, mde=mde(se), potencia=potencia(efecto, se, ALFA_CONFIRMACION) if efecto else None)


def informe_previo(spec: dict, meses) -> dict | None:
    """PREFLIGHT. `meses`: función período -> meses (la del embudo). None si la campaña no declara `potencia_previa`."""
    pp = spec.get("potencia_previa")
    if not pp: return None
    ops, sd, ef = float(pp["ops_mes"]), float(pp["sd_op"]), pp.get("efecto_util")
    n_fijo = int((spec.get("holdout") or {}).get("n_fijo", 150))
    out = dict(declarado=pp, desc=ventana(ops * meses(spec.get("desc")), sd, ef), holdout=ventana(n_fijo, sd, ef))
    if spec.get("oos"): out["oos"] = ventana(ops * meses(spec["oos"]), sd, ef)
    if ef and ef > 0:
        n_nec = ops_necesarias(float(ef), sd, 1)                # con se_actual = sd y n_actual = 1: n para potencia 0,8
        out.update(ops_necesarias=n_nec, meses_necesarios=round(n_nec / ops, 1) if ops > 0 and n_nec else None)
    return out


def por_candidata(p: dict, meses_desc: int, m_oos: int, n_fijo: int, fraccion_efecto: float = 0.5) -> dict:
    """Fin del DESC: proyección del MDE de una pista (dict con n, ic90, media_neta) al OOS y al holdout."""
    se = se_de_ic90(p["ic90"]); n = max(int(p["n"]), 1); ef = fraccion_efecto * float(p["media_neta"])
    n_oos = n / max(meses_desc, 1) * m_oos
    r = dict(celda=p["celda"], n_desc=n, ops_mes=round(n / max(meses_desc, 1), 2), efecto=ef)
    for k, nn in (("oos", n_oos), ("holdout", n_fijo)):
        if nn <= 0: r[k] = dict(n=0, mde=float("inf"), potencia=0.0); continue
        s = se * math.sqrt(n / nn); r[k] = dict(n=round(nn, 1), mde=mde(s), potencia=potencia(ef, s, ALFA_CONFIRMACION) if ef > 0 else 0.0)
    return r
