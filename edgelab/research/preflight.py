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
  ruido puro: 0 nominadas por el FDR q 0,10 ............ 7  (Romano-Wolf: aviso; decisión de Nico 2026-11-02)
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
        if (dif := I.causal_por_disparo(exp.disparos, ctx)): err.append(f"no causal (corte en la vela del disparo): {dif[0]}")
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
        # 2026-11-02 (decisión de Nico, opción 1): la compuerta es la misma que nomina en DESC desde el 2026-10-24, el FDR q 0,10.
        # Romano-Wolf con B_RW = 40 y pagos muy asimétricos rechazaba de más sobre ruido (2 de 6 semillas en u1_cfd, sin sesgo del
        # simulador): queda como aviso. Ver docs/research/relanzamiento_causal_20261102/RELANZAMIENTO.md.
        if tot["nominadas_fdr"] > 0: err.append(f"ruido puro con {tot['nominadas_fdr']} celdas nominadas por el FDR: hay un sesgo en el simulador o en las variables")
        if tot["n_rechazadas_rw"] > 0: avisos.append(f"ruido puro con {tot['n_rechazadas_rw']} celdas rechazadas por Romano-Wolf (diagnóstico, B_RW={GG.B_RW})")
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


CERTIFICADOS = ROOT / "config/causalidad_certificados.json"


def huella_codigo(modulo: str) -> str:
    """sha256 del experimento y de todo lo que importa del repo (lo que se embebe en el kernel)."""
    import hashlib
    from edgelab.research.embudo_runners import BASE_MODULOS, dependencias, modulo_a_ruta
    rutas = sorted(set(dependencias(modulo_a_ruta(modulo)) + [r for b in BASE_MODULOS for r in dependencias(b)]))
    h = hashlib.sha256()
    for r in rutas: h.update(r.encode()); h.update((ROOT / r).read_bytes())
    return h.hexdigest()


