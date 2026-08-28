"""R3 - CI clusterizado y equivalencia del costo de cruce. Protocolo congelado antes.

Protocolo: docs/research/R3_INFERENCIA_CLUSTERIZADA_PROTOCOLO.md
Insumos:   R1 sellado + R2 ejecutado (r2_matchability_es.json)

CIERRA EL PUNTO B5 DE LA AUDITORIA
==================================
H-ES-CRUCE-1 publico "delta pareada = 0" SIN intervalo de confianza. Sin CI no se
distingue un nulo real de falta de potencia, y sin margen de equivalencia declarado no se
puede afirmar equivalencia. R3 agrega las dos cosas, con la sesion como unidad de
remuestreo.

QUE NO CAMBIA
El estimando, el emparejamiento y las metricas son los que ya corrieron. R3 NO re-mide
nada nuevo: agrega inferencia sobre lo mismo, mas las cuatro sensibilidades que R2 dejo
obligatorias.

SOPORTE DECLARADO
R2 midio que el control solo existe para el 81,7% de las zonas, sesgado a las angostas
(ancho mediano 3,28 contra 7,76). El estimando es sobre ESE soporte y se rotula asi. No
se extiende a zonas anchas ni a Asia/Europa.

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

from diag.tasa_senales.r2_matchability_es import emparejar, fase_de  # noqa: E402
from diag.tasa_senales.velocidad_cruce_es import medir_cruce  # noqa: E402
from edgelab.bridge.kernels.hftzones_es_pure_v2_flat import run_con_casi  # noqa: E402
from edgelab.bridge.ticks import load_canonical_parquet  # noqa: E402
from edgelab.kaggle.sessions_cme import (session_bounds_utc_ns,  # noqa: E402
                                         trade_date_ymd)

SCHEMA_VERSION = "r3_inferencia_cruce_es_v1"
SNAPSHOT = REPO / "runs" / "oraculo_espurev2flat_ES_snapshot.sqlite"
PARQUET = REPO / "data" / "nt8" / "ES_parquet" / "ES_03-26_ticks.parquet"
CONTRATO = "ES 03-26"
CUTOFF_MS = session_bounds_utc_ns(20260701)[0] // 1_000_000
CANONICAL_OUT = REPO / "docs" / "research" / "r3_inferencia_cruce_es.json"
NY = ZoneInfo("America/New_York")

# --- CONGELADOS EN EL PROTOCOLO. No se tocan mirando resultados. --------------
B_BOOT = 10_000
SEED = 20260821
ALPHA_CI = 0.05                  # IC 95% para el primario
ALPHA_TOST = 0.10                # IC 90% para equivalencia (dos unilaterales al 5%)
MARGEN_REL = 0.05                # |delta| < 5% de la mediana del control
METRICA_PRIMARIA = "ticks_por_ancho"
METRICAS_SECUNDARIAS = ["ticks", "ms", "volumen", "vol_por_ancho"]
MIN_TICKS_POST = 200
MAX_SEP_MS = 30 * 60 * 1000
MAX_SEP_S4_MS = 5 * 60 * 1000


def make_run_id(head, claves, max_ses):
    partes = [SCHEMA_VERSION, head, CONTRATO, str(B_BOOT), str(SEED),
              str(MARGEN_REL), METRICA_PRIMARIA, str(max_ses),
              ",".join(str(t) for t in claves)]
    return hashlib.sha256("|".join(partes).encode("utf-8")).hexdigest()[:16]


def clasificar_run(max_ses, out_path):
    if not max_ses:
        return "full", True, None
    if pathlib.Path(out_path).resolve() == CANONICAL_OUT.resolve():
        return "truncated_probe", False, "truncada no sobrescribe %s" % CANONICAL_OUT
    return "truncated_probe", False, None


def boot_cluster(pares_por_sesion, campo, b=B_BOOT, seed=SEED, alpha=ALPHA_CI):
    """Bootstrap no parametrico de SESIONES completas.

    Cada replica sortea sesiones con reemplazo, AGRUPA todos sus pares y toma una sola
    mediana de las diferencias pareadas (zona-ponderada dentro de la replica, como
    congela el protocolo). Devuelve el punto, el IC y la distribucion resumida.
    """
    claves = list(pares_por_sesion)
    if not claves:
        return {}
    todos = np.concatenate([pares_por_sesion[k][campo] for k in claves])
    punto = float(np.median(todos))
    rng = np.random.default_rng(seed)
    reps = np.empty(b, dtype=np.float64)
    idx = rng.integers(0, len(claves), size=(b, len(claves)))
    for i in range(b):
        reps[i] = np.median(np.concatenate(
            [pares_por_sesion[claves[j]][campo] for j in idx[i]]))
    lo = float(np.percentile(reps, 100 * alpha / 2))
    hi = float(np.percentile(reps, 100 * (1 - alpha / 2)))
    lo90 = float(np.percentile(reps, 5.0))
    hi90 = float(np.percentile(reps, 95.0))
    # secundaria: mediana de medianas por sesion
    med_ses = float(np.median([np.median(pares_por_sesion[k][campo]) for k in claves]))
    return dict(
        n_pares=int(len(todos)), n_sesiones=len(claves),
        punto=round(punto, 4),
        ci95=[round(lo, 4), round(hi, 4)],
        ci90=[round(lo90, 4), round(hi90, 4)],
        cruza_cero=bool(lo <= 0 <= hi),
        punto_sesion_ponderada=round(med_ses, 4),
        mismo_signo_que_ponderada=bool(np.sign(punto) == np.sign(med_ses)
                                       or punto == 0 or med_ses == 0),
        B=b, seed=seed)


def tost(ci90, margen):
    dentro = (ci90[0] > -margen) and (ci90[1] < margen)
    return dict(margen=round(margen, 4), ci90=ci90, equivalencia=bool(dentro),
                nota=("equivalencia declarada solo si el IC 90% queda ENTERAMENTE dentro "
                      "de +-margen. El margen NO es economico: la metrica cuenta "
                      "operaciones por unidad de ancho, no dinero"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sesiones", type=int, default=0)
    ap.add_argument("--out", default=str(CANONICAL_OUT))
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--parquet", default=str(PARQUET))
    a = ap.parse_args()

    run_scope, publishable, err = clasificar_run(a.max_sesiones, a.out)
    if err:
        sys.exit("ABORTA: " + err)

    snapshot, parquet = pathlib.Path(a.snapshot), pathlib.Path(a.parquet)
    con = sqlite3.connect("file:%s?mode=ro" % snapshot.as_posix(), uri=True)
    zs = {}
    for f in con.execute(
            "SELECT id, start_ts, end_ts, bucket, dir, price_upper, price_lower "
            "FROM hft_zones WHERE instrument=? AND start_ts<? ORDER BY start_ts",
            (CONTRATO, CUTOFF_MS)):
        td = int(trade_date_ymd(np.array([f[1] * 1_000_000], dtype=np.int64))[0])
        zs.setdefault(td, []).append(f)
    con.close()

    universo = sorted(zs)
    claves = universo[:a.max_sesiones] if a.max_sesiones else list(universo)
    print("R3 inferencia  -  %s" % SCHEMA_VERSION)
    print("  universo %d -> seleccionadas %d  (%s)" % (len(universo), len(claves),
                                                       run_scope))

    CAMPOS = [METRICA_PRIMARIA] + METRICAS_SECUNDARIAS
    VARIANTES = ["base", "S1_inverso", "S1_permutado", "S2_solo_anterior",
                 "S3_con_reemplazo", "S4_sep_5min"]
    pares = {v: {} for v in VARIANTES}
    faltantes = []
    n_zonas_tot = 0

    for k, td in enumerate(claves):
        ini, fin = session_bounds_utc_ns(td)
        try:
            tk = load_canonical_parquet(parquet, start_utc_ns=ini, end_utc_ns=fin,
                                        instrument="ES")
        except ValueError as e:
            faltantes.append(dict(trade_date=td, motivo=str(e)[:100]))
            continue
        ts, pxt, vol, tsz = tk.ts_ns, tk.price_ticks, tk.volume, tk.tick_size
        if len(ts) == 0:
            faltantes.append(dict(trade_date=td, motivo="0 ticks"))
            continue
        dt = np.diff(ts, append=ts[-1])

        zl = []
        for (zid, st, en, bucket, dr, pu, pl) in zs[td]:
            if pu is None or pl is None:
                continue
            hi, lo = int(round(pu / tsz)), int(round(pl / tsz))
            if hi - lo <= 0:
                continue
            d = datetime.fromtimestamp(st / 1e3, tz=timezone.utc).astimezone(NY)
            zl.append(dict(start_ts=st, end_ts=en, lo=lo, hi=hi, ancho_ticks=hi - lo,
                           fase=fase_de(d.hour + d.minute / 60.0)))
        n_zonas_tot += len(zl)

        _z, casi = run_con_casi(ts, pxt * tsz, vol, tsz)
        cl = []
        for c0 in casi:
            hi = int(round(c0["price_upper"] / tsz))
            lo = int(round(c0["price_lower"] / tsz))
            if hi - lo > 0:
                cl.append(dict(start_ts=c0["start_ts"], end_ts=c0["end_ts"],
                               lo=lo, hi=hi, ancho_ticks=hi - lo))
        pool = {}
        for c in cl:
            pool.setdefault(c["ancho_ticks"], []).append(c)

        # --- memoizacion: el cruce de una banda no depende de con quien se empareje
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

        rng = np.random.default_rng(SEED + td)
        asign = {
            "base": emparejar(zl, pool),
            "S1_inverso": emparejar(zl, pool, orden=list(range(len(zl)))[::-1]),
            "S1_permutado": emparejar(zl, pool,
                                      orden=rng.permutation(len(zl)).tolist()),
            "S3_con_reemplazo": emparejar(zl, pool, con_reemplazo=True),
            "S4_sep_5min": emparejar(zl, pool, max_sep=MAX_SEP_S4_MS)}
        # S2: como base, pero descartando controles posteriores
        asign["S2_solo_anterior"] = {
            i: (r if (r and r[1] <= 0) else None) for i, r in asign["base"].items()}

        for var, mp in asign.items():
            acum = {c: [] for c in CAMPOS}
            for i, r in mp.items():
                if not r:
                    continue
                z = zl[i]
                c = pool[z["ancho_ticks"]][r[0]]
                mz = cruce(z, cache_z, i)
                mc = cruce(c, cache_c, (z["ancho_ticks"], r[0]))
                if not (mz and mc and mz.get("cruza") and mc.get("cruza")):
                    continue
                for campo in CAMPOS:
                    acum[campo].append(float(mz[campo]) - float(mc[campo]))
            if acum[METRICA_PRIMARIA]:
                pares[var][td] = {c: np.array(acum[c], dtype=np.float64)
                                  for c in CAMPOS}
        if (k + 1) % 10 == 0:
            print("    %d/%d  pares base: %d" % (
                k + 1, len(claves),
                sum(len(v[METRICA_PRIMARIA]) for v in pares["base"].values())))

    n_base = sum(len(v[METRICA_PRIMARIA]) for v in pares["base"].values())
    print("  %d pares en la base, %d sesiones" % (n_base, len(pares["base"])))

    # --- mediana del control, para el margen relativo -------------------------
    med_control = None
    try:
        h = json.loads((REPO / "docs" / "research" / "h_es_cruce_1.json")
                       .read_text(encoding="utf-8"))
        med_control = h["metricas"][METRICA_PRIMARIA]["control_mediana"]
    except Exception:
        pass
    margen = MARGEN_REL * med_control if med_control else None

    primario = boot_cluster(pares["base"], METRICA_PRIMARIA)
    resultado = dict(
        primario=dict(metrica=METRICA_PRIMARIA, **primario),
        equivalencia=(tost(primario["ci90"], margen) if margen and primario else None),
        secundarias={c: boot_cluster(pares["base"], c) for c in METRICAS_SECUNDARIAS},
        sensibilidades={v: boot_cluster(pares[v], METRICA_PRIMARIA)
                        for v in VARIANTES if v != "base"})

    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                   text=True).strip()
    sucios = [l[3:].strip() for l in subprocess.check_output(
        ["git", "-C", str(REPO), "status", "--porcelain"], text=True).splitlines() if l]
    out = dict(
        schema_version=SCHEMA_VERSION,
        run_id=make_run_id(head, claves, a.max_sesiones),
        run_scope=run_scope, publishable=publishable, max_sesiones_arg=a.max_sesiones,
        protocolo="docs/research/R3_INFERENCIA_CLUSTERIZADA_PROTOCOLO.md",
        outcomes_accessed=False, pnl_accessed=False, holdout_included=False,
        estimando=("diferencia pareada de %s, zona menos SU casi-zona, restringida al "
                   "soporte comun (zonas con control por ancho exacto y <=30 min)"
                   % METRICA_PRIMARIA),
        soporte=("R2 midio que el control existe para el 81,7%% de las zonas, sesgado a "
                 "las angostas (ancho mediano 3,28 contra 7,76). El estimando NO se "
                 "extiende a zonas anchas ni a Asia/Europa"),
        conteos=dict(n_universe_discovered=len(universo), n_selected=len(claves),
                     n_available=len(claves) - len(faltantes),
                     n_zonas=n_zonas_tot, n_pares_base=n_base,
                     n_sesiones_con_pares=len(pares["base"])),
        missing_items=faltantes,
        parametros_congelados=dict(B=B_BOOT, seed=SEED, alpha_ci=ALPHA_CI,
                                   alpha_tost=ALPHA_TOST, margen_relativo=MARGEN_REL,
                                   mediana_control=med_control, margen_absoluto=margen,
                                   metrica_primaria=METRICA_PRIMARIA,
                                   unidad_remuestreo="sesion completa",
                                   ponderacion="zona-ponderada dentro de la replica"),
        resultado=resultado,
        procedencia=dict(head_commit=head, arbol_limpio=not bool(sucios),
                         archivos_sucios=sorted(sucios), snapshot=str(snapshot),
                         parquet=str(parquet), comando=" ".join(sys.argv)))
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False),
                                   encoding="utf-8")

    p = resultado["primario"]
    print("\n  PRIMARIO %s" % METRICA_PRIMARIA)
    print("    punto %+.3f   IC95 [%+.3f, %+.3f]   cruza cero: %s"
          % (p["punto"], p["ci95"][0], p["ci95"][1], p["cruza_cero"]))
    print("    sesion-ponderada %+.3f   mismo signo: %s"
          % (p["punto_sesion_ponderada"], p["mismo_signo_que_ponderada"]))
    if resultado["equivalencia"]:
        e = resultado["equivalencia"]
        print("    TOST margen +-%.2f   IC90 [%+.3f, %+.3f]   EQUIVALENCIA: %s"
              % (e["margen"], e["ci90"][0], e["ci90"][1], e["equivalencia"]))
    print("\n  SENSIBILIDADES (punto e IC95)")
    for v, r in resultado["sensibilidades"].items():
        if r:
            print("    %-18s %+.3f  [%+.3f, %+.3f]  n=%d"
                  % (v, r["punto"], r["ci95"][0], r["ci95"][1], r["n_pares"]))
    print("\n  SECUNDARIAS")
    for c, r in resultado["secundarias"].items():
        if r:
            print("    %-14s %+10.2f  [%+10.2f, %+10.2f]"
                  % (c, r["punto"], r["ci95"][0], r["ci95"][1]))
    print("  escrito %s" % a.out)


if __name__ == "__main__":
    main()
