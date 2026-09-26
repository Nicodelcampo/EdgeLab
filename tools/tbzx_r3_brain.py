#!/usr/bin/env python3
r"""TBZX-R3 en el cerebro: partición, lecciones de método y una observación por corrida (con auditoría de controles).

El kernel de Kaggle (tools/tbzx_reingreso_kaggle.py) no tiene el repo: mide y deja r3_resumen.json, r3_celdas.csv(.gz)
y r3_ctrl.npz. Este script los ingiere acá, con el commit del código y el sha de cada artefacto.

    python tools/tbzx_r3_brain.py declare --ctrl <dir con r3_ctrl.npz>
    python tools/tbzx_r3_brain.py ingest --tag IT2-LOCAL46 --dir <salida> --ctrl <dir con r3_ctrl.npz> --note "..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

LEDGER = REPO / "artifacts" / "hippocampus" / "tbzx_r3_20260926.jsonl"
DOC = "docs/research/MANIFIESTO_TBZX_REINGRESO_3T_20260925.md"
PART = "P-TBZX-R3-EXP"
HOLD_S = 1800   # horizonte máximo de resultado (iteración 3); el de las iteraciones 1-2 era 300 s


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _celdas(d: Path) -> Path:
    for n in ("r3_celdas.csv.gz", "r3_celdas.csv"):
        if (d / n).exists():
            return d / n
    raise FileNotFoundError(f"sin r3_celdas en {d}")


def declare(ctrl_dir: Path):
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    from edgelab.edge_brain.hippocampus_store import DurableHippocampus
    if LEDGER.exists() and PART in DurableHippocampus(LEDGER).partitions:
        print("ya declarada"); return
    tds = [str(x) for x in np.load(ctrl_dir / "r3_ctrl.npz")["tds"]]
    with measurement_episode(LEDGER, "EP-TBZX-R3-DECLARE-20260926", goal="declarar partición y lecciones de método TBZX-R3",
                             recorded_by="tools/tbzx_r3_brain.py declare", repo=REPO, prereg_ref=DOC) as ep:
        ep.store.record_partition(PART, "EXPLORATION",
                                  "ES 25T jul-2025 a mar-2026 (mismas sesiones que P-TBZ-EXP; fijada en el pre-registro del "
                                  "25/09; asentada acá el 26/09, después de las corridas locales 1 y 2)",
                                  [f"ES:{d}" for d in tds])
        ep.store.record_lesson(LessonCandidate(
            lesson_id="LES-R3-ENTRY-AT-LEVEL-GAP-20260925", episode_id="EP-TBZX-R3-DECLARE-20260926",
            statement=("Entrada 'perfecta' al precio del NIVEL cuando el trade que dispara ya lo saltó regala ticks: sobre un "
                       "random walk sintético dio ~+2,5 pp de acierto a 'sigue' (r = 0). La entrada perfecta debe ser el "
                       "precio del trade que dispara (o el medio)."),
            confidence="HIGH", status="PROPOSED", scope="METHODOLOGICAL", robustness="REPLICATED",
            conditions=["simulaciones de entrada por toque de nivel", "precios con saltos"]))
        ep.store.record_lesson(LessonCandidate(
            lesson_id="LES-R3-TRADE-PRICE-BOUNCE-20260925", episode_id="EP-TBZX-R3-DECLARE-20260926",
            statement=("Con TP/SL chicos medidos sobre precios de trade, el rebote bid/ask domina: en ES (46 sesiones) "
                       "'sigue' con r >= 1 dio +5,5 pp sobre 50 % y el fantasma de otra sesión dio lo mismo o más. Medir la "
                       "dirección sobre el medio (bid+ask)/2 y comparar siempre contra un control."),
            confidence="HIGH", status="PROPOSED", scope="METHODOLOGICAL", robustness="REPLICATED",
            conditions=["ES, tick de 1 = spread", "TP <= 3 ticks"]))
        ep.note("particion", PART)
    print("declarada", PART, len(tds), "sesiones")


def ingest(tag: str, d: Path, ctrl_dir: Path, note: str, hold_s: float):
    from edgelab.edge_brain.control_guard import audit_event_controls
    from edgelab.edge_brain.episode_logger import measurement_episode
    from edgelab.edge_brain.hippocampus import LessonCandidate
    summ = json.loads((d / "r3_resumen.json").read_text())
    cp = _celdas(d)
    D = pd.read_csv(cp)
    pairs = np.load(ctrl_dir / "r3_ctrl.npz")["pairs"]
    audit = audit_event_controls(pairs[:, 0] // 1000, pairs[:, 1] // 1000, hold_s,
                                 same_session=np.zeros(len(pairs), bool))
    if audit["status"] != "PASS":
        raise SystemExit(f"auditoría de controles {audit['status']}: {audit['reason']}")
    sha = _sha(cp)
    has_tp = "TP" in D.columns
    if not has_tp:
        D["TP"] = 3
    w = lambda g, c: float((g[c] * g.n).sum() / max(g.n.sum(), 1))
    metrics = {}
    for (ex, sl, tp), g in D.groupby(["exec", "SL", "TP"]):
        gf = g.dropna(subset=["hit_fant"])
        metrics[f"{ex}|SL{sl}|TP{tp}"] = dict(celdas=int(len(g)), hit=round(w(g, "hit"), 4),
                                               hit_fant=round(w(gf, "hit_fant"), 4) if len(gf) else None,
                                               pnl=round(w(g, "pnl"), 3), mejor_pnl=round(float(g.pnl.max()), 3),
                                               sugerencias=int(g.sugerencia.sum()))
    res = dict(sesiones=summ["sesiones"], desde=summ["desde"], hasta=summ["hasta"], celdas_probadas=int(len(D)),
               configs=summ.get("configs_usadas"), fdr_q=0.10, bootstrap="por sesión, 1000", nota=note)
    ep_id = f"EP-TBZX-R3-{tag}"
    with measurement_episode(LEDGER, ep_id, goal=f"TBZX-R3 {tag}: reingreso a la franja y dirección/P&L tras penetrar",
                             recorded_by="tools/tbzx_r3_brain.py ingest", repo=REPO, prereg_ref=DOC,
                             inputs={"celdas": cp, "resumen": d / "r3_resumen.json"}) as ep:
        ep.store.record_observation(f"OBS-TBZX-R3-{tag}", "TBZX: se aleja D, vuelve, penetra p, retrocede r; resultado",
                                    "RESPONSE_PROFILE", [PART], metrics, res, sha, design="EVENT_VS_CONTROL",
                                    control_audit=audit)
        S = D[D.sugerencia]
        real = S[S["exec"] == "realista"]
        for i, r in enumerate(real.sort_values("pnl", ascending=False).head(10).itertuples()):
            ep.store.record_lesson(LessonCandidate(
                lesson_id=f"SUG-TBZX-R3-{tag}-{i + 1}", episode_id=ep_id,
                statement=(f"{r.cfg} lado {r.lado} D{r.D} p{r.p} r{r.r} {r.dir} SL{r.SL} TP{r.TP}: realista {r.pnl:.2f} t "
                           f"(IC {r.pnl_lo:.2f}..{r.pnl_hi:.2f}, n {r.n}), fantasma {r.pnl_fant:.2f}. Sólo exploración: "
                           f"confirmar en abr-jun (P-TBZ-CONF) con spec aparte."),
                confidence="LOW", status="PROPOSED", scope="SUGGESTED_ANALYSIS", robustness="SINGLE_SAMPLE"))
        ep.note("resumen", json.dumps(dict(celdas=len(D), sugerencias=int(len(S)), realistas=int(len(real)),
                                           audit=audit["status"])))
    print(tag, "celdas", len(D), "sugerencias", len(S), "realistas", len(real), "audit", audit["status"], "sha", sha[:12])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["declare", "ingest"])
    ap.add_argument("--dir"); ap.add_argument("--ctrl", required=True); ap.add_argument("--tag")
    ap.add_argument("--note", default=""); ap.add_argument("--hold", type=float, default=HOLD_S)
    a = ap.parse_args(argv)
    if a.step == "declare":
        declare(Path(a.ctrl))
    else:
        ingest(a.tag, Path(a.dir), Path(a.ctrl), a.note, a.hold)


if __name__ == "__main__":
    main()
