#!/usr/bin/env python3
r"""NQ-CRUCE25-CLIMA — pre-registro docs/research/MANIFIESTO_NQ_CRUCE25_POR_CLIMA_L2_20260929.md (v2, tras Entrada 067).
NO CORRER sin OK de Nico después de la re-auditoría. Pensado para Kaggle (dataset edgelab-nq-nt8-2026q3-l2ctx).

    python tools/nq_cruce25_clima.py --bars DIR_VELAS_25T --labels l2_contexts_NQ_labels.parquet --gate gate_report.json --out DIR

Cambios v2 (Entrada 067):
  - sesiones de evaluación = las 40 `eval_ids` congeladas del plan del modelo (hash fijo), no las que tienen etiquetas válidas;
    sesiones sin velas o sin etiquetas cuentan como «sin clima» / «sin velas», no desaparecen;
  - clima causal con timestamps enteros (`t_ns` de las velas; `available_utc_us` de tools/l2_labels_utc.py), la fila
    disponible más reciente debe ser válida por sí misma y tener edad ≤ 120 s;
  - control PRIMARIO del mismo clima (+ franja ±30 min + tercil de volatilidad); el control sin clima queda secundario;
  - volatilidad previa = RMS de los cambios firmados de cierre (20 velas 100t), no std(|Δ|);
  - max-T con bootstrap CONJUNTO: pesos multinomiales comunes sobre las 40 sesiones para todas las celdas, aplicados a la
    sesión del evento y a la sesión fuente de cada control;
  - potencia: celda evaluable sólo con ≥ 30 eventos Y ≥ 8 sesiones distintas; si no, «inconclusa» y fuera de la familia max-T.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "tools"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

M, HZ, SEED, N_CTRL, TOD_WIN_S, CAP_SES, N_BOOT = 4, 150, 20260929, 3, 1800, 300, 2000
MAX_AGE_US = 120_000_000
MIN_EVENTOS, MIN_SESIONES = 30, 8
LEVELS = {"N3": (17, 20), "N4": (13, 25), "N5": (9, 30)}
XS = (0.25, 0.5, 0.75, 1.0)
CLIMAS = ("calm", "normal", "volatile", "toxic")
ROLL = "20260915"
HOLDOUT_NS = 1_790_805_600 * 1_000_000_000       # sesión CME del 1-oct-2026 (HOLDOUT-A3)
EVAL_IDS_SHA256 = "f59aee57e369a47a4ffe917c314fd12ef5e9695e9d2b87c5d00b2e09d4ac3958"  # sha256 de ",".join(sorted(eval_ids))


def eval_ids_sha(ids) -> str:
    return hashlib.sha256(",".join(sorted(ids)).encode()).hexdigest()


def agg(h, l, c, v, t_ns):
    n = len(c) // M * M
    return (h[:n].reshape(-1, M).max(1), l[:n].reshape(-1, M).min(1), c[:n].reshape(-1, M)[:, -1],
            v[:n].reshape(-1, M).sum(1), t_ns[:n].reshape(-1, M)[:, -1])


def race(H, L, j, tgt, fail, s, end):
    for q in range(j + 1, end + 1):
        ht = (H[q] >= tgt) if s == 1 else (L[q] <= tgt)
        hf = (L[q] <= fail) if s == 1 else (H[q] >= fail)
        if ht and hf:
            return 0
        if ht:
            return 1
        if hf:
            return 0
    return 0


def outcome_from_close(H, L, C, j, tgt, fail, s, end):
    """Convención congelada (Entrada 069 §2): la señal es el CIERRE de la vela j y la entrada es ese cierre.
    Barreras medidas desde j+1. Si C[j] ya está en o más allá del objetivo → None («objetivo ya alcanzado al cierre»):
    no hay operación; se excluye de la prueba y se cuenta. Mecha de j que toca el objetivo con cierre antes: no cuenta
    (ocurrió antes de poder actuar); cuenta sólo lo que pase desde j+1. Misma regla para el control (geometría relativa al cierre)."""
    if s * (C[j] - tgt) >= 0:
        return None
    return race(H, L, j, tgt, fail, s, end)


def reconciliar(rows, sin_ctrl, x="0.25"):
    """Entrada 071: por clima, señales con clima = evaluables (3 controles del mismo clima y objetivo no alcanzado)
    + ya alcanzadas al cierre + sin control del mismo clima (con sesiones afectadas). Las «sin clima» no tienen clima
    y se reportan aparte, por nivel. Nada se imputa ni se oculta."""
    rep = {}
    for cl in CLIMAS:
        R_ = [r for r in rows if r["clima"] == cl]; SC = [e for e in sin_ctrl if e["clima"] == cl]
        ev = sum(1 for r in R_ if r["ev"].get(x) is not None); ya = len(R_) - ev
        rep[cl] = dict(senales=len(R_) + len(SC), evaluables=ev, ya_alcanzado_al_cierre=ya, sin_control_mismo_clima=len(SC),
                       sesiones_sin_control=sorted({e["session"] for e in SC}), cierra=len(R_) + len(SC) == ev + ya + len(SC))
    return rep


def vol_prev(C, k=20):
    """RMS de los cambios firmados de cierre en las k velas previas (sin incluir la actual)."""
    d = np.diff(C, prepend=C[0]).astype(float); out = np.full(len(C), np.nan)
    for i in range(k, len(C)):
        out[i] = np.sqrt(np.mean(d[i - k:i] ** 2))
    return out


def vol_prev_v1(C, k=20):
    """Definición v1 (std de |Δ|), sólo para publicar la comparación de terciles."""
    d = np.abs(np.diff(C, prepend=C[0])); out = np.full(len(C), np.nan)
    for i in range(k, len(C)):
        out[i] = d[i - k:i].std()
    return out


class ClimaLookup:
    """Clima causal: fila con la mayor `available_utc_us` ≤ t; debe ser elegible, as-of ok y con edad ≤ 120 s."""

    def __init__(self, lab: pd.DataFrame):
        lab = lab.sort_values("available_utc_us", kind="stable")
        self.t = lab["available_utc_us"].to_numpy(np.int64)
        ok = lab["evaluation_eligible"].fillna(False).to_numpy(bool) & lab["context_as_of_ok"].fillna(False).to_numpy(bool)
        st = lab["context_state"].astype(object).to_numpy()
        self.c = np.where(ok & pd.notna(st), st, None)

    def at_ns(self, t_ns: int):
        t_us = int(t_ns) // 1000                     # entero; piso: una etiqueta publicada a t_us exacto sí está disponible
        i = int(np.searchsorted(self.t, t_us, side="right")) - 1
        if i < 0 or t_us - int(self.t[i]) > MAX_AGE_US:
            return None
        return self.c[i]


def terciles(allv):
    return np.quantile(allv, [1 / 3, 2 / 3])


def ter_of(x, cut):
    return -1 if np.isnan(x) else (0 if x <= cut[0] else (2 if x > cut[1] else 1))


def tod_s(t_ns):
    return (int(t_ns) // 1_000_000_000) % 86400


def pick_controls(pool, s, tod, ter, clima, rng, n=N_CTRL):
    """pool: dict con arrays ses, tod, ter, clima. clima=None → control sin condición de clima (secundario)."""
    dt = np.abs(pool["tod"] - tod); dt = np.minimum(dt, 86400 - dt)
    m = (pool["ses"] != s) & (dt <= TOD_WIN_S) & (pool["ter"] == ter)
    if clima is not None:
        m &= pool["clima"] == clima
    idx = np.flatnonzero(m)
    if len(idx) < n:
        return None
    return rng.choice(idx, n, replace=False)


def cell_stat(ev, ctrl, ev_ses, ctrl_ses, w):
    """Diferencia ponderada evento − control con pesos de sesión w (índices enteros de sesión).
    ev: (n,), ctrl: (n, k), ev_ses: (n,), ctrl_ses: (n, k). Con w = 1 es la media pareada simple."""
    we = w[ev_ses]
    if we.sum() <= 0:
        return np.nan
    wc = we[:, None] * w[ctrl_ses]
    if wc.sum() <= 0:
        return np.nan
    return float((we * ev).sum() / we.sum() - (wc * ctrl).sum() / wc.sum())


def joint_maxT(cells, n_ses, n_boot=N_BOOT, seed=SEED + 7):
    """cells: lista de dict(ev, ctrl, ev_ses, ctrl_ses). Pesos multinomiales COMUNES a todas las celdas por réplica."""
    rng = np.random.default_rng(seed)
    Wb = rng.multinomial(n_ses, np.ones(n_ses) / n_ses, size=n_boot).astype(float)
    ones = np.ones(n_ses)
    obs = np.array([cell_stat(c["ev"], c["ctrl"], c["ev_ses"], c["ctrl_ses"], ones) for c in cells])
    B = np.array([[cell_stat(c["ev"], c["ctrl"], c["ev_ses"], c["ctrl_ses"], w) for c in cells] for w in Wb])
    se = np.nanstd(B, axis=0)
    T = np.abs((B - obs) / se)
    mx = np.nanmax(np.where(np.isnan(T), -np.inf, T), axis=1) if len(cells) else None
    crit = float(np.quantile(mx[np.isfinite(mx)], .95)) if len(cells) else None
    ic = np.nanquantile(B, [.05, .95], axis=0) if len(cells) else np.zeros((2, 0))
    return obs, se, crit, ic


def main():
    ap = argparse.ArgumentParser()
    for k in ("--bars", "--labels", "--gate", "--out"):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    from edgelab.bridge.indicators import espejo_impulsos as K
    from edgelab.research.espejo_nulo import simulate_null

    gate = json.loads(Path(a.gate).read_text(encoding="utf-8"))
    eval_ids = sorted(map(str, gate["plan"]["eval_ids"]))
    assert len(eval_ids) == 40 and eval_ids_sha(eval_ids) == EVAL_IDS_SHA256, "eval_ids no coinciden con los congelados"
    lab = pd.read_parquet(a.labels)
    CL = ClimaLookup(lab)
    sid = {s: i for i, s in enumerate(eval_ids)}
    S, sin_velas = {}, []
    for s in eval_ids:
        f = Path(a.bars) / f"{s}.npz"
        if not f.exists():
            sin_velas.append(s); continue
        z = np.load(f); h, l, c, v = (z[q].astype(float) for q in ("h", "l", "c", "v")); t_ns = z["t_ns"].astype(np.int64)
        assert int(t_ns.max()) < HOLDOUT_NS, f"{s}: vela en el holdout"
        H, L, C, V, T = agg(h, l, c, v, t_ns)
        o = np.r_[c[0], c[:-1]]
        S[s] = dict(H=H, L=L, C=C, V=V, T=T, n=len(C), vol=vol_prev(C), vol1=vol_prev_v1(C),
                    trip=np.column_stack([c - o, h - o, l - o]))
    allv = np.concatenate([D["vol"][~np.isnan(D["vol"])] for D in S.values()]); cut = terciles(allv)
    allv1 = np.concatenate([D["vol1"][~np.isnan(D["vol1"])] for D in S.values()]); cut1 = terciles(allv1)
    cand = [(s, q) for s, D in S.items() for q in range(20, D["n"] - 2)]
    pool = dict(ses=np.array([s for s, _ in cand]), q=np.array([q for _, q in cand]),
                tod=np.array([tod_s(S[s]["T"][q]) for s, q in cand]),
                ter=np.array([ter_of(S[s]["vol"][q], cut) for s, q in cand]),
                clima=np.array([CL.at_ns(S[s]["T"][q]) for s, q in cand], dtype=object))
    ter1 = np.array([ter_of(S[s]["vol1"][q], cut1) for s, q in cand])
    comp_vol = dict(acuerdo_tercil_v1_v2=float(np.mean(ter1 == pool["ter"])), n=int(len(cand)))
    soporte = {cl: int((pool["clima"] == cl).sum()) for cl in CLIMAS}
    soporte["sin_clima"] = int(sum(x is None for x in pool["clima"]))
    rng = np.random.default_rng(SEED)
    out = {}
    for lvl, (mw, mb) in LEVELS.items():
        rows, sin_ctrl, cnt = [], [], dict(sin_clima=0, sin_control_mismo_clima=0, sin_W=0, sesiones_cortas=0)
        for s, D in S.items():
            n = D["n"]
            if n < 60:
                cnt["sesiones_cortas"] += 1; continue
            H, L, C, V, T = D["H"], D["L"], D["C"], D["V"], D["T"]
            res = K.run(T / 1e9, np.r_[C[0], C[:-1]], H, L, C, V, np.zeros(n, int),
                        params=dict(e_max=1.01, atr_k=None, min_w=float(mw), max_bars=mb))
            comp = [e for e in res["events"] if e["kind"] == "MIRROR_COMPLETED"]
            imps = {im["imp_id"]: im for im in res["impulses"]}
            if len(comp) > CAP_SES:
                comp = [comp[i] for i in np.sort(rng.choice(len(comp), CAP_SES, replace=False))]
            for e in comp:
                im = imps[e["imp_id"]]; k = e["bar"]; d = im["dir"]; A = im["A"]; W = im["W"]
                E = A; j = None
                for q in range(k, n - 1):
                    E = min(E, L[q]) if d == 1 else max(E, H[q])
                    if d * (C[q] - A) > 0:
                        j = q; break
                if j is None or not W:
                    cnt["sin_W"] += 1; continue
                end = min(j + HZ, n - 1)
                clima = CL.at_ns(T[j])
                if clima is None:
                    cnt["sin_clima"] += 1; continue
                ter = ter_of(D["vol"][j], cut); tod = tod_s(T[j])
                cp = pick_controls(pool, s, tod, ter, clima, rng)
                if cp is None:
                    cnt["sin_control_mismo_clima"] += 1; sin_ctrl.append(dict(clima=clima, session=s)); continue
                cp2 = pick_controls(pool, s, tod, ter, None, rng)
                fail = E - d * 1
                r = dict(session=s, clima=clima, post_roll=s >= ROLL, O=float(d * (A - E) / W), ev={}, ctrl={}, ctrl_ses=[str(pool["ses"][i]) for i in cp],
                         ctrl_sc={}, ctrl_sc_ses=[str(pool["ses"][i]) for i in cp2] if cp2 is not None else None, sint={})
                p = D["trip"][:j * M]
                for x in XS:
                    tgt = A + d * x * W
                    r["ev"][str(x)] = outcome_from_close(H, L, C, j, tgt, fail, d, end)
                    if r["ev"][str(x)] is None:
                        continue
                    for key, pick in (("ctrl", cp), ("ctrl_sc", cp2)):
                        if pick is None:
                            continue
                        hits = []
                        for ci in pick:
                            Dc = S[pool["ses"][ci]]; q = int(pool["q"][ci])
                            hits.append(outcome_from_close(Dc["H"], Dc["L"], Dc["C"], q, Dc["C"][q] + (tgt - C[j]), Dc["C"][q] + (fail - C[j]), d,
                                                           min(q + (end - j), Dc["n"] - 1)))
                        r[key][str(x)] = hits
                    if len(p) >= 50:
                        seed = int(hashlib.sha256(f"{lvl}|{s}|{j}|{x}".encode()).hexdigest()[:8], 16)
                        r["sint"][str(x)] = simulate_null(C[j], tgt, fail, d, p, end - j, n=300, seed=seed, bars_per_step=M)["completa"]
                rows.append(r)
        out[lvl] = dict(eventos=rows, sin_control=sin_ctrl, reconciliacion=reconciliar(rows, sin_ctrl), **cnt)
        print(lvl, "eventos", len(rows), cnt, flush=True)

    def build(X, x="0.25", key="ctrl", seskey="ctrl_ses"):
        X = [r for r in X if r.get(seskey) and r["ev"].get(x) is not None]
        return dict(ev=np.array([r["ev"][x] for r in X], float), ctrl=np.array([r[key][x] for r in X], float).reshape(len(X), N_CTRL),
                    ev_ses=np.array([sid[r["session"]] for r in X], int),
                    ctrl_ses=np.array([[sid[c] for c in r[seskey]] for r in X], int).reshape(len(X), N_CTRL), n_ses=len({r["session"] for r in X}), n=len(X))

    # primarias: x = 0,25, nivel × clima, control del mismo clima, max-T conjunto sobre las celdas evaluables
    prim, fam = [], []
    for lvl, O in out.items():
        for cl in CLIMAS:
            c = build([r for r in O["eventos"] if r["clima"] == cl])
            info = dict(nivel=lvl, clima=cl, estudio="barreras desde el cierre de señal (no ejecución ni rentabilidad)", **O["reconciliacion"][cl], n_eventos=c["n"], n_sesiones=c["n_ses"], n_controles=c["n"] * N_CTRL)
            if c["n"] < MIN_EVENTOS or c["n_ses"] < MIN_SESIONES:
                info["inconclusa_por_potencia"] = True
            else:
                fam.append((info, c))
            prim.append(info)
    obs, se, crit, ic = joint_maxT([c for _, c in fam], len(eval_ids))
    for k, (info, c) in enumerate(fam):
        info.update(llega_evento=float(c["ev"].mean()), llega_control=float(c["ctrl"].mean()), dif=float(obs[k]), se=float(se[k]),
                    t=float(obs[k] / se[k]), ic90=[float(ic[0, k]), float(ic[1, k])], mde80=2.8 * float(se[k]),
                    sobrevive_maxT=bool(abs(obs[k] / se[k]) >= crit))
    # secundarias descriptivas (IC marginales, sin corrección familiar)
    sec = {}
    for lvl, O in out.items():
        E = O["eventos"]
        for name, X, key, sk in (("global_mismo_clima", E, "ctrl", "ctrl_ses"), ("global_sin_cond_clima", E, "ctrl_sc", "ctrl_sc_ses"),
                                 ("pre_roll_mismo_clima", [r for r in E if not r["post_roll"]], "ctrl", "ctrl_ses")):
            for x in XS:
                c = build(X, str(x), key, sk)
                if c["n"] < MIN_EVENTOS or c["n_ses"] < MIN_SESIONES:
                    sec[f"{lvl}|{name}|{x}"] = dict(n=c["n"], n_sesiones=c["n_ses"], inconclusa_por_potencia=True); continue
                o, s_, _, i_ = joint_maxT([c], len(eval_ids))
                sec[f"{lvl}|{name}|{x}"] = dict(n=c["n"], n_sesiones=c["n_ses"], dif=float(o[0]), se=float(s_[0]), ic90=[float(i_[0, 0]), float(i_[1, 0])])
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "nq_cruce25_clima.json").write_text(json.dumps(dict(
        eval_ids=eval_ids, sin_velas=sin_velas, cortes_vol=list(map(float, cut)), comparacion_vol=comp_vol, soporte_control=soporte,
        t_critico=crit, familia=len(fam), primarias=prim, secundarias=sec, detalle=out), default=float), encoding="utf-8")
    for c in prim:
        print(c if "t" not in c else f"{c['nivel']} {c['clima']:8s} n {c['n_eventos']} ses {c['n_sesiones']} evento {c['llega_evento']:.3f} "
              f"control {c['llega_control']:.3f} dif {c['dif']:+.3f} {[round(v, 3) for v in c['ic90']]} t {c['t']:.2f} maxT {c['sobrevive_maxT']}")
    print("t crítico", crit, "familia", len(fam), "sin velas", sin_velas)


if __name__ == "__main__":
    main()
