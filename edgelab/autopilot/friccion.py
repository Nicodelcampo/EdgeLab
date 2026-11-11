"""Criterio de fricción (pedido de Nico, 2026-10-16): elegir escenarios donde la fricción es baja frente al movimiento,
y no gastar análisis donde la fricción tiene altas chances de ganar.

Fricción por viaje redondo, techo conservador, de docs/research/REFERENCIA_COSTOS_PROPS_BROKERS_20261014.md §4:
spread medido + comisión máxima de la tabla + slippage declarado de 2 ticks. Un instrumento sin costo medido NO
recibe uno prestado de otro (regla del repo: no transportar costos entre instrumentos).
"""
from __future__ import annotations

from edgelab import costos as _costos

# Fuente única desde 2026-10-22: config/costos/costos_canonicos.json (edgelab/costos.py). Mismos valores que la tabla literal
# anterior (ES 3,55 · MES 4,62 · 6E 4,16 · NQ 6,18 · GC 6,05 · MNQ 7,91; verificado en tests/test_costos_canonicos.py), así que
# el ciclo autónomo no cambia de comportamiento; agregar un instrumento a la tabla canónica lo habilita acá.
FRICCION_RT_TICKS = {k: round(_costos.friccion_rt_ticks(k), 2) for k in ("ES", "MES", "6E", "NQ", "GC", "MNQ")}
RATIO_MIN = 3.0


def _todos() -> dict:
    """Fricción de TODOS los instrumentos de la tabla canónica (2026-11-11): la de arriba queda por compatibilidad del test."""
    out = {}
    for k in _costos.tabla()["instrumentos"]:
        try: out[k] = round(_costos.friccion_rt_ticks(k), 2)
        except Exception: continue                                              # sin componente medido: no recibe costo prestado
    return out


FRICCION_TODOS = _todos()        # el movimiento bruto esperado en el horizonte debe ser >= 3 veces la fricción RT


def instrumento(c) -> str:
    return str((getattr(c, "cfg", {}) or {}).get("inst") or getattr(c, "group", "") or "").upper()


def instrumentos(c) -> list:
    """Instrumentos reales de la propuesta (2026-11-11: las 11 promociones de una noche se rechazaron porque el proponente ponía
    etiquetas como MULTI, DATA o GC_ES). `cfg.insts` manda; si no, se parte la etiqueta por «_», «+», «,», «/» o espacios."""
    cfg = getattr(c, "cfg", {}) or {}
    if cfg.get("insts"): return [str(x).upper() for x in cfg["insts"]]
    import re
    return [x for x in re.split(r"[_+,/ ]+", instrumento(c)) if x]


def evaluar(c) -> dict:
    """ratio = movimiento esperado (ticks, declarado en cfg['mov_esperado_ticks'] desde evidencia previa) / fricción RT.
    mov_esperado_ticks es el movimiento bruto que la operación captura tras el fill (replay causal), no la amplitud nominal
    del objetivo: k32 (2026-10-16) tenía zonas de 16 ticks con edge bruto de 0,2 a 0,85 ticks/op, ratio < 0,25."""
    inst = instrumento(c); insts = instrumentos(c); mov = (getattr(c, "cfg", {}) or {}).get("mov_esperado_ticks")
    faltan = [i for i in insts if i not in FRICCION_TODOS]
    if not insts or faltan:
        return dict(inst=inst, costo=None, ratio=None, ok=False,
                    motivo=f"sin fricción medida para {', '.join(faltan) or inst or '?'}: declarar cfg.insts con instrumentos reales de edgelab/costos.py "
                           f"({', '.join(sorted(FRICCION_TODOS))}); una etiqueta como MULTI o DATA no es un instrumento (no se transporta costo de otro)")
    costo = max(FRICCION_TODOS[i] for i in insts)                               # varios instrumentos: el más caro (conservador)
    if mov is None:
        return dict(inst=inst, costo=costo, ratio=None, ok=False, motivo="falta cfg.mov_esperado_ticks: declarar el movimiento esperado en el horizonte desde evidencia previa")
    ratio = float(mov) / costo
    return dict(inst=inst, costo=costo, ratio=round(ratio, 2), ok=ratio >= RATIO_MIN,
                motivo=None if ratio >= RATIO_MIN else f"movimiento {mov} ticks vs fricción {costo}: ratio {ratio:.2f} < {RATIO_MIN}; la fricción probablemente gana")


def peso(c) -> float:
    """Para ordenar: 1 si el ratio alcanza, proporcional por debajo, y un piso chico si no hay datos (no se descarta, se posterga)."""
    e = evaluar(c)
    if e["ratio"] is None: return 0.1
    return min(1.0, e["ratio"] / RATIO_MIN)


def tabla_para_contexto() -> dict:
    return dict(friccion_rt_ticks=FRICCION_RT_TICKS, ratio_min=RATIO_MIN,
                regla="preferir escenarios (instrumento, horario, régimen, horizonte) donde el movimiento esperado supera holgadamente la fricción; ES es el más barato")
