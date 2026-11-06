#!/usr/bin/env python3
"""Barreras HFT frontales aplicadas a las reglas en seguimiento de `Estabilidad mensual en R2.html` (2026-11-05).

Misma batería de 320 reglas de barrera que `atlas_barreras_hft_r.py` (LIBRE >= 1/2/4R y TRAMO 0/1/2 zonas o sólo mitad lejana),
evaluada sobre las operaciones de DESARROLLO (DESC ago-2025..mar-2026 y REP abr..sep-2026) de cada regla seguida en ES y NQ.
No toca octubre-2026 (holdout). Efecto por regla = media(R | pasa) - media(R | todas); meta-análisis DerSimonian-Laird entre reglas,
BH q <= 0,10 en DESC y confirmación en REP (mismo signo, p unilateral < 0,05).
Limitación declarada: la entrada se aproxima por el cierre de la vela de decisión (las trayectorias guardadas no traen el precio de
llenado); en U1-CRUZADO, TORI-NQ-R y CONF-CVR-CFD-NQ-R el lado se infiere del movimiento de 30 velas (como en el atlas de contexto).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import atlas_barreras_hft_r as AB  # noqa: E402
import atlas_contexto_r as AC  # noqa: E402
from edgelab.research import barreras_hft as BH, fuentes_ticks as F  # noqa: E402

SAL = AB.BASE / "reglas_seguidas"
TRAY = ROOT / "docs/research/programa_r_20261103/trayectorias"
EXTRAS = [
    ("U1-CRUZADO", ROOT / "docs/research/canasta_7_20261030/desarrollo_en_r/U1-CRUZADO__{t}.json", "NQ", "REVERSION", 2.5),
    ("TORI-NQ-R", ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo/TORI-NQ-R__{t}.json", "NQ", "CONTINUACION", 2.0),
    ("CONF-CVR-CFD-NQ-R", ROOT / "docs/research/nominacion_forzada_R_20261103/desarrollo/CONF-CVR-CFD-NQ-R__{t}.json", "NQ", "REVERSION", 1.5),
]
PRIMARIAS = ["LIBRE|t0|e{e}|m1|r2", "TRAMO|t0|e{e}|m1|todo0", "TRAMO|t0|e{e}|m1|lejana1", "TRAMO|t0|e{e}|m1|todo1"]


def _ops_regla(regla: str, tramo: str, inst: str, sim: dict):
    """Devuelve (O, R, ses) con O en el formato de `evaluar_ops`, o None si no hay datos."""
    t_sim, c_sim = sim["t"], sim["c"]
    if regla in [e[0] for e in EXTRAS]:
        _, ruta, _, mec, rr = next(e for e in EXTRAS if e[0] == regla)
        f = Path(str(ruta).format(t="rep" if (tramo == "rep" and regla == "U1-CRUZADO") else ("oos" if tramo == "rep" else "desc")))
        if not f.exists():
            return None
        d = json.loads(f.read_text(encoding="utf-8")).get("operaciones") or {}
        ts = np.asarray(d.get("t", []), float)
        ses = np.asarray(d.get("ses", []), int)
        neto = np.asarray(d.get("neto", []), float)
        rg = np.asarray([np.nan if v is None else v for v in d.get("riesgo", [])], float)
        R = neto / rg
        ok = np.isfinite(R) & (ts > 0)
        ts, ses, rg, R = ts[ok], ses[ok], rg[ok], R[ok]
        ks = np.clip(np.searchsorted(t_sim, ts), 0, len(t_sim) - 1)
        mov = np.where(c_sim[ks] >= c_sim[np.maximum(0, ks - 30)], 1.0, -1.0)
        lados = mov if mec == "CONTINUACION" else -mov
        e = c_sim[ks]
        O = np.column_stack([np.arange(len(ts)), np.zeros(len(ts)), ks, np.zeros(len(ts)), lados, e, e - lados * rg, e + lados * rr * rg, np.zeros(len(ts))])
        return O, R, ses
    f = TRAY / f"{regla}__{tramo}.json"
    if not f.exists():
        return None
    trs = json.loads(f.read_text(encoding="utf-8")).get("trayectorias") or []
    trs = [tr for tr in trs if tr.get("R_regla") is not None]
    if not trs:
        return None
    ks = np.clip(np.searchsorted(t_sim, [tr["t"] for tr in trs]), 0, len(t_sim) - 1)
    lados = np.array([float(tr["lado"]) for tr in trs])
    rg = np.array([float(tr["riesgo"]) for tr in trs])
    obj = np.array([float(tr["objetivo_R"]) for tr in trs])
    e = c_sim[ks]
    O = np.column_stack([np.arange(len(trs)), np.zeros(len(trs)), ks, np.zeros(len(trs)), lados, e, e - lados * rg, e + lados * obj * rg, np.zeros(len(trs))])
    return O, np.array([float(tr["R_regla"]) for tr in trs]), np.array([int(tr["ses"]) for tr in trs])


def correr():
    SAL.mkdir(parents=True, exist_ok=True)
    reglas = sorted({p.name.split("__")[0] for p in TRAY.glob("*__*.json") if not p.name.startswith("handles")} | {e[0] for e in EXTRAS})
    res = {}
    for inst in ("ES", "NQ"):
        lec, tk = F.resolver(inst)
        sim = AC._contexto_m1_rapido(lec(20250721, 20260930, str(AC.DATA_LOCAL)), tk, con_perfil=True, con_ticks=False)
        zonas, clust = AB._zonas(inst)
        z = zonas[zonas["t_ns"].to_numpy(np.int64) >= int(sim["t"][0]) * 10**9]
        inv = BH.preparar_inventario_barreras(z, sim, clust)
        for regla in reglas:
            if (inst == "ES") != ("ES" in regla.split("-")):
                continue
            for tramo in ("desc", "rep"):
                x = _ops_regla(regla, tramo, inst, sim)
                if x is None:
                    continue
                O, R, ses = x
                ev = AB.evaluar_ops(sim, inv, O, R, ses)
                res[f"{regla}__{tramo}"] = dict(regla=regla, tramo=tramo, inst=inst, **ev)
                print(f"[ok] {regla}/{tramo} n={ev['base'].get('n')}", flush=True)
    (SAL / "crudo.json").write_text(json.dumps(res, default=float), encoding="utf-8")


def analizar():
    from edgelab.funnel.escalera import _N
    res = json.loads((SAL / "crudo.json").read_text(encoding="utf-8"))
    por = {"desc": {}, "rep": {}}
    for v in res.values():
        if v["base"].get("n", 0) < 20:
            continue
        mu = v["base"]["suma"] / v["base"]["n"]
        for k, a in v["reglas"].items():
            if a["n"] < 15:
                continue
            m = a["suma"] / a["n"]
            var = max(a["suma2"] / a["n"] - m * m, 1e-12)
            por[v["tramo"]].setdefault(k, {})[v["regla"]] = (m - mu, var / max(a["sesiones"], 1), a["n"], v["base"]["n"])
    def meta(tr):
        out = []
        for k, mp in por[tr].items():
            if len(mp) < 4:
                continue
            ds = [x[0] for x in mp.values()]
            m, se, _, _ = AC._dl(ds, [x[1] for x in mp.values()])
            z = m / se if se > 0 else 0
            out.append(dict(regla=k, k=len(mp), efecto=m, se=se, p=float(2 * (1 - _N.cdf(abs(z)))), p_uni=float(1 - _N.cdf(z)),
                            pasa_frac=float(np.mean([x[2] / x[3] for x in mp.values()])), mejoran=float(np.mean(np.array(ds) > 0))))
        return sorted(out, key=lambda r: r["p"])
    d, r = meta("desc"), {x["regla"]: x for x in meta("rep")}
    kmax = max([i for i, x in enumerate(d) if x["p"] <= 0.10 * (i + 1) / len(d)], default=-1)
    L = ["# Barreras HFT aplicadas a las reglas en seguimiento (Estabilidad mensual en R2)", "",
         f"Reglas evaluadas por tramo (DESC): {len(d)}; nominadas BH q ≤ 0,10: {kmax + 1}. Efecto = ΔR = R(pasa) − R(todas), meta DerSimonian-Laird entre reglas.", "",
         "| regla barrera | reglas | ΔR DESC | p | BH | ΔR REP | p uni REP | % ops que pasan | % reglas que mejoran |", "|---|---|---|---|---|---|---|---|---|"]
    for i, x in enumerate(d[:12]):
        q = r.get(x["regla"], {})
        L.append(f"| `{x['regla']}` | {x['k']} | {x['efecto']:+.3f} | {x['p']:.4f} | {'sí' if i <= kmax else 'no'} | {q.get('efecto', float('nan')):+.3f} | {q.get('p_uni', float('nan')):.3f} | {x['pasa_frac']:.0%} | {x['mejoran']:.0%} |")
    L += ["", "## Primarias por regla (tipo TODAS_HFT, NO_ATRAVESADA; ΔR en DESC / REP y % que pasa)", ""]
    for e in range(5):
        L += [f"### antigüedad nivel {e} ({BH.ANTIGUEDADES[e][0]})", "", "| regla | " + " | ".join(p.format(e=e).split('|')[0] + ':' + p.format(e=e).split('|')[-1] for p in PRIMARIAS) + " |", "|---|" + "---|" * len(PRIMARIAS)]
        for regla in sorted({v["regla"] for v in res.values()}):
            celdas = []
            for p in PRIMARIAS:
                k = p.format(e=e)
                partes = []
                for tr in ("desc", "rep"):
                    t = por[tr].get(k, {}).get(regla)
                    partes.append("—" if not t else f"{t[0]:+.2f}({t[2] / t[3]:.0%})")
                celdas.append(" / ".join(partes))
            L.append(f"| {regla} | " + " | ".join(celdas) + " |")
        L.append("")
    (AB.BASE / "RESULTADO_BARRERAS_REGLAS_SEGUIDAS.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[:25]))


if __name__ == "__main__":
    {"correr": correr, "analizar": analizar}[sys.argv[1]]()

