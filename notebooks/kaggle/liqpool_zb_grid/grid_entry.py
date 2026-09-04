#!/usr/bin/env python3
"""H-LIQPOOL-ZB paso 1: la repeticion de niveles, contra el nulo de grilla.

Diseno: docs/research/H-LIQPOOL-ZB_DISENO_2026-09-03.md

LA PREGUNTA
Nico propone que las secuencias de maximos (o minimos) al mismo nivel son
acumulacion de liquidez y atraen al precio. Antes de medir atraccion hay que
saber si el OBJETO existe: en ZB el tick es 1/32 y una sesion recorre decenas de
ticks, no cientos, asi que dos maximos pueden caer en el mismo precio POR PURA
DISCRETIZACION. Si la tasa observada no supera a la que produce la grilla, la
"acumulacion" es un artefacto y la familia se cierra aca.

EL NULO, y es la parte que importa
No sirve un nulo de niveles uniformes al azar. Este preserva:
  - la grilla de precios real (ticks enteros),
  - el recorrido y la volatilidad de cada sesion,
  - el numero de pivotes de esa sesion.
Se construye con un PASEO ALEATORIO sobre la misma grilla, con los mismos
incrementos observados barajados dentro de la sesion (bootstrap de incrementos).
Eso destruye cualquier estructura de niveles pero conserva la escala, la
discretizacion y la longitud. Es el nulo que separa "hay niveles" de "hay pocos
precios posibles".

QUE SE MIDE, target-free
  1. cuantos precios distintos toca cada sesion de ZB (la coarseness real);
  2. pivotes por sesion segun PivotStrength;
  3. la distribucion de TAMANO DE GRUPO: cuantos pivotes comparten nivel dentro
     de una tolerancia, observado contra el nulo;
  4. lo mismo estratificado por separacion temporal, que es el eje que distingue
     la microzona de la zona separada.

No se mide atraccion, ni retornos, ni P&L. Eso es el paso 3 y va despues.
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
EXPECTED_COMMIT = "ac2d0eaf4f19d7fce0ac5d28739bb93b0bf3e03e"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/liqpool_zb_grid")


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
BAR_TICKS = 200          # barras de 200 ticks: ZB opera poco, hace falta agregar
PIVOTS = (2, 3, 5)       # PivotStrength
TOL = (0, 1, 2)          # LevelToleranceTicks
NSIM = 200               # replicas del nulo por sesion


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries

    rng = np.random.default_rng(20260903)
    res = {}
    grid_stats = []

    for contrato in CONTRATOS:
        hits = sorted(KAGGLE_INPUT.rglob(f"{contrato}_ticks.parquet"))
        if not hits:
            print("falta", contrato, flush=True)
            continue
        t = ticks_mod.load_canonical_parquet(str(hits[0]))
        bars = bars_mod.build_tick_bars(t, BAR_TICKS)
        hi = bars.high_t.astype(np.int64)
        lo = bars.low_t.astype(np.int64)
        ses = bars_mod.session_ids(bars.end_ns).astype(np.int64)
        print(f"{contrato}: {len(t.ts_ns):,} ticks -> {len(hi):,} barras, "
              f"{len(np.unique(ses))} sesiones  t={time.time()-t0:.0f}s", flush=True)

        for s in np.unique(ses):
            m = ses == s
            H, L = hi[m], lo[m]
            if len(H) < 60:
                continue
            grid_stats.append(dict(contrato=contrato, barras=int(len(H)),
                                   precios_distintos=int(len(np.unique(np.concatenate((H, L))))),
                                   rango_ticks=int(H.max() - L.min())))

            # --- pivotes observados y del nulo ---
            # nulo: paseo aleatorio con los MISMOS incrementos de cierre barajados,
            # y el mismo half-range por barra. Conserva escala, grilla y longitud.
            mid = ((H + L) // 2).astype(np.int64)
            half = ((H - L) // 2).astype(np.int64)
            dif = np.diff(mid)

            for K in PIVOTS:
                obs = pivotes(H, L, K)
                for tol in TOL:
                    g_obs = grupos(obs, tol)
                    clave = f"K{K}_tol{tol}"
                    d = res.setdefault(clave, dict(K=K, tol=tol, sesiones=0,
                                                   obs=[], nulo=[], obs_span=[]))
                    d["sesiones"] += 1
                    d["obs"].append(g_obs["dist"])
                    d["obs_span"].append(g_obs["spans"])

            sim_acc = {f"K{K}_tol{tol}": [] for K in PIVOTS for tol in TOL}
            for _ in range(NSIM):
                paso = rng.permutation(dif)
                m2 = np.concatenate(([mid[0]], mid[0] + np.cumsum(paso)))
                H2 = m2 + half
                L2 = m2 - half
                for K in PIVOTS:
                    p2 = pivotes(H2, L2, K)
                    for tol in TOL:
                        sim_acc[f"K{K}_tol{tol}"].append(grupos(p2, tol)["dist"])
            for clave, lst in sim_acc.items():
                res[clave]["nulo"].append(lst)

    salida = {"schema": "liqpool_zb_grid_null_v1",
              "status": "TARGET_FREE_NO_OUTCOMES",
              "code_commit": commit,
              "bar_ticks": BAR_TICKS, "nsim_por_sesion": NSIM,
              "grid": resumen_grid(grid_stats),
              "variantes": {}}

    for clave, d in res.items():
        obs = agrega(d["obs"])
        nulo_medias = {}
        for tam in ("2", "3", "4", "5+"):
            vals = [np.mean([rep.get(tam, 0) for rep in reps]) for reps in d["nulo"]]
            nulo_medias[tam] = float(np.sum(vals))
        # p-valor empirico del conteo total de grupos de 3 o mas
        obs3 = sum(obs.get(k, 0) for k in ("3", "4", "5+"))
        sim3 = []
        for i in range(NSIM):
            tot = 0
            for reps in d["nulo"]:
                r = reps[i]
                tot += sum(r.get(k, 0) for k in ("3", "4", "5+"))
            sim3.append(tot)
        sim3 = np.array(sim3, float)
        p = float((sim3 >= obs3).mean())
        salida["variantes"][clave] = dict(
            K=d["K"], tol=d["tol"], sesiones=d["sesiones"],
            observado=obs, nulo_esperado=nulo_medias,
            grupos_3mas_observado=int(obs3),
            grupos_3mas_nulo_medio=float(sim3.mean()),
            grupos_3mas_nulo_p95=float(np.percentile(sim3, 95)),
            ratio_obs_sobre_nulo=round(obs3 / sim3.mean(), 4) if sim3.mean() else None,
            p_empirico=p)
        print(f"{clave}: grupos>=3 obs {obs3}  nulo {sim3.mean():.0f} "
              f"(p95 {np.percentile(sim3,95):.0f})  ratio "
              f"{obs3/sim3.mean() if sim3.mean() else float('nan'):.2f}  p={p:.4f}", flush=True)

    salida["elapsed_seconds"] = round(time.time() - t0, 1)
    salida["outcomes_accessed"] = False
    salida["holdout_accessed"] = False
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "grid_null_v1.json").write_text(
        json.dumps(salida, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps({k: v for k, v in salida.items() if k != "variantes"},
                     indent=2, ensure_ascii=False), flush=True)
    return 0


def pivotes(H, L, K):
    """Maximos y minimos que dominan estrictamente a K barras de cada lado."""
    import numpy as np
    n = len(H)
    if n < 2 * K + 1:
        return np.array([], dtype=np.int64)
    idx = np.arange(K, n - K)
    esHi = np.ones(len(idx), bool)
    esLo = np.ones(len(idx), bool)
    for d in range(1, K + 1):
        esHi &= (H[idx] > H[idx - d]) & (H[idx] > H[idx + d])
        esLo &= (L[idx] < L[idx - d]) & (L[idx] < L[idx + d])
    return np.concatenate((H[idx][esHi], L[idx][esLo]))


def grupos(niveles, tol):
    """Distribucion de tamano de grupo de niveles a distancia <= tol."""
    import numpy as np
    out = {"2": 0, "3": 0, "4": 0, "5+": 0}
    spans = []
    if len(niveles) == 0:
        return {"dist": out, "spans": spans}
    v = np.sort(niveles)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[j + 1] - v[j] <= tol:
            j += 1
        tam = j - i + 1
        if tam >= 2:
            out["5+" if tam >= 5 else str(tam)] += 1
            spans.append(int(v[j] - v[i]))
        i = j + 1
    return {"dist": out, "spans": spans}


def agrega(lista):
    out = {}
    for d in lista:
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return out


def resumen_grid(gs):
    import numpy as np
    if not gs:
        return {}
    pd_ = np.array([g["precios_distintos"] for g in gs])
    rg = np.array([g["rango_ticks"] for g in gs])
    ba = np.array([g["barras"] for g in gs])
    return dict(sesiones=len(gs),
                precios_distintos_mediana=int(np.median(pd_)),
                precios_distintos_p10=int(np.percentile(pd_, 10)),
                precios_distintos_p90=int(np.percentile(pd_, 90)),
                rango_ticks_mediana=int(np.median(rg)),
                barras_por_sesion_mediana=int(np.median(ba)))


if __name__ == "__main__":
    raise SystemExit(main())