def certificar_causalidad(modulo: str, guardar: bool = True) -> list:
    """Candado del lanzamiento (2026-11-02, Nico: «que ninguna corrida pueda mirar al futuro»). Un experimento sólo se lanza
    si `disparos` pasa la prueba de corte en la vela de cada disparo sobre los datos de control del preflight, con el código
    EXACTO que va a correr (huella del experimento y sus dependencias). El resultado se guarda por huella: si el código no
    cambió, no se repite. Devuelve la lista de errores (vacía = certificado)."""
    import time
    huella = huella_codigo(modulo)
    cert = json.loads(CERTIFICADOS.read_text(encoding="utf-8")) if CERTIFICADOS.exists() else {}
    if cert.get(modulo, {}).get("huella") == huella and cert[modulo].get("ok"): return []
    from edgelab.research import grilla_generica as GG, indicadores as I, sintetico
    exp = importlib.import_module(modulo)
    if not hasattr(exp, "disparos"): return [f"{modulo} no expone `disparos`: sin eso no se puede certificar que no mira el futuro"]
    t0 = dict(t0_s=exp.PREFLIGHT_T0_S) if hasattr(exp, "PREFLIGHT_T0_S") else {}
    ctx = GG.contexto_m1(sintetico.bloques(dias=150, planta=False, seed=11, **t0), tick=0.25)
    if getattr(exp, "CONFIRMADOR", False): ctx["conf"] = GG.contexto_m1(sintetico.bloques(dias=150, planta=False, seed=12), tick=0.25)
    try: err = I.causal_por_disparo(exp.disparos, ctx) + [f"cortes fijos: {e}" for e in I.causal(exp.disparos, ctx)]
    except Exception as ex: err = [f"no se pudo certificar: {type(ex).__name__}: {str(ex)[:200]}"]
    if guardar:
        cert[modulo] = dict(huella=huella, ok=not err, errores=err[:3], ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        CERTIFICADOS.write_text(json.dumps(cert, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return err


# ----------------------------------------------------------------------------------------------------------------- pre-registro (K32)
def north_star_sha256(repo: Path | None = None) -> str:
    """sha256 del cuerpo de docs/NORTH_STAR.md hasta el marcador (la misma cuenta que tests/test_north_star_hash.py)."""
    import hashlib
    repo = ROOT if repo is None else Path(repo)
    raw = (repo / "docs/NORTH_STAR.md").read_bytes()
    return hashlib.sha256(raw.split(b"<!-- SHA256-BODY-ABOVE -->", 1)[0].replace(b"\r\n", b"\n")).hexdigest()


REQUISITOS_PREREGISTRO = (      # (descripción, regex sobre el texto, de dónde sale la regla)
    ("encabezado «Estado:»", r"^Estado:", "DOCUMENTATION_PROTOCOL"),
    ("justificación económica", r"justificaci[oó]n econ[oó]mica", "CLAUDE.md, rituales"),
    ("cómo podría refutarse", r"c[oó]mo podr[ií]a refutarse", "CLAUDE.md, rituales"),
    ("etapa EF del embudo", r"\bEF[2-5]\b", "CLAUDE.md, contador global"),
    ("línea «Antecedentes:» (tools/antecedentes.py)", r"^Antecedentes:", "CLAUDE.md, reutilizar antes de construir (C1/K26)"),
    ("línea «Potencia previa:» (tools/potencia_previa.py)", r"Potencia previa:", "K27–K30"),
)


LECTURA_PREVIA_RX = r"^Lectura previa:.*LEER_ANTES_DE_CADA_CORRIDA v\d+"
DIAGNOSTICO_RX = r"^Diagn[oó]stico de mecanismo:"      # K55/K56 (2026-11-19): ver edgelab/research/diagnostico_grilla.py


def _sin_diagnostico(repo: Path) -> set:
    """Pre-registros anteriores a K55/K56 (2026-11-19): exentos sólo de «Diagnóstico de mecanismo:». Lista cerrada; no se agrega nada."""
    f = Path(repo) / "config/preregistros_sin_diagnostico.json"
    return set(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else set()


def _sin_lectura_previa(repo: Path) -> set:
    """Pre-registros anteriores al índice obligatorio (2026-11-18): exentos sólo de «Lectura previa:». Lista cerrada; no se agrega nada."""
    f = Path(repo) / "config/preregistros_sin_lectura_previa.json"
    return set(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else set()


def validar_preregistro(path, repo: Path | None = None, exigir_commit: bool = True) -> list:
    """K32 (Nico, 2026-11-17: «salteártela demuestra que hay que cambiarlo: tiene que usarse todo EdgeLab, y bien»): lo que CLAUDE.md
    pide de un pre-registro, verificado en código. Vacío = válido. Lo usan `tools/registro_global.py preregistrado` (antes de contar
    pruebas) y el test del contador global (toda fila nueva fuera de la maquinaria estándar)."""
    import subprocess
    repo = ROOT if repo is None else Path(repo)
    p = Path(path); p = p if p.is_absolute() else repo / p
    if not p.exists(): return [f"el pre-registro {path} no existe"]
    t = p.read_text(encoding="utf-8", errors="ignore"); e = []
    if north_star_sha256(repo) not in t: e.append("no cita el sha256 vigente de docs/NORTH_STAR.md")
    for desc, rx, fuente in REQUISITOS_PREREGISTRO:
        if not re.search(rx, t, re.M | re.I): e.append(f"falta {desc} ({fuente})")
    try: rel_p = p.relative_to(repo).as_posix()
    except ValueError: rel_p = p.as_posix()
    if rel_p not in _sin_lectura_previa(repo) and not re.search(LECTURA_PREVIA_RX, t, re.M):
        e.append("falta la línea «Lectura previa: LEER_ANTES_DE_CADA_CORRIDA vN — …» (docs/research/LEER_ANTES_DE_CADA_CORRIDA.md, "
                 "Nico 2026-11-18)")
    if rel_p not in _sin_diagnostico(repo) and not re.search(DIAGNOSTICO_RX, t, re.M):
        e.append("falta la línea «Diagnóstico de mecanismo: …» (K55/K56): qué mueve cada perilla y cómo se va a leer la grilla con "
                 "edgelab.research.diagnostico_grilla (operaciones por celda, número efectivo de variantes, episodios), o «no aplica — motivo»")
    base_f = repo / "config/preregistros_baseline.json"
    base_pre = set(json.loads(base_f.read_text(encoding="utf-8"))) if base_f.exists() else set()
    ex_ma_f = repo / "config/preregistros_sin_memoria_activa.json"
    ex_ma = set(json.loads(ex_ma_f.read_text(encoding="utf-8"))) if ex_ma_f.exists() else set()
    if rel_p not in base_pre and rel_p not in ex_ma:
        from edgelab.research.memoria_activa import verificar_memoria_activa
        e.extend(verificar_memoria_activa(t, familia=None, root=repo))
    if exigir_commit:
        rel = str(p.relative_to(repo))
        if not subprocess.run(["git", "log", "-1", "--format=%H", "--", rel], cwd=repo, capture_output=True, text=True).stdout.strip():
            e.append("no está committeado (se escribe y committea ANTES de contar y correr)")
        elif subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=repo).returncode:
            e.append("tiene cambios sin commitear: lo que se registra tiene que ser lo committeado")
    return e
