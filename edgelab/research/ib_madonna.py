"""IB-MADONNA (2026-11-18): Initial Balance + «Madonna» (Drysdale) refinada y 10 variantes de lógica distinta.
Diseño: docs/research/ib_madonna_20261118/DISENO.md; pre-registro: docs/research/ib_madonna_20261118/PREREGISTRO.md.

Contrato de `edgelab/research/tablas.py`: una fila por evento (vela M1 de decisión `k`, lado, precios de objetivo y stop por variante).
Todo en hora de Nueva York sobre la sesión RTH (9:30–16:00). Velas de decisión de 5 minutos alineadas a las 9:30, construidas desde M1;
la decisión se toma al cierre de la vela de 5 min (k = su última vela M1) y la entrada es el primer tick de la vela M1 siguiente (motor).
Unidades relativas (K36): buffer, distancias y anchos en fracciones del IB o del rango diario; nunca puntos fijos.

Definiciones (columnas booleanas) — cada una UNA hipótesis:
  V0  Madonna: primer toque de un borde del IB entre 10:30 y 12:00 que cierra adentro (el lado que cierra afuera queda aceptado);
      venta en el máximo / compra en el mínimo; stop extremo + 0,05·IB; objetivo mitad del IB; objetivo/riesgo ≥ 1; una por día
  V1  V0 con apertura 9:30 dentro del rango RTH previo (día de balance)          V0N1  V0 con apertura afuera (complemento)
  V2  V0 con IB/rango RTH ≥ su mediana de las 120 sesiones previas (IB ancho)   V0N2  complemento
  V3  aceptación: dos cierres de 5 min seguidos afuera por ≥ 0,1·IB → a favor; stop mitad del IB; objetivo borde ± 1·IB
  V4  ruptura fallida: cierre de 5 min afuera por ≥ 0,05·IB y, en ≤ 30 min, cierre de vuelta adentro → fade a la mitad; stop extremo
      de afuera + 0,05·IB
  V5  V0 con objetivo en el VWAP RTH (sólo si está entre la entrada y el borde opuesto)
  V6  V0 sólo en el lado que va hacia el cierre RTH previo (gap)                 V0N6  complemento
  V7  V0 con volumen de la vela de toque ≥ 2× el volumen medio de 5 min de 10:30–12:00 en las 20 sesiones previas  V0N7  complemento
  V8  V0 con una marca de impulso LUX-IMB (D3_20, ≥ 1 zona en el 25 % inicial) hacia el borde en los 15 min previos
  V9  V0 sin «Open-Drive» en los primeros 30 min                                 V0N9  complemento (con Open-Drive)
  V10 doble prueba: primer toque cerró afuera, volvió adentro y una segunda prueba sin nuevo extremo cierra adentro → fade; stop
      primer extremo + 0,05·IB
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NOMBRE = "IB-MADONNA"
EJECUCIONES = [("PRECIOS", "obj_v0", "stop_v0"), ("PRECIOS", "obj_v3", "stop_v3"), ("PRECIOS", "obj_v4", "stop_v4"),
               ("PRECIOS", "obj_v5", "stop_v0"), ("PRECIOS", "obj_v10", "stop_v10")]
DEFINICIONES = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10"]
CONTROL = {"V1": "V0N1", "V2": "V0N2", "V6": "V0N6", "V7": "V0N7", "V9": "V0N9"}
IB_INI, IB_FIN, VENT_FIN, V4_ESPERA, RTH_FIN = 570, 630, 720, 30, 960            # minutos NY (apertura de la vela M1)
BUF, ACEPT, FALLA, VOL_CLIMAX, DRIVE, MED_IB_N, IMP_MIN = 0.05, 0.10, 0.05, 2.0, 0.10, 120, 15
DEPENDENCIAS_KERNEL = ("edgelab.research.luximb_grilla",)


def minuto_ny(t) -> np.ndarray:
    """Minuto del día en Nueva York de la APERTURA de cada vela M1 (`t` es el cierre del minuto en segundos UTC)."""
    ny = pd.to_datetime(np.asarray(t, np.int64) - 60, unit="s", utc=True).tz_convert("America/New_York")
    return (ny.hour * 60 + ny.minute).to_numpy()


def _marcas_lux(ctx) -> pd.DataFrame:
    """Marcas de impulso LUX-IMB causales (k, d) con amplitud ≥ p60 causal y ≥ 1 zona en el 25 % inicial (como LUXIMB-A5, z1)."""
    from edgelab.research import luximb_grilla as LG
    o, h, l, c, t, seg = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "t", "seg")); out = []
    for sg in pd.unique(seg):
        idx = np.flatnonzero(seg == sg); a = idx[0]; b = idx[-1] + 1
        M = LG.marcas_segmento(t[a:b], o[a:b], h[a:b], l[a:b], c[a:b], float(ctx["tick"]), amp=((60.0, 0.0),), zon=((0.25, 1),))
        if len(M): out.append(pd.DataFrame(dict(k=M.k.to_numpy(np.int64) + a, d=M.d.to_numpy(np.int64))))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["k", "d"])


def eventos(ctx) -> pd.DataFrame:
    o, h, l, c, v, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "v", "ses"))
    o, h, l, c, v = (x.astype(float) for x in (o, h, l, c, v)); mo = minuto_ny(ctx["t"])
    lux = _marcas_lux(ctx); lux_k = lux.k.to_numpy(np.int64); lux_d = lux.d.to_numpy(np.int64)
    filas = []; prev = None; hist_ib = []; hist_vol = []
    for s in np.unique(ses):
        m = np.flatnonzero((ses == s) & (mo >= IB_INI) & (mo < RTH_FIN))
        if not len(m): continue
        mm = mo[m]; ib = m[mm < IB_FIN]
        rth_rango = h[m].max() - l[m].min(); prev_actual = dict(c=c[m[-1]], h=h[m].max(), l=l[m].min())
        if len(ib) < 50 or prev is None or not (mm >= IB_FIN).any():               # sólo lo conocido hasta la vela (sin exigir el futuro)
            prev = prev_actual; continue
        IBH, IBL = h[ib].max(), l[ib].min(); R = IBH - IBL; MID = (IBH + IBL) / 2
        if not R > 0:
            prev = prev_actual; continue
        apertura = o[ib[0]]
        # relación IB / rango RTH previo (causal: mediana de las MED_IB_N sesiones anteriores)
        rel = R / max(prev["h"] - prev["l"], 1e-9); med = np.median(hist_ib[-MED_IB_N:]) if len(hist_ib) >= 20 else np.nan
        hist_ib.append(rel)
        balance = prev["l"] <= apertura <= prev["h"]; ancho = rel >= med if med == med else None
        gap = np.sign(apertura - prev["c"])                                              # +1 gap arriba
        i30 = m[mm < IB_INI + 30]; H30, L30 = h[i30].max(), l[i30].min(); R30 = H30 - L30; O30, C30 = o[i30[0]], c[i30[-1]]
        drive = R30 > 0 and ((O30 - L30 <= DRIVE * R30 and H30 - C30 <= DRIVE * R30) or (H30 - O30 <= DRIVE * R30 and C30 - L30 <= DRIVE * R30))
        en_v = (mm >= IB_FIN) & (mm < VENT_FIN)
        vol5_ref = np.mean(hist_vol[-20:]) if len(hist_vol) >= 5 else np.nan                 # 5 min medios de 10:30–12:00, 20 sesiones previas
        vol5_hoy = v[m[en_v]].sum() / max(en_v.sum() / 5.0, 1.0)
        pv = np.cumsum(c[m] * v[m]); vv = np.cumsum(v[m])
        # velas de 5 min de 10:30 a 12:30 (la ventana de V0/V3/V10 termina a las 12:00; V4 puede volver hasta las 12:30)
        g5 = (mm - IB_INI) // 5; G = []
        for g in np.unique(g5[(mm >= IB_FIN) & (mm < VENT_FIN + V4_ESPERA)]):
            ii = np.flatnonzero(g5 == g); idx = m[ii]
            if mm[ii[-1]] != IB_INI + 5 * g + 4: continue                       # sólo velas de 5 min COMPLETAS (2026-11-18: con datos
                                                                                 # cortados se decidía con una vela a medio formar)
            G.append(dict(k=int(idx[-1]), H=h[idx].max(), L=l[idx].min(), C=c[idx[-1]], V=v[idx].sum(), fin=int(mm[ii[-1]]) + 1,
                          vw=pv[ii[-1]] / vv[ii[-1]] if vv[ii[-1]] > 0 else np.nan))
        en_vent = [x for x in G if x["fin"] <= VENT_FIN]
        # ----- V0 (y sus filtros) -----
        acept = {1: False, -1: False}; v0 = None
        for x in en_vent:
            for lado_borde, toca, adentro in ((1, x["H"] >= IBH, x["C"] < IBH), (-1, x["L"] <= IBL, x["C"] > IBL)):
                if v0 is not None or acept[lado_borde] or not toca: continue
                if not adentro: acept[lado_borde] = True; continue
                lado = -lado_borde; ext = x["H"] if lado_borde == 1 else x["L"]
                stop = ext + lado_borde * BUF * R; obj = MID; ent = x["C"]
                if lado * (obj - ent) >= lado * (ent - stop) and lado * (ent - stop) > 0: v0 = (x, lado, stop, obj, ext)
            if v0 is not None: break
        if v0 is not None:
            x, lado, stop, obj, ext = v0; k = x["k"]
            vw = x["vw"]; obj5 = vw if (vw == vw and lado * (vw - x["C"]) > 0 and lado * ((IBL if lado == -1 else IBH) - vw) > 0) else np.nan
            lux_ok = bool(np.any((lux_k <= k) & (lux_k >= k - IMP_MIN) & (lux_d == -lado)))
            f = dict(V1=balance, V2=bool(ancho) if ancho is not None else False, V6=(gap == 1 and lado == -1) or (gap == -1 and lado == 1),
                     V7=bool(vol5_ref == vol5_ref and x["V"] >= VOL_CLIMAX * vol5_ref), V9=not drive)
            fila = dict(k=k, lado=lado, ref=obj, ext=ext, rg=R, obj_v0=obj, stop_v0=stop, obj_v5=obj5, V0=True, V5=obj5 == obj5,
                        V8=lux_ok, V1=f["V1"], V0N1=not f["V1"], V2=f["V2"] and ancho is not None, V0N2=(ancho is not None) and not f["V2"],
                        V6=f["V6"], V0N6=not f["V6"], V7=f["V7"], V0N7=not f["V7"], V9=f["V9"], V0N9=not f["V9"])
            filas.append(fila)
        # ----- V3: aceptación (dos cierres de 5 min seguidos afuera por ≥ 0,1·IB) -----
        for a, b in zip(en_vent, en_vent[1:]):
            arriba = a["C"] >= IBH + ACEPT * R and b["C"] >= IBH + ACEPT * R; abajo = a["C"] <= IBL - ACEPT * R and b["C"] <= IBL - ACEPT * R
            if arriba or abajo:
                lado = 1 if arriba else -1
                filas.append(dict(k=b["k"], lado=lado, ref=(IBH + R) if arriba else (IBL - R), ext=b["C"], rg=R, obj_v3=(IBH + R) if arriba else (IBL - R),
                                  stop_v3=MID, V3=True)); break
        # ----- V4: ruptura fallida -----
        for i, a in enumerate(en_vent):
            fuera = 1 if a["C"] >= IBH + FALLA * R else (-1 if a["C"] <= IBL - FALLA * R else 0)
            if not fuera: continue
            ext = a["H"] if fuera == 1 else a["L"]
            for b in G[G.index(a) + 1:]:
                if b["fin"] > a["fin"] + V4_ESPERA: break
                ext = max(ext, b["H"]) if fuera == 1 else min(ext, b["L"])
                if (fuera == 1 and b["C"] < IBH) or (fuera == -1 and b["C"] > IBL):
                    lado = -fuera; stop = ext + fuera * BUF * R
                    if lado * (MID - b["C"]) > 0 and lado * (b["C"] - stop) > 0:
                        filas.append(dict(k=b["k"], lado=lado, ref=MID, ext=ext, rg=R, obj_v4=MID, stop_v4=stop, V4=True))
                    break
            break
        # ----- V10: doble prueba (primer toque aceptado afuera, vuelve, segunda prueba sin nuevo extremo cierra adentro) -----
        for lado_borde in (1, -1):
            borde = IBH if lado_borde == 1 else IBL; hecho = False; primero = None; volvio = False; ext = None
            for x in en_vent:
                toca = x["H"] >= borde if lado_borde == 1 else x["L"] <= borde
                adentro = x["C"] < borde if lado_borde == 1 else x["C"] > borde
                xe = x["H"] if lado_borde == 1 else x["L"]
                if primero is None:
                    if toca and adentro: break                                            # el primer toque fue Madonna: no aplica
                    if toca and not adentro: primero = x; ext = xe
                    continue
                if not volvio:
                    ext = max(ext, xe) if lado_borde == 1 else min(ext, xe)
                    if adentro: volvio = True
                    continue
                if toca and adentro and lado_borde * (xe - ext) <= 0:
                    lado = -lado_borde; stop = ext + lado_borde * BUF * R
                    if lado * (MID - x["C"]) > 0 and lado * (x["C"] - stop) > 0:
                        filas.append(dict(k=x["k"], lado=lado, ref=MID, ext=ext, rg=R, obj_v10=MID, stop_v10=stop, V10=True)); hecho = True
                    break
                if lado_borde * (xe - ext) > 0: break                                    # nuevo extremo: ya no es doble prueba
            if hecho: break
        hist_vol.append(vol5_hoy)                                                         # recién al terminar la sesión (causal)
        prev = prev_actual
    cols = ["k", "lado", "ref", "ext", "rg", "obj_v0", "stop_v0", "obj_v3", "stop_v3", "obj_v4", "stop_v4", "obj_v5", "obj_v10", "stop_v10"] + \
           DEFINICIONES + sorted(set(CONTROL.values()))
    E = pd.DataFrame(filas)
    for col in cols:
        if col not in E: E[col] = False if col in DEFINICIONES or col in CONTROL.values() else np.nan
    for col in DEFINICIONES + sorted(set(CONTROL.values())): E[col] = E[col].fillna(False).astype(bool)
    if not len(E): return pd.DataFrame(columns=cols)
    return E[cols].astype(dict(k=np.int64, lado=np.int64)).sort_values("k", kind="mergesort").reset_index(drop=True)
