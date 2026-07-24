"""Matcher de paridad Python vs NT8 (gates P2A/P2B).

Matching bipartito greedy por cercanía de created_ms + geometría en ticks.
Diagnósticos: MATCHED, TIMESTAMP_DIFF, GEOMETRY_DIFF, STATE_ORDER_DIFF,
FEATURE_DIFF, MISSING_IN_PYTHON, MISSING_IN_NT8; CALIBRATION_DIFF y
FOOTPRINT_MISMATCH entran vía `extra_diags` (los emiten sesiones/kernels/P1A,
no el matcher) y degradan a WARN, nunca se silencian.

Gate: PASS = cero huérfanas y cero GEOMETRY_DIFF; WARN = solo diffs
temporales/estado/feature/calibración dentro de tolerancias; FAIL = zonas
faltantes o discrepancia geométrica.
"""
from __future__ import annotations

WARN_CODES = ("TIMESTAMP_DIFF", "STATE_ORDER_DIFF", "FEATURE_DIFF",
              "CALIBRATION_DIFF", "FOOTPRINT_MISMATCH")
FAIL_CODES = ("MISSING_IN_NT8", "MISSING_IN_PYTHON", "GEOMETRY_DIFF")


def _geom_ticks(z, tick_size):
    top = z.get("top")
    bot = z.get("bottom")
    if top is None or bot is None or not tick_size:
        return None
    return (round(top / tick_size), round(bot / tick_size))


def match_zones(py_zones, nt8_zones, tick_size, tol_created_ms=60_000,
                tol_geom_ticks=0, strict_created_ms=1_000, extra_diags=None,
                maturity_frontier_ms=None):
    """Devuelve dict(pairs, diagnostics, summary, gate).

    Frontera de madurez (`maturity_frontier_ms`): NT8 exporta más rango que la
    ventana Python, así que las zonas creadas cerca del final no pueden completar
    su ciclo de vida (`max_age`) dentro de la ventana común. Para esas zonas
    INMADURAS (created_ms > frontier) se compara SOLO geometría + timestamp de
    creación; el estado final y touches se dejan fuera (su lifecycle está
    truncado por la ventana, no por el kernel). NO es ampliar tolerancia: la
    geometría se compara al 100%; una zona MADURA con STATE_ORDER_DIFF sigue
    siendo WARN/FAIL. `None` = todas maduras (comportamiento previo)."""
    used = set()
    pairs, diags = [], list(extra_diags or [])
    n_immature = 0

    def cand_cost(a, b):
        ca, cb = a.get("created_ms"), b.get("created_ms")
        if ca is None or cb is None:
            dt = None
        else:
            dt = abs(ca - cb)
            if dt > tol_created_ms:
                return None
        ga, gb = _geom_ticks(a, tick_size), _geom_ticks(b, tick_size)
        if ga is not None and gb is not None:
            gd = max(abs(ga[0] - gb[0]), abs(ga[1] - gb[1]))
            if gd > max(tol_geom_ticks, 8):   # límite duro para candidatear
                return None
        else:
            gd = None
        return ((dt if dt is not None else tol_created_ms),
                (gd if gd is not None else 0))

    order = sorted(range(len(py_zones)),
                   key=lambda i: py_zones[i].get("created_ms") or 0)
    for i in order:
        a = py_zones[i]
        best, best_cost = None, None
        for j, b in enumerate(nt8_zones):
            if j in used:
                continue
            c = cand_cost(a, b)
            if c is not None and (best_cost is None or c < best_cost):
                best, best_cost = j, c
        if best is None:
            diags.append(dict(code="MISSING_IN_NT8", py_id=a["id"], nt8_id=None,
                              detail="zona Python sin contraparte NT8"))
            continue
        used.add(best)
        b = nt8_zones[best]
        pairs.append((a["id"], b["id"]))
        codes = []
        dt = None
        if a.get("created_ms") is not None and b.get("created_ms") is not None:
            dt = abs(a["created_ms"] - b["created_ms"])
            if dt > strict_created_ms:
                codes.append(("TIMESTAMP_DIFF", "created_ms diff=%dms" % dt))
        ga, gb = _geom_ticks(a, tick_size), _geom_ticks(b, tick_size)
        if ga is not None and gb is not None:
            gd = max(abs(ga[0] - gb[0]), abs(ga[1] - gb[1]))
            if gd > tol_geom_ticks:
                codes.append(("GEOMETRY_DIFF",
                              "py=%s nt8=%s diff=%d ticks" % (ga, gb, gd)))
        immature = (maturity_frontier_ms is not None
                    and a.get("created_ms") is not None
                    and a["created_ms"] > maturity_frontier_ms)
        if immature:
            # zona en la cola: lifecycle/touches truncados por la ventana. Se
            # registra informativo (no WARN/FAIL) lo que se suprimió, para
            # trazabilidad; la geometría/timestamp de arriba SÍ cuentan.
            sa, sb = (a.get("state") or "").upper(), (b.get("state") or "").upper()
            supp = []
            if sa and sb and sa != sb:
                supp.append("state py=%s nt8=%s" % (sa, sb))
            if a.get("touches") is not None and b.get("touches") is not None \
                    and int(a["touches"]) != int(b["touches"]):
                supp.append("touches py=%s nt8=%s" % (a["touches"], b["touches"]))
            if supp:
                n_immature += 1
                diags.append(dict(code="MATURITY_TAIL", py_id=a["id"], nt8_id=b["id"],
                                  detail="lifecycle no comparable (cola de ventana): "
                                  + "; ".join(supp)))
        else:
            sa, sb = (a.get("state") or "").upper(), (b.get("state") or "").upper()
            if sa and sb and sa != sb:
                codes.append(("STATE_ORDER_DIFF", "py=%s nt8=%s" % (sa, sb)))
            if a.get("touches") is not None and b.get("touches") is not None \
                    and int(a["touches"]) != int(b["touches"]):
                codes.append(("FEATURE_DIFF",
                              "touches py=%s nt8=%s" % (a["touches"], b["touches"])))
        if not codes:
            diags.append(dict(code="MATCHED", py_id=a["id"], nt8_id=b["id"],
                              detail="dt=%sms" % (dt if dt is not None else "n/a")))
        else:
            for code, detail in codes:
                diags.append(dict(code=code, py_id=a["id"], nt8_id=b["id"],
                                  detail=detail))
    for j, b in enumerate(nt8_zones):
        if j not in used:
            diags.append(dict(code="MISSING_IN_PYTHON", py_id=None, nt8_id=b["id"],
                              detail="zona NT8 sin contraparte Python"))

    counts = {}
    for d in diags:
        counts[d["code"]] = counts.get(d["code"], 0) + 1
    fail = any(counts.get(c, 0) for c in FAIL_CODES)
    warn = any(counts.get(c, 0) for c in WARN_CODES)
    gate = "FAIL" if fail else ("WARN" if warn else "PASS")
    summary = dict(py_zones=len(py_zones), nt8_zones=len(nt8_zones),
                   matched_pairs=len(pairs), counts=counts, gate=gate,
                   tol_created_ms=tol_created_ms, tol_geom_ticks=tol_geom_ticks,
                   strict_created_ms=strict_created_ms,
                   maturity_frontier_ms=maturity_frontier_ms,
                   immature_tail=n_immature)
    return dict(pairs=pairs, diagnostics=diags, summary=summary, gate=gate)
