#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAZÓN DE VARIANZAS (Lo–MacKinlay 1988) — ¿hay algo que ganarle a la tabla nula?

## Qué pregunta contesta, y qué NO

**Contesta**: ¿el precio se desvía de un paseo aleatorio a los horizontes de la
grilla? Si no lo hace, **ninguna geometría de barreras puede ganarle al atlas
nulo** — eso es aritmética, no falta de ingenio.

**No contesta**: si existe un edge. Un VR distinto de 1 es condición
**necesaria, no suficiente**: la estructura puede vivir enteramente dentro del
spread y no pagarse nunca.

## Por qué esto y no una búsqueda

Es un test **pre-especificado sin parámetros libres**: los horizontes son los
mismos que ya están congelados en la config del atlas. No elige dirección, ni
umbral, ni candidato, ni indicador. No gasta presupuesto de hipótesis, y por eso
no cae bajo la regla STOP — es descriptivo del proceso, igual que el atlas nulo.

Probar los 5 indicadores contra la tabla "a ver qué pega" sería lo contrario:
42 combinaciones (H × P/N) por indicador, 210 hipótesis, ~10 falsos positivos
esperados a p<0,05 por puro azar. Eso es EXPLORE-001, con manifiesto y OK.

## Lectura

| VR | interpretación | qué favorecería |
|---|---|---|
| ≈ 1 | martingala: sin estructura lineal | nada; la tabla nula es el techo |
| > 1 | tendencia, los movimientos se continúan | objetivo lejos, stop cerca (P13/N8) |
| < 1 | reversión | lo contrario |

## Decisiones metodológicas, declaradas

1. **Unidad: ticks enteros**, no log-retornos. El problema de barreras vive en
   ticks y así no hay transformación que introduzca sesgo.
2. **Estadístico robusto a heterocedasticidad** (`z*`, el M2 del paper). Los
   mercados tienen agrupamiento de volatilidad; la versión homocedástica
   rechazaría la nula por eso solo, sin que haya nada predecible.
3. **Nunca se forma un retorno cruzando un hueco.** Cada día se parte en tramos
   de minutos consecutivos; el hueco de mantenimiento y las fronteras de día
   cortan. Un retorno que cruza 60 min de mercado cerrado no es un retorno.
4. **Inferencia por bootstrap de bloques de día**, igual que el atlas — no por
   el asintótico solo. Se reportan los dos: si discrepan, el asintótico miente.
5. **Mismo universo que el atlas**: pre-holdout, `COMPLETO` + `CIERRE_SEMANAL`.

## Auto-verificación

Corre el mismo estimador sobre un **paseo aleatorio sintético** con la misma
estructura de días y huecos. Si ahí no da VR≈1, el problema es el código y no el
mercado, y el resultado sobre datos reales no significa nada. Sin este control,
un VR≠1 sería indistinguible de un bug.

Uso:  .venv/Scripts/python tools/razon_de_varianzas.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

CT = ZoneInfo("America/Chicago")

# ---------------------------------------------------------------------------
# CONFIG CONGELADA. Los horizontes son los del atlas: no se eligen acá.
CFG = dict(
    horizontes_min=[10, 15, 20, 30, 45, 60, 90],
    base_min=1,                      # intervalo base del muestreo
    # Un minuto sin operaciones NO es un hueco: es un minuto sin cambio de
    # precio, y la serie de ultimo precio esta definida igual. Cortar ahi
    # partia los 191 dias en 4.041 tramos de ~60 min, con lo cual para q=90
    # casi ningun tramo alcanzaba el horizonte y el estimador se sesgaba: el
    # control sintetico daba 1.0465 en vez de 1. Solo cortan los huecos
    # ESTRUCTURALES (mantenimiento, frontera de dia).
    hueco_corte_min=5,
    holdout_desde="2026-07-01",
    tipos_de_dia=["COMPLETO", "CIERRE_SEMANAL"],
    bootstrap_reps=400,
    seed=20260727,
)
CFG_HASH = hashlib.sha256(json.dumps(CFG, sort_keys=True).encode()).hexdigest()[:16]


def _log(m):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), m), flush=True)


