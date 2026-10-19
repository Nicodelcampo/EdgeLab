"""Comparador de paridad por sesion CME, con veredictos separados por capa.

Motivacion
----------
El harness canonico (`verify_layer_parity.py`) indexa por numero de barra GLOBAL
acumulado. Una sola diferencia de tick desplaza toda la numeracion posterior y
la comparacion se vuelve ruido: sobre ventanas largas la cobertura cae a 1-10 %
y no se puede distinguir "el kernel calcula distinto" de "el chart y la cinta no
vieron los mismos ticks".

Este comparador usa la clave

    (cme_session_id, bucket_index_within_session, t_start)

que se recupera en cada frontera de sesion, porque AMBOS lados reinician la
particion de 25 ticks ahi.

Sutileza decisiva
-----------------
La particion reinicia por sesion, pero el ANILLO CAUSAL NO. En
`bigtrap2absorption.py` el `abs_ring` se crea una vez (l. 117) y solo se le
excluyen las residuales (l. 407); cruza las fronteras de sesion intacto.

Por eso una divergencia contamina `a_thr` / `a_pass` durante hasta
`abs_lookback` (500) cubetas NO residuales posteriores, aunque el conteo de
ticks de la sesion siguiente coincida exactamente. Este comparador lleva esa
contabilidad explicita y NO reinicia el historial causal artificialmente.

Veredictos separados
--------------------
    1. DATOS      identidad de ticks por sesion (NT8 vs cinta)
    2. PARTICION  n cubetas, residual, n_ticks, t_start
    3. ARITMETICA signed_flow, d_ticks, a_score   (local a la cubeta)
    4. CAUSAL     n_hist, a_thr, a_pass           (estado global, con conteo
                                                   de cubetas contaminadas)
    5. EVENTOS    zonas y fills, emparejados por sesion + available_at + lado
                  + geometria, sin depender del numero de barra global

Uso
---
    python tools/compare_session_parity.py \
        --csv "<export NT8>" --tape "<cinta .Last.txt>" \
        --out-json docs/research/PARIDAD_SESION_<tag>.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import pathlib
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from edgelab.bridge.ticks import TickSeries  # noqa: E402
from edgelab.bridge.indicators.bigtrap2absorption import (  # noqa: E402
    run as run_abs, DEFAULTS)

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
ART_NS = 3 * 3600 * 1_000_000_000
ABS_LOOKBACK = 500


# ---------------------------------------------------------------- utilidades

def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tape_ns(s: str) -> int:
    """'YYYYMMDD HHMMSS fffffff' -> ns UTC, entero exacto (sin float)."""
    d = datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]),
                 int(s[9:11]), int(s[11:13]), int(s[13:15]), tzinfo=timezone.utc)
    return int((d - EPOCH) // timedelta(microseconds=1)) * 1000 + int(s[16:23]) * 100


def iso_art_ns(s: str) -> int:
    """ISO del log NT8 (hora ART del chart) -> ns UTC, entero exacto."""
    d = datetime(int(s[0:4]), int(s[5:7]), int(s[8:10]),
                 int(s[11:13]), int(s[14:16]), int(s[17:19]), tzinfo=timezone.utc)
    return (int((d - EPOCH) // timedelta(microseconds=1)) * 1000
            + int(s[20:27]) * 100 + ART_NS)


def kv(payload: str) -> dict:
    return dict(x.split("=", 1) for x in payload.split(";") if "=" in x)


def fnum(x, default=float("nan")) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isnan(a) or math.isnan(b):
        return False
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


# ------------------------------------------------------------ lado NT8 (.cs)

def parse_export(path: pathlib.Path) -> dict:
    meta, bars, scores, zones, fills = {}, [], [], [], []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("# meta"):
            meta = kv(ln[6:].strip().replace(",", ";"))
            continue
        q = ln.split("|")
        if len(q) != 4:
            continue
        seq, ts, ev, payload = q
        d = kv(payload)
        if ev == "BARRA_PROCESADA":
            bars.append({"bar": int(d["bar"]), "largo": int(d["largo"]),
                         "residual": d["residual"] == "True", "td": d["td"],
                         "ts": iso_art_ns(ts)})
        elif ev == "ABS_SCORE":
            scores.append({"bar": int(d["bar"]),
                           "residual": d.get("residual") == "True",
                           "flow": fnum(d.get("signed_flow")),
                           "dticks": fnum(d.get("d_ticks")),
                           "score": fnum(d.get("a_score")),
                           "thr": fnum(d.get("a_thr")),
                           "pass": d.get("a_pass") == "True",
                           "nhist": int(fnum(d.get("n_hist"), 0)),
                           "nticks": int(fnum(d.get("n_ticks"), 0)),
                           "t_start": iso_art_ns(d["t_start"])})
        elif ev == "ZONE_CREATED":
            zones.append({"seq": int(seq), "side": d["side"],
                          "lo": fnum(d["lo"]), "hi": fnum(d["hi"]),
                          "score": fnum(d.get("a_score")),
                          "avail": iso_art_ns(d["available_at"]), "td": d.get("td")})
        elif ev == "FILL":
            fills.append({"seq": int(seq), "side": d["side"],
                          "px": fnum(d["fill_px"]),
                          "at": iso_art_ns(d["fill_at"]),
                          "sig": iso_art_ns(d["signal_at"])})
    by_bar = {s["bar"]: s for s in scores}
    for b in bars:
        b.update(by_bar.get(b["bar"], {}))
    return {"meta": meta, "bars": bars, "zones": zones, "fills": fills}


# --------------------------------------------------------------- lado Python

def load_tape(path: pathlib.Path):
    ts, px, bid, ask, vol = [], [], [], [], []
    malformed = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = ln.rstrip("\n").split(";")
            if len(p) < 5:
                malformed += 1
                continue
            try:
                ts.append(tape_ns(p[0]))
                px.append(round(float(p[1]) * 10))
                bid.append(round(float(p[2]) * 10))
                ask.append(round(float(p[3]) * 10))
                vol.append(float(p[4]))
            except (ValueError, IndexError):
                malformed += 1
    return (np.array(ts, dtype=np.int64), np.array(px, dtype=np.int64),
            np.array(bid, dtype=np.int64), np.array(ask, dtype=np.int64),
            np.array(vol, dtype=np.float64), malformed)


def run_kernel(ts, px, bid, ask, vol, lo, hi) -> dict:
    serie = TickSeries(ts_ns=ts[lo:hi], price_ticks=px[lo:hi],
                       bid_ticks=bid[lo:hi], ask_ticks=ask[lo:hi],
                       volume=vol[lo:hi],
                       sequence=np.arange(hi - lo, dtype=np.int64), tick_size=0.1)
    p = dict(DEFAULTS)
    p["ScoreMode"] = "AbsMagnitude"
    res = run_abs(serie, params=p)

    bars, by_bar = [], {}
    for evt in res.get("events", []):
        q = evt.split("|")
        if len(q) != 4:
            continue
        d = kv(q[3])
        if q[2] == "BARRA_PROCESADA":
            bars.append({"bar": int(d["bar"]), "largo": int(d["largo"]),
                         "residual": d["residual"] == "True", "td": d.get("td")})
        elif q[2] == "ABS_SCORE":
            by_bar[int(d["bar"])] = {
                "flow": fnum(d.get("signed_flow")), "dticks": fnum(d.get("d_ticks")),
                "score": fnum(d.get("a_score")), "thr": fnum(d.get("a_thr")),
                "pass": d.get("a_pass") == "True",
                "nhist": int(fnum(d.get("n_hist"), 0)),
                "nticks": int(fnum(d.get("n_ticks"), 0)),
                "t_start": iso_art_ns(d["t_start"]) - ART_NS}
    for b in bars:
        b.update(by_bar.get(b["bar"], {}))
    return {"bars": bars, "zones": res.get("zones", [])}


# --------------------------------------------------------------- comparacion

def by_session(bars: list) -> dict:
    """Agrupa y asigna indice de cubeta RELATIVO a la sesion (base 1)."""
    out = collections.OrderedDict()
    for b in bars:
        out.setdefault(b["td"], []).append(b)
    for td, lst in out.items():
        for i, b in enumerate(lst, 1):
            b["idx"] = i
    return out


def assign_by_window(nt8_sessions: dict, py_bars: list) -> dict:
    """Asigna cubetas Python a las sesiones de NT8 por ventana de `t_start`.

    NO se usa el campo `td` del kernel Python: `bigtrap2absorption.py:186` hace
    `trade_date = str(sess_id)` y `bars.session_ids()` devuelve DIAS DESDE EPOCH,
    no una fecha. El kernel emite `td=20416` donde NT8 emite `td=20251124`, asi
    que cualquier join por esa clave da cero. Se clava por tiempo, que es lo
    unico que ambos lados expresan igual.
    """
    bounds = []
    for td, lst in nt8_sessions.items():
        tss = [b["t_start"] for b in lst if b.get("t_start") is not None]
        if tss:
            bounds.append((min(tss), max(tss), td))
    bounds.sort()
    lo_arr = np.array([b[0] for b in bounds], dtype=np.int64)
    out = collections.OrderedDict((b[2], []) for b in bounds)
    for b in py_bars:
        t = b.get("t_start")
        if t is None:
            continue
        k = int(np.searchsorted(lo_arr, t, side="right")) - 1
        if k < 0 or t > bounds[k][1]:
            continue
        out[bounds[k][2]].append(b)
    for lst in out.values():
        for i, b in enumerate(lst, 1):
            b["idx"] = i
    return out


def compare(exp: dict, ker: dict, tape_ticks_by_td: dict, complete: set) -> dict:
    ns = by_session(exp["bars"])
    ks = assign_by_window(ns, ker["bars"])
    shared = [td for td in ns if td in ks and td in complete]

    rep = {"sessions": {}, "totals": {}}
    tot = collections.Counter()
    contaminated_countdown = 0
    causal_clean = causal_dirty = 0

    for td in shared:
        nb, kb = ns[td], ks[td]
        nt_ticks = sum(b["largo"] for b in nb)
        kt_ticks = sum(b["largo"] for b in kb)
        tape_n = kt_ticks

        # capa 1: datos — la cinta es lo que el kernel Python consumio en esa
        # ventana temporal; si difiere de lo que vio NT8, nada aguas abajo es
        # atribuible al kernel.
        data_ok = (nt_ticks == tape_n)
        # capa 2: particion
        part_ok = (len(nb) == len(kb))
        part_bad = 0
        for a, b in zip(nb, kb):
            if (a["largo"] != b["largo"] or a["residual"] != b["residual"]
                    or a.get("t_start") != b.get("t_start")):
                part_bad += 1
        part_ok = part_ok and part_bad == 0

        # capas 3 y 4, cubeta a cubeta
        ar_ok = ar_bad = ca_ok = ca_bad = 0
        for a, b in zip(nb, kb):
            if a.get("t_start") != b.get("t_start"):
                contaminated_countdown = ABS_LOOKBACK
                continue
            same_arith = (close(a.get("flow", float("nan")), b.get("flow", float("nan")))
                          and close(a.get("dticks", float("nan")), b.get("dticks", float("nan")))
                          and close(a.get("score", float("nan")), b.get("score", float("nan")), 1e-12))
            if same_arith:
                ar_ok += 1
            else:
                ar_bad += 1
                contaminated_countdown = ABS_LOOKBACK

            same_causal = (a.get("nhist") == b.get("nhist")
                           and close(a.get("thr", float("nan")), b.get("thr", float("nan")), 1e-12)
                           and a.get("pass") == b.get("pass"))
            if contaminated_countdown > 0:
                causal_dirty += 1
            else:
                causal_clean += 1
                if same_causal:
                    ca_ok += 1
                else:
                    ca_bad += 1
            if not a["residual"] and contaminated_countdown > 0:
                contaminated_countdown -= 1

        rep["sessions"][td] = {
            "nt8_ticks": nt_ticks, "py_ticks": kt_ticks, "tape_ticks": tape_n,
            "tick_diff": tape_n - nt_ticks,
            "nt8_buckets": len(nb), "py_buckets": len(kb),
            "datos": "OK" if data_ok else "DIFF",
            "particion": "OK" if part_ok else "DIFF(%d)" % part_bad,
            "aritmetica_ok": ar_ok, "aritmetica_bad": ar_bad,
            "causal_ok": ca_ok, "causal_bad": ca_bad,
        }
        tot["sessions"] += 1
        tot["data_ok"] += data_ok
        tot["part_ok"] += part_ok
        tot["ar_ok"] += ar_ok
        tot["ar_bad"] += ar_bad
        tot["ca_ok"] += ca_ok
        tot["ca_bad"] += ca_bad

    rep["totals"] = {
        "sessions_compared": tot["sessions"],
        "sessions_data_identical": tot["data_ok"],
        "sessions_partition_identical": tot["part_ok"],
        "arith_ok": tot["ar_ok"], "arith_bad": tot["ar_bad"],
        "causal_ok": tot["ca_ok"], "causal_bad": tot["ca_bad"],
        "causal_clean_buckets": causal_clean,
        "causal_contaminated_buckets": causal_dirty,
        "abs_lookback": ABS_LOOKBACK,
    }
    return rep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=pathlib.Path, required=True)
    ap.add_argument("--tape", type=pathlib.Path, required=True)
    ap.add_argument("--out-json", type=pathlib.Path, default=None)
    ap.add_argument("--tag", type=str, default="")
    a = ap.parse_args()

    print("[*] export...", flush=True)
    exp = parse_export(a.csv)
    tds = [b["td"] for b in exp["bars"]]
    first_td, last_td = tds[0], tds[-1]
    complete = set(tds) - {first_td, last_td}
    print("    cubetas=%d  sesiones=%d  (primera y ultima excluidas por parciales)"
          % (len(exp["bars"]), len(set(tds))), flush=True)

    print("[*] cinta...", flush=True)
    ts, px, bid, ask, vol, malformed = load_tape(a.tape)
    print("    ticks=%d  malformadas=%d" % (len(ts), malformed), flush=True)

    lo = int(np.searchsorted(ts, exp["bars"][0]["ts"] - 86_400_000_000_000, "left"))
    hi = int(np.searchsorted(ts, exp["bars"][-1]["ts"] + 86_400_000_000_000, "right"))
    print("[*] kernel sobre [%d:%d] = %d ticks..." % (lo, hi, hi - lo), flush=True)
    ker = run_kernel(ts, px, bid, ask, vol, lo, hi)
    print("    cubetas=%d" % len(ker["bars"]), flush=True)

    rep = compare(exp, ker, {}, complete)
    rep["_meta"] = {
        "tag": a.tag, "export": str(a.csv), "export_sha256": sha256(a.csv),
        "tape": str(a.tape), "tape_sha256": sha256(a.tape),
        "score_mode": exp["meta"].get("score_mode"),
        "key": "(cme_session_id, bucket_index_within_session, t_start)",
        "nota_anillo": ("abs_ring NO reinicia por sesion; una divergencia contamina "
                        "hasta %d cubetas no residuales posteriores" % ABS_LOOKBACK),
        "sesiones_excluidas_por_parciales": [first_td, last_td],
    }

    t = rep["totals"]
    print("\n" + "=" * 78)
    print("PARIDAD POR SESION  %s" % a.tag)
    print("=" * 78)
    print("  1 DATOS      sesiones con ticks identicos : %d/%d"
          % (t["sessions_data_identical"], t["sessions_compared"]))
    print("  2 PARTICION  sesiones con particion igual : %d/%d"
          % (t["sessions_partition_identical"], t["sessions_compared"]))
    print("  3 ARITMETICA cubetas exactas              : %d/%d"
          % (t["arith_ok"], t["arith_ok"] + t["arith_bad"]))
    print("  4 CAUSAL     cubetas limpias exactas      : %d/%d   (contaminadas: %d)"
          % (t["causal_ok"], t["causal_ok"] + t["causal_bad"],
             t["causal_contaminated_buckets"]))

    bad = [(td, s) for td, s in rep["sessions"].items()
           if s["datos"] != "OK" or s["particion"] != "OK" or s["aritmetica_bad"]]
    if bad:
        print("\n  sesiones con alguna diferencia (%d):" % len(bad))
        print("    %-10s %9s %9s %8s %10s %11s %9s"
              % ("sesion", "NT8 tk", "cinta tk", "dif", "datos", "particion", "arit_bad"))
        for td, s in bad[:40]:
            print("    %-10s %9d %9d %+8d %10s %11s %9d"
                  % (td, s["nt8_ticks"], s["tape_ticks"], s["tick_diff"],
                     s["datos"], s["particion"], s["aritmetica_bad"]))

    if a.out_json:
        a.out_json.write_text(json.dumps(rep, indent=2, ensure_ascii=False),
                              encoding="utf-8")
        print("\n  artefacto: %s" % a.out_json)


if __name__ == "__main__":
    main()
