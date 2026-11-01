"""Preflight OBLIGATORIO de experimentos de grilla y campañas (2026-10-23): convierte los errores cometidos en chequeos que corren
solos antes de lanzar (pedido de Nico: «que queden mitigados automáticamente en los próximos análisis»).
Revisión de errores: docs/research/areas_expansion_20261022/u1/REVISION_ERRORES_Y_PLAN_U1_CRUZADO.md.

  python -m edgelab.research.preflight edgelab.research.u1_indaga          # experimento: estático + dinámico (sintéticos)
Lo usan: el programador del agente (antes de aplicar un experimento), `generate.campanas_grilla` (cada campaña), la guía.

Qué ataca cada chequeo (número = error de la revisión):
  interfaz completa e INDICADORES usables ............ 19, 20  (y paridad sin evidencia)
  cada Variable bien formada (un solo tipo de corte) .. 2, 13
  disparos corre y trae las columnas declaradas ...... 1 (objeto inexistente o vacío)
  causalidad de disparos/variables ................... look-ahead en general
  cortes por cuantiles no degenerados (>= 10 % por nivel) 2
  control de ruido con potencia (celdas evaluables > 0) 16
  ruido puro: 0 rechazadas por Romano-Wolf ............ 7
  ejecuciones equivalentes (perillas muertas) ......... 4
  niveles_lote (si existe) idéntico a niveles ......... camino rápido sin oráculo
  sin excepciones con celdas vacías ................... 15
  n_celdas coherente con lo que se corre ............. 14
  campaña: campos, holdout, condiciones con test ...... 5, 6, 23 (condición escrita sin su línea de código)
  campaña con seguimiento: pérdida máxima estructural  10
"""
from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ATRIBUTOS = ("NOMBRE", "VARIABLES", "EJECUCIONES", "disparos", "niveles", "BASE", "INDICADORES")


def estatico(exp) -> list:
    from edgelab.research import indicadores as I
    err = [f"falta {a}" for a in ATRIBUTOS if not hasattr(exp, a)]
    if err: return err
    try: I.exigir(exp.INDICADORES)
    except I.IndicadorNoUsable as e: err.append(f"indicador no usable: {e}")
    cols = set()
    for v in exp.VARIABLES:
        tipos = sum(bool(x) for x in (v.cuantiles, v.cortes, v.categoria))
        if tipos != 1: err.append(f"variable {v.nombre}: declarar exactamente uno de cuantiles / cortes / categoria")
        n = v.categoria or (v.cuantiles if v.cuantiles else len(v.cortes) + 1 - (1 if v.piso else 0))
        if v.modo == "extremos" and n != 3: err.append(f"variable {v.nombre}: modo extremos exige 3 niveles (tiene {n})")
        if v.columna in cols: err.append(f"variable {v.nombre}: columna {v.columna} repetida")
        cols.add(v.columna)
    from edgelab.research.grilla_generica import NORMALIZACIONES
    if getattr(exp, "NORMALIZAR", None) not in (None,) + NORMALIZACIONES: err.append(f"NORMALIZAR {exp.NORMALIZAR!r}: uno de {NORMALIZACIONES}")
    nombres = [v.nombre for v in exp.VARIABLES] + ["ejecución"]
    for k in exp.BASE:
        if k not in nombres: err.append(f"BASE nombra una perilla inexistente: {k}")
    return err


