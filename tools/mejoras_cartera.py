#!/usr/bin/env python3
"""Mejoras de la cartera (pre-registro docs/research/cartera_20261116/PREREGISTRO_MEJORAS.md).

  python tools/mejoras_cartera.py probar      # M1–M3 en G ∪ H (y por separado) -> MEJORAS.json
  python tools/mejoras_cartera.py v2          # cartera v2 (A1 + A2 + las M que pasan) vs v1: desarrollo, holdout y prop -> CARTERA_V2.json
Reusa clasificar/delta de tools/perdidas_concentradas.py, _usd_diario/MICRO de tools/cartera_nov_analisis.py y estimar_propfirm.sim.
"""
import datetime as dt
import json, sys
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from cartera_nov import DIR, universo  # noqa: E402
from cartera_nov_analisis import MICRO  # noqa: E402
from perdidas_concentradas import GENERADORAS, clasificar, delta, _bh  # noqa: E402

UMBRAL_FRICCION, NY = 0.08, ZoneInfo("America/New_York")
PESO = {"PREAPERTURA-NQ": 0.5}
USD_R = 200.0


def _min_ny(t):
    h = dt.datetime.fromtimestamp(t, NY); return h.hour * 60 + h.minute


def marcar(f):
    """Para cada operación: fricción en R (Rb − R), si M1 la saltea, si M2 la saltea."""
    for x in f:
        x["fricR"] = x["Rb"] - x["R"]; x["m1"] = x["fricR"] > UMBRAL_FRICCION; x["m2"] = bool(x["t"]) and 840 <= _min_ny(x["t"]) < 975
    return f


def _con_bajo(F, campo):
    return {c: [dict(x, bajo=x[campo]) for x in f] for c, f in F.items()}


def _conjuntos():
    U = {r["cid"]: r for r in universo()}; T = {}
    for c, r in U.items():
        f = clasificar(c, r["spec"])
        if f: T[c] = marcar(f)
    G = {c: [x for x in f if x["tramo"] in ("desc", "rep")] for c, f in T.items() if c in GENERADORAS}
    H = {c: [x for x in f if x["tramo"] == "hold"] for c, f in T.items()}
    return T, G, {c: f for c, f in H.items() if f}


def _serie_tam(F, modo, B=10000, seed=11):
    """Serie por sesión (USD) con riesgo fijo (R × 200) o contrato fijo (R × riesgo × micros fijos, escalado a 200 USD de riesgo medio)."""
    from edgelab import costos as C
    U = {r["cid"]: r for r in universo()}; por = {}
    for c, f in F.items():
        sp = U[c.split(":")[-1]]["spec"]; ej = sp.get("ejecucion") or sp["sensor"]
        if ej not in MICRO: continue
        usd_pt = C.tick_value_usd(MICRO[ej]) / C.tick_size(MICRO[ej]); rmed = np.median([x["riesgo"] for x in f]) if f else 1
        for x in f:
            v = x["R"] * USD_R if modo == "R" else x["R"] * x["riesgo"] * usd_pt * (USD_R / (rmed * usd_pt))
            por[x["ses"]] = por.get(x["ses"], 0.0) + v
    return np.array([por[k] for k in sorted(por)])


def _t(v):
    return float(v.mean() / v.std(ddof=1) * np.sqrt(len(v))) if len(v) > 2 and v.std(ddof=1) > 0 else np.nan


def m3(F, B=10000, seed=11):
    a, b = _serie_tam(F, "R"), _serie_tam(F, "fijo"); d0 = _t(b) - _t(a); rng = np.random.default_rng(seed); n = len(a); bs = []
    for _ in range(B):
        i = rng.integers(0, n, n); bs.append(_t(b[i]) - _t(a[i]))
    bs = np.array(bs); bs = bs[np.isfinite(bs)]
    return dict(t_riesgo_fijo=_t(a), t_contrato_fijo=_t(b), delta_t=float(d0), p_una_cola=float((1 + (bs <= 0).sum()) / (1 + len(bs))), sesiones=n)


