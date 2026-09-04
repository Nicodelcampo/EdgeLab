#!/usr/bin/env python3
"""H-LIQPOOL-ZB paso 2: censo del detector EQH/EQL sobre ZB, con controles.

Detector: edgelab/bridge/indicators/liqpool.py v2.0, portado del consenso de
PyIndicators / LuxAlgo / SMC-Liquidity-Hunter
(docs/research/H-LIQPOOL_FUENTES_COMPARADAS_2026-09-03.md).

TARGET-FREE. No se calcula P&L, ni tasa de acierto, ni expectativa. Se cuenta qué
hay y se lo compara contra controles.

QUE SE MIDE

1. CENSO COMPLETO, incluidas las zonas que **nunca fueron tocadas** — que son las
   que el ojo no registra y las que hacen que el censo no esté seleccionado por
   resultado. Reparto por estado ACTIVE / SWEPT / BROKEN.

2. LANDSCAPE de parámetros: pivot_left/right x eq_tolerance_pct x min_pivots.
   Se publica entero. Si el censo no cambia de forma monótona con cada eje, los
   parámetros no controlan lo que dicen controlar y el detector está mal.

3. LOS TRES CONTROLES que el diseño exige desde el día cero, porque son los que
   mataron a la familia anterior (BIGTRAP2_MAGNET_LINE_CLOSED, F2.8):

   a. ESPEJO — el nivel reflejado respecto del precio de referencia: misma
      distancia, lado opuesto. Descarta "gana porque está más cerca".
   b. SIN MARCA, MISMA GEOMETRÍA — un nivel a la misma distancia y con la misma
      antigüedad donde NO hay acumulación de pivotes. Es el control que mató a la
      hipótesis anterior; va desde el principio.
   c. NULO DE GRILLA — paseo aleatorio con los mismos incrementos barajados,
      conservando la discretización de ZB. El paso 1 ya mostró que la repetición
      de niveles no supera al azar en FRECUENCIA; acá se mide si las zonas
      detectadas se comportan distinto de las del nulo.

   La métrica de comparación es target-free: **cuántas veces vuelve el precio al
   nivel antes de romperlo** (toques) y **cuánto vive la zona** (edad al sweep).
   Ninguna de las dos mira retornos.

COMO PODRIA REFUTARSE
Si las zonas reales no se distinguen de (b) ni de (c) en toques ni en vida, el
objeto no aporta información y la familia se cierra sin haber gastado un solo
grado de libertad en P&L. Es exactamente el desenlace de F2.8, y el diseño lo
tiene previsto en vez de descubrirlo al final.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "9ec8225a61c619f415f29058a5bc73c4d96cc5e9"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/liqpool_zb_censo")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
    if len(commit) != 40:
        raise SystemExit("EXPECTED_COMMIT debe ser SHA de 40 chars")
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    if not (REPO_DIR / ".git").exists():
        last = None
        for attempt in range(4):
            r = subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                                REPO_URL, str(REPO_DIR)], env=env)
            if r.returncode == 0:
                break
            last = r.returncode
            subprocess.run(["rm", "-rf", str(REPO_DIR)])
            time.sleep(5 * (attempt + 1))
        else:
            raise SystemExit(f"git clone fallo tras 4 intentos (rc={last})")
        subprocess.run(["git", "sparse-checkout", "set", "--no-cone",
                        "edgelab/**", "data/nt8_oracles/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "lowhigh", commit], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if actual != commit:
        raise SystemExit("code provenance gate failed")
    sys.path.insert(0, str(REPO_DIR))
    return actual


def parse_cells(text):
    out = {}
    for part in (text or "").split("|"):
        if not part:
            continue
        t, _, v = part.partition(":")
        try:
            out[int(t)] = float(v)
        except ValueError:
            pass
    return out


def _i(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def parse_iso_ns(s):
    import datetime as dt
    s = s.strip().replace("/", "-")
    for f in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
              "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return int(dt.datetime.strptime(s, f).replace(
                tzinfo=dt.timezone.utc).timestamp() * 10**9)
        except ValueError:
            continue
    raise ValueError(s)














CONTRATOS = ("ZB_03-26", "ZB_06-26", "ZB_12-25")
BAR_TICKS = 200
GRID = [dict(pivot_left=L, pivot_right=L, eq_tolerance_pct=t, min_pivots=m)
        for L in (1, 2, 3) for t in (0.05, 0.10, 0.20) for m in (2, 3)]
NSIM = 50


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.indicators import liqpool

    rng = np.random.default_rng(20260903)
    sesiones = []
    for contrato in CONTRATOS:
        hits = sorted(KAGGLE_INPUT.rglob(f"{contrato}_ticks.parquet"))
        if not hits:
            continue
        t = ticks_mod.load_canonical_parquet(str(hits[0]))
        bars = bars_mod.build_tick_bars(t, BAR_TICKS)
        ses = bars_mod.session_ids(bars.end_ns).astype(np.int64)
        hi = bars.high_t.astype(np.int64)
        lo = bars.low_t.astype(np.int64)
        cl = bars.close_t.astype(np.int64)
        for s in np.unique(ses):
            m = ses == s
            if m.sum() < 120:
                continue
            sesiones.append((hi[m].tolist(), lo[m].tolist(), cl[m].tolist()))
        print(f"{contrato}: {len(sesiones)} sesiones acumuladas  "
              f"t={time.time()-t0:.0f}s", flush=True)

    print(f"total sesiones: {len(sesiones)}", flush=True)

    def resumen(zonas):
        if not zonas:
            return dict(n=0)
        est = {}
        for z in zonas:
            est[z["state"]] = est.get(z["state"], 0) + 1
        toques = sorted(z["touches"] for z in zonas)
        edades = sorted(z["age_at_sweep"] for z in zonas
                        if z["age_at_sweep"] is not None)
        return dict(
            n=len(zonas), por_estado=est,
            toques_medio=round(sum(toques) / len(toques), 3),
            toques_mediana=toques[len(toques) // 2],
            edad_al_sweep_mediana=edades[len(edades) // 2] if edades else None,
            nunca_tocadas=sum(1 for z in zonas if z["first_touch_bar"] is None),
            nunca_barridas=sum(1 for z in zonas if z["swept_bar"] is None),
            tolerancia_mediana=sorted(z["tolerance_ticks"] for z in zonas)[len(zonas) // 2],
        )

    # ---------- 1 y 2: censo + landscape ----------
    landscape = {}
    for params in GRID:
        todas = []
        for hi, lo, cl in sesiones:
            todas.extend(liqpool.detect(hi, lo, cl, params))
        clave = (f"L{params['pivot_left']}_tol{params['eq_tolerance_pct']}"
                 f"_min{params['min_pivots']}")
        landscape[clave] = dict(params=params, **resumen(todas))
        print(f"{clave}: {landscape[clave]['n']} zonas  "
              f"toques_medio={landscape[clave].get('toques_medio')}  "
              f"t={time.time()-t0:.0f}s", flush=True)

    # ---------- 3: los tres controles, en los defaults ----------
    base = dict(pivot_left=2, pivot_right=2, eq_tolerance_pct=0.10, min_pivots=2)
    reales, espejo, sinmarca, nulo = [], [], [], []
    for hi, lo, cl in sesiones:
        zs = liqpool.detect(hi, lo, cl, base)
        reales.extend(zs)
        n = len(hi)

        # (a) ESPEJO: nivel reflejado respecto del cierre de creacion
        for z in zs:
            ref = cl[min(z["created_bar"], n - 1)]
            nivel = 2 * ref - z["far_edge_tick"]
            espejo.append(_seguir(hi, lo, cl, z, nivel))

        # (b) SIN MARCA, misma geometria: mismo desplazamiento respecto del cierre,
        #     pero en una barra al azar donde NO hay zona detectada
        con_zona = set(z["created_bar"] for z in zs)
        libres = [b for b in range(20, n - 20) if b not in con_zona]
        if libres:
            for z in zs:
                b = int(rng.choice(libres))
                d = z["far_edge_tick"] - cl[min(z["created_bar"], n - 1)]
                zc = dict(z)
                zc["created_bar"] = b
                sinmarca.append(_seguir(hi, lo, cl, zc, cl[b] + d))

        # (c) NULO DE GRILLA: paseo con los mismos incrementos barajados
        mid = [(hi[i] + lo[i]) // 2 for i in range(n)]
        half = [(hi[i] - lo[i]) // 2 for i in range(n)]
        dif = np.diff(np.array(mid, dtype=np.int64))
        for _ in range(max(1, NSIM // 25)):
            paso = rng.permutation(dif)
            m2 = np.concatenate(([mid[0]], mid[0] + np.cumsum(paso))).astype(np.int64)
            h2 = (m2 + np.array(half, dtype=np.int64)).tolist()
            l2 = (m2 - np.array(half, dtype=np.int64)).tolist()
            nulo.extend(liqpool.detect(h2, l2, m2.tolist(), base))

    report = {
        "schema": "liqpool_zb_censo_v1",
        "status": "TARGET_FREE_NO_OUTCOMES",
        "code_commit": commit,
        "bar_ticks": BAR_TICKS, "n_sesiones": len(sesiones),
        "params_base": base,
        "censo_real": resumen(reales),
        "control_a_espejo": resumen(espejo),
        "control_b_sin_marca": resumen(sinmarca),
        "control_c_nulo_grilla": resumen(nulo),
        "landscape": landscape,
        "lectura": ("si las zonas reales no se distinguen del control (b) ni del (c) "
                    "en toques ni en vida, el objeto no aporta y la familia se cierra "
                    "sin gastar un grado de libertad en P&L -- que es exactamente el "
                    "desenlace de F2.8 en la familia anterior"),
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "censo_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "landscape"},
                     indent=2, ensure_ascii=False), flush=True)
    return 0


def _seguir(hi, lo, cl, z, nivel):
    """Sigue un nivel de CONTROL con la misma regla de toques y sweep que la zona."""
    tol = z["tolerance_ticks"]
    esH = z["side"] == "H"
    out = dict(state="ACTIVE", touches=0, first_touch_bar=None,
               swept_bar=None, age_at_sweep=None, tolerance_ticks=tol)
    dentro = False
    for i in range(z["created_bar"] + 1, len(hi)):
        if esH:
            toca = hi[i] >= nivel - tol
            mecha = hi[i] > nivel
            cierre = cl[i] > nivel
        else:
            toca = lo[i] <= nivel + tol
            mecha = lo[i] < nivel
            cierre = cl[i] < nivel
        if toca and not dentro:
            out["touches"] += 1
            dentro = True
            if out["first_touch_bar"] is None:
                out["first_touch_bar"] = i
        elif not toca:
            dentro = False
        if cierre:
            out["state"] = "BROKEN"
            if out["swept_bar"] is None:
                out["swept_bar"] = i
            out["age_at_sweep"] = i - z["created_bar"]
            break
        if mecha and out["swept_bar"] is None:
            out["swept_bar"], out["state"] = i, "SWEPT"
            out["age_at_sweep"] = i - z["created_bar"]
    return out


if __name__ == "__main__":
    raise SystemExit(main())