def dinamico(exp, dias=150, b_rw=40) -> tuple:
    from edgelab.research import grilla_generica as GG, indicadores as I, sintetico
    err, avisos = [], []
    viejo_b = GG.B_RW; GG.B_RW = b_rw
    try:
        t0 = dict(t0_s=exp.PREFLIGHT_T0_S) if hasattr(exp, "PREFLIGHT_T0_S") else {}   # 2026-11-01: bloques alineados a la sesión CME
        ctx = GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=11, **t0), tick=0.25)          # si el experimento lo pide
        if getattr(exp, "CONFIRMADOR", False):                        # experimento con segundo instrumento: otro sintético independiente
            ctx["conf"] = GG.contexto_m1(sintetico.bloques(dias=dias, planta=False, seed=12), tick=0.25)
        D = exp.disparos(ctx)
        if not len(D): return [f"disparos vacío en {dias} días sintéticos: el objeto no aparece o la definición es demasiado estrecha"], avisos
        faltan = [c for c in ["k"] + [v.columna for v in exp.VARIABLES] if c not in D.columns]
        if faltan: return [f"disparos no trae las columnas {faltan}"], avisos
        if (dif := I.causal(exp.disparos, ctx)): err.append(f"no causal: {dif[0]}")
        cortes = GG.cortes_e0(D, exp.VARIABLES)
        for v, b in zip(exp.VARIABLES, GG.discretizar(D, exp.VARIABLES, cortes)):
            if v.cuantiles:
                frac = np.bincount(b[b >= 0], minlength=v.cuantiles) / max((b >= 0).sum(), 1)
                if frac.min() < 0.10: err.append(f"variable {v.nombre}: un nivel con {frac.min():.0%} de los disparos (cortes degenerados)")
            falt = float((b < 0).mean())
            if falt > 0.5: avisos.append(f"variable {v.nombre}: {falt:.0%} fuera de nivel (faltante o bajo el piso)")
        if hasattr(exp, "niveles_lote"):                              # camino rápido opcional: debe ser idéntico a niveles (oráculo)
            O1, O2 = GG.ops_por_fila(exp, D, ctx), GG._ops_lote(exp, D, ctx)
            if O1.shape != O2.shape or not np.array_equal(O1, O2, equal_nan=True):
                err.append(f"niveles_lote no coincide con niveles ({len(O2)} vs {len(O1)} operaciones): corregir antes de usarlo")
        res, _ = GG.correr(exp, ctx, modo="DESC", friccion=1.0, extra_adverso=0.5, cortes=cortes, log=lambda s: None)
        tot = res["canales"]["total"]
        if tot["evaluables"] == 0: err.append("control de ruido sin celdas evaluables: no tiene con qué fallar (más días o perillas más anchas)")
        if tot["n_rechazadas_rw"] > 0: err.append(f"ruido puro con {tot['n_rechazadas_rw']} celdas rechazadas por Romano-Wolf: hay un sesgo en el simulador o en las variables")
        if res.get("ejecuciones_equivalentes"): err.append(f"{len(res['ejecuciones_equivalentes'])} grupos de ejecuciones idénticas (perillas muertas): rediseñar, no duplicar pruebas")
        if res["celdas"] != GG.n_celdas(exp, cortes): err.append("n_celdas no coincide con las celdas que se corren")
        return err, avisos
    except Exception as e:                                            # cualquier excepción con datos de control es un error de preflight
        return err + [f"excepción con datos sintéticos: {type(e).__name__}: {e}"[:300]], avisos
    finally:
        GG.B_RW = viejo_b


def verificar_experimento(modulo: str, dinamico_tambien=True) -> dict:
    exp = importlib.import_module(modulo)
    err = estatico(exp); avisos = []
    if not err and dinamico_tambien:
        e2, avisos = dinamico(exp); err += e2
    return dict(modulo=modulo, ok=not err, errores=err, avisos=avisos)


def verificar_campana(d: dict, repo: Path = ROOT) -> list:
    """Chequeos baratos de una campaña (los corre generate.campanas_grilla para cada JSON)."""
    from edgelab.autopilot import guard
    from edgelab.autopilot.generate import CAMPO_CAMPANA
    err = [f"falta {k}" for k in CAMPO_CAMPANA if k not in d]
    for n in d.get("needs", []):
        p = n.split(":")
        if len(p) == 3 and (p[2] >= guard.HOLDOUT_FIRST_TRADE_DATE or p[1] >= guard.HOLDOUT_FIRST_TRADE_DATE) and d.get("modo") != "HOLDOUT":
            err.append(f"need {n} toca el holdout")
    if d.get("modo") == "REP" and not (d.get("celdas") and d.get("cortes") is not None): err.append("REP sin celdas y cortes congelados")
    for c in d.get("condiciones", []):                                 # cada condición escrita tiene su test (error 5/6)
        archivo, _, fn = str(c.get("test", "")).partition("::")
        if not fn or not (repo / archivo).exists() or not re.search(rf"def {re.escape(fn)}\(", (repo / archivo).read_text(encoding="utf-8")):
            err.append(f"condición sin test que la verifique: {c.get('texto', '?')[:80]} -> {c.get('test')}")
    if d.get("seguimiento") and not d.get("perdida_max_estructural"):
        err.append("seguimiento secuencial sin pérdida máxima estructural por operación (cotas del peor caso visto: error de U1-B)")
    return err


if __name__ == "__main__":
    r = verificar_experimento(sys.argv[1])
    print(json.dumps(r, indent=1, ensure_ascii=False)); sys.exit(0 if r["ok"] else 1)


def codigo_vigente(resultado: dict, repo: Path = ROOT) -> list:
    """Error 23 (corrida con código que después se corrigió): compara los SHA de los módulos que registró el kernel
    (`modulos`) con los archivos actuales. Lista de módulos que cambiaron: si no está vacía, esa corrida no se interpreta sin
    revisar qué cambió (y si el cambio toca la medición, se relanza)."""
    import hashlib
    cambios = []
    for m, sha in (resultado.get("modulos") or {}).items():
        f = repo / m
        if f.name == "__init__.py": continue                              # se embeben vacíos
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != sha: cambios.append(m)
    return cambios