# ---------------------------------------------------------------------------
def tramos_de_un_dia(minutos, precios):
    """Parte el día en tramos de minutos CONSECUTIVOS.

    Un retorno que cruza el hueco de mantenimiento no es un retorno: son 60 min
    de mercado cerrado. Sin este corte, cada día aportaría un salto espurio que
    infla la varianza a horizontes largos y simula tendencia donde no la hay.
    """
    if len(minutos) < 2:
        return []
    # 1) rejilla completa de minutos, con el ultimo precio arrastrado. Un minuto
    #    sin operaciones es un minuto sin cambio, no un agujero.
    # 2) se corta SOLO donde hubo un hueco estructural en el dato original.
    salida, ini = [], 0
    bordes = list(np.flatnonzero(np.diff(minutos) > CFG["hueco_corte_min"]) + 1) + [len(minutos)]
    for fin in bordes:
        m, p = minutos[ini:fin], precios[ini:fin]
        ini = fin
        if len(m) < 2:
            continue
        rej = np.arange(m[0], m[-1] + 1)
        idx = np.searchsorted(m, rej, side="right") - 1
        salida.append(p[idx])
    return [s for s in salida if len(s) > 1]


def componentes_vr(tramos, q):
    """Sumas de Lo–MacKinlay acumuladas sobre tramos, sin cruzarlos.

    Se devuelven los COMPONENTES (no el cociente) para poder agregarlos entre
    días y entre réplicas de bootstrap: el estimador agrupado es el cociente de
    las sumas, no el promedio de los cocientes.
    """
    s_a = n_a = s_c = n_c = 0.0
    r_all = []
    for p in tramos:
        r = np.diff(p.astype(np.float64))
        if len(r) < 1:
            continue
        r_all.append(r)
        s_a += float((r ** 2).sum()); n_a += len(r)
        if len(p) > q:
            d = p[q:].astype(np.float64) - p[:-q].astype(np.float64)
            s_c += float((d ** 2).sum()); n_c += len(d)
    return dict(s_a=s_a, n_a=n_a, s_c=s_c, n_c=n_c,
                r=np.concatenate(r_all) if r_all else np.empty(0))


def vr_de_componentes(c, q):
    """VR = varianza a q pasos / (q x varianza a 1 paso). Deriva ~0 en ticks."""
    if c["n_a"] < 2 or c["n_c"] < 2:
        return float("nan")
    var1 = c["s_a"] / c["n_a"]
    varq = c["s_c"] / c["n_c"]
    return float(varq / (q * var1)) if var1 > 0 else float("nan")


def z_robusto(r, q, vr):
    """z* de Lo–MacKinlay robusto a heterocedasticidad (el M2 del paper).

    La versión homocedástica rechaza la nula por el agrupamiento de volatilidad
    solo, sin que haya nada predecible. Usarla acá daría un falso positivo
    garantizado sobre cualquier serie financiera.
    """
    n = len(r)
    if n < 4 * q or not np.isfinite(vr):
        return float("nan")
    u = r - r.mean()
    u2 = u ** 2
    den = float(u2.sum()) ** 2
    if den <= 0:
        return float("nan")
    # delta_j ya viene normalizado a O(1/n) por la definicion del paper: el
    # numerador es O(n) y el denominador O(n^2). Multiplicarlo por n de nuevo
    # -- como estaba -- hacia theta O(1) y el z* salia ~0.004 para todo, que se
    # imprimia como 0.00 y parecia "sin evidencia" cuando era un bug de escala.
    theta = 0.0
    for j in range(1, q):
        num = float((u2[j:] * u2[:-j]).sum())
        theta += ((2.0 * (q - j) / q) ** 2) * (num / den)
    return float((vr - 1.0) / np.sqrt(theta)) if theta > 0 else float("nan")


# ---------------------------------------------------------------------------
def serie_por_dia(con, archivo, fecha, data_dir):
    """Último precio en TICKS por minuto CT del día."""
    p = os.path.join(data_dir, archivo).replace("\\", "/")
    df = con.execute(
        "select cast(epoch(make_timestamp(cast(ts_utc_ns/1000 as bigint))) / 60 "
        "as bigint) m, last(price_ticks order by ts_utc_ns) px "
        "from read_parquet('%s') "
        "where cast(make_timestamp(cast(ts_utc_ns/1000 as bigint)) - interval 5 hour "
        "as date) = date '%s' group by 1 order by 1" % (p, fecha)).df()
    if not len(df):
        return None
    return df.m.values.astype(np.int64), df.px.values.astype(np.int64)


def sintetico(dias_reales, rng):
    """Paseo aleatorio con la MISMA estructura de días, tramos y longitudes.

    Control negativo: si el estimador no da VR~1 acá, el problema es el codigo.
    Los incrementos son +-1 tick equiprobables, o sea una martingala exacta.
    """
    out = {}
    for k, tramos in dias_reales.items():
        out[k] = [np.cumsum(rng.choice([-1, 1], size=len(t))).astype(np.int64)
                  for t in tramos]
    return out


