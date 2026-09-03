#!/usr/bin/env python3
"""AUDITORIA: la particion de 120 ticks contra las 233.601 barras del BARPROFILE.

QUE SE AUDITA
La rama research/avolcluster-nq-parity-oracle-20260901 (commit 6f4e32f) certifica
paridad de aVolClusterPOI. El cambio que sostiene esa certificacion es la nueva
particion de barras: conteo estricto de 120 transacciones por barra con resync al
inicio de sesion (build_resolved_tick_bars). Su evidencia declarada es:

  "10 de 10 barras de muestra auditadas contra BARPROFILE coincidieron de forma
   100,00% identica en Low y High"

Diez de 233.601. Este kernel corre la misma comparacion sobre TODAS las filas.

POR QUE IMPORTA
El BARPROFILE es la unica fuente independiente de la frontera real de NT8: lo
escribe el propio indicador (instrumentacion P-70) y trae low_tick, high_tick y
primary_bar_volume por barra. Si la particion de Python reproduce esos tres
campos en las 233.601 barras, la certificacion queda firme y el eslabon debil
desaparece. Si no, sabemos exactamente cuantas barras fallan y donde.

OBSERVACION SOBRE EL CODIGO AUDITADO (leida de la fuente, no supuesta)
build_resolved_tick_bars lee target_vols = df_bp["profile_volume"] y NUNCA lo
usa. La particion es un paso fijo de 120 ticks con resync por sesion; ademas
toma e_ns = bar_times del propio CSV de NT8. Consecuencias:
  - el nombre "resolved ... contra el perfil" no describe lo que hace;
  - el "0 ms TIMESTAMP_DIFF" de su capa 3 es en parte definicional, porque los
    cierres de barra no se calculan sino que se copian del oraculo;
  - por lo tanto la unica parte falsable de la particion es la geometria:
    low_tick, high_tick y primary_bar_volume. Es lo que mide este kernel.

QUE SE REPORTA
  - coincidencia exacta de low_tick, high_tick y primary_bar_volume, por separado
    y conjunta, sobre todas las barras emparejadas;
  - distribucion del error cuando no coincide;
  - si el error se concentra al inicio de sesion (deriva que el resync corrige)
    o esta repartido;
  - cuantas barras produce la particion contra las 233.601 del oraculo.

COMO PODRIA REFUTARSE ESTA AUDITORIA
Si la comparacion falla por una convencion de zona horaria o por el recorte de
ticks del parquet y no por la particion, el fallo apareceria como un corrimiento
global constante (casi todas las barras mal, con el mismo signo). Se distingue
mirando la fraccion de aciertos: un corrimiento global da ~0%, un defecto real
de particion da un valor intermedio y estructurado.

Target-free. No modifica codigo ni oraculos. No toca retornos ni holdout.
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
EXPECTED_COMMIT = "6f4e32f"  # se resuelve a SHA completo abajo
BRANCH = "research/avolcluster-nq-parity-oracle-20260901"
REPO_DIR = Path("/kaggle/working/EdgeLab")
KAGGLE_INPUT = Path("/kaggle/input")
DIAG_CSV = "data/nt8_oracles/avolcluster_v05_NQ0626_120t_DIAG_20260901.csv"
ART_TO_UTC_NS = 3 * 3600 * 10**9
TICKS_PER_BAR = 120
WINDOW_BARS = 10
OUT = Path("/kaggle/working/avolcluster_partition_audit")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def checkout(commit: str) -> str:
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
                        "edgelab/**", "tools/**"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "fetch", "origin", BRANCH, "--depth", "50"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", "audit", "FETCH_HEAD"], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    if not actual.startswith(commit):
        raise SystemExit("code provenance gate failed: HEAD=%s esperado %s" % (actual, commit))
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










BARPROFILE_NAME = "avolcluster_v05_NQ0626_120t_BARPROFILE_20260902.csv"
PARQUET_NAME = "NQ_06-26_ticks.parquet"


def main() -> int:
    t0 = time.time()
    commit = checkout(EXPECTED_COMMIT)
    print("repo_commit=", commit, flush=True)
    import numpy as np
    import pandas as pd
    from edgelab.bridge import bars as bars_mod, ticks as ticks_mod

    bp_hits = sorted(KAGGLE_INPUT.rglob(BARPROFILE_NAME))
    if not bp_hits:
        raise SystemExit("falta el BARPROFILE en los inputs")
    bp_path = bp_hits[0]
    print("barprofile:", bp_path, "sha256:", sha256(bp_path), flush=True)

    df = pd.read_csv(bp_path, skiprows=1)
    print("filas BARPROFILE=", len(df), flush=True)

    pq = sorted(KAGGLE_INPUT.rglob(PARQUET_NAME))[0]
    t = ticks_mod.load_canonical_parquet(str(pq))
    print("ticks parquet=", len(t.ts_ns), flush=True)

    bars = bars_mod.build_resolved_tick_bars(t, str(bp_path), ticks_per_bar=TICKS_PER_BAR)
    nb = len(bars.end_ns)
    print("barras reconstruidas=", nb, "t=", round(time.time() - t0, 1), flush=True)

    m = min(nb, len(df))
    low_o = df["low_tick"].values[:m].astype(np.int64)
    high_o = df["high_tick"].values[:m].astype(np.int64)
    vol_o = df["primary_bar_volume"].values[:m].astype(np.float64)
    sess_o = df["session_index"].values[:m].astype(np.int64)
    bbc_o = df["block_bar_count"].values[:m].astype(np.int64)

    low_p = np.asarray(bars.low_t[:m], dtype=np.int64)
    high_p = np.asarray(bars.high_t[:m], dtype=np.int64)
    vol_p = np.asarray(bars.volume[:m], dtype=np.float64)

    eq_low = low_p == low_o
    eq_high = high_p == high_o
    eq_vol = np.abs(vol_p - vol_o) < 1e-9
    eq_all = eq_low & eq_high & eq_vol

    dlow = low_p - low_o
    dhigh = high_p - high_o
    dvol = vol_p - vol_o

    def dist(x, cap=6):
        out = {}
        for v in range(-cap, cap + 1):
            c = int((x == v).sum())
            if c:
                out[str(v)] = c
        out["|d|>%d" % cap] = int((np.abs(x) > cap).sum())
        return out

    # concentracion al inicio de sesion: el resync se hace en el primer bar
    first_of_sess = np.concatenate(([True], sess_o[1:] != sess_o[:-1]))
    pos_in_sess = np.zeros(m, np.int64)
    k = 0
    for i in range(m):
        k = 0 if first_of_sess[i] else k + 1
        pos_in_sess[i] = k
    deciles = {}
    for d in range(10):
        lo_i = np.percentile(pos_in_sess, d * 10)
        hi_i = np.percentile(pos_in_sess, (d + 1) * 10)
        sel = (pos_in_sess >= lo_i) & (pos_in_sess <= hi_i)
        if sel.sum():
            deciles[str(d)] = {"barras": int(sel.sum()),
                               "aciertos_pct": round(float(eq_all[sel].mean()), 6)}

    # primeras 200 barras de cada sesion: donde vive el resync
    early = pos_in_sess < 200
    late = ~early

    verdict = ("PARTICION_CONFIRMADA" if eq_all.mean() > 0.9999 else
               "PARTICION_MAYORMENTE_CORRECTA" if eq_all.mean() > 0.95 else
               "PARTICION_PARCIAL" if eq_all.mean() > 0.05 else
               "PARTICION_NO_REPRODUCE_EL_ORACULO")

    report = {
        "schema": "avolclusterpoi_partition_audit_v1",
        "status": "AUDIT_NO_CODE_CHANGED",
        "audited_branch": "research/avolcluster-nq-parity-oracle-20260901",
        "audited_commit": commit,
        "claim_under_audit": "10 de 10 barras de muestra coincidieron 100% en Low y High",
        "barprofile_sha256": sha256(bp_path),
        "n_barprofile_rows": int(len(df)),
        "n_bars_reconstructed": int(nb),
        "n_compared": int(m),
        "exact_low_pct": round(float(eq_low.mean()), 6),
        "exact_high_pct": round(float(eq_high.mean()), 6),
        "exact_volume_pct": round(float(eq_vol.mean()), 6),
        "exact_all_three_pct": round(float(eq_all.mean()), 6),
        "exact_all_three_count": int(eq_all.sum()),
        "delta_low_dist": dist(dlow),
        "delta_high_dist": dist(dhigh),
        "delta_volume_abs_mean": round(float(np.abs(dvol).mean()), 4),
        "delta_volume_abs_max": float(np.abs(dvol).max()),
        "aciertos_primeras_200_barras_de_sesion": round(float(eq_all[early].mean()), 6) if early.sum() else None,
        "aciertos_resto_de_la_sesion": round(float(eq_all[late].mean()), 6) if late.sum() else None,
        "aciertos_por_decil_de_posicion_en_sesion": deciles,
        "verdict": verdict,
        "nota_codigo": ("build_resolved_tick_bars lee profile_volume y no lo usa; "
                        "la particion es un paso fijo de 120 ticks con resync por "
                        "sesion, y e_ns se copia del CSV de NT8, asi que el "
                        "TIMESTAMP_DIFF=0 de la capa 3 es en parte definicional"),
        "elapsed_seconds": round(time.time() - t0, 1),
        "outcomes_accessed": False, "holdout_accessed": False, "code_modified": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "partition_audit_v1.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
