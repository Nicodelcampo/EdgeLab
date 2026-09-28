"""Guardia automática de controles en diseños evento-contra-control (lección LES-CTRL-TIMING-20260924).

El 24/09 una "ventaja" de +13,7 ticks en NQ (absorción × tendencia de 30 min) resultó ser la deriva de los controles.
Los controles sorteados en [t0 − 30 min, t0) heredan el camino con el que el precio llegó al nivel del evento: −6,6
ticks a 300 s, y −20,7 si se solapan con la aproximación. Se detectó a mano; esta guardia la vuelve automática.

Regla (versión CTRL_TIMING_V1). Un control de la MISMA sesión que su evento es válido sólo si
    t_control >= t_evento + horizonte_max_s
es decir, después de que se cerró la ventana de resultado del evento. Los controles de OTRA sesión (misma hora del día,
por ejemplo) no tienen esa restricción. Todo control previo al evento o dentro de su ventana hace FAIL.

`DurableHippocampus.record_observation(..., design="EVENT_VS_CONTROL", control_audit=...)` rechaza el registro si la
auditoría falta, no es de la versión vigente o no es PASS. No se relaja después de ver resultados: cambiar la regla
exige una versión nueva y consultarlo con Nico.
"""
from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

RULE_VERSION = "CTRL_TIMING_V1"
RULE_TEXT = "same-session control valid only if t_control >= t_event + horizon_max_s; other-session controls exempt"
RULE_SHA256 = hashlib.sha256(f"{RULE_VERSION}|{RULE_TEXT}".encode()).hexdigest()
DESIGNS = frozenset({"EVENT_VS_CONTROL", "NO_CONTROL", "OTHER"})


def audit_event_controls(event_ts_us, control_ts_us, horizon_max_s: float, same_session=None,
                         control_y=None) -> dict[str, Any]:
    """Audita controles emparejados. `event_ts_us[i]` es el instante del evento al que pertenece el control i
    (mismo largo que `control_ts_us`). `same_session[i]` indica si el control está en la sesión de su evento (por
    defecto, todos). `control_y` (opcional) agrega un diagnóstico descriptivo: la media del resultado de los
    controles por tramo temporal. No es parte del gate, pero muestra la deriva cuando existe."""
    te = np.asarray(event_ts_us, dtype=np.int64)
    tc = np.asarray(control_ts_us, dtype=np.int64)
    if te.shape != tc.shape:
        raise ValueError("event_ts_us y control_ts_us deben tener el mismo largo (un evento por control)")
    same = np.ones(len(tc), bool) if same_session is None else np.asarray(same_session, bool)
    h_us = int(round(horizon_max_s * 1_000_000))
    dt = tc - te
    before = same & (dt < 0)
    inside = same & (dt >= 0) & (dt < h_us)
    n = int(len(tc))
    audit = dict(rule_version=RULE_VERSION, rule_sha256=RULE_SHA256, horizon_max_s=float(horizon_max_s),
                 n_controls=n, n_before_event=int(before.sum()), n_inside_event_window=int(inside.sum()),
                 n_other_session=int((~same).sum()))
    if n == 0:
        audit.update(status="FAIL", reason="NO_CONTROLS")
    elif before.any():
        audit.update(status="FAIL", reason="CONTROL_BEFORE_EVENT")
    elif inside.any():
        audit.update(status="FAIL", reason="CONTROL_INSIDE_EVENT_WINDOW")
    else:
        audit.update(status="PASS", reason=None)
    if control_y is not None and n:
        y = np.asarray(control_y, float)
        buckets = {"antes": same & (dt < 0), "dentro": inside, "despues": same & (dt >= h_us), "otra_sesion": ~same}
        audit["diagnostic_mean_y"] = {k: (float(np.nanmean(y[m])) if m.any() else None) for k, m in buckets.items()}
    return audit


def check_observation_design(kind: str, design: str | None, control_audit: dict | None) -> None:
    """Gate para `record_observation`. Toda observación nueva declara su diseño. Si es evento-contra-control y mira
    retornos (RESPONSE_PROFILE), exige una auditoría PASS de la versión vigente."""
    if design is None:
        raise ValueError(f"design must be declared, one of {sorted(DESIGNS)}")
    if design not in DESIGNS:
        raise ValueError(f"design must be one of {sorted(DESIGNS)}")
    if design == "EVENT_VS_CONTROL" and kind == "RESPONSE_PROFILE":
        if not control_audit:
            raise ValueError("EVENT_VS_CONTROL response profile requires control_audit (edgelab.edge_brain.control_guard)")
        if control_audit.get("rule_version") != RULE_VERSION or control_audit.get("rule_sha256") != RULE_SHA256:
            raise ValueError(f"control_audit is not {RULE_VERSION}")
        if control_audit.get("status") != "PASS":
            raise ValueError(f"control_audit FAIL: {control_audit.get('reason')} "
                             f"(before={control_audit.get('n_before_event')}, inside={control_audit.get('n_inside_event_window')})")
