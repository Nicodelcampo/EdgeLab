"""Memoria de nivel: ¿sobrevive a un nulo bien especificado? Y ¿cuánto vale el N real?

POR QUE ESTE ARCHIVO EXISTE
===========================
El censo de contextos encontro lo unico positivo de toda la familia: las zonas se apilan
en niveles de precio mas de lo que el tiempo-en-precio explica (8 zonas sobre un nivel
contra 4 del nulo, p < 0,05 en el 71% de las sesiones).

La busqueda en la literatura levanto dos objeciones, y las dos son serias.

OBJECION 1 - AGRUPAMIENTO EN NUMEROS REDONDOS
El clustering de precios en niveles redondos esta documentado desde mediados del siglo XX
y es enorme: en derivados de indice de LIFFE, el 98% de los precios cotizados y operados
caen en ticks pares pese a un tick minimo de 0,5 puntos. Si el precio prefiere niveles
redondos, cualquier objeto derivado del precio se apila ahi sin que haya mecanismo.

OBJECION 2 - EL NULO COMPARA OBJETOS DISTINTOS
Y esta es una falla de especificacion mia. El estadistico observado usa el MID de la
zona, `(swL + swH) / 2`. El nulo muestreaba PRECIOS DE TICK SUELTOS. Un mid y un precio
operado no tienen la misma afinidad a los niveles redondos: el mid de una banda de ancho
impar cae en medio tick.

    real:  mid = swL + ancho/2,  con swL = precio operado
    nulo:  px[i]                 <- le falta el `+ ancho/2`

El nulo correcto construye el mid IGUAL que el real: precio operado al azar mas el mismo
ancho. Asi hereda a la vez el tiempo-en-precio Y la aritmetica del mid.

QUE MIDE ESTE SCRIPT
====================
1. Si los ticks de ES se apilan en niveles redondos, medido directo sobre el dato en vez
   de citar la literatura.
2. La memoria de nivel contra el nulo corregido (mismo ancho, mismo constructor de mid).
3. El EFECTO DE DISENO. Con Fano 7,78 y 81% de solape, las zonas no son observaciones
   independientes. DEFF = 1 + (m-1)*rho, y N_efectivo = N / DEFF. Todo intervalo publicado
   sobre esta familia que no clusterice esta mal por ese factor.

TARGET-FREE. Sin outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (session_bounds_utc_ns,  # noqa: E402
                                         trade_date_ymd)

SCHEMA_VERSION = "memoria_nivel_nulo_correcto_v2_atj15"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
CONTRATO = "ES 03-26"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
N_NULO = 400                 # B: remuestreos Monte Carlo del nulo
SEMILLA = 20260820
MIN_ZONAS_MEMORIA = 10       # regla de elegibilidad de la metrica de memoria
CANONICAL_OUT = REPO / "docs" / "research" / "memoria_nivel_nulo_correcto.json"


def p_montecarlo(nulo_vals, observado, b):
    """p Monte Carlo de North et al. 2002: (1 + #{nulo >= obs}) / (B + 1).

    Nunca devuelve 0: el minimo posible es 1/(B+1). La version `#{...}/B` publicaba
    p = 0,0 en 5 de 59 sesiones, que es artefacto del estimador y no certeza.
    """
    return float((1 + np.sum(np.asarray(nulo_vals) >= observado)) / (b + 1))


def p_minimo_posible(b):
    return 1.0 / (b + 1)


def clasificar_run(max_sesiones, out_path):
    """ATJ-15: una corrida truncada no puede hacerse pasar por completa.

    Devuelve (run_scope, publishable, error). Si esta truncada y apunta al output
    canonico, `error` explica por que no puede escribirse.
    """
    if not max_sesiones:
        return "full", True, None
    if pathlib.Path(out_path).resolve() == CANONICAL_OUT.resolve():
        return ("truncated_probe", False,
                "corrida truncada (--max-sesiones=%d) no puede sobrescribir el output "
                "canonico %s; usar --out distinto" % (max_sesiones, CANONICAL_OUT))
    return "truncated_probe", False, None


def make_run_id(head_commit, trade_dates, max_sesiones):
    """Identidad determinista de la corrida: sin reloj ni azar, dos corridas con la
    misma identidad producen el mismo run_id."""
    partes = [SCHEMA_VERSION, head_commit, CONTRATO, SNAPSHOT.name, str(N_NULO),
              str(SEMILLA), str(MIN_ZONAS_MEMORIA), str(max_sesiones),
              ",".join(str(t) for t in trade_dates)]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def concentracion(mids_medio_tick):
    """mids en MEDIOS TICKS enteros: un mid puede caer en medio tick."""
    _, c = np.unique(mids_medio_tick, return_counts=True)
    return float(c.max()), float(len(c)), float((c >= 3).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(REPO / "docs" / "research"
                                         / "memoria_nivel_nulo_correcto.json"))
    a = ap.parse_args()

    con = sqlite3.connect("file:%s?mode=ro" % SNAPSHOT.as_posix(), uri=True)
    zs = {}
    for f in con.execute(
            "SELECT start_ts, price_upper, price_lower FROM hft_zones "
            "WHERE instrument=? AND start_ts<? ORDER BY start_ts",
            (CONTRATO, CUTOFF_MS)):
        td = int(trade_date_ymd(np.array([f[0] * 1_000_000], dtype=np.int64))[0])
        zs.setdefault(td, []).append(f)
    con.close()

    universo = sorted(zs)                       # ANTES de --max-sesiones
    claves = universo[:a.max_sesiones] if a.max_sesiones else list(universo)

    run_scope, publishable, err = clasificar_run(a.max_sesiones, a.out)
    if err:
        sys.exit('ABORTA: ' + err)
    print("universo %d  ->  seleccionadas %d   (%s, publishable=%s)"
          % (len(universo), len(claves), run_scope, publishable))
    print("memoria de nivel  -  %s\n  %d sesiones" % (SCHEMA_VERSION, len(claves)))

    ses, redondos = [], []
    faltantes, excluidas = [], []
    trade_dates_redondeo = []
    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(PARQUET, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError as e:
            faltantes.append(dict(trade_date=td, etapa="load_canonical_parquet",
                                  motivo=str(e)[:160]))
            continue
        pxt, tsz = tk.price_ticks.astype(np.int64), tk.tick_size
        if len(pxt) == 0:
            faltantes.append(dict(trade_date=td, etapa="ventana_vacia",
                                  motivo="0 ticks en la ventana de sesion"))
            continue

        # --- 1. los ticks de ES, se apilan en niveles redondos? ------------------
        # 1 punto = 4 ticks. Si no hubiera preferencia, cada resto 0..3 seria 0,25.
        r = np.bincount(np.mod(pxt, 4), minlength=4).astype(np.float64)
        redondos.append(r / r.sum())
        trade_dates_redondeo.append(td)

        zl = zs[td]
        anchos = np.array([int(round((u - l) / tsz)) for _, u, l in zl], dtype=np.int64)
        lows = np.array([int(round(l / tsz)) for _, _, l in zl], dtype=np.int64)
        ok = anchos > 0
        anchos, lows = anchos[ok], lows[ok]
        if len(anchos) < MIN_ZONAS_MEMORIA:
            # ATJ-15: la lista de exclusion se COMPUTA y se serializa. Hardcodearla en
            # un comentario la deja obsoleta en silencio si cambia el dato.
            excluidas.append(dict(trade_date=td, n_brutas=len(zl),
                                  n_ancho_positivo=int(len(anchos)),
                                  umbral=MIN_ZONAS_MEMORIA,
                                  motivo="menos de %d zonas con ancho > 0 tras excluir "
                                         "altura 0" % MIN_ZONAS_MEMORIA))
            continue
        # mid en MEDIOS TICKS -> entero, sin perder el medio tick por redondeo
        mids = 2 * lows + anchos
        obs = concentracion(mids)

        rng = np.random.default_rng(SEMILLA + td)
        # nulo VIEJO: precio de tick suelto (mal especificado, se conserva para contraste)
        viejo = np.array([concentracion(2 * pxt[rng.integers(0, len(pxt), len(anchos))])
                          for _ in range(N_NULO)])
        # nulo CORREGIDO: mismo constructor de mid, mismo ancho, ancla en precio operado
        nuevo = np.array([
            concentracion(2 * pxt[rng.integers(0, len(pxt), len(anchos))] + anchos)
            for _ in range(N_NULO)])

        ses.append(dict(
            trade_date=td, n_zonas=int(len(anchos)),
            max_en_un_nivel=int(obs[0]), niveles=int(obs[1]),
            niveles_3_o_mas=int(obs[2]),
            nulo_viejo=dict(max=round(float(np.median(viejo[:, 0])), 2),
                            p_max=round(p_montecarlo(viejo[:, 0], obs[0], N_NULO), 4)),
            nulo_corregido=dict(
                max=round(float(np.median(nuevo[:, 0])), 2),
                p_max=round(p_montecarlo(nuevo[:, 0], obs[0], N_NULO), 4),
                p_3omas=round(p_montecarlo(nuevo[:, 2], obs[2], N_NULO), 4))))
        if (k + 1) % 15 == 0:
            print("    %d/%d" % (k + 1, len(claves)))

    R = np.array(redondos)
    pv = np.array([s["nulo_viejo"]["p_max"] for s in ses])
    pn = np.array([s["nulo_corregido"]["p_max"] for s in ses])

    # --- 3. efecto de diseno -------------------------------------------------
    n = np.array([s["n_zonas"] for s in ses], dtype=np.float64)
    # rho intra-sesion sobre el ancho: cuanto se parecen las zonas de una misma sesion
    todos, grupos = [], []
    for i, s in enumerate(ses):
        todos.append(s["max_en_un_nivel"])
        grupos.append(i)
    m_bar = float(n.mean())

    head_commit = subprocess.check_output(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    procesadas = [s_["trade_date"] for s_ in ses]
    run_id = make_run_id(head_commit, claves, a.max_sesiones)

    # ATJ-15: cada metrica declara SU poblacion. price-rounding usa las sesiones
    # procesadas; memoria usa las elegibles. No son el mismo denominador y no pueden
    # compartir un unico `n_sesiones`.
    out = dict(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        run_scope=run_scope,
        publishable=publishable,
        max_sesiones_arg=a.max_sesiones,
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,

        # --- lineage de denominadores (ATJ-15) --------------------------------
        conteos=dict(
            n_universe_discovered=len(universo),
            n_selected=len(claves),
            n_available=len(claves) - len(faltantes),
            n_processed=len(redondos),
            n_eligible_rounding=len(redondos),
            n_eligible_memory=len(ses)),
        eligibility_rule=dict(
            rounding="toda sesion con >=1 tick cargado",
            memory=">=%d zonas con ancho > 0 tras excluir altura 0" % MIN_ZONAS_MEMORIA),
        missing_items=faltantes,
        excluded_items=excluidas,
        poblaciones=dict(
            P_PROCESSED=dict(id="P_PROCESSED", n=len(redondos),
                             trade_dates=trade_dates_redondeo),
            P_ELIGIBLE_MEMORY=dict(id="P_ELIGIBLE_MEMORY", n=len(ses),
                                   trade_dates=procesadas)),

        # --- metodo Monte Carlo ------------------------------------------------
        montecarlo=dict(B=N_NULO, seed=SEMILLA,
                        method="(1 + count(null >= observed)) / (B + 1)",
                        p_minimo_posible=round(p_minimo_posible(N_NULO), 7),
                        referencia="North, Curtis & Sham 2002"),

        # --- alias deprecado: sin consumidores en codigo, solo en docs ---------
        n_sesiones=len(ses),
        n_sesiones_DEPRECATED=("alias de conteos.n_eligible_memory. Ambiguo: no distingue "
                               "universo, seleccionadas, procesadas ni elegibles. No usar "
                               "en artefactos nuevos."),
        n_nulo=N_NULO, semilla=SEMILLA,

        agrupamiento_en_numeros_redondos=dict(
            population_id="P_PROCESSED",
            numerator="ticks con resto r modulo 4",
            denominator="todos los ticks de las %d sesiones procesadas" % len(redondos),
            nota=("fraccion de ticks por resto modulo 4 (1 punto = 4 ticks). Sin "
                  "preferencia, cada resto daria 0,25. Medido sobre el dato, no citado"),
            resto_0_punto_entero=round(float(R[:, 0].mean()), 4),
            resto_1=round(float(R[:, 1].mean()), 4),
            resto_2_medio_punto=round(float(R[:, 2].mean()), 4),
            resto_3=round(float(R[:, 3].mean()), 4),
            exceso_sobre_uniforme_pp=round(float((R[:, 0].mean() - 0.25) * 100), 2)),
        nulo_viejo=dict(
            estado="NON_INTERPRETABLE_LEGACY_DIAGNOSTIC",
            descripcion=("precio de tick suelto: MAL ESPECIFICADO, le falta el +ancho/2. "
                         "Se conserva solo como contraste del efecto de la correccion; "
                         "NO se interpreta como resultado"),
            population_id="P_ELIGIBLE_MEMORY",
            numerator="sesiones con p_max < 0,05", denominator="sesiones elegibles",
            p_mediana=round(float(np.median(pv)), 4),
            frac_sesiones_p_menor_005=round(float(np.mean(pv < 0.05)), 4)),
        nulo_corregido=dict(
            descripcion=("mid construido igual que el real: precio operado al azar mas "
                         "el MISMO ancho de la zona"),
            population_id="P_ELIGIBLE_MEMORY",
            numerator="sesiones con p_max < 0,05", denominator="sesiones elegibles",
            p_mediana=round(float(np.median(pn)), 4),
            frac_sesiones_p_menor_005=round(float(np.mean(pn < 0.05)), 4)),
        efecto_de_diseno=dict(
            formula="DEFF = 1 + (m-1)*rho ; N_efectivo = N / DEFF",
            population_id="P_ELIGIBLE_MEMORY",
            zonas_por_sesion_media=round(m_bar, 1),
            estado="INFERRED_NOT_VERIFIED",
            nota=("rho NO fue estimado. Se publica m para que cualquier intervalo futuro "
                  "lo aplique. Con m=%.0f, un rho tan chico como 0,05 ya da DEFF=%.1f. "
                  "No usar N/DEFF como N efectivo medido."
                  % (m_bar, 1 + (m_bar - 1) * 0.05))),
        procedencia=dict(head_commit=head_commit,
                         arbol_limpio=not bool(sucios),
                         archivos_sucios=sorted(sucios),
                         snapshot=str(SNAPSHOT), contrato=CONTRATO,
                         comando=" ".join(sys.argv)),
        sesiones=ses)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("\n  1. TICKS DE ES POR RESTO MODULO 4 (1 punto = 4 ticks)")
    print("     punto entero %.4f   +0,25 %.4f   medio punto %.4f   +0,75 %.4f"
          % (R[:, 0].mean(), R[:, 1].mean(), R[:, 2].mean(), R[:, 3].mean()))
    print("     (sin preferencia seria 0,2500 cada uno)")
    print("\n  2. MEMORIA DE NIVEL")
    print("     nulo VIEJO      p mediana %.4f   p<0,05 en %.0f%% de las sesiones"
          % (np.median(pv), 100 * np.mean(pv < 0.05)))
    print("     nulo CORREGIDO  p mediana %.4f   p<0,05 en %.0f%% de las sesiones"
          % (np.median(pn), 100 * np.mean(pn < 0.05)))
    print("  CONTEOS  universo %d -> seleccionadas %d -> disponibles %d -> "
          "procesadas %d -> elegibles memoria %d"
          % (out["conteos"]["n_universe_discovered"], out["conteos"]["n_selected"],
             out["conteos"]["n_available"], out["conteos"]["n_processed"],
             out["conteos"]["n_eligible_memory"]))
    print("  faltantes %d   excluidas %d   run_id %s   scope %s"
          % (len(faltantes), len(excluidas), run_id, run_scope))
    print("\n  3. EFECTO DE DISENO: m = %.0f zonas/sesion  ->  con rho=0,05 DEFF=%.1f, "
          "N_ef = N/%.1f" % (m_bar, 1 + (m_bar - 1) * 0.05, 1 + (m_bar - 1) * 0.05))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
