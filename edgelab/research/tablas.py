"""Tablas de eventos estandarizadas (2026-11-11, `docs/autopilot/AUTOMATIZACION_PROCESOS_20261111.md` I1/I5–I7/L1/V2/R5).

Una familia nueva que mide reglas sobre eventos se escribe como UN módulo con este contrato; el resto (desenlaces, kernel,
lanzamiento, causalidad, calibración, análisis, congelado y holdout) es común:

  NOMBRE        str (letras, números y «-»: es el slug de Kaggle)
  EJECUCIONES   lista de ejecuciones de `edgelab/research/ejecucion.py` ("MERCADO", "VUELTA", "LIMITE")
  eventos(ctx)  DataFrame con k, lado, ref, ext, rg (contrato de `ejecucion`) + rasgos causales (todo con velas ≤ k)
  opcionales:   DEFINICIONES  columnas booleanas: cada una es una definición del evento (la búsqueda las recorre)
                CONTROL       {definición: su control} (p. ej. la misma marca sin la condición que se quiere probar)
                FILTROS       {nombre: (columna, op, valor)} con op en <, <=, >, >=, ==; se aplican en el análisis, no en el kernel
                PERIODOS      [(nombre, desde, hasta)] (por defecto DESC ≤ 2026-03-31 y REP después)
                FUENTE_COSTO  {fuente: instrumento de edgelab/costos.py} (por defecto el futuro de la fuente; un spot usa el de su futuro)

`generar(modulo, ctx)` arma la tabla; `preflight(modulo)` corre TODAS las pruebas antes de lanzar; `conteo(modulo)` da las pruebas
de la exploración para el registro global.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research import ejecucion as X

ROOT = Path(__file__).resolve().parents[2]
CALIBRACION = ROOT / "config/autopilot/calibracion_motor.json"
OBLIGATORIAS = ("k", "lado", "ref", "ext", "rg")
OPS = {"<": np.less, "<=": np.less_equal, ">": np.greater, ">=": np.greater_equal, "==": np.equal}


def cargar(modulo):
    return importlib.import_module(modulo) if isinstance(modulo, str) else modulo


def contrato(mod) -> list:
    """Errores del contrato del módulo (vacía = cumple)."""
    e = []
    if not re.fullmatch(r"[A-Za-z0-9-]{3,30}", str(getattr(mod, "NOMBRE", ""))): e.append("NOMBRE: 3–30 letras, números o «-» (es el slug)")
    if not callable(getattr(mod, "eventos", None)): e.append("falta eventos(ctx)")
    if not getattr(mod, "EJECUCIONES", None): e.append("falta EJECUCIONES")
    else: e += X.validar(mod.EJECUCIONES)
    for n, f in (getattr(mod, "FILTROS", None) or {}).items():
        if not (isinstance(f, tuple) and len(f) == 3 and f[1] in OPS): e.append(f"FILTROS[{n}]: (columna, op, valor) con op en {list(OPS)}")
    return e


def generar(modulo, ctx) -> pd.DataFrame:
    mod = cargar(modulo); E = mod.eventos(ctx)
    falta = [c for c in OBLIGATORIAS if c not in E.columns]
    if falta: raise ValueError(f"{mod.NOMBRE}.eventos no entrega {falta} (contrato de edgelab/research/ejecucion.py)")
    k = E.k.to_numpy(np.int64)
    if "ses" not in E: E["ses"] = np.asarray(ctx["ses"])[k]
    if "t" not in E: E["t"] = np.asarray(ctx["t"], float)[k]
    return X.desenlaces(E, ctx, mod.EJECUCIONES)


def conteo(modulo) -> int:
    """Celdas de la exploración: definiciones × (ejecuciones × (1 + filtros))."""
    mod = cargar(modulo)
    return max(len(getattr(mod, "DEFINICIONES", []) or [None]), 1) * len(mod.EJECUCIONES) * (1 + len(getattr(mod, "FILTROS", {}) or {}))


# ----------------------------------------------------------------------------------------------- kernel (I5, I6)
def modulo_a_ruta(m: str) -> str:
    return m.replace(".", "/") + ".py"


def dependencias(modulo: str) -> list:
    """Todo lo que el kernel tiene que embeber: el módulo, el motor, los lectores y lo que importen (grafo de imports)."""
    from edgelab.research.embudo_runners import dependencias as dep
    rutas = []
    for r in (modulo_a_ruta(modulo), "edgelab/research/tablas.py", "edgelab/research/fuentes_ticks.py", "edgelab/research/grilla_generica.py",
              "edgelab/research/sintetico.py", "edgelab/holdout.py"):
        for x in dep(r):
            if x not in rutas: rutas.append(x)
    return rutas


def ruta_kernel(modulo) -> Path:
    return ROOT / "tools/kaggle_grilla/tablas" / f"kernel_{cargar(modulo).NOMBRE.lower()}.py"


def construir_kernel(modulo: str) -> Path:
    sys.path.insert(0, str(ROOT / "tools/kaggle_grilla"))
    from construir_kernel import construir
    out = ruta_kernel(modulo); out.parent.mkdir(parents=True, exist_ok=True)
    construir("tools/kaggle_grilla/tabla_main.py", str(out), dependencias(modulo))
    return out


# ----------------------------------------------------------------------------------------------- preflight (L1, V2, V3)
def calibracion() -> dict:
    """La del motor actual (se recalcula si el motor cambió; ≈ 10 s)."""
    h = X.huella_motor()
    if CALIBRACION.exists():
        c = json.loads(CALIBRACION.read_text(encoding="utf-8"))
        if c.get("huella") == h: return c
    c = X.calibrar(); c.pop("detalle", None)
    CALIBRACION.parent.mkdir(parents=True, exist_ok=True); CALIBRACION.write_text(json.dumps(c, indent=1), encoding="utf-8")
    return c


def bloques_sinteticos(mod, dias: int, seed: int):
    """Bloques sintéticos a la escala del módulo: `PREFLIGHT_PRECIO = (precio base, tick)` (p. ej. FX: (1.10, 0.00001)); si no,
    los de NQ (20000, 0,25). Mismo recorrido en ticks: sólo cambia la escala."""
    from edgelab.research import sintetico
    base, tick = getattr(mod, "PREFLIGHT_PRECIO", (None, 0.25))
    for b in sintetico.bloques(dias=dias, planta=False, seed=seed):
        if base is not None: b = b.assign(px=base + (b.px - 20000.0) * tick / 0.25)
        yield b


def preflight(modulo: str, dias: int = 60, kernel: bool = True) -> list:
    """Errores que impiden lanzar (vacía = puede lanzarse): contrato, causalidad por disparo y por cortes de los eventos, motor
    calibrado sin optimismo, la tabla sintética completa, y el kernel generado corriendo de punta a punta con FUENTE=SINT."""
    from edgelab.research import grilla_generica as GG, indicadores as I
    mod = cargar(modulo); e = contrato(mod)
    if e: return e
    ctx = GG.contexto_m1(list(bloques_sinteticos(mod, dias, 11)), tick=getattr(mod, "PREFLIGHT_PRECIO", (None, 0.25))[1])
    try:
        e += [f"causalidad: {x}" for x in I.causal_por_disparo(mod.eventos, ctx)[:3]]
        e += [f"causalidad (cortes): {x}" for x in I.causal(mod.eventos, ctx)[:3]]
    except Exception as ex: e.append(f"causalidad: no se pudo probar ({type(ex).__name__}: {str(ex)[:160]})")
    c = calibracion()
    if c.get("optimistas"): e.append(f"motor de ejecuciones optimista en {c['optimistas']}: no se lanza nada hasta corregirlo")
    try:
        T = generar(mod, ctx)
        if not len(T): e.append("la tabla sintética salió vacía: el generador no produce eventos (o los filtra todos)")
        for s in mod.EJECUCIONES:
            if f"r_{X.nombre(s)}" not in T: e.append(f"falta la columna de {X.nombre(s)}")
    except Exception as ex: e.append(f"generar: {type(ex).__name__}: {str(ex)[:200]}")
    if kernel and not e:
        k = construir_kernel(modulo if isinstance(modulo, str) else mod.__name__)
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, MODULO=mod.__name__, FUENTE="SINT", DESDE="20250805", HASTA="20250930")
            r = subprocess.run([sys.executable, str(k)], cwd=d, env=env, capture_output=True, text=True, timeout=900)
            if r.returncode or not list(Path(d).glob("TABLA_*.csv.gz")): e.append(f"el kernel no corre con FUENTE=SINT: {(r.stdout + r.stderr)[-400:]}")
    return e


# ----------------------------------------------------------------------------------------------- lectura y costos
def fuente_costo(mod, fuente: str) -> str:
    m = getattr(mod, "FUENTE_COSTO", None) or {}
    if fuente in m: return m[fuente]
    from edgelab.research.fuentes_ticks import DUKASCOPY
    spot = {v: k for k, v in reversed(list(DUKASCOPY.items()))}                         # USATECHIDXUSD -> NQ (el primero)
    return spot.get(fuente.replace("DK:", ""), fuente)


def periodo(mod, ses) -> np.ndarray:
    P = getattr(mod, "PERIODOS", None) or [("DESC", 0, 20260331), ("REP", 20260401, 20260930)]
    s = np.asarray(ses, np.int64); out = np.full(len(s), "OTRO", object)
    for n, d0, d1 in P: out[(s >= d0) & (s <= d1)] = n
    return out


def filtro(T: pd.DataFrame, f) -> np.ndarray:
    col, op, v = f
    with np.errstate(invalid="ignore"): return OPS[op](T[col].to_numpy(float), v)
