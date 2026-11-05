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
RUTA_AGENTE = RUTA.parent / "grillas" / "indicadores_agente.json"    # perímetro del programador: SÓLO estado NATIVO_AGENTE
USABLES = ("PASS", "PASS_CON_CAVEAT", "NATIVO_AGENTE")


class IndicadorNoUsable(ValueError):
    pass


def registro(ruta: Path = RUTA, ruta_agente: Path | None = None) -> dict:
    """Registro canónico + indicadores propios del agente. El archivo del agente vive en su perímetro (se aplica solo con tests),
    por eso sólo puede declarar NATIVO_AGENTE y nunca pisar un id canónico: una paridad PASS la da un oráculo NT8, no el agente."""
    reg = {r["id"]: r for r in json.loads(Path(ruta).read_text(encoding="utf-8"))["indicadores"]}
    ra = Path(ruta_agente) if ruta_agente is not None else (RUTA_AGENTE if Path(ruta) == RUTA else None)
    if ra is not None and ra.exists():
        for r in json.loads(ra.read_text(encoding="utf-8")).get("indicadores", []):
            if r.get("estado") != "NATIVO_AGENTE": raise IndicadorNoUsable(f"{ra.name}: {r.get('id')} declara {r.get('estado')}; el agente sólo registra NATIVO_AGENTE")
            if r["id"] in reg: raise IndicadorNoUsable(f"{ra.name}: {r['id']} ya existe en el registro canónico")
            for k in ("modulo", "test_causal"):
                if not r.get(k): raise IndicadorNoUsable(f"{ra.name}: {r['id']} sin {k}")
            reg[r["id"]] = dict(r, evidencia=r.get("evidencia", f"causalidad: {r['test_causal']}"), doc=r.get("doc", ""))
    return reg


def exigir(ids, ruta: Path = RUTA, ruta_agente: Path | None = None) -> list:
    """Devuelve las notas/caveats a citar; falla si algún indicador no está en un estado usable."""
    reg = registro(ruta, ruta_agente); notas = []
    for i in ids:
        r = reg.get(i)
        if r is None: raise IndicadorNoUsable(f"{i}: no está en el registro de indicadores ({ruta.name})")
        if r["estado"] not in USABLES: raise IndicadorNoUsable(f"{i}: estado {r['estado']} ({r['evidencia']}); primero paridad o causalidad")
        if r["estado"] != "PASS": notas.append(f"{i}: {r['estado']} — {r['evidencia']}")
    return notas


def _prefijo(ctx: dict, m: int) -> dict:
    n = len(ctx["c"]); cx = {k: (v[:m] if isinstance(v, np.ndarray) and len(v) == n else v) for k, v in ctx.items()}
    for k in ("vp_start", "tstart"):
        if k in ctx: cx[k] = ctx[k][:m + 1]
    if "vp_start" in ctx:
        hasta = int(ctx["vp_start"][m]); cx["vp_px"], cx["vp_vol"] = ctx["vp_px"][:hasta], ctx["vp_vol"][:hasta]
    if "tstart" in ctx: cx["tpx"] = ctx["tpx"][:int(ctx["tstart"][m])]
    if "conf" in ctx:
        mc = int(np.searchsorted(ctx["conf"]["t"], ctx["t"][m - 1], side="right")); nc = len(ctx["conf"]["c"])
        cx["conf"] = {k: (v[:mc] if isinstance(v, np.ndarray) and len(v) == nc else v) for k, v in ctx["conf"].items()}
    return cx


COLUMNAS_ESPERA = ("j_hacev15", "j_hacev25")      # u1_indaga: vela FUTURA donde «se hizo volumen» (entrada con espera, decidida en j)


def causal_por_disparo(fn, ctx: dict, n: int = 40, seed: int = 0, columnas=None, espera=COLUMNAS_ESPERA) -> list:
    """Causalidad por definición (2026-11-02, hallazgo del look-ahead de `areas_expansion.disparos`): para una muestra de las
    velas con disparo, corta el contexto JUSTO después de esa vela y exige que los disparos de esa vela sean exactamente los
    mismos (cantidad y valores). Una decisión en la vela k no puede depender de nada posterior a k. `causal` (cortes fijos)
    no vio el caso; ésta sí (tests/research/test_causalidad_estricta.py). Las columnas de ESPERA (vela futura donde se decide
    una entrada con espera) se verifican cortando en su propia vela, no en la del disparo."""
    import pandas as pd
    full = fn(ctx)
    if not len(full): return []
    ks = np.unique(full.k.to_numpy(np.int64)); rng = np.random.default_rng(seed)
    sel = np.sort(rng.choice(ks, min(n, len(ks)), replace=False)); errores = []
    cols = columnas or [c for c in full.columns if c != "k" and c not in espera and pd.api.types.is_numeric_dtype(full[c])]
    for col in [c for c in espera if c in full.columns]:                 # una espera se decide en SU vela j: se corta en j
        conj = full[np.isfinite(full[col].to_numpy(float))]
        for i in rng.choice(len(conj), min(n // 4, len(conj)), replace=False) if len(conj) else []:
            r = conj.iloc[int(i)]; j = int(r[col]); pre = fn(_prefijo(ctx, j + 1))
            m = pre[(pre.k == r.k) & np.isclose(pre.lado, r.lado) & np.isclose(pre.E, r.E)] if len(pre) and {"lado", "E"} <= set(pre.columns) else pre[pre.k == r.k] if len(pre) else pre
            if not len(m) or not np.isclose(m[col].to_numpy(float), j).any():
                errores.append(f"espera {col} = {j} del disparo en {int(r.k)} cambia al cortar en su propia vela")
    for k in sel:
        pre = fn(_prefijo(ctx, int(k) + 1))
        a = full[full.k == k][["k"] + cols].sort_values(["k"] + cols).reset_index(drop=True)
        b = pre[pre.k == k][["k"] + cols].sort_values(["k"] + cols).reset_index(drop=True) if len(pre) else a.iloc[0:0]
        try: pd.testing.assert_frame_equal(a, b, check_dtype=False)
        except AssertionError as e: errores.append(f"disparo en la vela {int(k)} cambia al cortar los datos ahí: {str(e)[:200]}")
    return errores


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
        if "conf" in ctx:                                                  # segundo instrumento (U1-CONFIRMA): también se corta en el tiempo
            mc = int(np.searchsorted(ctx["conf"]["t"], ctx["t"][corte], side="right")); nc = len(ctx["conf"]["c"])
            cx["conf"] = {k: (v[:mc] if isinstance(v, np.ndarray) and len(v) == nc else v) for k, v in ctx["conf"].items()}
        pre = fn(cx)
        cols = columnas or [c for c in full.columns if c in pre.columns]
        a = full[full.k <= corte - margen][cols].sort_values(cols).reset_index(drop=True)
        b = pre[pre.k <= corte - margen][cols].sort_values(cols).reset_index(drop=True) if len(pre) else pd.DataFrame(columns=cols)   # sin disparos en el prefijo: mismas columnas
        try: pd.testing.assert_frame_equal(a, b, check_dtype=False)
        except AssertionError as e: errores.append(f"corte {f:.2f}: {str(e)[:300]}")
    return errores
