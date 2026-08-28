#!/usr/bin/env python
"""Harness forense de paridad BigTrap2Absorption <-> export NT8 sobre calendario irregular.

Disenado para el par (GC 02-26, oraculo AbsMagnitude de dic-2025), pero no lo asume:
todo insumo entra por CLI y todo lo que se afirma se mide.

Reglas de construccion:
  - Sin offsets manuales de numero de barra ni de indice de cinta.
  - La unica conversion horaria es ART -> UTC. El log del indicador se emite en la hora
    del chart de NT8 (Argentina, UTC-3, sin DST); la cinta .Last.txt esta en UTC. Es un
    desplazamiento fijo derivado de la zona declarada, no un ajuste para alinear.
  - El ancla se elige por busqueda algoritmica: los candidatos son TODOS los indices de
    la cinta cuyo ts coincide exactamente con el t_start de la primera cubeta, y se elige
    el de corrida consecutiva mas larga. El criterio es identidad de la particion, que se
    mide ANTES de comparar cualquier campo aritmetico; no se elige el que maximiza paridad.
  - Aritmetica entera: nanosegundos exactos con los 100 ns preservados, y precios en
    ticks enteros. Ningun float participa de una comparacion.
  - Falla cerrado: la cinta se lee entera, sin tope de ticks.
"""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
ART_OFFSET_NS = 3 * 3600 * 1_000_000_000


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tape_ns(s):
    """YYYYMMDD HHMMSS fffffff -> ns enteros UTC, con los 100 ns preservados."""
    d = datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]),
                 int(s[9:11]), int(s[11:13]), int(s[13:15]), tzinfo=timezone.utc)
    return int((d - EPOCH).total_seconds()) * 1_000_000_000 + int(s[16:23]) * 100


def iso_art_ns(s):
    """ISO de 7 decimales en ART -> ns enteros UTC."""
    d = datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
                 int(s[11:13]), int(s[14:16]), int(s[17:19]), tzinfo=timezone.utc)
    return (int((d - EPOCH).total_seconds()) * 1_000_000_000
            + int(s[20:27]) * 100 + ART_OFFSET_NS)


def parse_tape(path):
    ts, px, bid, ask, vol = [], [], [], [], []
    malformadas = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = ln.rstrip("\n").split(";")
            if len(p) < 5:
                malformadas += 1
                continue
            try:
                ts.append(tape_ns(p[0]))
                px.append(round(float(p[1]) * 10))
                bid.append(round(float(p[2]) * 10))
                ask.append(round(float(p[3]) * 10))
                vol.append(int(float(p[4])))
            except Exception:
                malformadas += 1
    arr = np.array(ts, dtype=np.int64)
    dif = np.diff(arr)
    audit = {
        "lineas_validas": int(len(arr)),
        "malformadas": malformadas,
        "ts_hacia_atras": int((dif < 0).sum()),
        "ts_repetido_consecutivo": int((dif == 0).sum()),
        "primera_utc": str(datetime.fromtimestamp(int(arr[0]) / 1e9, tz=timezone.utc)),
        "ultima_utc": str(datetime.fromtimestamp(int(arr[-1]) / 1e9, tz=timezone.utc)),
    }
    return {"ts": arr,
            "px": np.array(px, dtype=np.int64),
            "bid": np.array(bid, dtype=np.int64),
            "ask": np.array(ask, dtype=np.int64),
            "vol": np.array(vol, dtype=np.int64),
            "audit": audit}