def correr(dias, etiqueta):
    res = {}
    for q in CFG["horizontes_min"]:
        comp = [componentes_vr(t, q) for t in dias.values()]
        agg = dict(s_a=sum(c["s_a"] for c in comp), n_a=sum(c["n_a"] for c in comp),
                   s_c=sum(c["s_c"] for c in comp), n_c=sum(c["n_c"] for c in comp))
        vr = vr_de_componentes(agg, q)
        r = np.concatenate([c["r"] for c in comp if len(c["r"])])
        res["q%d" % q] = dict(vr=vr, z_robusto=z_robusto(r, q, vr),
                              n_ret=int(agg["n_a"]), n_solapadas=int(agg["n_c"]))
    return res


def bootstrap_vr(dias, q, reps=None):
    """IC del VR remuestreando DÍAS, igual que el atlas."""
    reps = reps or CFG["bootstrap_reps"]
    claves = list(dias)
    if len(claves) < 3:
        return None
    comp = {k: componentes_vr(dias[k], q) for k in claves}
    SA = np.array([comp[k]["s_a"] for k in claves]); NA = np.array([comp[k]["n_a"] for k in claves])
    SC = np.array([comp[k]["s_c"] for k in claves]); NC = np.array([comp[k]["n_c"] for k in claves])
    r = np.random.default_rng(CFG["seed"])
    vals = []
    for _ in range(reps):
        i = r.choice(len(claves), size=len(claves), replace=True)
        na, nc = NA[i].sum(), NC[i].sum()
        if na > 1 and nc > 1:
            v1 = SA[i].sum() / na
            if v1 > 0:
                vals.append(float((SC[i].sum() / nc) / (q * v1)))
    if not vals:
        return None
    return dict(media=float(np.mean(vals)),
                ic90=[float(np.percentile(vals, 5)), float(np.percentile(vals, 95))])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifiesto", default=os.path.join(REPO, "runs", "censo",
                                                         "manifiesto_universo.json"))
    ap.add_argument("--data", default=os.path.join(REPO, "data", "nt8", "6E"))
    ap.add_argument("--out", default=os.path.join(REPO, "runs", "vr"))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)

    import duckdb
    con = duckdb.connect(); con.execute("set enable_progress_bar=false")

    # PUERTA UNICA — ver edgelab/research/universo_estudio.py
    from edgelab.research.universo_estudio import cargar_dias_de_estudio
    dd, info = cargar_dias_de_estudio(a.manifiesto,
                                      tipos_de_dia=CFG["tipos_de_dia"],
                                      caller="razon_de_varianzas")
    _log("RAZON DE VARIANZAS — %d dias efectivos (holdout descartado: %d), cfg=%s"
         % (len(dd), info["descartados_holdout"], CFG_HASH))
    _log("  DESCRIPTIVO. Condicion NECESARIA para que exista un edge, no suficiente.")

    dias = {}
    for d in dd:
        s = serie_por_dia(con, d["archivo"], d["fecha"], a.data)
        if s is None:
            continue
        t = tramos_de_un_dia(*s)
        if t:
            dias["%s|%s" % (d["archivo"], d["fecha"])] = t
    _log("  series armadas: %d dias, %d tramos, %d minutos"
         % (len(dias), sum(len(v) for v in dias.values()),
            sum(len(x) for v in dias.values() for x in v)))

    _log("  control negativo (paseo aleatorio sintetico)...")
    sint = correr(sintetico(dias, np.random.default_rng(CFG["seed"])), "sintetico")
    _log("  datos reales...")
    real = correr(dias, "real")
    boot = {("q%d" % q): bootstrap_vr(dias, q) for q in CFG["horizontes_min"]}

    out = dict(etiqueta=("DESCRIPTIVO — condicion NECESARIA, no suficiente. "
                         "No es un edge ni una estrategia."),
               config=CFG, config_hash=CFG_HASH, n_dias=len(dias),
               control_sintetico=sint, real=real, bootstrap=boot,
               generado_utc=datetime.now(timezone.utc).isoformat())
    json.dump(out, open(os.path.join(a.out, "vr.json"), "w", encoding="utf-8"),
              indent=1, ensure_ascii=False)

    print()
    print("%-6s %10s %10s %22s %12s" % ("q(min)", "VR_real", "z*_robusto", "IC90 bootstrap", "VR_sintetico"))
    for q in CFG["horizontes_min"]:
        k = "q%d" % q
        r, b, s = real[k], boot[k], sint[k]
        ic = ("[%.4f , %.4f]" % tuple(b["ic90"])) if b else "-"
        print("%-6d %10.4f %10.2f %22s %12.4f" % (q, r["vr"], r["z_robusto"], ic, s["vr"]))
    print()
    print("VR=1 martingala · VR>1 tendencia · VR<1 reversion")
    print("El control sintetico DEBE dar ~1: si no, el estimador esta mal y el resto no vale.")
    _log("salida: %s" % os.path.join(a.out, "vr.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
