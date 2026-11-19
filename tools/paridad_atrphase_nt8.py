#!/usr/bin/env python3
"""Paridad del algoritmo de nt8/strategies/EdgeLabAtrPhaseStop.cs contra el simulador de EdgeLab (run_r): reimplementación línea a línea de la
lógica del C# (velas de 10 min armadas como NT8 desde el M1, decisiones al cierre de 10 min, llenado en la apertura del minuto siguiente,
reversa en el minuto siguiente a la salida) y comparación de entradas con docs/research/regimen_forward_20261119/R_REFERENCIA_PARIDAD.csv.
No reemplaza la paridad dentro de NT8 (compilación, plantilla de sesión, eventos): verifica el algoritmo. Target-free respecto del P&L.

  python tools/paridad_atrphase_nt8.py     # → docs/research/regimen_forward_20261119/PARIDAD_ALGORITMO.json
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/regimen_forward_20261119"
VEND = {20220803, 20220830, 20230405, 20240704, 20241224, 20250120, 20250703, 20250829}


def senales_cs(D, usar_vendedor=True, tick=0.25):
    """D: M1 de NQ con índice = APERTURA del minuto en hora de NY (m1_largo.cargar). Devuelve entradas (minuto de llenado ET, lado)."""
    b = D.copy(); b["fin"] = b.index + pd.Timedelta(minutes=1)                        # NT8 sella la vela con su cierre
    clave = (b.index.floor("10min"))                                                    # vela de 10 min = minutos que abren en [hh:m0, hh:m0+10)
    g = b.groupby(clave); B = pd.DataFrame(dict(o=g.o.first(), h=g.h.max(), l=g.l.min(), c=g.c.last(), v=g.v.sum()))
    B["cierre"] = B.index + pd.Timedelta(minutes=10)
    st = dict(pc=False, oscr=False, atrr=False, emar=False, trs=0.0, trn=0, prev=0.0, osc=0.0, atr=0.0, ema=0.0, sh=0, vd=None, vv=0.0, vp=0.0)
    pos = 0; ent = []; pend_rev = 0; acciones = []                                      # acciones: (minuto ET del cierre de 10 min, 'E'/'X', lado)
    utc = B.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").tz_convert("UTC")
    for k, (t0, r) in enumerate(B.iterrows()):
        if k < 1: continue
        fecha = t0.year * 10000 + t0.month * 100 + t0.day
        cierre = r.cierre; cmin = cierre.hour * 60 + cierre.minute
        if usar_vendedor and fecha in VEND:
            st["sh"] = 0; acciones.append((cierre, "X", 0)); continue
        u = utc[k]
        if u is not pd.NaT and u.hour == 0 and u.minute == 0 and st["pc"] and abs(r.o - st["prev"]) > 400 * tick:
            hab = st["sh"] != 0; st.update(pc=False, oscr=False, atrr=False, emar=False, trs=0.0, trn=0, prev=0.0, osc=0.0, atr=0.0, ema=0.0, sh=0, vd=None, vv=0.0, vp=0.0)
            if hab: acciones.append((cierre, "X", 0))
        po, pr = st["osc"], st["oscr"]
        a = 2 / 22.0; st["ema"] = r.c if not st["emar"] else a * r.c + (1 - a) * st["ema"]; st["emar"] = True
        tr = (r.h - r.l) if not st["pc"] else max(r.h - r.l, abs(r.h - st["prev"]), abs(r.l - st["prev"])); st["prev"] = r.c; st["pc"] = True
        if not st["atrr"]:
            st["trn"] += 1; st["trs"] += tr
            if st["trn"] == 14: st["atr"] = st["trs"] / 14; st["atrr"] = True
        else: st["atr"] = (13 * st["atr"] + tr) / 14
        ok = st["atrr"] and st["atr"] > 0
        if ok:
            raw = 100 * (r.c - st["ema"]) / (3 * st["atr"]); st["osc"] = raw if not st["oscr"] else 0.5 * raw + 0.5 * st["osc"]; st["oscr"] = True
        vwok = False; amin = t0.hour * 60 + t0.minute
        if 570 <= amin < 960:
            if st["vd"] != t0.date(): st.update(vd=t0.date(), vv=0.0, vp=0.0)
            st["vp"] += (r.h + r.l + r.c) / 3 * r.v; st["vv"] += r.v
            if st["vv"] > 0 and st["atrr"]: vwok = abs(r.c - st["vp"] / st["vv"]) < 2.5 * st["atr"]
        if cmin == 960: st["sh"] = 0; acciones.append((cierre, "X", 0)); continue
        if not pr or not ok: continue
        al = po <= 100 and st["osc"] > 100; ba = po >= -100 and st["osc"] < -100
        if not al and not ba: continue
        nv = 1 if al else -1
        if st["sh"] == nv: continue
        env = 570 <= cmin < 660
        if st["sh"] == 0:
            if not env: continue
            st["sh"] = nv
            if vwok: acciones.append((cierre, "E", nv))
            continue
        if not env: st["sh"] = 0; acciones.append((cierre, "X", 0)); continue
        st["sh"] = nv; acciones.append((cierre, "R", nv if vwok else 0))
    # ejecución: E entra si está plano (llena en la apertura del minuto del cierre de 10 min); X sale; R sale y, si lado ≠ 0, entra un minuto después
    for cierre, tipo, lado in acciones:
        if tipo == "E" and pos == 0: pos = lado; ent.append((cierre, lado))
        elif tipo == "X": pos = 0
        elif tipo == "R":
            if pos != 0:
                pos = 0
                if lado != 0: pos = lado; ent.append((cierre + pd.Timedelta(minutes=1), lado))
            elif lado != 0: pos = lado; ent.append((cierre, lado))
    return pd.DataFrame(ent, columns=["entrada", "side"])


def main():
    from datos import ruta
    from m1_largo import cargar
    ref = pd.read_csv(OUT / "R_REFERENCIA_PARIDAD.csv")
    D = cargar("NQ", ruta("M1NT8")); D = D[(D.index >= "2023-09-01") & (D.index < "2025-08-01")]
    E = senales_cs(D); E = E[(E.entrada >= "2024-01-01") & (E.entrada < "2025-08-01")]
    E["entrada_et"] = (E.entrada + pd.Timedelta(minutes=1)).dt.strftime("%Y-%m-%d %H:%M")   # sello = CIERRE del minuto de llenado (NT8 y simulador)
    m = ref.merge(E[["entrada_et", "side"]], on=["entrada_et", "side"], how="outer", indicator=True)
    res = dict(referencia=int(len(ref)), algoritmo_cs=int(len(E)), coinciden=int((m._merge == "both").sum()),
               solo_referencia=m[m._merge == "left_only"].entrada_et.tolist(), solo_cs=m[m._merge == "right_only"].entrada_et.tolist())
    res["paridad"] = res["coinciden"] / max(res["referencia"], 1)
    (OUT / "PARIDAD_ALGORITMO.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
