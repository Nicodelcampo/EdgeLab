#!/usr/bin/env python3
r"""IPC-NIVEL × HFT (MES) — pedido prioritario de Nico 28/09: discriminar los niveles de picos según la cercanía y
densidad de zonas HFTZonesNQPureV4 (SCALED_FUNNEL_V1, paridad no validada: se usa como está) por encima o por debajo.

Reusa los eventos ya medidos (resultado y nulo) de la formación (`artifacts/ipc_nivel/eventos.json`) y del regreso virgen
(`artifacts/ipc_nivel_regreso/eventos.json`); sólo agrega el rasgo HFT, calculado as-of:
- zona HFT activa en la vela j si ya estaba disponible (available_ts ≤ t[j]) y hace ≤ 500 velas (extensión fija del visor);
- distancia al nivel en ticks (0 si el nivel cae dentro de la zona); cuentan las zonas a ≤ 20 t;
- puntaje de densidad y cercanía S = Σ 1 / (1 + distancia/2).
Tres niveles: baja / media / alta (terciles de S sobre los eventos de zona de cada estudio; si más de un tercio tiene
S = 0, baja = S 0 y media/alta parten los positivos por la mediana). Descriptivo: zonas del lado del barrido vs del otro.
Pruebas: estudio (formación, regreso) × lado (techo, piso) × {exceso en baja, media, alta; alta − baja} = 16, BH q 0,10,
bootstrap por sesión, n ≥ 30 por celda.

    .venv\Scripts\python tools\ipc_nivel_hft.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

import ipc_nivel_regreso as RG  # noqa: E402
import ipc_nivel_run as B  # noqa: E402

OUT = REPO / "artifacts" / "ipc_nivel_hft"
EXT_BARS, MAXD, MIN_N, N_BOOT, SEED = 500, 20, 30, 1000, 20260928


def month_data(month):
    """{sesión: dict(asset, O,H,L,C,V,T, zonas[(avail_ts, bottom_t, top_t)])} con el mejor contrato por sesión."""
    best = {}
    for c in B.CONTRACTS:
        f = B.VIEW / f"MES_{c}_{month}_25T_HFT.json"
        if not f.exists():
            continue
        b = json.loads(f.read_text(encoding="utf-8")); tick = float(b["meta"]["tick_size"])
        cd = b["bar_series"]["tick_25"]["candles"]
        zs = [(float(z["available_ts"]), z["bottom"] / tick, z["top"] / tick) for z in b["runs"][0]["zones"]]
        del b
        t = np.array([x["time"] for x in cd], float)
        O, H, L, C = (np.round(np.array([x[k] for x in cd]) / tick) for k in ("open", "high", "low", "close"))
        V = np.array([x["volume"] for x in cd], float); del cd
        za = np.array(zs, float) if zs else np.zeros((0, 3))
        cuts = np.r_[0, np.flatnonzero(np.diff(t) > 1800) + 1, len(t)]
        for a0, b0 in zip(cuts[:-1], cuts[1:]):
            if b0 - a0 < 500:
                continue
            key = str(np.datetime64(int(t[a0] + 8 * 3600), "s").astype("datetime64[D]")).replace("-", "")
            if key > "20260331":
                continue
            if key not in best or (b0 - a0) > len(best[key]["C"]):
                T = t[a0:b0]
                zz = za[(za[:, 0] >= T[0]) & (za[:, 0] <= T[-1])] if len(za) else za
                best[key] = dict(asset=f"MES_{c}_{month}", O=O[a0:b0], H=H[a0:b0], L=L[a0:b0], C=C[a0:b0], V=V[a0:b0], T=T, Z=zz)
    return best


def hft_feature(S, j, ref, s):
    T, Z = S["T"], S["Z"]
    if not len(Z):
        return 0.0, 0, 0
    abar = np.searchsorted(T, Z[:, 0], side="left")            # vela en que la zona queda disponible
    act = (Z[:, 0] <= T[j]) & (abar >= j - EXT_BARS)
    if not act.any():
        return 0.0, 0, 0
    lo, hi = Z[act, 1], Z[act, 2]
    dist = np.where(ref < lo, lo - ref, np.where(ref > hi, ref - hi, 0.0))
    near = dist <= MAXD
    score = float(np.sum(1.0 / (1.0 + dist[near] / 2.0)))
    mid = (lo + hi) / 2
    beyond = int(np.sum(near & (s * (mid - ref) > 0)))           # del lado del barrido (arriba de un techo)
    return score, beyond, int(near.sum()) - beyond


def levels(scores):
    sc = np.asarray(scores, float)
    if np.mean(sc == 0) > 1 / 3:
        med = np.median(sc[sc > 0]) if (sc > 0).any() else 0
        return np.where(sc == 0, 0, np.where(sc <= med, 1, 2)), dict(regla="baja = sin zonas HFT cerca", mediana_positivos=float(med))
    q = np.quantile(sc, [1 / 3, 2 / 3])
    return np.where(sc <= q[0], 0, np.where(sc > q[1], 2, 1)), dict(regla="terciles", cortes=q.tolist())


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    fr = json.loads(B.FROZEN.read_text(encoding="utf-8"))["elegido"]; R, tol = fr["R"], fr["tol"]
    ev_f = [r for r in json.loads((REPO / "artifacts/ipc_nivel/eventos.json").read_text(encoding="utf-8"))]
    ev_r = [r for r in json.loads((REPO / "artifacts/ipc_nivel_regreso/eventos.json").read_text(encoding="utf-8")) if r["grupo"] == "zona"]
    idx_f = {(r["session"], r["bar"], r["kind"], r["grupo"]): r for r in ev_f}
    idx_r = {(r["session"], r["bar"], r["kind"]): r for r in ev_r}
    out_f, out_r = [], []
    for m in B.MONTHS:
        data = month_data(m)
        for key, S in data.items():
            H, L, C, V = S["H"], S["L"], S["C"], S["V"]
            # formación (zona y control): ref = C[j] + s·d
            for (ses, bar, kind, grupo), r in list(idx_f.items()):
                if ses != key:
                    continue
                s = 1 if kind == "H" else -1
                sc, bey, bef = hft_feature(S, bar, C[bar] + s * r["d"], s)
                out_f.append(dict(r, S=sc, beyond=bey, before=bef)); idx_f.pop((ses, bar, kind, grupo))
            # regreso: se recalcula el ref de cada zona formada y se empareja por (vela, lado)
            piv = B.zigzag(H, L, R)
            for e in B.zone_events(piv, H, L, tol):
                vmed = float(np.median(V[:e["bar"]])) if e["bar"] >= 20 else float(np.median(V))
                g = RG.regreso(e["ref"], e["bar"], e["kind"], H, L, V, max(vmed, 1.0))
                if g is None:
                    continue
                k = g[0]; r = idx_r.pop((key, int(k), e["kind"]), None)
                if r is None:
                    continue
                s = 1 if e["kind"] == "H" else -1
                sc, bey, bef = hft_feature(S, k, e["ref"], s)
                out_r.append(dict(r, S=sc, beyond=bey, before=bef))
        print(m, "formación", len(out_f), "regreso", len(out_r), flush=True)
        del data
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eventos.json").write_text(json.dumps(dict(formacion=out_f, regreso=out_r), default=float), encoding="utf-8")
    rng = np.random.default_rng(SEED); cells = []; reglas = {}
    NAMES = ("baja", "media", "alta")
    for estudio, E in (("formacion", [r for r in out_f if r["grupo"] == "zona"]), ("regreso", out_r)):
        lv, regla = levels([r["S"] for r in E]); reglas[estudio] = regla
        for r, v in zip(E, lv):
            r["nivel_hft"] = int(v)
        for kind in ("H", "L"):
            X = [r for r in E if r["kind"] == kind]
            p0 = np.array([r["p0"]["completa"] if isinstance(r["p0"], dict) else r["p0"] for r in X])
            exc = np.array([r["res"] == "barre" for r in X], float) - p0
            ses = np.array([r["session"] for r in X]); lvx = np.array([r["nivel_hft"] for r in X])
            u = np.unique(ses); ix = {x: np.flatnonzero(ses == x) for x in u}
            tests = [(f"exceso {NAMES[v]}", lvx == v, None) for v in range(3)] + [("alta - baja", lvx == 2, lvx == 0)]
            for name, g1, g2 in tests:
                n1 = int(g1.sum()); n2 = int(g2.sum()) if g2 is not None else None
                est = exc[g1].mean() - (exc[g2].mean() if g2 is not None else 0) if n1 else np.nan
                if n1 < MIN_N or (g2 is not None and n2 < MIN_N):
                    cells.append(dict(estudio=estudio, lado=kind, prueba=name, n1=n1, n2=n2, estimado=float(est), p_bilateral=1.0, sin_potencia=True)); continue
                bs = np.empty(N_BOOT)
                for bi in range(N_BOOT):
                    a = np.concatenate([ix[x] for x in rng.choice(u, len(u))])
                    bs[bi] = exc[a][g1[a]].mean() - (exc[a][g2[a]].mean() if g2 is not None else 0)
                p = float(min(1.0, 2 * min(np.nanmean(bs <= 0), np.nanmean(bs >= 0))))
                cells.append(dict(estudio=estudio, lado=kind, prueba=name, n1=n1, n2=n2, estimado=float(est),
                                  ic90=[float(np.nanquantile(bs, .05)), float(np.nanquantile(bs, .95))], p_bilateral=p,
                                  mde80=2.8 * float(np.nanstd(bs)),
                                  barre=float(np.mean([X[i]["res"] == "barre" for i in np.flatnonzero(g1)])),
                                  zonas_lado_barrido=float(np.mean([X[i]["beyond"] for i in np.flatnonzero(g1)])),
                                  zonas_otro_lado=float(np.mean([X[i]["before"] for i in np.flatnonzero(g1)]))))
    ps = np.array([c["p_bilateral"] for c in cells]); o = np.argsort(ps); mm = len(ps)
    ok = ps[o] <= 0.10 * np.arange(1, mm + 1) / mm; kmax = (np.max(np.flatnonzero(ok)) + 1) if ok.any() else 0
    surv = set(o[:kmax].tolist())
    for i, c in enumerate(cells):
        c["bh_q10"] = i in surv
    ctrl = [r for r in out_f if r["grupo"] == "control"]
    rep = dict(pedido="Nico 28/09, prioritario", code_commit=head, tree_dirty=dirty, reglas_niveles=reglas,
               eventos=dict(formacion_zona=sum(r["grupo"] == "zona" for r in out_f), formacion_control=len(ctrl), regreso=len(out_r)),
               control_S_medio=float(np.mean([r["S"] for r in ctrl])) if ctrl else None,
               zona_S_medio=float(np.mean([r["S"] for r in out_f if r["grupo"] == "zona"])) if out_f else None,
               pruebas=cells, sobreviven=[f"{c['estudio']} {c['lado']} {c['prueba']}" for c in cells if c["bh_q10"]])
    (OUT / "reporte.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "pruebas"}, indent=1, ensure_ascii=False))
    for c in cells:
        print(c["estudio"], c["lado"], c["prueba"], c["n1"], c["n2"], round(c["estimado"], 3), [round(x, 3) for x in c.get("ic90", [])],
              round(c["p_bilateral"], 3), "barre", c.get("barre") and round(c["barre"], 3))


if __name__ == "__main__":
    main()