def probar():
    T, G, H = _conjuntos(); GH = {**{f"G:{c}": f for c, f in G.items()}, **{f"H:{c}": f for c, f in H.items()}}
    out = {}
    for m, campo in (("M1", "m1"), ("M2", "m2")):
        out[m] = dict(GH=delta(_con_bajo(GH, campo)), G=delta(_con_bajo(G, campo), B=3000), H=delta(_con_bajo(H, campo), B=3000))
    out["M3"] = dict(GH=m3(GH), G=m3(G, B=3000), H=m3(H, B=3000))
    ps = [out["M1"]["GH"]["p_una_cola"], out["M2"]["GH"]["p_una_cola"], out["M3"]["GH"]["p_una_cola"]]; bh = _bh(ps)
    for m, b in zip(("M1", "M2", "M3"), bh):
        d = out[m]; sentido = (lambda x: x["delta"] < 0) if m != "M3" else (lambda x: x["delta_t"] > 0)
        d["nominada_BH"] = b; d["entra_v2"] = bool(b and sentido(d["G"]) and sentido(d["H"]))
    (DIR / "MEJORAS.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps({m: dict(GH={k: out[m]["GH"].get(k) for k in ("delta", "delta_t", "p_una_cola", "n_bajo", "R_total_bajo", "reglas_con_delta_neg")},
                              G={k: out[m]["G"].get(k) for k in ("delta", "delta_t", "n_bajo")}, H={k: out[m]["H"].get(k) for k in ("delta", "delta_t", "n_bajo")},
                              nominada=out[m]["nominada_BH"], entra=out[m]["entra_v2"]) for m in out}, indent=1, default=float))


def _usd_ops(cids, tramos, filtros, a1, pesos, tam="R"):
    """USD por sesión de la cartera: micros enteros a 200 USD por R (como cartera_nov_analisis._usd_diario) con A1/A2/M1/M2/M3."""
    from edgelab import costos as C
    U = {r["cid"]: r for r in universo()}; d = {}
    for c in cids:
        sp = U[c]["spec"]; ej = sp.get("ejecucion") or sp["sensor"]; m = MICRO[ej]; usd_pt = C.tick_value_usd(m) / C.tick_size(m)
        dfr = C.friccion_rt_puntos(m, criterio="max") - C.friccion_rt_puntos(m, criterio="min")
        todas = marcar(clasificar(c, sp)); f = [x for x in todas if x["tramo"] in tramos]
        rmed = np.median([x["riesgo"] for x in todas if x["tramo"] != "hold"])          # micros fijos: riesgo mediano de DESARROLLO
        for x in f:
            if ("m1" in filtros and x["m1"]) or ("m2" in filtros and x["m2"]): continue
            R = x["R"] + (dfr / x["riesgo"] if a1 else 0.0); r1 = x["riesgo"] * usd_pt; objetivo = USD_R * pesos.get(c, 1.0)
            if tam == "fijo": n = max(1, round(objetivo / (rmed * usd_pt)))
            else:
                if r1 > 2 * objetivo: continue
                n = max(1, round(objetivo / r1))
            d[x["ses"]] = d.get(x["ses"], 0.0) + R * n * r1
    return d


def v2():
    import importlib.util
    import pandas as pd
    spec = importlib.util.spec_from_file_location("ep", ROOT / "docs/research/canasta_7_20261030/estimar_propfirm.py"); ep = importlib.util.module_from_spec(spec); spec.loader.exec_module(ep)
    S = json.loads((DIR / "SELECCION.json").read_text())["futuros"]; M = json.loads((DIR / "MEJORAS.json").read_text())
    filtros = [m.lower() for m in ("M1", "M2") if M[m]["entra_v2"]]; tam = "fijo" if M["M3"]["entra_v2"] else "R"
    contr = json.loads((DIR / "PROP.json").read_text())["factor_contraccion"]
    dev_ses = [int(x.strftime("%Y%m%d")) for x in pd.bdate_range("20250805", "20260930")]
    hold_ses = sorted(json.loads((DIR / "NOVIEMBRE.json").read_text())["sesiones_nov"] +
                      [int(x.strftime("%Y%m%d")) for x in pd.bdate_range("20261001", "20261030") if int(x.strftime("%Y%m%d")) != 20261007])
    out = dict(filtros=filtros, tamano=tam, pesos=PESO, comision="minima (A1)", versiones={})
    for nom, kw in (("v1", dict(filtros=[], a1=False, pesos={}, tam="R")), ("v1+A1+A2", dict(filtros=[], a1=True, pesos=PESO, tam="R")),
                    ("v2", dict(filtros=filtros, a1=True, pesos=PESO, tam=tam))):
        dv = _usd_ops(S, ("desc", "rep"), **kw); x = np.array([dv.get(s, 0.0) for s in dev_ses])
        hv = _usd_ops(S, ("hold",), **kw); y = np.array([hv.get(s, 0.0) for s in hold_ses])
        r = dict(dev=ep.res(x), hold=ep.res(y), hold_nov_usd=float(sum(hv.get(s, 0.0) for s in hold_ses if s >= 20261102)))
        for k, mu in (("media_dev", x.mean()), ("media_contraida", x.mean() * contr), ("azar_0", 0.0)):
            p, q = ep.sim(x, ep.CUENTAS["50K"], mu=mu); r[k] = dict(pasa=float(p), quema=float(q))
        out["versiones"][nom] = r
    (DIR / "CARTERA_V2.json").write_text(json.dumps(out, indent=1, default=float)); print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"probar": probar, "v2": v2}[sys.argv[1]]()
