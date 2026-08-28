"""H-ES-CTX-2 — costo de cruce CONDICIONADO a los contextos congelados.

Pre-registro: docs/research/H-ES-CTX-2_PREREGISTRO.md  (congelado ANTES de esta corrida)
Inferencia:   docs/research/R3_INFERENCIA_CLUSTERIZADA_PROTOCOLO.md

CONTEXTOS, YA ELEGIDOS Y CONGELADOS
===================================
C-A PRIMARIO   `pct_rv` en terciles: percentil EXPANSIVO de la volatilidad realizada de
               los 5 min previos, contra el historial acumulado del mismo bucket de 15
               min. bajo < 0,33 <= medio < 0,67 <= alto.
C-B SECUNDARIO `es_primera_5s`: no hubo zona en los 5 s anteriores.

Se eligieron sobre el atlas F1 (target-free) y la literatura, con el filtro dominante que
R2 impuso: baja correlacion con el ANCHO, que es la variable que sesga el emparejamiento.
La fase de sesion quedo RECHAZADA por corr -0,255 con el ancho.

QUE NO SE TOCA
==============
El estimando, el emparejamiento, B, la semilla, el margen y la multiplicidad ya estaban
congelados. Este script los APLICA dentro de cada celda; no elige nada.

El MDE por celda sale del MISMO bootstrap y se publica junto al punto. No se deriva
analiticamente: la version IQR/1,349 del pre-registro anterior asumia normalidad sobre
una distribucion sesgada.

Sin outcomes direccionales, sin P&L, sin holdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from diag.tasa_senales.atlas_hft_es import PercentilExpansivo  # noqa: E402
from diag.tasa_senales.r2_matchability_es import emparejar  # noqa: E402
from diag.tasa_senales.r3_inferencia_cruce_es import (ALPHA_CI, B_BOOT,  # noqa: E402
                                                      MARGEN_REL, METRICA_PRIMARIA,
                                                      METRICAS_SECUNDARIAS,
                                                      MIN_TICKS_POST, SEED,
                                                      boot_cluster, tost)
from diag.tasa_senales.velocidad_cruce_es import medir_cruce  # noqa: E402
from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import run_con_casi  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (session_bounds_utc_ns,  # noqa: E402
                                         trade_date_ymd)

SCHEMA_VERSION = "h_es_ctx2_condicionado_v1"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
CONTRATO = "ES 03-26"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
CANONICAL_OUT = REPO / "docs" / "research" / "h_es_ctx2_condicionado.json"
NY = ZoneInfo("America/New_York")

# --- CONGELADOS EN EL PRE-REGISTRO -------------------------------------------
TERCILES = ((0.0, 1 / 3, "bajo"), (1 / 3, 2 / 3, "medio"), (2 / 3, 1.01, "alto"))
HUECO_EPISODIO_MS = 5_000
BUCKET_MIN = 15
VENTANA_PREV_MS = 5 * 60 * 1000
# MDE(80%, alpha=0,05) = (z_{1-a/2} + z_{0,8}) * SE, con SE del propio bootstrap.
FACTOR_MDE = 1.959964 + 0.841621


def make_run_id(head, claves):
    partes = [SCHEMA_VERSION, head, CONTRATO, str(B_BOOT), str(SEED),
              str(HUECO_EPISODIO_MS), ",".join(str(t) for t in claves)]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def mde_desde_bootstrap(r):
    """MDE derivado del MISMO bootstrap, no de una formula analitica.

    SE se lee del ancho del IC del bootstrap; la unica hipotesis que queda es normalidad
    de la DISTRIBUCION MUESTRAL del estadistico -- mucho mas defendible que suponerla
    sobre los datos crudos, que estan sesgados.
    """
    if not r or "ci95" not in r:
        return None
    se = (r["ci95"][1] - r["ci95"][0]) / (2 * 1.959964)
    return round(FACTOR_MDE * se, 4)


def holm(pares):
    """Holm-Bonferroni. `pares` = [(nombre, p)]. Devuelve {nombre: p_ajustado}."""
    orden = sorted(pares, key=lambda kv: kv[1])
    m = len(orden)
    out, prev = {}, 0.0
    for i, (nombre, p) in enumerate(orden):
        aj = min(1.0, max(prev, (m - i) * p))
        out[nombre] = round(aj, 4)
        prev = aj
    return out


def p_bootstrap(pares_por_sesion, campo, b=B_BOOT, seed=SEED):
    """p bilateral del bootstrap: fraccion de replicas del lado opuesto al punto,
    con la correccion (1+c)/(B+1) para que nunca sea 0."""
    claves = list(pares_por_sesion)
    if not claves:
        return None
    todos = np.concatenate([pares_por_sesion[k][campo] for k in claves])
    punto = float(np.median(todos))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(claves), size=(b, len(claves)))
    reps = np.array([np.median(np.concatenate(
        [pares_por_sesion[claves[j]][campo] for j in idx[i]])) for i in range(b)])
    c = np.sum(reps <= 0) if punto > 0 else np.sum(reps >= 0)
    return round(min(1.0, 2.0 * (1 + c) / (b + 1)), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--parquet", default=str(PARQUET))
    a = ap.parse_args()
    if a.max_sesiones and pathlib.Path(a.out).resolve() == CANONICAL_OUT.resolve():
        sys.exit("ABORTA: corrida truncada no sobrescribe el canonico")

    snapshot, parquet = pathlib.Path(a.snapshot), pathlib.Path(a.parquet)
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    zs = {}
    for f in con.execute(
            "SELECT start_ts, end_ts, price_upper, price_lower FROM hft_zones "
            "WHERE instrument=? AND start_ts<? ORDER BY start_ts", (CONTRATO, CUTOFF_MS)):
        td = int(trade_date_ymd(np.array([f[0] * 1_000_000], dtype=np.int64))[0])
        zs.setdefault(td, []).append(f)
    con.close()

    universo = sorted(zs)
    claves = universo[:a.max_sesiones] if a.max_sesiones else list(universo)
    print("H-ES-CTX-2 condicionado  -  %s" % SCHEMA_VERSION)
    print("  universo %d -> seleccionadas %d" % (len(universo), len(claves)))

    CAMPOS = [METRICA_PRIMARIA] + METRICAS_SECUNDARIAS
    CELDAS = [t[2] for t in TERCILES] + ["primera_5s", "no_primera_5s", "TODAS"]
    pares = {c: {} for c in CELDAS}
    pct_rv = PercentilExpansivo()
    sin_pct = 0

    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(parquet, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError:
            continue
        ts, pxt, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        if len(ts) < 1000:
            continue
        dt = np.diff(ts, append=ts[-1])

        zl = []
        prev_ts = None
        for (st, en, pu, pl) in zs[td]:
            if pu is None or pl is None:
                continue
            hi, lo = int(round(pu / tsz)), int(round(pl / tsz))
            if hi - lo <= 0:
                continue
            j = int(np.searchsorted(ts, st * 1_000_000, side="left"))
            j0 = int(np.searchsorted(ts, st * 1_000_000
                                     - VENTANA_PREV_MS * 1_000_000))
            pr = pxt[j0:j]
            if len(pr) < 2:
                continue
            rv = float(np.sqrt((np.diff(pr.astype(np.float64)) ** 2).sum()))
            d = datetime.fromtimestamp(st / 1e3, tz=timezone.utc).astimezone(NY)
            b15 = int((d.hour + d.minute / 60.0) * 60 // BUCKET_MIN)
            p = pct_rv.pct(b15, rv)
            primera = (prev_ts is None) or (st - prev_ts >= HUECO_EPISODIO_MS)
            prev_ts = st
            zl.append(dict(start_ts=st, end_ts=en, lo=lo, hi=hi,
                           ancho_ticks=hi - lo, pct_rv=p, primera=primera))

        _z, casi = run_con_casi(ts, pxt * tsz, vol, tsz)
        pool = {}
        for c0 in casi:
            hi = int(round(c0["price_upper"] / tsz))
            lo = int(round(c0["price_lower"] / tsz))
            if hi - lo > 0:
                pool.setdefault(hi - lo, []).append(
                    dict(start_ts=c0["start_ts"], end_ts=c0["end_ts"], lo=lo, hi=hi,
                         ancho_ticks=hi - lo))

        cache_z, cache_c = {}, {}

        def cruce(ev, cache, key):
            if key in cache:
                return cache[key]
            j = int(np.searchsorted(ts, (ev["end_ts"] or ev["start_ts"]) * 1_000_000,
                                    side="right"))
            r = None
            if len(ts) - j >= MIN_TICKS_POST:
                r = medir_cruce(pxt[j:], ts[j:], vol[j:], dt[j:], ev["lo"], ev["hi"])
            cache[key] = r
            return r

        acum = {c: {campo: [] for campo in CAMPOS} for c in CELDAS}
        for i, r in emparejar(zl, pool).items():
            if not r:
                continue
            z = zl[i]
            c = pool[z["ancho_ticks"]][r[0]]
            mz, mc = cruce(z, cache_z, i), cruce(c, cache_c, (z["ancho_ticks"], r[0]))
            if not (mz and mc and mz.get("cruza") and mc.get("cruza")):
                continue
            dif = {campo: float(mz[campo]) - float(mc[campo]) for campo in CAMPOS}
            destinos = ["TODAS", "primera_5s" if z["primera"] else "no_primera_5s"]
            if z["pct_rv"] is None:
                sin_pct += 1
            else:
                destinos += [lab for lo_, hi_, lab in TERCILES
                             if lo_ <= z["pct_rv"] < hi_]
            for celda in destinos:
                for campo in CAMPOS:
                    acum[celda][campo].append(dif[campo])
        for celda in CELDAS:
            if acum[celda][METRICA_PRIMARIA]:
                pares[celda][td] = {campo: np.array(acum[celda][campo], dtype=np.float64)
                                    for campo in CAMPOS}
        if (k + 1) % 10 == 0:
            print("    %d/%d  pares %d" % (
                k + 1, len(claves),
                sum(len(v[METRICA_PRIMARIA]) for v in pares["TODAS"].values())))

    # --------------------------------------------------------------- inferencia
    try:
        h = json.loads((REPO / "docs" / "research" / "h_es_cruce_1.json")
                       .read_text(encoding="utf-8"))
        margen = MARGEN_REL * h["metricas"][METRICA_PRIMARIA]["control_mediana"]
    except Exception:
        margen = None

    res, ps = {}, []
    for celda in CELDAS:
        r = boot_cluster(pares[celda], METRICA_PRIMARIA, alpha=ALPHA_CI)
        if not r:
            res[celda] = {}
            continue
        p = p_bootstrap(pares[celda], METRICA_PRIMARIA)
        res[celda] = dict(
            **r, mde=mde_desde_bootstrap(r), p_bootstrap=p,
            equivalencia=(tost(r["ci90"], margen) if margen else None))
        if celda in [t[2] for t in TERCILES]:
            ps.append((celda, p))
    ajustados = holm(ps) if ps else {}
    for celda, aj in ajustados.items():
        res[celda]["p_holm"] = aj

    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                   text=True).strip()
    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version=SCHEMA_VERSION, run_id=make_run_id(head, claves),
        run_scope="full" if not a.max_sesiones else "truncated_probe",
        publishable=not bool(a.max_sesiones),
        preregistro="docs/research/H-ES-CTX-2_PREREGISTRO.md",
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        contextos=dict(
            C_A_primario="pct_rv en terciles (percentil expansivo, bucket 15 min)",
            C_B_secundario="es_primera_5s (sin zona en los 5 s previos)",
            rechazado="fase de sesion: corr -0,255 con el ancho"),
        parametros_congelados=dict(B=B_BOOT, seed=SEED, margen_relativo=MARGEN_REL,
                                   margen_absoluto=margen, terciles=[t[2] for t in TERCILES],
                                   hueco_episodio_ms=HUECO_EPISODIO_MS,
                                   metrica_primaria=METRICA_PRIMARIA,
                                   mde="derivado del MISMO bootstrap: (z.975+z.80)*SE",
                                   multiplicidad="Holm sobre los 3 terciles"),
        soporte=("comun: solo zonas con control emparejado. R2 midio 81,7%, sesgado a "
                 "angostas (ancho mediano 3,28 vs 7,76)"),
        pares_sin_percentil=sin_pct,
        resultado=res,
        procedencia=dict(head_commit=head, arbol_limpio=not bool(sucios),
                         archivos_sucios=sorted(sucios), snapshot=str(snapshot),
                         parquet=str(parquet), comando=" ".join(sys.argv)))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")

    print("\n  celda            n_pares  ses   punto      IC95              MDE     p_holm  equiv")
    for celda in CELDAS:
        r = res.get(celda) or {}
        if not r:
            print("  %-16s sin datos" % celda)
            continue
        eq = (r.get("equivalencia") or {}).get("equivalencia")
        print("  %-16s %7d %4d  %+7.3f  [%+7.3f,%+7.3f]  %7.3f  %6s  %s"
              % (celda, r["n_pares"], r["n_sesiones"], r["punto"],
                 r["ci95"][0], r["ci95"][1], r["mde"] or -1,
                 r.get("p_holm", "-"), eq))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
