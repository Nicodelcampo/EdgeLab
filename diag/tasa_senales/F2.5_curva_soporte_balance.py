# -*- coding: utf-8 -*-
"""F2.5 -- curva descriptiva de soporte comun y balance (target-free).

ESCRITO POR EL AUDITOR SIN PODER EJECUTAR NADA. Correr la suite y arreglar lo
que rompa antes de darle valor a ningun numero de aca.

## Por que existe

F2.3 dejo `smd_pre_within_estrato ~= smd_post` y lo leyo como "no hay
solapamiento". Eso estaba sobre-extendido: con pool tipico ~9.6 y K=8 el
matcher toma ~83% del pool, asi que `mean(controles) ~= mean(pool)` queda
forzado ARITMETICAMENTE, haya o no solapamiento. Las dos hipotesis predicen el
mismo numero.

F2.4 midio la posicion de cada fuente dentro de su propio pool y encontro dos
problemas distintos, no uno:

- `log1p_sigma60_ticks`: 0.213 fuera de rango contra ~0.20 esperado POR AZAR
  (bajo intercambiabilidad, con la fuente excluida del pool, el rango de la
  fuente entre los n+1 valores es uniforme, asi que
  `P(fuente > max del pool) = 1/(n+1)`; con n=9 eso da 0.10 por cola). No hay
  problema de soporte comun: el desbalance es el efecto censo de K=8.
- `log1p_bar_volume`: 0.361 por encima del maximo contra ~0.10 esperado. Con
  la cola inferior vacia (0.004) y el decil inferior del histograma en 9 zonas
  donde se esperan ~99. Distribucion corrida, no cola alta.

La causa de lo segundo es definicional: BigTrap2 dispara con una condicion de
volumen (`min_trap_volume=30`), asi que balancear `bar_volume` es condicionar
sobre una funcion casi determinista de la asignacion.

Lo que falta para decidir A/B/C/D no es otra vuelta de tuning: es saber si ese
corrimiento es LOCAL (artefacto del pool de 9 candidatos del mismo minuto) o
GLOBAL (la fuente supera tambien al maximo del archivo entero). Esta curva lo
contesta en una corrida.

## Que hace

Recorre una rejilla CONGELADA de 5 x 6 x 4 = 120 celdas:

    ventana_minuto : 0, 1, 5, 15, None (= todo el archivo)
    k              : 1, 3, 5, 8, 12, None (= todos)
    caliper        : None, 0.1, 0.2, 0.5   (en unidades de MAD del pool)

y reporta por celda: cobertura, ratio de seleccion, diferencia cruda de medias
y SMD con `sd_ref` CONGELADO; y por ventana: las metricas de soporte comun de
F2.4 (above/below/percentil/deciles).

## Que NO hace

No importa ni llama `zone_lifecycle` ni `endpoint_binario`. No puede producir
un efecto ni por accidente. `estimand_suppressed=True`,
`outcomes_accessed=False`, `holdout_opened=False`.

## Aditivo por diseno

No modifica una sola linea de `F1.1_nulo_condicional_distancia.py`. Lo importa
via `importlib` (su nombre tiene un punto y no es importable con `import`) y
reusa `construir_universo_zonas`, `calcular_covariables_causales`,
`indexar_por_minuto`, `horizonte_zona`, `muestra_pre_matching` y `_mad`. Por lo
tanto no puede romper los tests existentes ni el sellado `spec_sha256` de la
rama que va a la corrida formal.

La duplicacion inevitable (el pool con ventana y la seleccion con caliper) esta
pinneada por dos tests de EQUIVALENCIA: con ventana 0 el pool es identico al de
`construir_pool_candidatos`, y sin caliper la seleccion elige exactamente los
mismos `bar_index` que `emparejar_controles`.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np

REPO_PATH = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_PATH))

_F11_FILENAME = "F1.1_nulo_condicional_distancia.py"


def _cargar_f11():
    """`F1.1_nulo_condicional_distancia` tiene un punto en el nombre del modulo,
    asi que no es importable con `import`. Se carga por ruta, igual que hacen
    los tests. Se registra en sys.modules ANTES de ejecutarlo para que sus
    propios imports relativos al repo no lo carguen dos veces."""
    ruta = Path(__file__).resolve().parent / _F11_FILENAME
    if not ruta.exists():
        raise RuntimeError("no se encontro %s junto a este script" % _F11_FILENAME)
    spec = importlib.util.spec_from_file_location("f11_nulo_condicional_distancia", ruta)
    if spec is None or spec.loader is None:
        raise RuntimeError("no se pudo construir el spec de importacion de %s" % ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


f11 = _cargar_f11()

SCHEMA_VERSION = "F2.5_curva_soporte_balance_v1"
SPEC_PATH = REPO_PATH / "specs" / "bigtrap2_soporte_balance_curve_v1.json"

COVARIABLES = ("log1p_sigma60_ticks", "log1p_bar_volume")

# ---- rejilla CONGELADA. Cualquier cambio aca cambia el hash y hay que
# ---- actualizar la spec en el MISMO commit, o el script aborta con exit 6.
VENTANAS_MINUTO = (0, 1, 5, 15, None)
K_GRID = (1, 3, 5, 8, 12, None)
CALIPER_GRID = (None, 0.1, 0.2, 0.5)

_ETIQUETA_VENTANA_TODO = "todo_el_archivo"
_ETIQUETA_K_TODOS = "todos"
_ETIQUETA_SIN_CALIPER = "ninguno"


# ======================================================================
# Rejilla y su hash (gate fail-closed contra la spec)
# ======================================================================

def rejilla_declarada():
    """Serializacion canonica de la rejilla. Es lo que se hashea y lo que la
    spec tiene que declarar identico."""
    return dict(
        ventanas_minuto=[_ETIQUETA_VENTANA_TODO if v is None else v for v in VENTANAS_MINUTO],
        k=[_ETIQUETA_K_TODOS if k is None else k for k in K_GRID],
        caliper_en_mad=[_ETIQUETA_SIN_CALIPER if c is None else c for c in CALIPER_GRID],
        celda_central=dict(ventana_minutos=0, k=f11.K_CONTROLS, caliper=_ETIQUETA_SIN_CALIPER),
        min_controls_regla="min(k, MIN_CONTROLS) si k es entero; MIN_CONTROLS si k es 'todos'",
        sd_ref_regla="congelado en la definicion within-stratum de ventana 0",
    )


def multiverse_manifest_sha256():
    return hashlib.sha256(
        json.dumps(rejilla_declarada(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def spec_sha256():
    return hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()


def verificar_rejilla_contra_spec():
    """Fail-closed: si el codigo y el pre-registro no declaran la MISMA rejilla,
    no se computa nada. Un multiverso editable despues de ver resultados no es
    robustez, es el jardin de senderos que se bifurcan con mejor prensa."""
    if not SPEC_PATH.exists():
        return False, "no existe %s" % SPEC_PATH
    try:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 -- se reporta tal cual
        return False, "spec ilegible: %r" % (exc,)
    declarada = ((spec.get("multiverse") or {}).get("rejilla"))
    if declarada != rejilla_declarada():
        return False, ("la rejilla de la spec no coincide con la del codigo\n"
                       "  spec:   %r\n  codigo: %r" % (declarada, rejilla_declarada()))
    return True, None


def etiqueta_celda(ventana, k, caliper):
    return "w=%s|k=%s|cal=%s" % (
        _ETIQUETA_VENTANA_TODO if ventana is None else ventana,
        _ETIQUETA_K_TODOS if k is None else k,
        _ETIQUETA_SIN_CALIPER if caliper is None else caliper)


# ======================================================================
# Funciones puras (todo lo testeable sin datos vive aca)
# ======================================================================

def pool_por_ventana(zona, por_minuto, creadoras, n_bars, horizon_i, ventana_minutos):
    """Igual que `construir_pool_candidatos` pero con la restriccion de minuto
    relajada a `|minuto_candidato - minuto_fuente| <= ventana_minutos`.

    `ventana_minutos=0` devuelve EXACTAMENTE lo mismo que
    `construir_pool_candidatos` (hay un test de equivalencia que lo pinnea).
    `ventana_minutos=None` quita la restriccion de minuto por completo.

    Los otros tres filtros se mantienen intactos en toda la rejilla: otra
    sesion, barra no creadora de ninguna zona, y >= horizon_i barras futuras.
    """
    m = zona["minute_of_session"]
    ses_fuente = zona["session_date"]
    if ventana_minutos is None:
        minutos = sorted(por_minuto.keys())
    else:
        minutos = [mm for mm in range(m - int(ventana_minutos), m + int(ventana_minutos) + 1)
                   if mm in por_minuto]
    candidatos = []
    for mm in minutos:
        for ses, bar_idx in por_minuto.get(mm, ()):
            if ses == ses_fuente:
                continue
            if bar_idx in creadoras:
                continue
            if (n_bars - 1) - bar_idx < horizon_i:
                continue
            candidatos.append((ses, bar_idx))
    return candidatos


def scores_del_pool(zona_cov, pool_covs):
    """Distancia euclidea robustamente estandarizada por el MAD del pool,
    identica a `emparejar_controles` (MAD=0 => esa covariable aporta 0).

    `pool_covs`: lista de (log1p_sigma60, log1p_bar_volume) en el MISMO orden
    que el pool, porque el MAD se calcula sobre ese pool y no sobre otro.
    """
    s60 = np.asarray([c[0] for c in pool_covs], dtype=np.float64)
    lv = np.asarray([c[1] for c in pool_covs], dtype=np.float64)
    mad_s60 = f11._mad(s60)
    mad_lv = f11._mad(lv)
    zs60, zlv = zona_cov
    d_s60 = np.zeros_like(s60) if mad_s60 == 0 else ((s60 - zs60) / mad_s60) ** 2
    d_lv = np.zeros_like(lv) if mad_lv == 0 else ((lv - zlv) / mad_lv) ** 2
    return np.sqrt(d_s60 + d_lv), float(mad_s60), float(mad_lv)


def min_controls_efectivo(k, min_controls=None):
    """Con K=1 o K=3, exigir MIN_CONTROLS=5 controles abstendria la celda
    entera por construccion y la haria vacia sin informar nada. La regla
    declarada es `min(k, MIN_CONTROLS)` para k entero y `MIN_CONTROLS` para
    k='todos'."""
    base = f11.MIN_CONTROLS if min_controls is None else int(min_controls)
    return base if k is None else min(int(k), base)


def seleccionar(triples, k, caliper, min_controls):
    """`triples`: lista de (score, session_date, bar_index).

    Caliper primero (se descartan los candidatos con score > caliper), despues
    los k mas cercanos con el desempate `(score, session_date, bar_index)` de
    `emparejar_controles`. Devuelve None si quedan menos de `min_controls`.

    `heapq.nsmallest(k, ...)` devuelve el mismo resultado que `sorted(...)[:k]`
    para tuplas totalmente ordenadas -- y `bar_index` es unico dentro de un
    archivo, asi que no hay empates posibles en la tupla completa.
    """
    candidatos = triples if caliper is None else [t for t in triples if t[0] <= float(caliper)]
    if k is None:
        elegidos = sorted(candidatos)
    else:
        elegidos = heapq.nsmallest(int(k), candidatos)
    if len(elegidos) < min_controls:
        return None
    return elegidos


def posicion_en_pool(x, vals):
    """Devuelve (above_max, below_min, pct) con pct = fraccion del pool
    ESTRICTAMENTE menor que x. Misma definicion que F2.4."""
    return (bool(x > max(vals)), bool(x < min(vals)),
            sum(1 for v in vals if v < x) / len(vals))


def sd_pooled_within(estratos_por_archivo, clave):
    """Replica exacta de `_acumular_within` de F2.3: sqrt(SS_within/(N-G)) sobre
    los estratos (archivo x minuto_de_sesion) de la muestra pre-matching de
    VENTANA 0. Es el denominador congelado de toda la curva."""
    ss, gl, n_obs, n_estratos, n_singleton = 0.0, 0, 0, 0, 0
    for arch in sorted(estratos_por_archivo):
        for _m, e in (estratos_por_archivo.get(arch) or {}).items():
            xs = [x for x in (list(e["fuentes_" + clave]) + list(e["pool_" + clave]))
                  if math.isfinite(x)]
            n_obs += len(xs)
            n_estratos += 1
            if len(xs) < 2:
                n_singleton += 1
                continue
            arr = np.asarray(xs, dtype=np.float64)
            ss += float(np.sum((arr - arr.mean()) ** 2))
            gl += len(arr) - 1
    sd = math.sqrt(ss / gl) if gl > 0 else None
    return (sd if (sd is not None and sd > 0) else None), dict(
        n_estratos=n_estratos, n_estratos_singleton=n_singleton,
        n_obs=n_obs, grados_libertad=gl)


# ======================================================================
# Acumuladores CRUDOS (se poolean entre archivos ANTES de reducir)
# ======================================================================

def _soporte_vacio():
    return dict(n_zonas=0, n_sin_pool=0, suma_n_pool=0,
                por_covariable={c: dict(above=0, below=0, pcts=[]) for c in COVARIABLES})


def _celda_vacia():
    return dict(n_zonas=0, n_zonas_ok=0, suma_n_pool_ok=0, suma_k_efectivo=0,
                suma_fuente_s60=0.0, suma_ctrl_s60=0.0,
                suma_fuente_lv=0.0, suma_ctrl_lv=0.0)


def fusionar_crudos(destino, origen):
    """Suma los crudos de un archivo al total. Nunca se promedian fracciones ya
    reducidas por archivo: se suman conteos y se extienden listas, y las
    fracciones se calculan UNA vez al final."""
    for w, s in origen["soporte"].items():
        d = destino["soporte"].setdefault(w, _soporte_vacio())
        d["n_zonas"] += s["n_zonas"]
        d["n_sin_pool"] += s["n_sin_pool"]
        d["suma_n_pool"] += s["suma_n_pool"]
        for c in COVARIABLES:
            d["por_covariable"][c]["above"] += s["por_covariable"][c]["above"]
            d["por_covariable"][c]["below"] += s["por_covariable"][c]["below"]
            d["por_covariable"][c]["pcts"].extend(s["por_covariable"][c]["pcts"])
    for etiqueta, cel in origen["celdas"].items():
        d = destino["celdas"].setdefault(etiqueta, _celda_vacia())
        for campo, valor in cel.items():
            d[campo] += valor
    return destino


def crudo_vacio():
    return dict(soporte={}, celdas={})


# ======================================================================
# Reduccion final
# ======================================================================

def _pct(valor, total):
    return (valor / total) if total else None


def resumir_soporte(soporte_total):
    """F2.5 fix (encontrado al correr el smoke, no lo atrapo la suite): las
    claves de `out` tienen que ser SIEMPRE string. Con `etiqueta = w` para
    `w` entero, `out` terminaba con claves mixtas (0, 1, 5, 15 como int,
    "todo_el_archivo" como str) -- json.dumps(..., sort_keys=True) no puede
    comparar str con int para ordenar y el payload nunca llegaba a
    escribirse (TypeError al final de main(), despues de correr TODA la
    curva)."""
    out = {}
    for w, s in soporte_total.items():
        etiqueta = _ETIQUETA_VENTANA_TODO if w is None else str(w)
        fila = dict(n_zonas=s["n_zonas"], n_sin_pool=s["n_sin_pool"],
                    tamano_pool_medio=_pct(s["suma_n_pool"], s["n_zonas"]),
                    por_covariable={})
        for c in COVARIABLES:
            dc = s["por_covariable"][c]
            pcts = dc["pcts"]
            n = len(pcts)
            deciles = [0] * 10
            for p in pcts:
                deciles[min(9, int(p * 10))] += 1
            # Valor esperado bajo intercambiabilidad: con pool de tamano medio
            # nbar, P(fuente > max) = 1/(nbar+1). Se publica al lado del
            # observado para que la fraccion no se lea contra cero.
            nbar = _pct(s["suma_n_pool"], s["n_zonas"])
            esperado = (1.0 / (nbar + 1.0)) if nbar else None
            fila["por_covariable"][c] = dict(
                frac_above_max=_pct(dc["above"], n),
                frac_below_min=_pct(dc["below"], n),
                frac_fuera_de_rango=_pct(dc["above"] + dc["below"], n),
                frac_above_max_esperada_por_azar=esperado,
                exceso_sobre_azar=((dc["above"] / n) / esperado)
                if (n and esperado) else None,
                pct_p50=float(np.percentile(pcts, 50)) if pcts else None,
                pct_p90=float(np.percentile(pcts, 90)) if pcts else None,
                histograma_pct_deciles=deciles,
            )
        out[etiqueta] = fila
    return out


def resumir_celdas(celdas_total, sd_ref_s60, sd_ref_lv,
                   max_abs_smd=None, min_cobertura=None):
    max_abs = f11.MAX_ABS_SMD if max_abs_smd is None else max_abs_smd
    min_cob = f11.MIN_ZONE_COVERAGE if min_cobertura is None else min_cobertura
    filas = []
    for etiqueta in sorted(celdas_total):
        cel = celdas_total[etiqueta]
        n_ok = cel["n_zonas_ok"]
        cobertura = _pct(n_ok, cel["n_zonas"])
        dif_s60 = _pct(cel["suma_fuente_s60"] - cel["suma_ctrl_s60"], n_ok)
        dif_lv = _pct(cel["suma_fuente_lv"] - cel["suma_ctrl_lv"], n_ok)
        smd_s60 = f11.smd_con_sd_ref(dif_s60, 0.0, sd_ref_s60)
        smd_lv = f11.smd_con_sd_ref(dif_lv, 0.0, sd_ref_lv)
        ok_s60 = smd_s60 is not None and math.isfinite(smd_s60) and abs(smd_s60) <= max_abs
        ok_lv = smd_lv is not None and math.isfinite(smd_lv) and abs(smd_lv) <= max_abs
        filas.append(dict(
            celda=etiqueta, n_zonas=cel["n_zonas"], n_zonas_ok=n_ok,
            cobertura=cobertura, cobertura_ok=(cobertura is not None and cobertura >= min_cob),
            tamano_pool_medio_ok=_pct(cel["suma_n_pool_ok"], n_ok),
            k_efectivo_medio=_pct(cel["suma_k_efectivo"], n_ok),
            ratio_seleccion=_pct(cel["suma_k_efectivo"], cel["suma_n_pool_ok"]),
            dif_cruda_log1p_sigma60_ticks=dif_s60,
            dif_cruda_log1p_bar_volume=dif_lv,
            smd_log1p_sigma60_ticks=smd_s60, smd_log1p_bar_volume=smd_lv,
            smd_sigma60_ok=ok_s60, smd_bar_volume_ok=ok_lv,
            celda_pasa_gates=bool(
                ok_s60 and ok_lv and cobertura is not None and cobertura >= min_cob),
        ))
    return filas


# ======================================================================
# Orquestacion por archivo
# ======================================================================

def procesar_archivo_curva(kernel_zones, close_t, bar_volume, ses_de_barra, rango_sesion,
                           fechas_universo, tick_size, n_bars,
                           ventanas=VENTANAS_MINUTO, k_grid=K_GRID, caliper_grid=CALIPER_GRID):
    """Devuelve los CRUDOS de un archivo mas su muestra pre-matching de ventana
    0 (insumo del sd_ref congelado). No calcula ninguna fraccion."""
    universo, creadoras = f11.construir_universo_zonas(
        kernel_zones, ses_de_barra, rango_sesion, fechas_universo, tick_size, n_bars)
    cov = f11.calcular_covariables_causales(close_t, bar_volume)
    cov_por_barra = {}
    for i in range(n_bars):
        s60, lv = cov["log1p_sigma60_ticks"][i], cov["log1p_bar_volume"][i]
        if math.isfinite(s60) and math.isfinite(lv):
            cov_por_barra[i] = (float(s60), float(lv))
    por_minuto = f11.indexar_por_minuto(ses_de_barra, rango_sesion, n_bars)

    zonas = []
    for zona in universo:
        cb = zona["created_bar"]
        zonas.append(dict(zona, horizon_i=f11.horizonte_zona(cb, n_bars),
                          covariables_fuente=cov_por_barra.get(cb, (None, None))))

    # sd_ref congelado: se usa la MISMA funcion de F1.1, en ventana 0, para que
    # el denominador sea literalmente el de F2.3 y los numeros sean comparables.
    estratos = f11.muestra_pre_matching(zonas, por_minuto, creadoras, cov_por_barra, n_bars)

    crudo = dict(soporte={w: _soporte_vacio() for w in ventanas}, celdas={})
    for etiqueta in (etiqueta_celda(w, k, c)
                     for w in ventanas for k in k_grid for c in caliper_grid):
        crudo["celdas"][etiqueta] = _celda_vacia()

    for z in zonas:
        zc = z["covariables_fuente"]
        if zc[0] is None:
            continue
        for w in ventanas:
            candidatos = pool_por_ventana(z, por_minuto, creadoras, n_bars, z["horizon_i"], w)
            pool = [(cov_por_barra[b][0], cov_por_barra[b][1], s, b)
                    for s, b in candidatos if cov_por_barra.get(b) is not None]
            s = crudo["soporte"][w]
            s["n_zonas"] += 1
            s["suma_n_pool"] += len(pool)
            for k in k_grid:
                for cal in caliper_grid:
                    crudo["celdas"][etiqueta_celda(w, k, cal)]["n_zonas"] += 1
            if not pool:
                s["n_sin_pool"] += 1
                continue
            for idx, nombre in enumerate(COVARIABLES):
                above, below, pct = posicion_en_pool(zc[idx], [p[idx] for p in pool])
                dc = s["por_covariable"][nombre]
                dc["above"] += int(above)
                dc["below"] += int(below)
                dc["pcts"].append(pct)
            scores, _mad_s60, _mad_lv = scores_del_pool(zc, [(p[0], p[1]) for p in pool])
            triples = [(float(scores[i]), pool[i][2], pool[i][3]) for i in range(len(pool))]
            for k in k_grid:
                for cal in caliper_grid:
                    elegidos = seleccionar(triples, k, cal, min_controls_efectivo(k))
                    if elegidos is None:
                        continue
                    cel = crudo["celdas"][etiqueta_celda(w, k, cal)]
                    cel["n_zonas_ok"] += 1
                    cel["suma_n_pool_ok"] += len(triples)
                    cel["suma_k_efectivo"] += len(elegidos)
                    n_e = len(elegidos)
                    cel["suma_fuente_s60"] += zc[0]
                    cel["suma_fuente_lv"] += zc[1]
                    cel["suma_ctrl_s60"] += sum(
                        cov_por_barra[b][0] for _sc, _ses, b in elegidos) / n_e
                    cel["suma_ctrl_lv"] += sum(
                        cov_por_barra[b][1] for _sc, _ses, b in elegidos) / n_e

    return dict(crudo=crudo, estratos_pre_matching=estratos,
                n_zonas_universo=len(universo))


# ======================================================================
# main
# ======================================================================

def _parsear_ventanas(texto):
    if not texto:
        return VENTANAS_MINUTO
    salida = []
    for parte in texto.split(","):
        parte = parte.strip()
        if parte in ("todo", "todo_el_archivo", "none", "None"):
            salida.append(None)
        else:
            salida.append(int(parte))
    return tuple(salida)


def main(argv=None):
    ap = argparse.ArgumentParser(description="F2.5 curva de soporte comun y balance")
    ap.add_argument("--out", default=None)
    ap.add_argument("--smoke-archivo", default=None,
                    help="corre SOLO ese archivo. Recomendado ANTES de las 201 sesiones: "
                         "la ventana 'todo el archivo' evalua ~6122 candidatos por zona "
                         "en vez de ~9.6 y hay que medir el costo real primero.")
    ap.add_argument("--ventanas", default=None,
                    help="subconjunto de ventanas, coma-separado (ej '0,1,todo'). Solo para "
                         "acotar el costo: la rejilla completa sigue siendo la de la spec.")
    a = ap.parse_args(argv)

    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve() != (REPO_PATH / ".venv").resolve():
        print("NO ES EL .venv DEL REPO -- no se ejecuta.")
        return 2

    head_start = f11.git_head()
    dirty_start = f11.git_dirty()
    if dirty_start:
        print("ABSTAIN_PROVENANCE: el arbol de trabajo esta sucio ANTES de empezar -- "
              "se aborta ACA, sin computar ni imprimir ningun diagnostico.")
        return 5
    ns_hash = f11.north_star_body_sha256()
    if ns_hash != f11.NORTH_STAR_BODY_SHA256_EXPECTED:
        print("ABSTAIN_PROVENANCE: hash de NORTH_STAR.md no coincide (%s != %s)"
              % (ns_hash, f11.NORTH_STAR_BODY_SHA256_EXPECTED))
        return 3
    rejilla_ok, motivo = verificar_rejilla_contra_spec()
    if not rejilla_ok:
        print("ABSTAIN_PREREGISTRO: %s" % motivo)
        return 6

    ventanas = _parsear_ventanas(a.ventanas)

    dias, info = f11.dias_research()
    por_arch = {}
    for d in dias:
        por_arch.setdefault(d["archivo"], []).append(d["fecha"])
    plan = [(x, sorted(f)) for x, f in sorted(por_arch.items())]
    if a.smoke_archivo:
        plan = [(x, f) for x, f in plan if x == a.smoke_archivo]
        if not plan:
            print("archivo de smoke no encontrado en el plan: %s" % a.smoke_archivo)
            return 4
    peor = max(f for _x, fs in plan for f in fs)
    assert peor <= f11.MAX_FECHA, "FIREWALL: %s > %s" % (peor, f11.MAX_FECHA)
    ns_sesiones = sum(len(fs) for _x, fs in plan)

    print("F2.5 CURVA DE SOPORTE COMUN Y BALANCE -- descriptiva, target-free")
    print("  universo %d sesiones | ventanas=%r | k=%r | caliper=%r"
          % (ns_sesiones, ventanas, K_GRID, CALIPER_GRID))
    print("  multiverse_manifest_sha256=%s" % multiverse_manifest_sha256())

    total = crudo_vacio()
    estratos_por_archivo = {}
    por_contrato = {}
    for arch, fechas in plan:
        print("\n== %s : %d sesiones" % (arch, len(fechas)), flush=True)
        ini = (f11.pd.Timestamp(fechas[0] + " 00:00:00", tz="America/Chicago")
               - f11.pd.Timedelta(days=f11.LEAD_DAYS))
        fin_contrato = (f11.pd.Timestamp(fechas[-1] + " 00:00:00", tz="America/Chicago")
                        + f11.pd.Timedelta(days=1))
        fin = min(fin_contrato.tz_convert("UTC"), f11.corte_del_sello())
        tk = f11.ticks_mod.load_canonical_parquet(
            str(f11.data_root() / "nt8" / "6E" / arch),
            start_utc_ns=int(ini.value), end_utc_ns=int(fin.value))
        if not bool((np.diff(np.asarray(tk.sequence)) > 0).all()):
            por_contrato[arch] = dict(estado="ABSTAIN", motivo="`sequence` no es orden total")
            continue

        b = f11.bars_mod.build_time_bars(tk, 1)
        n_bars = len(b)
        bar_end = np.asarray(b.end_ns)
        close_t = np.asarray(b.close_t)
        bar_volume = np.asarray(b.volume, dtype=np.float64)
        fp = f11.bars_mod.build_footprints(tk, b) if f11.INDICADOR in f11.BAR_DRIVEN else None
        mod = f11.REGISTRY[f11.INDICADOR]
        r = (mod.run(tk, b, fp, chart_tz=f11.TZ_CHART) if fp is not None
             else mod.run(tk, b, chart_tz=f11.TZ_CHART))

        ses_de_barra, rango_sesion = f11.sesiones_de_barras(bar_end, fechas)
        res = procesar_archivo_curva(
            r.get("zones") or [], close_t, bar_volume, ses_de_barra, rango_sesion,
            fechas, tk.tick_size, n_bars, ventanas=ventanas)
        fusionar_crudos(total, res["crudo"])
        estratos_por_archivo[arch] = res["estratos_pre_matching"]
        por_contrato[arch] = dict(estado="OK", sesiones=len(fechas),
                                  n_zonas=res["n_zonas_universo"])
        print("   zonas=%d" % res["n_zonas_universo"])

    sd_ref_s60, diag_s60 = sd_pooled_within(estratos_por_archivo, "s60")
    sd_ref_lv, diag_lv = sd_pooled_within(estratos_por_archivo, "lv")
    soporte = resumir_soporte(total["soporte"])
    celdas = resumir_celdas(total["celdas"], sd_ref_s60, sd_ref_lv)

    print("\n" + "=" * 78)
    print("SOPORTE COMUN POR VENTANA (observado contra el esperado por azar)")
    for etiqueta, fila in soporte.items():
        print("  ventana %s: n=%s pool_medio=%s"
              % (etiqueta, fila["n_zonas"], fila["tamano_pool_medio"]))
        for c in COVARIABLES:
            dc = fila["por_covariable"][c]
            print("    %-22s above=%s (esperado %s, exceso %sx) below=%s pct_p50=%s"
                  % (c, dc["frac_above_max"], dc["frac_above_max_esperada_por_azar"],
                     dc["exceso_sobre_azar"], dc["frac_below_min"], dc["pct_p50"]))

    print("\nCURVA DE BALANCE -- %d celdas, sd_ref CONGELADO (s60=%s, lv=%s)"
          % (len(celdas), sd_ref_s60, sd_ref_lv))
    print("  %-26s %8s %8s %9s %9s %6s"
          % ("celda", "cobert", "ratio", "smd_s60", "smd_lv", "pasa"))
    for fila in celdas:
        print("  %-26s %8s %8s %9s %9s %6s"
              % (fila["celda"], fila["cobertura"], fila["ratio_seleccion"],
                 fila["smd_log1p_sigma60_ticks"], fila["smd_log1p_bar_volume"],
                 fila["celda_pasa_gates"]))

    head_end = f11.git_head()
    dirty_end = f11.git_dirty()
    if dirty_start or dirty_end or head_start != head_end:
        print("\nABSTAIN_PROVENANCE: arbol sucio o HEAD se movio durante la corrida "
              "(dirty_start=%r dirty_end=%r head_start=%s head_end=%s)"
              % (dirty_start, dirty_end, head_start, head_end))
        return 5

    payload = dict(
        schema_version=SCHEMA_VERSION, fase="F2.5_curva_soporte_balance",
        status="SMOKE" if a.smoke_archivo else "FULL_RUN",
        spec_path=str(SPEC_PATH.relative_to(REPO_PATH)), spec_sha256=spec_sha256(),
        multiverse_manifest_sha256=multiverse_manifest_sha256(),
        rejilla=rejilla_declarada(), ventanas_corridas=[
            _ETIQUETA_VENTANA_TODO if w is None else w for w in ventanas],
        north_star_body_sha256=ns_hash,
        head_start=head_start, head_end=head_end,
        dirty_start=dirty_start, dirty_end=dirty_end,
        sd_ref_congelado=dict(log1p_sigma60_ticks=sd_ref_s60, log1p_bar_volume=sd_ref_lv,
                              definicion="pooled_within_stratum(archivo x minuto_de_sesion), ventana 0",
                              diagnostico=dict(log1p_sigma60_ticks=diag_s60,
                                               log1p_bar_volume=diag_lv)),
        max_abs_smd=f11.MAX_ABS_SMD, min_zone_coverage=f11.MIN_ZONE_COVERAGE,
        soporte_por_ventana=soporte, curva_de_balance=celdas,
        session_count=ns_sesiones, max_fecha_universo=peor,
        firewall_max_fecha=f11.MAX_FECHA, universe_filter_report=info,
        outcomes_accessed=False, holdout_opened=False, estimand_suppressed=True,
        por_contrato=por_contrato, code_commit=head_end,
        measurement_code_sha256=f11.huella_del_codigo([f11.INDICADOR]),
        entorno=dict(python=sys.version.split()[0], plataforma=platform.platform()))
    payload["payload_sha256"] = hashlib.sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

    salida = Path(a.out) if a.out else (
        Path(__file__).resolve().parent
        / ("F2.5_curva_soporte_balance__%s.json" % payload["payload_sha256"][:12]))
    salida.write_text(json.dumps(payload, indent=1, ensure_ascii=False, default=str) + "\n",
                      encoding="utf-8")
    print("\n-> %s" % salida)
    return 0


if __name__ == "__main__":
    sys.exit(main())