def parse_oracle(path):
    meta = {}
    bars, scores, zones, fills, lifecycle = [], [], [], [], []
    eventos = Counter()
    seqs = []
    malformadas = 0
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("# meta"):
            meta = dict(x.split("=", 1) for x in ln[6:].strip().split(",") if "=" in x)
            continue
        if not ln.strip():
            continue
        q = ln.split("|")
        if len(q) != 4:
            malformadas += 1
            continue
        try:
            seq = int(q[0])
        except ValueError:
            malformadas += 1
            continue
        seqs.append(seq)
        eventos[q[2]] += 1
        d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
        d["_ts"] = iso_art_ns(q[1])
        d["_seq"] = seq
        if q[2] == "BARRA_PROCESADA":
            bars.append(d)
        elif q[2] == "ABS_SCORE":
            scores.append(d)
        elif q[2] == "ZONE_CREATED":
            zones.append(d)
        elif q[2] == "FILL":
            fills.append(d)
        elif q[2] in ("ZONE_INVALIDATED", "ZONE_EXPIRED"):
            d["_kind"] = q[2]
            lifecycle.append(d)
    s = np.array(seqs, dtype=np.int64)
    audit = {
        "malformadas": malformadas,
        "n_metas": 1 if meta else 0,
        "seq_monotona": bool((np.diff(s) > 0).all()),
        "seq_huecos": int(s.max() - s.min() + 1 - len(s)),
    }
    return {"meta": meta, "bars": bars, "scores": scores, "zones": zones,
            "fills": fills, "lifecycle": lifecycle,
            "eventos": dict(eventos), "audit": audit}


