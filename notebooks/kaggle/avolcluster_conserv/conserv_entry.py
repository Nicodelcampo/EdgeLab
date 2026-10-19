#!/usr/bin/env python3
"""FASE 5: conservacion de volumen a nivel SESION. Test decisivo.

Fases previas:
  F2 desalineacion REFUTADA. F3 filtro Low/High REFUTADO.
  F4 fase de particion: k=-1 da un pico nitido (9,0% de bloques exactos contra
     0,07% en k=0) pero es la misma magnitud que el re-etiquetado de F3. El
     off-by-one es real y explica ~9%. NO explica el 91% restante.

Queda una sola familia de causa grande: NT8 y el parquet no ven el MISMO
CONJUNTO DE TICKS. Lo sugiere la direccion del desvio -- NT8 tiene MAS volumen
que Python en 21,5% de los bloques, y ninguna hipotesis que solo reparta o
filtre puede producir eso.

TEST: cualquier diferencia de PARTICION se cancela al sumar. Si NT8 cubre B
bloques en una sesion, cubre 10*B barras = 1200*B ticks desde el primer tick de
la sesion. Se compara ese total contra el volumen de los primeros 1200*B ticks
de la sesion en el parquet.

  totales iguales  -> mismos ticks, el problema es 100% de particion (arreglable
                      en el kernel Python, sin tocar el .cs)
  totales distintos-> conjuntos de ticks distintos: el problema es de FUENTE DE
                      DATOS y ningun cambio de kernel logra paridad

Es la bifurcacion que decide si la paridad de aVolClusterPOI es alcanzable.
Target-free. No modifica el .cs ni el kernel.
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
EXPECTED_COMMIT = "706c4fe261eec3f856cf84cc66f6d3d31f0f6680"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/avolcluster_conserv")


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






def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    import numpy as np
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
    from edgelab.bridge.ticks import TickSeries

    csv_path = REPO_DIR / DIAG_CSV
    with csv_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = [l for l in f if not l.startswith("# meta")]
    rows = []
    for r in csv.DictReader(lines):
        try:
            ts = parse_iso_ns(r["bar_close_time"]) + ART_TO_UTC_NS
        except ValueError:
            continue
        c = parse_cells(r.get("cells"))
        if not c:
            continue
        rows.append({"ts": ts, "sess_nt8": r.get("session_index"),
                     "bar_index": int(r["bar_index"]) if r.get("bar_index", "").strip() else -1,
                     "vol": sum(c.values())})
    print("NT8 bloques=", len(rows), flush=True)
    lo_ns, hi_ns = min(x["ts"] for x in rows), max(x["ts"] for x in rows)

    hits = sorted(KAGGLE_INPUT.rglob("NQ_06-26_ticks.parquet"))
    full = ticks_mod.load_canonical_parquet(str(hits[0]))
    idx = np.flatnonzero((full.ts_ns >= lo_ns - 3 * 86400 * 10**9)
                         & (full.ts_ns <= hi_ns + 86400 * 10**9))
    ts_ns = full.ts_ns[idx]
    vol = full.volume[idx].astype(np.float64)
    n = len(ts_ns)
    sess = bars_mod.session_ids(ts_ns).astype(np.int64)
    starts = np.flatnonzero(np.concatenate(([True], sess[1:] != sess[:-1])))
    ends = np.concatenate((starts[1:], [n]))
    cum = np.concatenate(([0.0], np.cumsum(vol)))
    print("ticks=", n, "sesiones parquet=", len(starts), flush=True)

    # agrupar bloques NT8 por sesion propia de NT8 (columna session_index)
    from collections import defaultdict
    by_sess = defaultdict(list)
    for r in rows:
        by_sess[r["sess_nt8"]].append(r)

    per_session = []
    for sname, blocks in sorted(by_sess.items(), key=lambda kv: min(b["ts"] for b in kv[1])):
        blocks.sort(key=lambda b: b["ts"])
        B = len(blocks)
        nt8_vol = sum(b["vol"] for b in blocks)
        t_first = blocks[0]["ts"]
        # sesion del parquet que contiene el cierre del primer bloque
        si = int(np.searchsorted(ts_ns, t_first)) 
        si = min(max(si, 0), n - 1)
        k = int(np.searchsorted(starts, si, side="right") - 1)
        if k < 0:
            continue
        s0, s1 = int(starts[k]), int(ends[k])
        need = 1200 * B
        take = min(need, s1 - s0)
        py_vol = float(cum[s0 + take] - cum[s0])
        per_session.append({
            "sess_nt8": sname, "blocks": B, "ticks_needed": need,
            "ticks_available_in_session": s1 - s0,
            "nt8_volume": nt8_vol, "py_volume": py_vol,
            "ratio": round(nt8_vol / py_vol, 6) if py_vol else None,
            "diff": round(nt8_vol - py_vol, 3),
        })

    ok = [s for s in per_session if s["py_volume"] and abs(s["diff"]) < 0.5]
    ratios = sorted(s["ratio"] for s in per_session if s["ratio"])
    tot_nt8 = sum(s["nt8_volume"] for s in per_session)
    tot_py = sum(s["py_volume"] for s in per_session)
    med = ratios[len(ratios) // 2] if ratios else None

    if med is not None and abs(med - 1.0) < 0.002 and len(ok) / max(len(per_session), 1) > 0.5:
        verdict = "MISMOS_TICKS_PROBLEMA_DE_PARTICION"
    elif med is not None and abs(med - 1.0) < 0.05:
        verdict = "TICKS_CASI_IGUALES_DESVIO_PEQUENIO_NO_EXPLICADO"
    else:
        verdict = "CONJUNTOS_DE_TICKS_DISTINTOS_PROBLEMA_DE_FUENTE"

    report = {
        "schema": "avolclusterpoi_session_volume_conservation_v1",
        "status": "DIAGNOSTIC_NO_CODE_CHANGED",
        "code_commit": commit, "nt8_csv_sha256": sha256(csv_path),
        "n_sessions_compared": len(per_session),
        "sessions_with_exact_total": len(ok),
        "ratio_median": med,
        "ratio_p05": ratios[int(0.05 * len(ratios))] if ratios else None,
        "ratio_p95": ratios[int(0.95 * len(ratios))] if ratios else None,
        "total_nt8_volume": tot_nt8, "total_py_volume": tot_py,
        "total_ratio": round(tot_nt8 / tot_py, 6) if tot_py else None,
        "verdict": verdict,
        "sessions": per_session[:400],
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "conservation_report_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    small = dict(report); small.pop("sessions")
    print(json.dumps(small, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
