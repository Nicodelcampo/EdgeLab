"""Registro de indicadores para barridos (config/autopilot/indicadores.json) y prueba de causalidad para los indicadores propios.

Pedido de Nico (2026-10-23): con la paridad de los indicadores validada, el agente diseña sus propios barridos con ellos, o crea
sus propios indicadores. Reglas que este módulo hace cumplir:
- `exigir(ids)`: un experimento sólo usa indicadores PASS / PASS_CON_CAVEAT o NATIVO_AGENTE; cualquier otro estado frena.
- `causal(fn, ctx, ...)`: un indicador propio es causal si su salida en la vela k no cambia al cortar todo lo posterior a k.
  Es la condición mínima para research; para operarlo en vivo hace falta además su versión NT8 con paridad.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RUTA = Path(__file__).resolve().parents[2] / "config" / "autopilot" / "indicadores.json"
USABLES = ("PASS", "PASS_CON_CAVEAT", "NATIVO_AGENTE")


class IndicadorNoUsable(ValueError):
    pass


def registro(ruta: Path = RUTA) -> dict:
    return {r["id"]: r for r in json.loads(Path(ruta).read_text(encoding="utf-8"))["indicadores"]}


def exigir(ids, ruta: Path = RUTA) -> list:
    """Devuelve las notas/caveats a citar; falla si algún indicador no está en un estado usable."""
    reg = registro(ruta); notas = []
    for i in ids:
        r = reg.get(i)
        if r is None: raise IndicadorNoUsable(f"{i}: no está en el registro de indicadores ({ruta.name})")
        if r["estado"] not in USABLES: raise IndicadorNoUsable(f"{i}: estado {r['estado']} ({r['evidencia']}); primero paridad o causalidad")
        if r["estado"] != "PASS": notas.append(f"{i}: {r['estado']} — {r['evidencia']}")
    return notas


def causal(fn, ctx: dict, cortes=(0.3, 0.55, 0.8), margen: int = 5, columnas=None) -> list:
    """Corre `fn(ctx) -> DataFrame con columna k` sobre el contexto completo y sobre prefijos; las filas con k <= corte-margen
    deben ser idénticas. Devuelve la lista de diferencias (vacía = causal). `ctx` como el de grilla_generica.contexto_m1."""
    import pandas as pd
    full = fn(ctx); n = len(ctx["c"]); errores = []
    for f in cortes:
        corte = int(n * f); m = corte + 1
        cx = {k: (v[:m] if isinstance(v, np.ndarray) and len(v) == n else v) for k, v in ctx.items()}
        for k in ("vp_start", "tstart"):
            if k in ctx: cx[k] = ctx[k][:m + 1]
        if "vp_start" in ctx:
            hasta = int(ctx["vp_start"][m]); cx["vp_px"], cx["vp_vol"] = ctx["vp_px"][:hasta], ctx["vp_vol"][:hasta]
        if "tstart" in ctx: cx["tpx"] = ctx["tpx"][:int(ctx["tstart"][m])]
        pre = fn(cx)
        cols = columnas or [c for c in full.columns if c in pre.columns]
        a = full[full.k <= corte - margen][cols].sort_values(cols).reset_index(drop=True)
        b = pre[pre.k <= corte - margen][cols].sort_values(cols).reset_index(drop=True) if len(pre) else pre
        try: pd.testing.assert_frame_equal(a, b, check_dtype=False)
        except AssertionError as e: errores.append(f"corte {f:.2f}: {str(e)[:300]}")
    return errores