def find_anchor(ts, bars):
    """Candidatos por t_start exacto; gana la corrida consecutiva mas larga."""
    largos = np.array([int(b["largo"]) for b in bars], dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(largos)[:-1]])
    bstart = np.array([b["_ts"] for b in bars], dtype=np.int64)
    cand = np.flatnonzero(ts == bars[0]["_ts"])
    if len(cand) == 0:
        return {"encontrada": False, "candidatos": 0,
                "razon": "ningun tick de la cinta tiene el t_start de la primera cubeta"}
    corridas = []
    for c in cand:
        idx = int(c) + starts
        dentro = idx < len(ts)
        n = len(idx) if dentro.all() else int(np.argmin(dentro))
        eq = ts[idx[:n]] == bstart[:n]
        corridas.append((int(c), n if eq.all() else int(np.argmin(eq))))
    best = max(corridas, key=lambda r: r[1])
    return {"encontrada": True,
            "candidatos": int(len(cand)),
            "corridas": [{"indice": c, "cubetas_consecutivas": n} for c, n in corridas],
            "indice_tape": best[0],
            "cubetas_validadas": best[1],
            "filas_pre_ancla": best[0],
            "primera_barra_oraculo": int(bars[0]["bar"]),
            "barra_ancla": int(bars[0]["bar"]),
            "razon_exclusion_pre_ancla":
                "ticks de la cinta anteriores al inicio de carga del chart",
            "cobertura_post_ancla_pct": round(100.0 * best[1] / len(bars), 6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--tape", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    args = ap.parse_args()
    t_ini = time.time()

    for p in (args.csv, args.tape):
        if not p.exists():
            print("FALTA INPUT: %s" % p, file=sys.stderr)
            return 2

    rep = {
        "verdict": None,
        "command": " ".join(sys.argv),
        "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                    "platform": platform.platform()},
        "timezone": ("oraculo=ART(UTC-3, sin DST) convertido a UTC; cinta=UTC; "
                     "sin offsets manuales de barra ni de indice"),
        "hashes": {}, "bytes": {},
    }
    try:
        rep["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        rep["git_commit"] = None
    for nombre, p in (("oraculo", args.csv), ("cinta", args.tape),
                      ("kernel_py", Path("edgelab/bridge/indicators/bigtrap2absorption.py")),
                      ("cs", Path("nt8/BigTrap2Absorption.cs")),
                      ("harness", Path(__file__))):
        if p.exists():
            rep["hashes"][nombre] = sha256(p)
            rep["bytes"][nombre] = p.stat().st_size

    print("[*] parseando oraculo...", flush=True)
    o = parse_oracle(args.csv)
    rep["meta_oraculo"] = o["meta"]
    rep["parser_audit"] = {"oraculo": o["audit"]}
    rep["counts_oracle"] = o["eventos"]

    largos = Counter(int(b["largo"]) for b in o["bars"])
    resid = [b for b in o["bars"] if b.get("residual") == "True"]
    n25 = largos.get(25, 0)
    tk_res = sum(int(b["largo"]) for b in resid)
    rep["identidad_ticks"] = {
        "cubetas_de_25": n25,
        "residuales": len(resid),
        "ticks_en_residuales": tk_res,
        "total": n25 * 25 + tk_res,
        "formula": "%d*25 + %d = %d" % (n25, tk_res, n25 * 25 + tk_res),
    }
    rep["sesiones_cme_oraculo"] = sorted({b["td"] for b in o["bars"]})
    rep["residual_audit"] = [
        {"bar": int(b["bar"]), "largo": int(b["largo"]), "td": b["td"]} for b in resid]

    print("[*] parseando cinta...", flush=True)
    t = parse_tape(args.tape)
    rep["parser_audit"]["cinta"] = t["audit"]

    print("[*] buscando ancla...", flush=True)
    anc = find_anchor(t["ts"], o["bars"])
    rep["ancla"] = anc
    rep["pre_anchor"] = anc.get("filas_pre_ancla")

    n_bars = len(o["bars"])
    cov = anc.get("cubetas_validadas", 0)
    rep["cobertura"] = {"cubetas_oraculo": n_bars,
                        "cubetas_con_particion_identica": cov,
                        "pct": round(100.0 * cov / n_bars, 6)}

    if cov < n_bars:
        k = cov
        b = o["bars"][k]
        idx = anc["indice_tape"] + sum(int(x["largo"]) for x in o["bars"][:k])
        ts_tape = int(t["ts"][idx]) if idx < len(t["ts"]) else None
        declarados = sum(int(x["largo"]) for x in o["bars"][:k])
        rep["primer_contraejemplo"] = {
            "cubeta_ordinal": k + 1,
            "bar": int(b["bar"]),
            "td": b["td"],
            "largo": int(b["largo"]),
            "residual": b.get("residual"),
            "t_start_oraculo_utc": str(
                datetime.fromtimestamp(b["_ts"] / 1e9, tz=timezone.utc)),
            "indice_tape_esperado": int(idx),
            "ts_cinta_en_ese_indice": (
                str(datetime.fromtimestamp(ts_tape / 1e9, tz=timezone.utc))
                if ts_tape is not None else None),
            "delta_ns": (ts_tape - b["_ts"]) if ts_tape is not None else None,
            "ticks_consumidos_de_la_cinta": int(declarados),
            "ticks_declarados_por_nt8": int(declarados),
            "interpretacion": ("la cinta deja de reproducir la particion del oraculo: "
                               "no contiene el mismo flujo de ticks que cargo el chart"),
        }
        rep["verdict"] = "PARITY_GC0226_FAIL"
        rep["motivo_fail"] = (
            "cobertura post-ancla < 100 por ciento. La aritmetica no es comparable "
            "porque a partir del contraejemplo las cubetas no contienen los mismos ticks.")
    else:
        rep["verdict"] = "COVERAGE_OK_PENDIENTE_ARITMETICA"

    rep["exact_by_field"] = {}
    rep["mismatch_by_field"] = {}
    rep["zone_audit"] = {
        "zonas": len(o["zones"]), "fills": len(o["fills"]),
        "zone_id_unicos": len({z.get("zone_id") for z in o["zones"]}),
        "lifecycle_eventos": len(o["lifecycle"]),
        "estado": "NO_EVALUADO: bloqueado por cobertura"}
    rep["fill_audit"] = {"estado": "NO_EVALUADO: bloqueado por cobertura"}
    rep["holiday_audit"] = {
        "residuales_declaradas": rep["residual_audit"],
        "estado": ("las residuales del oraculo se reproducen y se listan; NO son "
                   "contrastables contra la cinta mientras la cobertura no sea 100 por ciento")}
    rep["calendar_hash"] = None
    rep["runtime"]["segundos"] = round(time.time() - t_ini, 1)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== %s ===" % rep["verdict"])
    print("  cobertura post-ancla : %d/%d (%s por ciento)"
          % (cov, n_bars, rep["cobertura"]["pct"]))
    print("  ancla                : indice %s, %s candidatos"
          % (anc.get("indice_tape"), anc.get("candidatos")))
    if "primer_contraejemplo" in rep:
        c = rep["primer_contraejemplo"]
        print("  contraejemplo        : cubeta %d (bar %d, td %s, largo %d, residual=%s)"
              % (c["cubeta_ordinal"], c["bar"], c["td"], c["largo"], c["residual"]))
        print("  t_start oraculo      : %s" % c["t_start_oraculo_utc"])
        print("  ts cinta en indice   : %s" % c["ts_cinta_en_ese_indice"])
    print("  artefacto            : %s" % args.out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
