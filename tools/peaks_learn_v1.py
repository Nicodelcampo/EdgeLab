#!/usr/bin/env python3
r"""Detector de «picos consecutivos» v1: candidatos amplios + rasgos por zona + clasificador validado entre sesiones.

    .venv\Scripts\python tools\peaks_learn_v1.py --asset ES_03-26_202601_25T_HFT

1. **Candidatos** (alta cobertura, causales): el detector v0 (`peaks_learn.py`) con una configuración permisiva.
2. **Rasgos de cada candidato**, calculados con los pivotes de la banda dentro de la zona (todo pasado respecto del final
   de la zona):
   - toques; duración (velas y segundos); ancho de la banda (ticks);
   - distancia media entre picos consecutivos (|Δprecio|, ticks) — propuesto por Nico;
   - distancia media recorrida entre un pico y el siguiente (excursión hacia el otro lado, ticks) — propuesto por Nico;
   - excursión máxima, excursión / ancho, separación media en velas, picos por cada 100 velas;
   - volumen por vela en la zona / volumen normal de la sesión; hora del día (ET).
3. **Etiqueta:** positivo si empareja 1 a 1 con un rango de Nico del mismo tipo (IoU ≥ 0,3); negativo si cae dentro de la
   ventana supuesta revisada y no empareja (**supuesto declarado:** Nico no marcó las zonas «grises», así que parte de los
   negativos pueden ser positivos no marcados; la precisión está subestimada).
4. **Clasificador:** árbol de decisión chico (interpretable) y gradient boosting, con **validación entre sesiones**
   (entrena en una, prueba en la otra). Umbral elegido en la sesión de entrenamiento.
5. Salida: métricas por sesión de prueba, importancia de rasgos, reglas del árbol, y las zonas del mes que el mejor modelo
   acepta → `bundles/peaks_det/<asset>.json` (reemplaza a la v0; la capa del visor es la misma).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import peaks_learn as P  # noqa: E402

VIEW = P.VIEW
CAND = dict(W=(100, 150, 250), tau=(2, 4), nmin=(4, 6, 8), w=(1, 2), gap=20, dmin=10, dedupe_iou=0.8)   # unión de configuraciones
FEATS = ["toques", "dur_velas", "dur_seg", "ancho_t", "dist_media_picos_t", "recorrido_medio_t", "recorrido_max_t",
         "recorrido_sobre_ancho", "sep_media_velas", "picos_x100", "vol_rel", "hora_et"]


def load(asset):
    lab = json.loads((VIEW / "labels" / f"{asset}.json").read_text(encoding="utf-8"))
    b = json.loads((VIEW / "bundles" / f"{asset}.json").read_text(encoding="utf-8"))
    tick = float(b["meta"]["tick_size"])
    c = b["bar_series"][next(iter(b["bar_series"]))]["candles"]
    cd = dict(t=np.array([x["time"] for x in c], float), h=np.array([x["high"] for x in c]), l=np.array([x["low"] for x in c]),
              v=np.array([x.get("volume", 0) for x in c], float))
    return lab, cd, tick


def ranges_with_kind(lab):
    R = []
    for r in lab["ranges"]:
        if "i0" not in r:
            continue
        k = [z[0]["kind"] for z in lab["zigzags"] if z and r["i0"] - 3 <= z[0]["i"] <= r["i1"] + 3 and r["i0"] - 3 <= z[-1]["i"] <= r["i1"] + 3]
        if k:
            R.append(dict(r, kind=k[0]))
    return R


def features(z, cd, tick, vnorm):
    i0, i1, H = z["i0"], z["i1"], z["kind"] == "H"
    x = cd["h"] if H else -cd["l"]
    band_lo = (z["p1"] if H else -z["p0"]) - (z["p1"] - z["p0"]) - 1e-9     # banda en el espacio «techo»
    top = z["p1"] if H else -z["p0"]
    piv = [q for q in range(max(i0, 1), min(i1, len(x) - 2) + 1) if x[q] >= x[q - 1] and x[q] >= x[q + 1] and x[q] >= band_lo]
    if len(piv) < 2:
        piv = [i0, i1]
    pr = x[piv]
    exc = []
    for a, b in zip(piv[:-1], piv[1:]):
        lo = (cd["l"][a:b + 1].min() if H else -cd["h"][a:b + 1].max())       # recorrido hacia el otro lado entre picos
        exc.append((min(x[a], x[b]) - lo) / tick)
    width = max((top - band_lo) / tick, 1)
    dur = max(i1 - i0, 1)
    hour = pd.Timestamp(cd["t"][i1], unit="s", tz="UTC").tz_convert("America/New_York").hour
    return dict(toques=len(piv), dur_velas=dur, dur_seg=cd["t"][i1] - cd["t"][i0], ancho_t=width,
                dist_media_picos_t=float(np.mean(np.abs(np.diff(pr))) / tick), recorrido_medio_t=float(np.mean(exc)),
                recorrido_max_t=float(np.max(exc)), recorrido_sobre_ancho=float(np.mean(exc) / width),
                sep_media_velas=float(np.mean(np.diff(piv))), picos_x100=100 * len(piv) / dur,
                vol_rel=float(cd["v"][i0:i1 + 1].mean() / max(vnorm[i1], 1)), hora_et=hour)


def main(argv=None):
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.tree import DecisionTreeClassifier, export_text
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", required=True); a = ap.parse_args(argv)
    lab, cd, tick = load(a.asset)
    R = ranges_with_kind(lab)
    gaps = np.flatnonzero(np.diff(cd["t"]) > 1800) + 1
    so = np.searchsorted(gaps, np.arange(len(cd["t"])), side="right")
    vnorm = pd.Series(cd["v"]).rolling(2000, min_periods=1).mean().to_numpy()
    import itertools
    allz = []
    for W, tau, nmin, w in itertools.product(CAND["W"], CAND["tau"], CAND["nmin"], CAND["w"]):
        for z in P.merge(P.zones(cd, tick, W, tau, nmin, w), CAND["gap"], CAND["dmin"]):
            z.update(cfg_W=W, cfg_tau=tau, cfg_nmin=nmin, cfg_w=w); allz.append(z)
    allz.sort(key=lambda z: (z["kind"], z["i0"], -(z["i1"] - z["i0"])))
    Z = []                                         # sin duplicados: misma zona (mismo tipo, IoU >= 0,8) una sola vez
    last = {"H": [], "L": []}
    for z in allz:
        near = [y for y in last[z["kind"]] if y["i1"] >= z["i0"] - 1]
        if any(P.iou(z["i0"], z["i1"], y["i0"], y["i1"]) >= CAND["dedupe_iou"] for y in near):
            continue
        Z.append(z); last[z["kind"]] = near + [z]
    print("candidatos totales", len(Z))
    for z in Z:
        z.update(features(z, cd, tick, vnorm)); z["ses"] = int(so[z["i0"]])
    S = sorted({int(so[r["i0"]]) for r in R})
    wins = {}
    for s in S:
        rs = [r for r in R if so[r["i0"]] == s]
        t0, t1 = cd["t"][min(r["i0"] for r in rs)] - 1800, cd["t"][max(r["i1"] for r in rs)] + 600
        wins[s] = (int(np.searchsorted(cd["t"], t0)), int(np.searchsorted(cd["t"], t1)))
    # etiquetas de candidatos (1 a 1, mismo tipo, IoU >= 0,3) dentro de las ventanas
    rows = []
    for s in S:
        a0, a1 = wins[s]
        Zs = [z for z in Z if z["ses"] == s and P.overlap(z["i0"], z["i1"], a0, a1) > 0]
        Rs = [r for r in R if so[r["i0"]] == s]
        pairs = sorted(((P.iou(z["i0"], z["i1"], r["i0"], r["i1"]), zi, ri) for zi, z in enumerate(Zs) for ri, r in enumerate(Rs) if z["kind"] == r["kind"]), reverse=True)
        uz, ur = set(), set()
        for v, zi, ri in pairs:
            if v >= 0.3 and zi not in uz and ri not in ur:
                uz.add(zi); ur.add(ri)
        for zi, z in enumerate(Zs):
            touches = any(z["kind"] == r["kind"] and P.overlap(z["i0"], z["i1"], r["i0"], r["i1"]) > 0 for r in Rs)
            if zi in uz:
                rows.append(dict(z, y=1, n_rangos=len(Rs)))
            elif not touches:                          # negativo sólo si no toca ninguna marca del mismo tipo
                rows.append(dict(z, y=0, n_rangos=len(Rs)))
            # fragmentos de una marca (la misma acumulación con otros bordes): ignorados, no son negativos
    D = pd.DataFrame(rows)
    D["es_H"] = (D.kind == "H").astype(int)
    X = FEATS + ["es_H"]
    cobertura_candidatos = {s: float(D[(D.ses == s)].y.sum() / D[(D.ses == s)].n_rangos.iloc[0]) for s in S}
    print("candidatos en ventanas", len(D), "positivos", int(D.y.sum()), "cobertura máxima de los candidatos", cobertura_candidatos)
    results = {}
    for name, mk in (("arbol", lambda: DecisionTreeClassifier(max_depth=3, min_samples_leaf=4, class_weight="balanced", random_state=0)),
                     ("gboost", lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, class_weight="balanced", random_state=0))):
        per = []
        for te in S:
            tr = D[D.ses != te]; ts = D[D.ses == te]
            if tr.y.sum() < 3 or ts.y.sum() < 1:
                continue
            m = mk().fit(tr[X], tr.y)
            ptr = m.predict_proba(tr[X])[:, 1]
            best_thr, best_f = 0.5, -1
            for thr in np.linspace(0.05, 0.95, 19):                         # umbral elegido en ENTRENAMIENTO
                pred = ptr >= thr
                tp = int((pred & (tr.y == 1)).sum()); fp = int((pred & (tr.y == 0)).sum())
                rec = tp / max(tr.groupby("ses").n_rangos.first().sum(), 1); prec = tp / max(tp + fp, 1)
                f = 2 * prec * rec / max(prec + rec, 1e-9)
                if f > best_f:
                    best_f, best_thr = f, thr
            pt = m.predict_proba(ts[X])[:, 1] >= best_thr
            tp = int((pt & (ts.y == 1)).sum()); fp = int((pt & (ts.y == 0)).sum())
            rec = tp / max(int(ts.n_rangos.iloc[0]), 1); prec = tp / max(tp + fp, 1)
            per.append(dict(prueba=int(te), umbral=round(float(best_thr), 2), cobertura=round(rec, 3), precision=round(prec, 3),
                            f1=round(2 * prec * rec / max(prec + rec, 1e-9), 3), zonas_aceptadas=int(pt.sum()), rangos=int(ts.n_rangos.iloc[0])))
        results[name] = per
        print(name, per)
    # modelo final (todas las sesiones) con el de mejor F1 medio fuera de muestra
    best = max(results, key=lambda k: np.mean([p["f1"] for p in results[k]]) if results[k] else -1)
    mk = {"arbol": lambda: DecisionTreeClassifier(max_depth=3, min_samples_leaf=4, class_weight="balanced", random_state=0),
          "gboost": lambda: HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, class_weight="balanced", random_state=0)}[best]
    m = mk().fit(D[X], D.y)
    thr = float(np.median([p["umbral"] for p in results[best]]))
    tree = DecisionTreeClassifier(max_depth=3, min_samples_leaf=4, class_weight="balanced", random_state=0).fit(D[X], D.y)
    reglas = export_text(tree, feature_names=X)
    imp = dict(sorted(zip(X, tree.feature_importances_.round(3).tolist()), key=lambda kv: -kv[1]))
    A = pd.DataFrame(Z); A["es_H"] = (A.kind == "H").astype(int)
    A["p"] = m.predict_proba(A[X])[:, 1]
    acc = A[A.p >= thr]
    days = len(set((cd["t"] // 86400).astype(int)))
    pos_stats = D[D.y == 1][FEATS].median().round(2).to_dict(); neg_stats = D[D.y == 0][FEATS].median().round(2).to_dict()
    out = dict(schema="EDGELAB_PEAKS_DET_V1", asset=a.asset, modelo=best, umbral=thr, validacion_entre_sesiones=results,
               candidatos=CAND, cobertura_maxima_candidatos=cobertura_candidatos, importancia=imp, reglas_arbol=reglas,
               mediana_positivos=pos_stats, mediana_negativos=neg_stats,
               parametros=dict(cobertura=float(np.mean([p["cobertura"] for p in results[best]])), precision=float(np.mean([p["precision"] for p in results[best]]))),
               zonas=[{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in z.items() if k in ("kind", "i0", "i1", "t0", "t1", "p0", "p1", "toques", "p")}
                      for z in acc.to_dict("records")],
               zonas_por_dia=round(len(acc) / max(days, 1), 1),
               supuesto="negativos = candidatos no marcados dentro de la ventana de cada sesión; Nico dejó zonas grises sin marcar, así que la precisión está subestimada")
    for z in out["zonas"]:
        z["toques"] = int(z["toques"]); z["i0"] = int(z["i0"]); z["i1"] = int(z["i1"])
    p = VIEW / "bundles" / "peaks_det" / f"{a.asset}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), default=float), encoding="utf-8")
    print("mejor", best, "umbral", thr, "zonas/día", out["zonas_por_dia"])
    print("importancia", imp); print(reglas)
    print("medianas positivos", pos_stats); print("medianas negativos", neg_stats)


if __name__ == "__main__":
    main()
