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

SCHEMA_VERSION = "memoria_nivel_nulo_correcto_v1"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
CONTRATO = "ES 03-26"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
N_NULO = 400
SEMILLA = 20260820


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

    claves = sorted(zs)
    if a.max_sesiones:
        claves = claves[:a.max_sesiones]
    print("memoria de nivel  -  %s\n  %d sesiones" % (SCHEMA_VERSION, len(claves)))

    ses, redondos = [], []
    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(PARQUET, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            continue
        pxt, tsz = tk.price_ticks.astype(np.int64), tk.tick_size

        # --- 1. los ticks de ES, se apilan en niveles redondos? ------------------
        # 1 punto = 4 ticks. Si no hubiera preferencia, cada resto 0..3 seria 0,25.
        r = np.bincount(np.mod(pxt, 4), minlength=4).astype(np.float64)
        redondos.append(r / r.sum())

        zl = zs[td]
        anchos = np.array([int(round((u - l) / tsz)) for _, u, l in zl], dtype=np.int64)
        lows = np.array([int(round(l / tsz)) for _, _, l in zl], dtype=np.int64)
        ok = anchos > 0
        anchos, lows = anchos[ok], lows[ok]
        if len(anchos) < 10:
            # Sesiones excluidas por tener < 10 zonas con ancho > 0:
            # 20260216 (8 brutas -> <10 tras h0), 20260317 (9 -> <10),
            # 20260319 (4 -> <10). Total: 62 -> 59.
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
                            p_max=round(float((1 + np.sum(viejo[:, 0] >= obs[0])) / (N_NULO + 1)), 4)),
            nulo_corregido=dict(max=round(float(np.median(nuevo[:, 0])), 2),
                                p_max=round(float((1 + np.sum(nuevo[:, 0] >= obs[0])) / (N_NULO + 1)), 4),
                                p_3omas=round(float((1 + np.sum(nuevo[:, 2] >= obs[2])) / (N_NULO + 1)), 4))))
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

    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version=SCHEMA_VERSION, outcomes_accessed=False, pnl_accessed=False,
        holdout_included=False, n_sesiones=len(ses), n_nulo=N_NULO, semilla=SEMILLA,
        agrupamiento_en_numeros_redondos=dict(
            nota=("fraccion de ticks por resto modulo 4 (1 punto = 4 ticks). Sin "
                  "preferencia, cada resto daria 0,25. Medido sobre el dato, no citado"),
            resto_0_punto_entero=round(float(R[:, 0].mean()), 4),
            resto_1=round(float(R[:, 1].mean()), 4),
            resto_2_medio_punto=round(float(R[:, 2].mean()), 4),
            resto_3=round(float(R[:, 3].mean()), 4),
            exceso_sobre_uniforme_pp=round(float((R[:, 0].mean() - 0.25) * 100), 2)),
        nulo_viejo=dict(
            descripcion="precio de tick suelto: MAL ESPECIFICADO, le falta el +ancho/2",
            p_mediana=round(float(np.median(pv)), 4),
            frac_sesiones_p_menor_005=round(float(np.mean(pv < 0.05)), 4)),
        nulo_corregido=dict(
            descripcion=("mid construido igual que el real: precio operado al azar mas "
                         "el MISMO ancho de la zona"),
            p_mediana=round(float(np.median(pn)), 4),
            frac_sesiones_p_menor_005=round(float(np.mean(pn < 0.05)), 4)),
        efecto_de_diseno=dict(
            formula="DEFF = 1 + (m-1)*rho ; N_efectivo = N / DEFF",
            zonas_por_sesion_media=round(m_bar, 1),
            nota=("rho hay que estimarlo por metrica; aca se publica m para que "
                  "cualquier intervalo futuro lo aplique. Con m=%.0f, un rho tan chico "
                  "como 0,05 ya da DEFF=%.1f" % (m_bar, 1 + (m_bar - 1) * 0.05))),
        procedencia=dict(head_commit=subprocess.check_output(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
            archivos_sucios=sorted(sucios)),
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
    print("\n  3. EFECTO DE DISENO: m = %.0f zonas/sesion  ->  con rho=0,05 DEFF=%.1f, "
          "N_ef = N/%.1f" % (m_bar, 1 + (m_bar - 1) * 0.05, 1 + (m_bar - 1) * 0.05))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
