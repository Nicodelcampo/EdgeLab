#!/usr/bin/env python3
r"""IPC-NIVEL-MES — descubrimiento (OK de Nico 28/09). Manifiesto: docs/research/MANIFIESTO_IPC_NIVEL_MES_20260928.md

MES 25t (bundles mensuales del visor, research-v2 Lucid, precio de trade), ago-2025 → mar-2026.
- Zona: detector v2 congelado, construido en forma CAUSAL: el evento es la vela en que el zigzag confirma el pivote que
  abre la 3.ª visita. Variante N4: ≥ 4 picos en ese momento.
- Resultado: barre (≥ 2 t más allá del pico extremo del nivel) antes de alejarse d más (d = distancia cierre-nivel);
  horizonte 200 velas o fin de sesión; censura aparte.
- Nulo: simulate_null con ternas 25t estrictamente anteriores a la vela del evento, sin agrupar (bars_per_step = 1).
- Control C-PIV: pivote suelto del mismo tipo, misma sesión, distancia d ± 2 t y edad ± 50 %, fuera de toda zona.
- 8 pruebas bilaterales (P1 zona − p0; P2 zona − control), v2/N4 × techo/piso, BH q = 0,10, bootstrap por sesión.

    .venv\Scripts\python tools\ipc_nivel_run.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402

from edgelab.research.espejo_nulo import simulate_null  # noqa: E402

VIEW = REPO / "viewer" / "nt8_bridge" / "bundles"
OUT = REPO / "artifacts" / "ipc_nivel"
FROZEN = REPO / "docs" / "research" / "IPC_NIVEL_PARAMETROS_CONGELADOS_20260928.json"
MONTHS = ["202508", "202509", "202510", "202511", "202512", "202601", "202602", "202603"]
CONTRACTS = ["09-25", "12-25", "03-26", "06-26"]
MIN_VISITS, BIG_EXIT, MAX_GAP = 3, 14, 200
HZ, SWEEP, N_NULL, N_BOOT, SEED = 200, 2, 2000, 1000, 20260928


def zigzag(h, l, R):
    """Pivotes (idx, kind, precio, idx_confirmación) dentro de una sesión."""
    piv = []; d = 1; ei = 0; ext = h[0]
    for j in range(1, len(h)):
        if d == 1:
            if h[j] >= ext:
                ext = h[j]; ei = j
            elif ext - l[j] >= R:
                piv.append((ei, "H", ext, j)); d = -1; ext = l[j]; ei = j
        else:
            if l[j] <= ext:
                ext = l[j]; ei = j
            elif h[j] - ext >= R:
                piv.append((ei, "L", ext, j)); d = 1; ext = h[j]; ei = j
    return piv


def zone_events(piv, h, l, tol):
    """Eventos causales: (kind, vela_evento, ref_extremo, picos, n_picos, índices de pivotes usados)."""
    ev = []
    for kind in ("H", "L"):
        P = [p for p in piv if p[1] == kind]; s = 1 if kind == "H" else -1
        for a in range(len(P)):
            visits = [[P[a]]]
            for b in range(a + 1, len(P)):
                q = P[b]; last = visits[-1][-1]
                if q[0] - last[0] > MAX_GAP:
                    break
                tl = tol if len(visits) < 2 else 1.5 * tol
                if s * (q[2] - last[2]) > 0:
                    break
                if -s * (q[2] - last[2]) > tl:
                    continue
                exc = (P[a][2] - l[last[0]:q[0] + 1].min()) if kind == "H" else (h[last[0]:q[0] + 1].max() - P[a][2])
                if exc >= BIG_EXIT:
                    visits.append([q])
                    if len(visits) == MIN_VISITS:
                        pk = [p for v in visits for p in v]
                        ref = max(p[2] for p in pk) if kind == "H" else min(p[2] for p in pk)
                        ev.append(dict(kind=kind, bar=q[3], ref=ref, n_picos=len(pk), picos=[p[0] for p in pk]))
                        break
                else:
                    visits[-1].append(q)
    ev.sort(key=lambda e: e["bar"])
    keep = []
    for e in ev:                                         # el mismo nivel visto desde otro pico de arranque: el primero
        if not any(k["kind"] == e["kind"] and abs(k["ref"] - e["ref"]) <= 2 * tol and e["bar"] - k["bar"] <= MAX_GAP for k in keep):
            keep.append(e)
    return keep


def race(h, l, j, target, away, s, end):
    for k in range(j + 1, end + 1):
        hit_t = (h[k] >= target) if s == 1 else (l[k] <= target)
        hit_a = (l[k] <= away) if s == 1 else (h[k] >= away)
        if hit_t and hit_a:
            return "ambigua"
        if hit_t:
            return "barre"
        if hit_a:
            return "se_aleja"
    return "censurada"


def sessions_of_month(month):
    """{clave_sesión: (asset, o, h, l, c)} eligiendo, en meses con dos contratos, el de más velas por sesión."""
    best = {}
    for c in CONTRACTS:
        f = VIEW / f"MES_{c}_{month}_25T_HFT.json"
        if not f.exists():
            continue
        b = json.loads(f.read_text(encoding="utf-8")); tick = float(b["meta"]["tick_size"])
        cd = b["bar_series"]["tick_25"]["candles"]; del b
        t = np.array([x["time"] for x in cd], float)
        O, H, L, C = (np.round(np.array([x[k] for x in cd]) / tick) for k in ("open", "high", "low", "close"))
        del cd
        cuts = np.r_[0, np.flatnonzero(np.diff(t) > 1800) + 1, len(t)]
        for a0, b0 in zip(cuts[:-1], cuts[1:]):
            key = str(np.datetime64(int(t[a0] + 8 * 3600), "s").astype("datetime64[D]")).replace("-", "")
            if key[:6] != month and not (key[:6] > month):
                pass
            if b0 - a0 < 500:
                continue
            if key not in best or (b0 - a0) > len(best[key][2]):
                best[key] = (f"MES_{c}_{month}", O[a0:b0], H[a0:b0], L[a0:b0], C[a0:b0])
    return best


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "edgelab", "tools"], cwd=REPO, capture_output=True, text=True).stdout.strip())
    fr = json.loads(FROZEN.read_text(encoding="utf-8"))["elegido"]; R, tol = fr["R"], fr["tol"]
    allses = {}
    for m in MONTHS:
        for k, v in sessions_of_month(m).items():
            if k <= "20260331" and (k not in allses or len(v[2]) > len(allses[k][2])):
                allses[k] = v
        print(m, "sesiones acumuladas", len(allses), flush=True)
    rows, prev_trip = [], None
    for key in sorted(allses):
        asset, O, H, L, C = allses[key]
        trip = np.column_stack([C - O, H - O, L - O])
        piv = zigzag(H, L, R)
        evs = zone_events(piv, H, L, tol)
        zone_piv = {p for e in evs for p in e["picos"]}
        last_piv = {"H": np.full(len(C), -1), "L": np.full(len(C), -1)}       # último pivote confirmado por vela
        for p in piv:
            last_piv[p[1]][p[3]:] = p[0]
        piv_price = {p[0]: p[2] for p in piv}
        n = len(C)
        pprice = {k: np.where(last_piv[k] >= 0, np.array([piv_price.get(int(x), np.nan) for x in last_piv[k]]), np.nan) for k in ("H", "L")}
        ctrl_ok = {k: (last_piv[k] >= 0) & ~np.isin(last_piv[k], list(zone_piv)) for k in ("H", "L")}

        def measure(j, ref, s, tag, extra):
            d = s * (ref - C[j])
            if d < 2:
                return None
            end = min(j + HZ, n - 1)
            target = ref + s * SWEEP; away = C[j] - s * d
            res = race(H, L, j, target, away, s, end)
            pool = trip[:j]
            if len(pool) < 50 and prev_trip is not None:
                pool = np.vstack([prev_trip[-(200 - len(pool)):], pool])
            if len(pool) < 50 or end <= j:
                return None
            seed = int(hashlib.sha256(f"{key}|{j}|{tag}".encode()).hexdigest()[:8], 16)
            p0 = simulate_null(C[j], target, away, s, pool, end - j, n=N_NULL, seed=seed, bars_per_step=1)
            return dict(session=key, asset=asset, grupo=tag, bar=int(j), d=float(d), res=res, p0=p0, **extra)

        rng = np.random.default_rng(int(key))
        for e in evs:
            s = 1 if e["kind"] == "H" else -1; j = e["bar"]
            r = measure(j, e["ref"], s, "zona", dict(kind=e["kind"], n_picos=e["n_picos"], N4=e["n_picos"] >= 4))
            if r is None:
                continue
            rows.append(r)
            age = j - e["picos"][-1]
            lp = last_piv[e["kind"]]; ok = ctrl_ok[e["kind"]]
            ag = np.arange(n) - lp; dd = s * (pprice[e["kind"]] - C)
            m = ok & (np.abs(np.arange(n) - j) >= 100) & (np.abs(dd - r["d"]) <= 2) & (ag >= 0.5 * age) & (ag <= 1.5 * max(age, 1))
            m[:50] = False; m[-1] = False
            cand = np.flatnonzero(m)
            if len(cand):
                jj = int(cand[np.argmin(np.abs(cand - j))])
                rc = measure(jj, piv_price[last_piv[e["kind"]][jj]], s, "control", dict(kind=e["kind"], n_picos=1, N4=r["N4"], de=j))
                if rc is not None:
                    rows.append(rc)
        prev_trip = trip
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "eventos.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    rep = dict(manifiesto="docs/research/MANIFIESTO_IPC_NIVEL_MES_20260928.md", code_commit=head, tree_dirty=dirty,
               sesiones=len(allses), eventos_zona=sum(r["grupo"] == "zona" for r in rows),
               eventos_control=sum(r["grupo"] == "control" for r in rows))
    for tag_feb, filt in (("con_febrero", lambda r: True), ("sin_febrero", lambda r: not r["session"].startswith("202602"))):
        cells = []
        for var in ("v2", "N4"):
            for kind in ("H", "L"):
                Z = [r for r in rows if r["grupo"] == "zona" and r["kind"] == kind and (var == "v2" or r["N4"]) and filt(r)]
                K = [r for r in rows if r["grupo"] == "control" and r["kind"] == kind and (var == "v2" or r["N4"]) and filt(r)]
                ez = np.array([(r["res"] == "barre") - r["p0"]["completa"] for r in Z]); sz = np.array([r["session"] for r in Z])
                ek = np.array([(r["res"] == "barre") - r["p0"]["completa"] for r in K]); sk = np.array([r["session"] for r in K])
                rng = np.random.default_rng(SEED)
                u = np.unique(np.r_[sz, sk]); iz = {x: np.flatnonzero(sz == x) for x in u}; ik = {x: np.flatnonzero(sk == x) for x in u}
                b1 = np.empty(N_BOOT); b2 = np.empty(N_BOOT)
                for bi in range(N_BOOT):
                    pick = rng.choice(u, len(u))
                    a = np.concatenate([iz[x] for x in pick]); c = np.concatenate([ik[x] for x in pick])
                    b1[bi] = ez[a].mean() if len(a) else np.nan
                    b2[bi] = (ez[a].mean() if len(a) else np.nan) - (ek[c].mean() if len(c) else np.nan)
                for name, est, bs in (("P1", ez.mean() if len(ez) else np.nan, b1),
                                      ("P2", (ez.mean() - ek.mean()) if len(ez) and len(ek) else np.nan, b2)):
                    p = float(min(1.0, 2 * min(np.nanmean(bs <= 0), np.nanmean(bs >= 0))))
                    cells.append(dict(prueba=name, variante=var, lado=kind, n_zona=len(Z), n_control=len(K), estimado=float(est),
                                      ic90=[float(np.nanquantile(bs, .05)), float(np.nanquantile(bs, .95))],
                                      p_bilateral=p, mde80=2.8 * float(np.nanstd(bs)),
                                      barre_zona=float(np.mean([r["res"] == "barre" for r in Z])) if Z else None,
                                      p0_zona=float(np.mean([r["p0"]["completa"] for r in Z])) if Z else None,
                                      barre_control=float(np.mean([r["res"] == "barre" for r in K])) if K else None,
                                      se_aleja_zona=float(np.mean([r["res"] == "se_aleja" for r in Z])) if Z else None,
                                      censurada_zona=float(np.mean([r["res"] == "censurada" for r in Z])) if Z else None))
        ps = [c["p_bilateral"] for c in cells]; o = np.argsort(ps); m = len(ps)
        ok = np.array(ps)[o] <= 0.10 * np.arange(1, m + 1) / m; kmax = (np.max(np.flatnonzero(ok)) + 1) if ok.any() else 0
        for i, c in enumerate(cells):
            c["bh_q10"] = bool(i in set(o[:kmax]))
        rep[tag_feb] = dict(pruebas=cells, sobreviven=[f"{c['prueba']} {c['variante']} {c['lado']}" for c in cells if c["bh_q10"]])
    (OUT / "reporte.json").write_text(json.dumps(rep, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("con_febrero", "sin_febrero")}, indent=1))
    for c in rep["con_febrero"]["pruebas"]:
        print(c["prueba"], c["variante"], c["lado"], c["n_zona"], c["n_control"], round(c["estimado"], 3), [round(x, 3) for x in c["ic90"]],
              round(c["p_bilateral"], 3), round(c["mde80"], 3), "barre", round(c["barre_zona"] or 0, 3), "p0", round(c["p0_zona"] or 0, 3),
              "ctrl", round(c["barre_control"] or 0, 3))
    print("sobreviven con feb", rep["con_febrero"]["sobreviven"], "sin feb", rep["sin_febrero"]["sobreviven"])


if __name__ == "__main__":
    main()
