#!/usr/bin/env python3
r"""Zonas escalonadas de ES (familias PLANAS y EMPINADAS) con su vela de DETECCIÓN en tiempo real.

    python tools/escalonadas_det.py --asset ES_03-26_202602_25T_HFT

Misma regla que `peaks_rule.series` (cada pico no supera al anterior, escalón ≤ max_step, retroceso ≥ min_pull, hueco
≤ max_gap), pero causal: se recorren los picos propios de cada serie en el orden en que se CONFIRMAN (pico q conocido
en q + w) y la zona se detecta en la primera confirmación en que el prefijo conocido —con la extensión hacia atrás, que
sólo usa velas anteriores— ya cumple todos los filtros de la familia. Una serie que nunca cumple no es zona.
Salida por zona: `det_i`, `det_t` (vela de cierre de la detección), `det_pico` (cuántos picos había), `det_precio`
(cierre de esa vela) y `det_nivel` (precio del último pico conocido). Sin resultados de trading.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
import peaks_rule as R  # noqa: E402

VIEW = REPO / "viewer" / "nt8_bridge"
TICK = 0.25
# parámetros ajustados a las marcas y juicios de Nico (29/09); ver docs/research/IDEA_ES_ESCALONADAS_ENTRADA_RETROCESO_20260929.md
FAMILIAS = {
    "planas": dict(sufijo="", nombre="ES escalonadas PLANAS v2", w=2, max_gap=15, max_step=2, min_pull=5, nmin=3,
                   dmax=35, total_min=0, step_min=0),
    "empinadas": dict(sufijo="__empinadas", nombre="ES escalonadas EMPINADAS v2", w=2, max_gap=15, max_step=3, min_pull=6,
                      nmin=3, dmax=35, total_min=5, step_min=3),
}


def pasa(pk, src, f):
    pr = src[pk]
    if pk[-1] - pk[0] > f["dmax"]:
        return False
    if abs(pr[-1] - pr[0]) / TICK < f["total_min"] - 1e-9:
        return False
    if len(pk) > 1 and np.abs(np.diff(pr)).max() / TICK < f["step_min"] - 1e-9:
        return False
    return True


def detectar(cd, f):
    Z = []
    for kind in (1, -1):
        rows, member = R.chains(cd["h"], cd["l"], cd["t"], TICK, f["w"], f["max_gap"], f["max_step"], f["min_pull"], f["nmin"], kind)
        src = cd["h"] if kind == 1 else cd["l"]
        xx = cd["h"] if kind == 1 else -cd["l"]
        piv = R.pivots(xx, f["w"])
        by = {}
        for q in np.flatnonzero(member >= 0):
            by.setdefault(int(member[q]), []).append(int(q))
        for zi, r in enumerate(rows):
            own = by.get(zi, [])
            det = None
            for k in range(f["nmin"], len(own) + 1):               # confirmación del k-ésimo pico propio, en own[k-1] + w
                pk = R.backfill(own[:k], xx, piv, cd["t"], TICK, f["max_gap"], f["max_step"])
                if pasa(pk, src, f):
                    det = (k, pk); break
            if det is None:
                continue
            k, pk_det = det
            di = min(own[k - 1] + f["w"], len(cd["t"]) - 1)
            full = R.backfill(own, xx, piv, cd["t"], TICK, f["max_gap"], f["max_step"])
            # dibujo: hasta el último pico mientras la zona siga cumpliendo el tope de duración
            full = [q for q in full if q - full[0] <= f["dmax"]] or pk_det
            pr = src[full]
            Z.append(dict(kind="H" if kind == 1 else "L", i0=int(full[0]), i1=int(full[-1]), t0=float(cd["t"][full[0]]),
                          t1=float(cd["t"][full[-1]]), p0=float(pr.min()), p1=float(pr.max()), toques=len(full),
                          picos=[[int(q), float(cd["t"][q]), float(src[q])] for q in full],
                          det_i=int(di), det_t=float(cd["t"][di]), det_pico=len(pk_det), det_precio=float(cd["c"][di]),
                          det_nivel=float(src[pk_det[-1]]), det_idx=int(full.index(pk_det[-1])) if pk_det[-1] in full else len(full) - 1, fin_serie_i=int(r[1])))
    return Z


TOQUE_TICKS = 1      # visual: la vela «toca» el nivel si llega a 1 tick de él (límite apenas antes del pico anterior)


def candidatas(cd, f, zonas):
    """Opción 3 (Nico, 29/09): con 2 picos propios confirmados la serie es CANDIDATA; nivel = último pico; ENTRADA = primera
    vela posterior que llega a TOQUE_TICKS del nivel antes de max_gap velas. Causal. No mide resultados."""
    C = []
    det_by = {(z["kind"], z["picos"][0][0]) for z in zonas}
    n = len(cd["t"])
    for kind in (1, -1):
        rows, member = R.chains(cd["h"], cd["l"], cd["t"], TICK, f["w"], f["max_gap"], f["max_step"], f["min_pull"], 2, kind)
        src = cd["h"] if kind == 1 else cd["l"]
        xx = cd["h"] if kind == 1 else -cd["l"]
        piv = R.pivots(xx, f["w"])
        by = {}
        for q in np.flatnonzero(member >= 0):
            by.setdefault(int(member[q]), []).append(int(q))
        for zi, r in enumerate(rows):
            own = by.get(zi, [])
            if len(own) < 2:
                continue
            ci = own[1] + f["w"]
            if ci >= n:
                continue
            pk = R.backfill(own[:2], xx, piv, cd["t"], TICK, f["max_gap"], f["max_step"])
            if pk[-1] - pk[0] > f["dmax"]:
                continue
            lvl = float(src[own[1]]); ent = None
            for j in range(ci + 1, min(own[1] + f["max_gap"], n - 1) + 1):
                if cd["t"][j] - cd["t"][j - 1] > 1800:
                    break
                if (kind == 1 and cd["h"][j] >= lvl - TOQUE_TICKS * TICK) or (kind == -1 and cd["l"][j] <= lvl + TOQUE_TICKS * TICK):
                    ent = j; break
            C.append(dict(kind="H" if kind == 1 else "L", cand_i=int(ci), cand_t=float(cd["t"][ci]), nivel=lvl,
                          picos=[[int(q), float(cd["t"][q]), float(src[q])] for q in pk],
                          entrada_i=None if ent is None else int(ent), entrada_t=None if ent is None else float(cd["t"][ent]),
                          se_confirmo=("H" if kind == 1 else "L", int(pk[0])) in det_by or ("H" if kind == 1 else "L", int(own[0])) in det_by))
    return C


CONF_TICKS = 2       # confirmación por precio (Nico, 29/09): < 2,5 ticks = distancia media de la detección por velas


def chains_px(h, l, t, w, max_gap, max_step, min_pull, nmin, kind, X):
    """Como peaks_rule.chains, pero el pico q se CONFIRMA en la primera vela j > q cuyo extremo opuesto se aleja X ticks
    de él sin que ninguna vela entre q y j lo supere (izquierda: w velas no mayores, igual que el pivote por velas).
    Devuelve series [(picos, confirmaciones, fin)] en orden causal de confirmación."""
    n = len(h); x = h if kind == 1 else -l; y = l if kind == 1 else -h
    ev = []
    for q in range(w, n - 1):
        if any(x[q] < x[q - o] for o in range(1, w + 1)):
            continue
        for j in range(q + 1, min(q + 60, n)):
            if t[j] - t[j - 1] > 1800 or x[j] > x[q] + 1e-9:
                break
            if (x[q] - y[j]) / TICK >= X - 1e-9:
                ev.append((j, q)); break
    ev.sort()
    out, cur, conf = [], [], []
    P = None
    def close(fin):
        if len(cur) >= nmin:
            out.append((list(cur), list(conf), fin))
    ei = 0
    for j in range(n):
        if cur and ((t[j] - t[j - 1] > 1800) or (x[j] > P + 1e-9 and j > cur[-1]) or (j - cur[-1] > max_gap)):
            close(j); cur.clear(); conf.clear(); P = None
        while ei < len(ev) and ev[ei][0] == j:
            q = ev[ei][1]; ei += 1
            if cur and q <= cur[-1]:
                continue
            if not cur:
                cur.append(q); conf.append(j); P = x[q]; continue
            mn = min(y[cur[-1] + 1:q]) if q > cur[-1] + 1 else None
            pull = (P - mn) / TICK if mn is not None else 0.0
            step = (P - x[q]) / TICK
            if x[q] <= P + 1e-9 and step <= max_step and pull >= min_pull:
                cur.append(q); conf.append(j); P = x[q]
    close(n - 1)
    return out


def detectar_px(cd, f, X=CONF_TICKS):
    Z = []
    for kind in (1, -1):
        src = cd["h"] if kind == 1 else cd["l"]; xx = cd["h"] if kind == 1 else -cd["l"]
        piv = R.pivots(xx, f["w"])
        for own, conf, fin in chains_px(cd["h"], cd["l"], cd["t"], f["w"], f["max_gap"], f["max_step"], f["min_pull"], f["nmin"], kind, X):
            det = None
            for k in range(f["nmin"], len(own) + 1):
                pk = R.backfill(own[:k], xx, piv, cd["t"], TICK, f["max_gap"], f["max_step"])
                if pasa(pk, src, f):
                    det = (k, pk); break
            if det is None:
                continue
            k, pk_det = det; di = conf[k - 1]
            trig = float(src[own[k - 1]] - (1 if kind == 1 else -1) * X * TICK)      # precio exacto del disparo
            full = R.backfill(own, xx, piv, cd["t"], TICK, f["max_gap"], f["max_step"])
            full = [q for q in full if q - full[0] <= f["dmax"]] or pk_det
            pr = src[full]
            Z.append(dict(kind="H" if kind == 1 else "L", i0=int(full[0]), i1=int(full[-1]), t0=float(cd["t"][full[0]]),
                          t1=float(cd["t"][full[-1]]), p0=float(pr.min()), p1=float(pr.max()), toques=len(full),
                          picos=[[int(q), float(cd["t"][q]), float(src[q])] for q in full],
                          det_i=int(di), det_t=float(cd["t"][di]), det_pico=len(pk_det), det_precio=trig,
                          det_nivel=float(src[pk_det[-1]]), det_idx=int(full.index(pk_det[-1])) if pk_det[-1] in full else len(full) - 1, fin_serie_i=int(fin), confirmacion=f"precio {X} ticks"))
    return Z


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--asset", required=True)
    ap.add_argument("--conf", default="velas", choices=["velas", "precio"], help="precio: confirmación a CONF_TICKS del pico")
    ap.add_argument("--escala", type=float, default=1.0, help="multiplica todo lo que está en ticks (transferencia a otro activo sin re-marcar)")
    ap.add_argument("--w", type=int, default=None, help="pivote de w velas (por defecto el de la familia, 2); sufijo __w<w>")
    ap.add_argument("--solo-planas", action="store_true")
    a = ap.parse_args()
    if a.solo_planas:
        FAMILIAS.pop("empinadas", None)
    if a.w:
        for f in FAMILIAS.values():
            f["w"] = a.w; f["sufijo"] = f["sufijo"] + f"__w{a.w}"
    global CONF_TICKS
    if a.escala != 1.0:
        CONF_TICKS = int(round(CONF_TICKS * a.escala))
        for f in FAMILIAS.values():
            for k in ("max_step", "min_pull", "total_min", "step_min"):
                f[k] = int(round(f[k] * a.escala))
            f["nombre"] = f["nombre"].replace("ES ", a.asset.split("_")[0] + " ") + f" (transferido de ES ×{a.escala:g}, sin marcas propias)"
    b = json.loads((VIEW / "bundles" / f"{a.asset}.json").read_text(encoding="utf-8"))
    c = b["bar_series"][next(iter(b["bar_series"]))]["candles"]; del b
    cd = {k: np.array([x[v] for x in c], float) for k, v in (("t", "time"), ("h", "high"), ("l", "low"), ("c", "close"))}; del c
    days = len(set((cd["t"] // 86400).astype(int)))
    for fam, f in FAMILIAS.items():
        Z = detectar_px(cd, f, CONF_TICKS) if a.conf == "precio" else detectar(cd, f)
        CA = candidatas(cd, f, Z) if a.conf == "velas" else []
        lag = [z["det_i"] - z["picos"][-1][0] for z in Z]
        out = dict(schema="EDGELAB_PEAKS_DET_V2_REGLA", asset=a.asset, variante=f["nombre"] + (f" · confirmación por precio ({CONF_TICKS} ticks)" if a.conf == "precio" else " · con vela de detección"),
                   parametros={k: v for k, v in f.items() if k not in ("sufijo", "nombre")}, causal=True, zonas=Z, candidatas=CA,
                   zonas_por_dia=round(len(Z) / max(days, 1), 1))
        suf = f["sufijo"] + ("__precio" if a.conf == "precio" else "")
        if a.conf == "precio" and not suf.startswith("__"):
            suf = "__precio"
        (VIEW / "bundles" / "peaks_det" / f"{a.asset}{suf}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(json.dumps(dict(familia=fam, candidatas=len(CA), con_entrada=sum(c["entrada_i"] is not None for c in CA), zonas=len(Z), por_dia=out["zonas_por_dia"],
                              det_pico={int(k): int(v) for k, v in zip(*np.unique([z["det_pico"] for z in Z], return_counts=True))} if Z else {},
                              velas_desde_det_hasta_ultimo_pico_mediana=float(np.median(lag)) if Z else None), default=int, ensure_ascii=False))


if __name__ == "__main__":
    main()
