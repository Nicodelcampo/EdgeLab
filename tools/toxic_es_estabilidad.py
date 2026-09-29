#!/usr/bin/env python3
"""TOXIC-ES-1 — docs/research/PREREG_TOXIC_ES_ESTABILIDAD_20260929.md. Target-free (sin retornos).

    python tools/toxic_es_estabilidad.py [--labels artifacts/l2_contexts/ES/labels.parquet] [--gate ...gate_report.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SEED, N_BOOT = 20260929, 5000
EXCL = ("20260811", "20260812")


def runs(df):
    """Rachas de toxic contiguas (mismo día, minutos consecutivos)."""
    d = df.sort_values(["cme_session", "minute_id"])
    t = d["tox"].to_numpy(bool); s = d["cme_session"].to_numpy(); m = d["minute_id"].to_numpy()
    out, n = [], 0
    for i in range(len(t)):
        cont = i > 0 and s[i] == s[i - 1] and m[i] == m[i - 1] + 1
        if t[i] and cont and t[i - 1]:
            n += 1
        else:
            if n:
                out.append(n)
            n = 1 if t[i] else 0
    if n:
        out.append(n)
    return np.array(out)


def criterios(ev, tr, ses_order):
    r = {}
    share = lambda x: float(x["tox"].mean())
    h = len(ses_order) // 2; A, B = set(ses_order[:h]), set(ses_order[h:])
    a, b = ev[ev.cme_session.isin(A)], ev[ev.cme_session.isin(B)]
    sa, sb = share(a), share(b)
    # bootstrap por sesión de la diferencia de proporciones
    g = ev.groupby("cme_session")["tox"].agg(["sum", "size"])
    ga, gb = g.loc[sorted(A & set(g.index))], g.loc[sorted(B & set(g.index))]
    rng = np.random.default_rng(SEED); diffs = []
    for _ in range(N_BOOT):
        ia = rng.integers(0, len(ga), len(ga)); ib = rng.integers(0, len(gb), len(gb))
        diffs.append(ga["sum"].values[ia].sum() / ga["size"].values[ia].sum() - gb["sum"].values[ib].sum() / gb["size"].values[ib].sum())
    ic = [float(np.quantile(diffs, .05)), float(np.quantile(diffs, .95))]
    ratio = max(sa, sb) / max(min(sa, sb), 1e-12)
    r["E1"] = dict(mitad1=sa, mitad2=sb, razon=ratio, ic90_dif=ic, pass_=bool(ratio <= 2.0 and ic[0] <= 0 <= ic[1]))
    se, st = share(ev), share(tr)
    r["E2"] = dict(evaluacion=se, entrenamiento=st, razon=se / st if st else None, pass_=bool(st and 0.5 <= se / st <= 2.0))
    rl = runs(ev)
    r["E3"] = dict(rachas=int(len(rl)), mediana=float(np.median(rl)) if len(rl) else 0.0,
                   frac_le3=float(np.mean(rl <= 3)) if len(rl) else 1.0,
                   pass_=bool(len(rl) and np.median(rl) >= 5 and np.mean(rl <= 3) < 0.5))
    tx = ev[ev.tox]
    s2h = tx["slot2h"].value_counts(normalize=True); maj = max(se, 1 - se)
    slot = ev.groupby("slot30")["tox"].mean()
    acc = float(np.mean(ev["slot30"].map(slot > 0.5).to_numpy(bool) == ev["tox"].to_numpy(bool)))
    r["E4"] = dict(max_share_2h=float(s2h.max()) if len(s2h) else 0.0, franja=str(s2h.idxmax()) if len(s2h) else None,
                   acc_solo_hora=acc, mayoria=maj, pass_=bool(len(s2h) and s2h.max() <= 0.5 and acc - maj <= 0.02))
    ps = tx["cme_session"].value_counts(normalize=True)
    con = ev.groupby("cme_session")["tox"].any()
    r["E5"] = dict(max_share_sesion=float(ps.max()) if len(ps) else 0.0, sesion=str(ps.idxmax()) if len(ps) else None,
                   frac_sesiones_con_toxic=float(con.mean()), pass_=bool(len(ps) and ps.max() <= 0.15 and con.mean() >= 0.75))
    r["PASS"] = all(v["pass_"] for k, v in r.items() if k.startswith("E"))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=str(REPO / "artifacts/l2_contexts/ES/labels.parquet"))
    ap.add_argument("--gate", default=str(REPO / "artifacts/l2_contexts/ES/gate_report.json"))
    ap.add_argument("--out", default=str(REPO / "docs/research/l2_contexts_ES/TOXIC_ES_1_resultado.json"))
    a = ap.parse_args()
    plan = json.loads(Path(a.gate).read_text(encoding="utf-8"))["plan"]
    lab = pd.read_parquet(a.labels)
    lab = lab[lab["context_state"].notna()].copy()
    lab["cme_session"] = lab["cme_session"].astype(str)
    lab["tox"] = lab["context_state"].astype(str) == "toxic"
    ct = pd.to_datetime(lab["minute_start_us"] + 3 * 3600 * 10**6, unit="us", utc=True).dt.tz_convert("America/Chicago")
    lab["slot30"] = ct.dt.hour * 2 + ct.dt.minute // 30; lab["slot2h"] = ct.dt.hour // 2
    lab["semana"] = ct.dt.strftime("%G-W%V")
    ev_ids = sorted(map(str, plan["eval_ids"])); tr_ids = set(map(str, plan["train_ids"]))
    ev = lab[lab.cme_session.isin(ev_ids) & lab["evaluation_eligible"].fillna(False)]
    tr = lab[lab.cme_session.isin(tr_ids)]
    out = dict(n_eval_min=int(len(ev)), n_train_min=int(len(tr)), sesiones_eval=len(ev_ids),
               primaria=criterios(ev, tr, ev_ids),
               sensibilidad_sin_11_12_ago=criterios(ev[~ev.cme_session.isin(EXCL)], tr, [s for s in ev_ids if s not in EXCL]),
               semanal=ev.groupby("semana")["tox"].mean().round(4).to_dict())
    Path(a.out).write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
