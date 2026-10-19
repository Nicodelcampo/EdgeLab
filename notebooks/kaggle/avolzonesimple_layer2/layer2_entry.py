#!/usr/bin/env python3
"""AVolZoneSimple — PARIDAD CAPA 2: reconstruccion end-to-end desde los ticks.

CAPA 1, ya cerrada y con dos replicas: alimentando el kernel Python con las celdas
que escribio NT8, el acuerdo es EXACTO -- 3.086/3.086 en NQ SEP26 y 5.778/5.778 en
NQ 06-26. Eso prueba que las dos implementaciones son la misma funcion, y nada mas.

CAPA 2, esto: Python arma el perfil DESDE LOS TICKS del parquet, sin mirar las
celdas de NT8, y se compara zona contra zona. Es la unica capa que mide lo que el
rediseno prometia.

POR QUE ES LA PRUEBA QUE IMPORTA
El techo conocido es duro y esta medido: la particion de barras de NT8 se
reproduce al 89,81% sobre 233.601 barras, con el error creciendo dentro de la
sesion (decil 0: 97,27%, decil 9: 73,07%), porque los dos flujos de ticks NO son
identicos transaccion por transaccion
(docs/research/avolcluster_partition_audit_20260903/).

Con aVolClusterPOI eso se traducia en 15,27% de bloques con celdas identicas: el
indicador amplificaba la diferencia de ticks porque decidia con un umbral por
celda que un contrato cruzaba en el 89,60% de los bloques.

AVolZoneSimple define la zona como una SUMA sobre muchas celdas, y su turnover
bajo ruido de +-1 contrato bajo de 30,87% a 4,97%. La prediccion es que el
acuerdo end-to-end sea MUCHO mayor que el 15,27% de la version vieja, pese a que
la particion de barras sigue siendo la misma de siempre.

QUE SE MIDE, y separado a proposito
  1. acuerdo de DECISION (CREATE / ABSTAIN_*) bloque a bloque;
  2. acuerdo de GEOMETRIA exacta (lower, upper) entre los CREATE de los dos lados;
  3. cuanto se corre cuando no coincide: distribucion de |delta lower| y de
     jaccard del intervalo -- un tick de corrimiento no es "otra zona";
  4. lo mismo restringido a los bloques donde el perfil reconstruido coincide
     EXACTO con el de NT8. Ese corte separa "el algoritmo diverge" de "los ticks
     son distintos", que es la confusion que arruina este tipo de medicion.

COMO PODRIA REFUTARSE
Si el acuerdo end-to-end resulta tan bajo como el de aVolClusterPOI, el rediseno
no compro robustez donde importaba y la premisa cae. Si el corte (4) da acuerdo
casi total mientras el global es bajo, el problema es 100% de datos y ningun
cambio de indicador lo mejora.

Target-free: no toca retornos ni P&L. Ventana pre-holdout.
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
EXPECTED_COMMIT = "2d2bc83e7b0c8a70a91a72a5768adcee44bcd2c2"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/avolzonesimple_layer2")


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










ORACLE_CSV = "data/nt8_oracles/avolzonesimple_NQ0626_20260903.csv"


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries
    from edgelab.bridge.indicators.avolzonesimple import detect_block

    csv_path = REPO_DIR / ORACLE_CSV
    texto = csv_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    meta = {}
    for parte in next(l for l in texto if l.startswith("# meta")).lstrip("#").split(","):
        k, _, v = parte.partition("=")
        if k.strip():
            meta[k.strip()] = v.strip()
    params = dict(bars_per_block=int(meta["bars_per_block"]),
                  area_share_pct=int(meta["area_share_pct"]),
                  max_zone_ticks=int(meta["max_zone_ticks"]),
                  min_concentration=int(meta["min_concentration"]))
    WIN = params["bars_per_block"]
    print("params del oraculo:", params, flush=True)

    nt8 = []
    for r in csv.DictReader([l for l in texto if not l.startswith("# meta")]):
        cells = parse_cells(r.get("cells"))
        if not cells:
            continue
        try:
            ts = parse_iso_ns(r["bar_close_time_utc"])
        except ValueError:
            continue
        nt8.append(dict(ts=ts, cells=cells, decision=r["decision"].strip(),
                        lower=_i(r.get("lower_tick")), upper=_i(r.get("upper_tick")),
                        close=_i(r.get("close_tick"))))
    print("bloques NT8=", len(nt8), flush=True)
    lo_ns = min(x["ts"] for x in nt8)
    hi_ns = max(x["ts"] for x in nt8)

    pq = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))[0]
    full = ticks_mod.load_canonical_parquet(str(pq))
    idx = np.flatnonzero((full.ts_ns >= lo_ns - 5 * 86400 * 10**9)
                         & (full.ts_ns <= hi_ns + 86400 * 10**9))
    t = TickSeries(ts_ns=full.ts_ns[idx], price_ticks=full.price_ticks[idx],
                   volume=full.volume[idx],
                   bid_ticks=full.bid_ticks[idx] if full.bid_ticks is not None else None,
                   ask_ticks=full.ask_ticks[idx] if full.ask_ticks is not None else None,
                   sequence=full.sequence[idx], tick_size=full.tick_size,
                   instrument=full.instrument, contract=full.contract, source=full.source)
    bars = bars_mod.build_tick_bars(t, TICKS_PER_BAR)
    nb = len(bars.end_ns)
    px = t.price_ticks.astype(np.int64)
    vol = t.volume.astype(np.float64)
    bidx = bars.tick_bar_idx.astype(np.int64)
    print("ticks=", len(px), "barras=", nb, flush=True)

    span = int(px.max() - px.min()) + 1
    base = int(px.min())
    key = bidx * span + (px - base)
    o = np.argsort(key, kind="stable")
    ks, vs = key[o], vol[o]
    e = np.flatnonzero(np.concatenate(([True], ks[1:] != ks[:-1])))
    sums = np.add.reduceat(vs, e)
    ub = (ks[e] // span).astype(np.int64)
    up = (ks[e] % span + base).astype(np.int64)
    st = np.searchsorted(ub, np.arange(nb), side="left")
    en = np.searchsorted(ub, np.arange(nb), side="right")

    end_ns = bars.end_ns
    ts_arr = np.array([x["ts"] for x in nt8], dtype=np.int64)
    pos = np.searchsorted(end_ns, ts_arr)

    n = matched = 0
    dec_ok = geom_ok = both_create = 0
    perfil_exacto = 0
    geom_ok_perfil_exacto = 0
    both_create_perfil_exacto = 0
    dlow = {}
    jac = []
    matriz = {}

    for i in range(len(nt8)):
        q = int(pos[i])
        best = None
        bd = None
        for c in (q - 1, q, q + 1):
            if 0 <= c < nb:
                d = abs(int(end_ns[c]) - int(ts_arr[i]))
                if bd is None or d < bd:
                    bd, best = d, c
        if best is None or bd > 10**9 or best - WIN + 1 < 0:
            continue
        matched += 1
        pc = {}
        for b in range(best - WIN + 1, best + 1):
            for j in range(st[b], en[b]):
                kk = int(up[j])
                pc[kk] = pc.get(kk, 0) + int(sums[j])
        r = detect_block(pc, params, nt8[i]["close"])

        mismo_perfil = (pc == {k: int(v) for k, v in nt8[i]["cells"].items()})
        if mismo_perfil:
            perfil_exacto += 1

        d_nt8, d_py = nt8[i]["decision"], r["decision"]
        matriz[d_nt8 + " -> " + d_py] = matriz.get(d_nt8 + " -> " + d_py, 0) + 1
        if d_nt8 == d_py:
            dec_ok += 1
        if d_nt8 == "CREATE" and d_py == "CREATE":
            both_create += 1
            a = (nt8[i]["lower"], nt8[i]["upper"])
            b2 = (r["lower_tick"], r["upper_tick"])
            if a == b2:
                geom_ok += 1
                if mismo_perfil:
                    geom_ok_perfil_exacto += 1
            dd = abs(a[0] - b2[0])
            kk = str(dd) if dd <= 5 else "6+"
            dlow[kk] = dlow.get(kk, 0) + 1
            lo2 = max(a[0], b2[0]); hi2 = min(a[1], b2[1])
            inter = max(0, hi2 - lo2 + 1)
            union = max(a[1], b2[1]) - min(a[0], b2[0]) + 1
            jac.append(inter / union if union else 0.0)
            if mismo_perfil:
                both_create_perfil_exacto += 1

    jac.sort()

    def pct(a, b):
        return round(a / b, 6) if b else None

    report = {
        "schema": "avolzonesimple_layer2_endtoend_v1",
        "status": "PARITY_LAYER2_FROM_TICKS",
        "estimand": ("reconstruccion end-to-end: el perfil se arma DESDE LOS TICKS del "
                     "parquet, sin mirar las celdas de NT8. Distinto de la capa 1, que "
                     "usa el perfil del propio NT8 y ya dio EXACT dos veces."),
        "code_commit": commit,
        "oraculo": ORACLE_CSV,
        "oraculo_sha256": sha256(csv_path),
        "params": params,
        "n_bloques_nt8": len(nt8),
        "n_emparejados": matched,
        "acuerdo_decision": pct(dec_ok, matched),
        "acuerdo_decision_n": dec_ok,
        "ambos_CREATE": both_create,
        "geometria_exacta_entre_ambos_CREATE": geom_ok,
        "geometria_exacta_pct": pct(geom_ok, both_create),
        "matriz_de_decisiones": matriz,
        "delta_lower_dist": dlow,
        "jaccard_mediano": jac[len(jac) // 2] if jac else None,
        "jaccard_ge_0_8_pct": pct(sum(1 for x in jac if x >= 0.8), len(jac)),
        "perfil_reconstruido_exacto": perfil_exacto,
        "perfil_reconstruido_exacto_pct": pct(perfil_exacto, matched),
        "corte_perfil_exacto": {
            "ambos_CREATE": both_create_perfil_exacto,
            "geometria_exacta": geom_ok_perfil_exacto,
            "geometria_exacta_pct": pct(geom_ok_perfil_exacto, both_create_perfil_exacto),
            "lectura": ("si aca el acuerdo es casi total mientras el global es bajo, la "
                        "divergencia es 100% de datos y ningun cambio de indicador la "
                        "mejora"),
        },
        "referencia_avolclusterpoi": {"bloques_con_celdas_identicas": 0.152664},
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "layer2_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
