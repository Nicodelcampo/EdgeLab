#!/usr/bin/env python3
"""AVZP2-RACIMO-GRILLA, enmienda 2: auditoría de O5 por volumen e intensidad previos
(manifiesto docs/research/AVZP2_RACIMO_GRILLA_MANIFIESTO_20261008.md, enmienda 2).

Uso: python tools/avzp2_racimo_grid_vol_stage2.py <dir_parquets> <dir_salida> [json_publicado]
1) Integridad: sin el control, O5 tiene que reproducir el JSON publicado. Si no, sale con error sin leer el control.
2) O5 con FE por decil de vol_occ, vol_100, dur_occ, dur_100; Holm sobre celdas evaluables; confirmación en lo que pase.
3) Descriptivo: diferencia real - pseudo en cada variable de actividad. Informativo: O1 con todos los controles."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avzp2_racimo_stage2 import beta, prep  # noqa: E402
from avzp2_racimo_grid_stage2 import CONF, MIN_RAC, holm  # noqa: E402

IN, OUT = Path(sys.argv[1]), Path(sys.argv[2])
PUB = Path(sys.argv[3]) if len(sys.argv) > 3 else None
VOL = ("voD", "v1D", "duD", "d1D")
ACT = ("vol_occ", "vol_100", "dur_occ", "dur_100")
TOL = 1e-9


def lectura(n_pasan, n_ev):
    """Umbrales fijados en la enmienda para 23 celdas; se escalan si cambiara el número de evaluables."""
    hi, lo = int(np.floor(18 / 23 * n_ev)), int(np.floor(5 / 23 * n_ev))
    return "robusta" if n_pasan >= hi else ("retractada" if n_pasan <= lo else "parcial")


def main():
    fs = sorted(glob.glob(str(IN / "**" / "*_avzp2racgrid.parquet"), recursive=True))
    t = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    assert all(c in t for c in ACT), "los parquets no traen las variables de actividad (kernels viejos)"
    D, C = t[~t.contract.isin(CONF)], t[t.contract.isin(CONF)]
    nreal = D[D.kind == "real"].groupby("cell").size()
    cells = sorted(t.cell.unique(), key=lambda c: tuple(int(x) for x in c.split("_")))
    ev = [c for c in cells if nreal.get(c, 0) >= MIN_RAC]
    P = {c: prep(D[D.cell == c]) for c in ev}
    base = {c: beta(P[c], P[c]["y_O5"].to_numpy(float)) for c in ev}
    out = {"procedencia": [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(IN / "**" / "procedencia.json"), recursive=True))],
           "contratos": sorted(t.contract.unique()), "evaluables": ev, "O5_sin_control": base}

    # 1) integridad: reproducir lo publicado antes de mirar el control
    if PUB is not None:
        pub = json.loads(PUB.read_text(encoding="utf-8"))
        dif = {c: abs(base[c]["beta"] - pub["O5"][c]["beta"]) for c in ev if c in pub["O5"]}
        out["reproduccion"] = dict(celdas_publicadas=len(pub["O5"]), celdas_comparadas=len(dif), max_dif_beta=max(dif.values()) if dif else None,
                                   mismas_evaluables=sorted(pub["evaluables"]) == sorted(ev), reproduce=bool(dif and max(dif.values()) <= TOL and sorted(pub["evaluables"]) == sorted(ev)))
        print("REPRODUCCION", json.dumps(out["reproduccion"]))
        if not out["reproduccion"]["reproduce"]:
            OUT.mkdir(parents=True, exist_ok=True)
            (OUT / "AVZP2_RACIMO_GRILLA_VOL_RESULTADOS.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
            print("NO REPRODUCE lo publicado: se frena acá, sin leer el control.")
            sys.exit(2)

    # 2) O5 con control de actividad
    ctrl = {c: beta(P[c], P[c]["y_O5"].to_numpy(float), extra=VOL) for c in ev}
    holm(ctrl)
    for c in ev:
        ctrl[c]["razon_sobre_sin_control"] = ctrl[c]["beta"] / base[c]["beta"] if base[c]["beta"] else np.nan
        ctrl[c]["pasa_desc"] = bool(ctrl[c]["beta"] < 0 and ctrl[c]["p_holm"] <= 0.05)
    pasan = [c for c in ev if ctrl[c]["pasa_desc"]]
    conf = {}
    for c in pasan:
        if (C.cell == c).any():
            cc = prep(C[C.cell == c])
            conf[c] = beta(cc, cc["y_O5"].to_numpy(float), extra=VOL)
    if conf:
        holm(conf)
        for c, v in conf.items():
            v["confirma"] = bool(v["beta"] < 0 and v["p_holm"] <= 0.05)
    sostienen = [c for c in pasan if conf.get(c, {}).get("confirma")]
    out.update(O5_con_control=ctrl, pasan_desc=pasan, confirmacion=conf, sostienen=sostienen,
               retractadas=[c for c in ev if c not in sostienen],
               lectura_global=dict(pasan_desc=len(pasan), evaluables=len(ev), veredicto_desc=lectura(len(pasan), len(ev)),
                                   sostienen_desc_y_conf=len(sostienen)))

    # 3) descriptivo: ¿los reales venían con más actividad que sus pseudo? (misma especificación base, y = variable)
    out["balance_actividad"] = {c: {a: {k: v for k, v in beta(P[c], P[c][a].to_numpy(float)).items() if k in ("beta", "se", "z", "media_real", "media_pseudo")}
                                    for a in ACT} for c in ev}
    # informativo: O1 con tendencia + momentum + actividad
    out["O1_informativo"] = {c: dict(enm1=beta(P[c], P[c]["y_O1"].to_numpy(float), extra=("trD", "moD")),
                                     enm1_mas_actividad=beta(P[c], P[c]["y_O1"].to_numpy(float), extra=("trD", "moD") + VOL)) for c in ev}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "AVZP2_RACIMO_GRILLA_VOL_RESULTADOS.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")

    print("celda        n   O5 base   O5 ctrl  razon  mde    pholm | conf ctrl pholm | dif real-pseudo: vol500 vol100 dur500 dur100 (z)")
    for c in ev:
        b, k, v = base[c], ctrl[c], conf.get(c)
        bal = out["balance_actividad"][c]
        print("%-10s %4d  %+.4f  %+.4f  %5.2f  %.3f  %.4f | %s | %s" % (
            c, nreal[c], b["beta"], k["beta"], k["razon_sobre_sin_control"], k["mde"], k["p_holm"],
            ("%+.4f %.4f %s" % (v["beta"], v["p_holm"], "SI" if v["confirma"] else "no")) if v else "     -          ",
            " ".join("%+.2f(%+.1f)" % (bal[a]["beta"], bal[a]["z"]) for a in ACT)))
    print("LECTURA", json.dumps(out["lectura_global"]))
    print("O1 informativo (celdas de ventana 1000):")
    for c in ev:
        if "_1000_" in c:
            o = out["O1_informativo"][c]
            print("  %-10s enm1 %+.3f (z %+.1f) | + actividad %+.3f (z %+.1f)" % (c, o["enm1"]["beta"], o["enm1"]["z"], o["enm1_mas_actividad"]["beta"], o["enm1_mas_actividad"]["z"]))


if __name__ == "__main__":
    main()
