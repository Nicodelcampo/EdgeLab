#!/usr/bin/env python3
"""Aplica la escalera del embudo (edgelab/funnel/escalera.py) a los dos candidatos reales del sprint 20-22/10, con costos canónicos.

  1. LUX-IMB, regla del visor (fade de impulsos con OG/VI al inicio), versión realista congelada para holdout, NQ.
  2. ORB0100 1,5R / rango 01:00-01:15 / a favor del VWAP, NQ (descubrimiento jul-mar, réplica pre-registrada abr-sep).

Los simuladores son los de las campañas originales, sin cambios; sólo se reconstruye el bruto por operación y se cobra la fricción
canónica (edgelab/costos.py). Primero se verifica que se reproduce lo publicado (n y puntos); si no, se aborta.
No abre datos nuevos: el holdout de LUX-IMB es la MISMA mirada exploratoria ya consumida (2026-10-21), releída con el monitor
secuencial, sin decisión de diseño nueva.

  python tools/escalera_candidatos_20261022.py <bundles_full_dir> <out.json>
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO)); LUX = REPO / "tools" / "luximb_parity"; sys.path.insert(0, str(LUX))
sys.path.insert(0, str(REPO / "tools" / "orb0100"))
from edgelab import costos  # noqa: E402
from edgelab.funnel import escalera as E  # noqa: E402
from edgelab.funnel.secuencial import MonitorCandidato  # noqa: E402
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402

TICK = 0.25; FRIC = costos.friccion_rt_puntos("NQ"); FRIC_ADV = costos.friccion_rt_puntos("NQ", "adverso")
BUN = REPO / "viewer/nt8_bridge/bundles"
PUBLICADO_LUX = {"09-25": (20, -127.8), "12-25": (99, 370.0), "03-26": (100, 573.9), "06-26": (130, 808.8), "09-26": (150, 846.1), "12-26": (1, -12.1)}


def lux_trades(bundle: Path, scratch: Path):
    from luximb_m11 import sim
    from luximb_outcomes import GAP_S, TOPE_MIN
    ip = scratch / ("imp_" + bundle.name)
    if not ip.exists():
        subprocess.run([sys.executable, "-X", "utf8", str(LUX / "luximb_impulsos.py"), str(bundle), str(ip), "--modo", "inicio", "--p-rango", "60",
                        "--min-ini", "3", "--share-ini", "0.5", "--rango-min-abs", "60"], check=True, cwd=REPO, capture_output=True)
    B = json.load(open(bundle, encoding="utf-8")); I = json.load(open(ip, encoding="utf-8"))
    cl = np.array([x["close"] for x in B["bar_series"]["time_1m"]["candles"]]); T = B["bar_series"]["tick_25"]["candles"]
    t = np.array([x["time"] for x in T]); h = np.array([x["high"] for x in T]); l = np.array([x["low"] for x in T]); c = np.array([x["close"] for x in T]); del B, T
    out = []
    for ev in I["impulsos"]:
        s = 1 if ev["dir"] == "up" else -1; A = ev["p0"]; E_ = cl[ev["ic"]] - s * TICK; D = s * (E_ - A)
        if D <= 0: continue
        i = int(np.searchsorted(t, ev["tc"], "left")); b = i
        while b < len(t) and t[b] <= ev["tc"] + TOPE_MIN * 60 and (b == i or t[b] - t[b - 1] <= GAP_S): b += 1
        ex, why = sim(s, E_, E_ - s * 1.0 * D, E_ + s * 0.2 * D, None, h[i:b], l[i:b], c[i:b], TICK)
        pts_pub = -s * (ex - E_) - 0.225                                      # lo que publicó el tablero realista
        bruto = pts_pub + 0.225 + TICK + (TICK if why != "TP" else 0.0)      # sin comisión ni los ticks de deslizamiento ya cobrados
        out.append(dict(ts=int(ev["tc"]), sesion=int((ev["tc"] + 6 * 3600) // 86400), riesgo=0.2 * D, pts_pub=pts_pub, bruto=bruto, why=why))
    return out


def a_r(ops, fric):
    return np.array([(o["bruto"] - fric) / o["riesgo"] for o in ops])


def lux(scratch: Path):
    srcs = {"09-25": BUN / "NQ_09-25_M1_LUXIMB.json", "12-25": BUN / "NQ_12-25_M1_LUXIMB.json", "03-26": BUN / "NQ_03-26_M1_LUXIMB.json",
            "06-26": scratch / "NQ_06-26_M1_LUXIMB.json", "09-26": BUN / "NQ_09-26_M1_LUXIMB.json", "12-26": scratch / "NQ_12-26_M1_LUXIMB.json"}
    per, todas = {}, []
    for c, p in srcs.items():
        ops = lux_trades(p, scratch); n, pts = len(ops), round(sum(o["pts_pub"] for o in ops), 1)
        per[c] = dict(n=n, pts_publicados=pts, coincide=(n, pts) == PUBLICADO_LUX[c]); [o.update(periodo=c) for o in ops]; todas += ops
        print("LUX", c, per[c], flush=True)
    if not all(v["coincide"] for v in per.values()):
        raise SystemExit("no se reproduce el tablero publicado: abortar (integridad antes que interpretación)")
    hold = lux_trades(BUN / "NQ_12-26_HOLDOUT_M1_LUXIMB.json", scratch); hold = [o for o in hold if o["ts"] >= 1790812800]   # >= 2026-10-01
    x = a_r(todas, FRIC); xa = a_r(todas, FRIC_ADV); ses = [o["sesion"] for o in todas]
    d = E.resumen_sesiones(x, ses)
    g = TrialRegistry(REPO / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl")
    fam = sum(r["n_trials"] for r in g._rows() if r["family_id"] in ("LUXIMB_FADE_VISOR",))
    prog = sum(r["n_trials"] for r in g._rows() if str(r["family_id"]).startswith("LUXIMB"))
    eco = E.economia(x, xa, ses, periodos=[o["periodo"] for o in todas])
    v = E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=fam, efecto_util=0.0, economico=eco)
    v_prog = E.evaluar(descubrimiento=d, nominada=False, n_pruebas_familia=prog, efecto_util=0.0, economico=eco)
    m = MonitorCandidato(piso=-2.0, techo=5.0, mu_util=max(0.5 * float(np.mean(x)), 0.01))
    st = m.agregar(a_r(hold, FRIC).tolist()) if hold else None
    return dict(regla="LUX-IMB fade, TP 1,0·D / SL 0,2·D, entrada cierre -1 tick, tope 240 min (congelada, sha256 3c44bc32...)",
                reproduccion=per, unidades="R (riesgo = 0,2·D) neto de fricción canónica NQ base %.3f pts; adverso %.3f" % (FRIC, FRIC_ADV),
                friccion_que_uso_la_campania_pts=round(0.225 + 2 * TICK, 3), friccion_canonica_pts=round(FRIC, 3),
                media_pts_publicada=float(np.mean([o["pts_pub"] for o in todas])), media_pts_canonica=float(np.mean([o["bruto"] - FRIC for o in todas])),
                n_pruebas_familia=fam, n_pruebas_programa_luximb=prog,
                nota_muestra=("los 6 períodos pre-holdout se miraron en el tablero ANTES de congelar la regla: todo es descubrimiento; "
                              "no hay réplica limpia anterior al holdout"),
                veredicto_familia=v.to_dict(), veredicto_programa=v_prog.to_dict(), holdout_secuencial=st, holdout_n=len(hold))


def orb():
    import pandas as pd
    import orb0100_v2 as V
    import orb0100_replica as RP
    res = {}
    for nombre, d in (("descubrimiento", V.cargar("NQ")), ("replica", RP.cargar_rep())):
        ops = []
        for s in V.senales(d, 100, 115, 1600):
            if not ((s["c"] > s["vwap"]) if s["dir"] > 0 else (s["c"] < s["vwap"])): continue
            r = V.operar(d, s, 1.5, 0.25, 0.62)
            if r:
                pts, R, why = r; riesgo = pts / R if R else np.nan
                bruto = pts + 0.62 + TICK + (TICK if why != "TP" else 0.0)
                ops.append(dict(fecha=str(s["fecha"]), pts_pub=pts, bruto=bruto, riesgo=riesgo, why=why))
        res[nombre] = ops; print("ORB", nombre, len(ops), round(float(np.mean([o["pts_pub"] for o in ops])), 3), flush=True); del d
    pub = json.load(open(REPO / "docs/research/orb0100_20261021/RESULTADOS_REPLICACION_NQ.json", encoding="utf-8"))["MNQ"]
    rep_ok = len(res["replica"]) == pub["n"] and round(float(np.mean([o["pts_pub"] for o in res["replica"]])), 3) == pub["pts_op"]
    if not rep_ok: raise SystemExit("ORB: no se reproduce la réplica publicada")
    xs = {k: np.array([(o["bruto"] - FRIC) for o in v]) for k, v in res.items()}
    d = E.resumen_sesiones(xs["descubrimiento"], [o["fecha"] for o in res["descubrimiento"]])
    r = E.resumen_sesiones(xs["replica"], [o["fecha"] for o in res["replica"]])
    g = TrialRegistry(REPO / "docs/research/TRIAL_REGISTRY_GLOBAL.jsonl")
    fam = sum(x["n_trials"] for x in g._rows() if x["family_id"] in ("ORB0100", "ORB_HORARIOS"))
    xa_rep = np.array([(o["bruto"] - FRIC_ADV) for o in res["replica"]])
    eco = E.economia(xs["replica"], xa_rep, [o["fecha"] for o in res["replica"]], periodos=[o["fecha"][:7] for o in res["replica"]])
    L = E.LordPP(); alfa = L.nivel()
    v = E.evaluar(descubrimiento=d, nominada=True, n_pruebas_familia=fam, replica=r, alfa_replica=alfa, economico=eco, n_esperado_holdout=45)
    return dict(regla="ORB0100 01:00-01:15 ET, 1a vela 5m fuera, a favor del VWAP, TP 1,5R, cierre 16:00, NQ", reproduccion_replica=rep_ok,
                unidades="puntos NQ netos de fricción canónica base %.3f pts" % FRIC, friccion_que_uso_la_campania_pts=round(0.62 + 2 * TICK, 3),
                n_pruebas_familia=fam, nominada_supuesto="sí (se trata como nominada: fue la celda de partida elegida antes del barrido)",
                alfa_replica_lordpp=alfa, veredicto=v.to_dict())


def main():
    scratch, out = Path(sys.argv[1]), Path(sys.argv[2]); res = dict(lux_imb=lux(scratch), orb0100=orb(),
                                                                   costos=costos.desglose("NQ"), escalera="edgelab/funnel/escalera.py")
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    for k in ("lux_imb", "orb0100"):
        v = res[k].get("veredicto_familia", res[k].get("veredicto")); print(k, v["estado"], v["motivos"], v["siguiente_paso"])
    print("holdout LUX", res["lux_imb"]["holdout_secuencial"])


if __name__ == "__main__":
    main()
