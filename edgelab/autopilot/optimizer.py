"""Optimización de corridas, con mejora recursiva ACOTADA: un cambio (script, configuración) solo se acepta si la salida es idéntica y la ganancia supera un margen.
El resto se descarta y se conserva la línea base; el aprendizaje de por qué queda en el libro."""
from __future__ import annotations

import hashlib
import json
import statistics
import time

TIMING_KEYS = {"seconds", "generated_utc", "wall_seconds", "elapsed", "time"}


def canonical(o, drop=TIMING_KEYS):
    """Salida canónica sin campos de tiempo, con floats redondeados a 12 cifras significativas, para comparar corridas."""
    if isinstance(o, dict): return {k: canonical(v, drop) for k, v in sorted(o.items()) if k not in drop}
    if isinstance(o, (list, tuple)): return [canonical(v, drop) for v in o]
    if isinstance(o, float): return float(f"{o:.12g}")
    return o


def output_hash(o) -> str:
    return hashlib.sha256(json.dumps(canonical(o), sort_keys=True, default=str).encode()).hexdigest()


def compare(baseline_fn, candidate_fn, repeats: int = 3, min_speedup: float = 1.2) -> dict:
    """Ejecuta ambas implementaciones `repeats` veces sobre el MISMO fixture (las funciones lo cierran) y decide.
    ACEPTAR solo si hash de salida idéntico en todas las repeticiones y mediana(base)/mediana(cand) ≥ min_speedup; si no, RECHAZAR con el motivo."""
    tb, tc, hb, hc = [], [], set(), set()
    for _ in range(repeats):
        t = time.perf_counter(); hb.add(output_hash(baseline_fn())); tb.append(time.perf_counter() - t)
        t = time.perf_counter(); hc.add(output_hash(candidate_fn())); tc.append(time.perf_counter() - t)
    sp = statistics.median(tb) / statistics.median(tc)
    if len(hb) != 1: return dict(decision="RECHAZAR", reason="la línea base no es determinista", speedup=sp)
    if hb != hc: return dict(decision="RECHAZAR", reason="salida distinta a la línea base", speedup=sp)
    if sp < min_speedup: return dict(decision="RECHAZAR", reason=f"ganancia {sp:.2f}× < {min_speedup}×", speedup=sp)
    return dict(decision="ACEPTAR", reason="salida idéntica y ganancia suficiente", speedup=sp)


def advise(telemetry: list, limit_seconds: int = 43200) -> list:
    """Reglas simples sobre la telemetría del libro: qué cambiar de la configuración de lanzamiento. Son propuestas (no se aplican solas)."""
    adv = []
    by = {}
    for t in telemetry: by.setdefault((t["family"], t["group"]), []).append(t)
    for (fam, grp), rs in by.items():
        ok = [r["seconds"] for r in rs if r["status"] == "ANALYZED" and r["seconds"]]
        fails = [r for r in rs if r["status"] == "FAILED"]
        if ok and statistics.median(ok) > 0.5 * limit_seconds:
            adv.append(dict(target=f"{fam}/{grp}", advice="mediana > 50 % del límite de sesión: perfilar el análisis posterior, paralelizar contratos y verificar salida idéntica (optimizer.compare)"))
        if fails and len(fails) >= max(2, len(rs) // 2):
            adv.append(dict(target=f"{fam}/{grp}", advice=f"{len(fails)} de {len(rs)} corridas fallaron: probar local con datos parciales antes de lanzar y revisar --internet / datasets adjuntos"))
    return adv
