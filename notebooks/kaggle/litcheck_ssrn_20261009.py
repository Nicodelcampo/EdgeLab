#!/usr/bin/env python3
r"""LITCHECK-SSRN-20261009: contraste EXPLORATORIO de 5 hallazgos SSRN sobre ticks CME de ES y NQ.

Propuesto por el Edge Brain (edgelab/edge_brain/literature_planner.py, consultas en docs/research/
LITCHECK_SSRN_20261009.md). Pre-registro: este archivo (hipotesis, metricas, umbrales y reglas de veredicto se
fijan ANTES de leer datos; su sha256 y el commit quedan en la attestation). Solo descriptivo: no promueve ni
descarta estrategias. Particion EXPLORATION = sesiones aprobadas por el resolver entre 2025-07-01 y 2026-06-30
(pre-holdout tambien bajo la definicion vieja 2026-07-01; HOLDOUT-A1 = desde 2026-10-01: no se toca).

Hipotesis (H) -> metrica primaria -> regla (IC bootstrap por sesion al 99.5 %, Bonferroni 0.05/10 pruebas):
 H1 CLAIM-SSRN-FINDING-0439 (SRC-SSRN-0174) volumen y trades suben en marcas horarias, mas en :00/:30 que en
    :10 y :05. Ventanas de 30 s en RTH 08:40-14:55 CT sin 08:55-09:05, 12:55-13:05, 13:25-13:35 CT. Exceso de una
    marca = log((v_marca+1)/(media v vecinas+1)); vecinas = ventanas :30 s a 2.5-5 min de la marca.
    CONSISTENT: exceso HORA y MEDIA > 0 (IC inf > 0) y Spearman(redondez, exceso) >= 0.8.
    INCONSISTENT: IC de HORA incluye 0 o Spearman <= 0.4. Si no, INCONCLUSIVE.
 H2 CLAIM-SSRN-FINDING-0440 (SRC-SSRN-0174) el impacto en precio (lambda de Kyle) es mayor en las marcas.
    lambda = sum(dp*q)/sum(q^2) por categoria (dp cierre-a-cierre de la ventana en ticks, q volumen firmado).
    CONSISTENT: lambda_HORA/lambda_vecinas > 1 y lambda_DIEZ/lambda_vecinas > 1 (IC inf > 1).
    INCONSISTENT: IC sup de la razon HORA < 1, o IC de HORA incluye 1. Si no, INCONCLUSIVE.
 H3 CLAIM-SSRN-FINDING-0168 (SRC-SSRN-0051) continuidad del flujo: P(compra|compra) > 0.5 y P(venta|venta) > 0.5.
    "Orden" = racha de prints consecutivos con mismo ts_utc_ns y mismo agresor (un barrido = una orden).
    CONSISTENT: medianas por sesion de ambas > 0.5 y >= 80 % de sesiones con ambas > 0.5.
    INCONSISTENT: alguna mediana <= 0.5. Si no, INCONCLUSIVE. (Asimetria venta>compra: solo descriptiva.)
 H4 CLAIM-SSRN-FINDING-0609 (SRC-SSRN-0265) el numero de trades explica la volatilidad mas que el tamano medio.
    Barras de 5 min RTH (sin primera y ultima); |dp| en ticks ~ z(log n_trades) + z(log tamano medio), efectos fijos
    de sesion y de franja horaria. CONSISTENT: b_n > 0 (IC inf > 0) y b_n - b_size > 0 (IC inf > 0).
    INCONSISTENT: IC sup de b_n - b_size < 0 o IC de b_n incluye 0. Si no, INCONCLUSIVE.
 H5 CLAIM-SSRN-FINDING-0200 (SRC-SSRN-0063) el desbalance de volumen predice el movimiento de corto plazo.
    Barras de 1 min RTH; OI_t = volumen firmado / volumen; corr(OI_t, dp_{t+1}) agrupada (por sesion, demean).
    CONSISTENT: corr > 0 (IC inf > 0). INCONSISTENT: IC incluye 0 o IC sup <= 0. Secundario descriptivo:
    P(|dp_{t+1}| >= 2 ticks) en el quintil superior vs inferior de |OI_t|.
Veredicto por hallazgo: CONSISTENT_EXPLORATORY si ES y NQ son CONSISTENT; INCONSISTENT_EXPLORATORY si ambos son
INCONSISTENT; si no, INCONCLUSIVE. Nada de esto es confirmatorio (EXPLORAR != CONFIRMAR).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RUN_ID = "LITCHECK-SSRN-20261009"
EXPECTED_COMMIT = os.environ.get("EDGELAB_EXPECTED_COMMIT", "UNSET")
INSTRUMENTS = ("ES", "NQ")
DESDE, HASTA = "2025-07-01", "2026-06-30"
OLD_HOLDOUT, SEED, NBOOT, ALPHA = "2026-07-01", 20261009, 2000, 0.005
CT = "America/Chicago"
RTH0, RTH1 = 8 * 3600 + 30 * 60, 15 * 3600            # 08:30-15:00 CT
EXCL = [(8 * 3600 + 30 * 60, 8 * 3600 + 40 * 60), (8 * 3600 + 55 * 60, 9 * 3600 + 5 * 60),
        (12 * 3600 + 55 * 60, 13 * 3600 + 5 * 60), (13 * 3600 + 25 * 60, 13 * 3600 + 35 * 60),
        (14 * 3600 + 55 * 60, 15 * 3600)]
CATS = ("HOUR", "HALF", "TEN", "FIVE", "MINUTE")       # redondez 4..0
ROUND = {c: 4 - i for i, c in enumerate(CATS)}

KAGGLE = Path("/kaggle/input").exists()
OUT = Path("/kaggle/working") if KAGGLE else Path(os.environ.get("LITCHECK_OUT", "/tmp/litcheck"))
OUT.mkdir(parents=True, exist_ok=True)


def _setup_catalog():
    roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")] if KAGGLE else \
        [Path(p) for p in os.environ.get("EDGELAB_DATA_ROOTS", "").split(os.pathsep) if p]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in roots)
    cat = next(p.parent for r in roots for p in r.glob("**/edgelab_data.py"))
    sys.path.insert(0, str(cat))
    import edgelab_data as ed
    return ed, cat


# ---------- calculos por sesion (puros: testeados con datos sinteticos) ----------

def ct_seconds(ts_ns: np.ndarray) -> np.ndarray:
    """Segundo del dia en hora de Chicago (convierte una vez por hora UTC: el offset no cambia dentro de la hora)."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    hours, inv = np.unique(ts // 3_600_000_000_000, return_inverse=True)
    loc = pd.to_datetime(hours * 3_600_000_000_000, utc=True).tz_convert(CT)
    off = np.asarray((loc.tz_localize(None) - pd.to_datetime(hours * 3_600_000_000_000)).total_seconds(), dtype=np.int64)
    return ((ts // 1_000_000_000 + off[inv]) % 86400).astype(np.int64)


def _excluded(sec: np.ndarray) -> np.ndarray:
    m = np.zeros(len(sec), dtype=bool)
    for a, b in EXCL:
        m |= (sec >= a) & (sec < b)
    return m


def mark_category(start_sec: int) -> str | None:
    mm, ss = (start_sec // 60) % 60, start_sec % 60
    if ss == 30:
        return None
    if mm == 0:
        return "HOUR"
    if mm == 30:
        return "HALF"
    if mm % 10 == 0:
        return "TEN"
    if mm % 5 == 0:
        return "FIVE"
    return "MINUTE"


def bin_session(sec, price, vol, sign, width):
    """Agrega una sesion RTH en ventanas de `width` s: volumen, trades, volumen firmado, ultimo precio."""
    m = (sec >= RTH0) & (sec < RTH1)
    sec, price, vol, sign = sec[m], price[m], vol[m], sign[m]
    nb = (RTH1 - RTH0) // width
    b = (sec - RTH0) // width
    v = np.bincount(b, weights=vol, minlength=nb)
    n = np.bincount(b, minlength=nb).astype(float)
    q = np.bincount(b, weights=vol * sign, minlength=nb)
    last = np.full(nb, np.nan)
    if len(b):
        idx = np.flatnonzero(np.r_[b[1:] != b[:-1], True])
        last[b[idx]] = price[idx]
    last = pd.Series(last).ffill().to_numpy()
    dp = np.r_[np.nan, np.diff(last)]
    return v, n, q, dp


def h12_session(sec, price, vol, sign):
    """Por categoria de marca: sumas de exceso log (vol, trades) y de dp*q, q^2 en marca y en vecinas."""
    v, n, q, dp = bin_session(sec, price, vol, sign, 30)
    starts = RTH0 + 30 * np.arange(len(v))
    excl = _excluded(starts)
    out = {c: dict(k=0, ex_v=0.0, ex_n=0.0, lam_num=0.0, lam_den=0.0, nb_num=0.0, nb_den=0.0) for c in CATS}
    base = np.flatnonzero((starts % 60 == 30) & ~excl)
    for i, s0 in enumerate(starts):
        c = mark_category(int(s0))
        if c is None or excl[i]:
            continue
        d = np.abs(starts[base] - s0)
        nb_ = base[(d >= 150) & (d <= 300)]
        if len(nb_) < 3 or np.isnan(dp[i]):
            continue
        o = out[c]
        o["k"] += 1
        o["ex_v"] += np.log((v[i] + 1) / (v[nb_].mean() + 1))
        o["ex_n"] += np.log((n[i] + 1) / (n[nb_].mean() + 1))
        o["lam_num"] += dp[i] * q[i]; o["lam_den"] += q[i] ** 2
        ok = ~np.isnan(dp[nb_])
        o["nb_num"] += float(np.sum(dp[nb_][ok] * q[nb_][ok])) / max(1, ok.sum())
        o["nb_den"] += float(np.sum(q[nb_][ok] ** 2)) / max(1, ok.sum())
    return out


def h3_session(ts, sign):
    """Rachas mismo-ts-mismo-agresor = una orden. Devuelve conteos de transiciones (orden y print)."""
    m = sign != 0
    ts, s = ts[m], sign[m]
    if len(s) < 3:
        return None
    new = np.r_[True, (ts[1:] != ts[:-1]) | (s[1:] != s[:-1])]
    o = s[new]
    def tr(x):
        a, b = x[:-1], x[1:]
        return dict(bb=int(np.sum((a > 0) & (b > 0))), bs=int(np.sum((a > 0) & (b < 0))),
                    ss=int(np.sum((a < 0) & (b < 0))), sb=int(np.sum((a < 0) & (b > 0))))
    return dict(orders=tr(o), prints=tr(s), n_orders=int(len(o)), n_prints=int(len(s)))


def h4_session(sec, price, vol, sign):
    v, n, q, dp = bin_session(sec, price, vol, sign, 300)
    k = np.arange(len(v))
    ok = (n > 0) & ~np.isnan(dp) & (k > 0) & (k < len(v) - 1)
    return pd.DataFrame(dict(slot=k[ok], absdp=np.abs(dp[ok]), lnn=np.log(n[ok]), lnsize=np.log(v[ok] / n[ok])))


def h5_session(sec, price, vol, sign):
    v, n, q, dp = bin_session(sec, price, vol, sign, 60)
    oi = np.where(v > 0, q / np.maximum(v, 1), np.nan)
    nxt = np.r_[dp[1:], np.nan]
    ok = ~np.isnan(oi) & ~np.isnan(nxt) & ~np.isnan(dp)
    return pd.DataFrame(dict(oi=oi[ok], dp=dp[ok], dp_next=nxt[ok]))


# ---------- resumen con bootstrap por sesion ----------

def _ci(samples):
    lo, hi = np.nanquantile(samples, [ALPHA / 2, 1 - ALPHA / 2])
    return [float(lo), float(hi)]


def _spearman(x, y):
    return float(pd.Series(x).rank().corr(pd.Series(y).rank()))


def summarize(inst, per_session, rng):
    S = sorted(per_session)
    B = [rng.integers(0, len(S), len(S)) for _ in range(NBOOT)]
    res = {"instrument": inst, "sessions": len(S), "first_session": S[0], "last_session": S[-1]}
    # H1/H2
    arr = {c: np.array([[per_session[s]["h12"][c][f] for f in ("k", "ex_v", "ex_n", "lam_num", "lam_den", "nb_num", "nb_den")]
                        for s in S]) for c in CATS}
    def h1stat(idx):
        return {c: arr[c][idx, 1].sum() / max(1, arr[c][idx, 0].sum()) for c in CATS}
    def h2stat(idx, c):
        a = arr[c][idx]
        lam, nb = a[:, 3].sum() / a[:, 4].sum(), a[:, 5].sum() / a[:, 6].sum()
        return lam / nb
    ex = h1stat(np.arange(len(S)))
    exn = {c: arr[c][:, 2].sum() / max(1, arr[c][:, 0].sum()) for c in CATS}
    boots = [h1stat(i) for i in B]
    ci1 = {c: _ci([b[c] for b in boots]) for c in CATS}
    rho = _spearman([ROUND[c] for c in CATS], [ex[c] for c in CATS])
    v1 = "CONSISTENT" if ci1["HOUR"][0] > 0 and ci1["HALF"][0] > 0 and rho >= 0.8 else \
        "INCONSISTENT" if (ci1["HOUR"][0] <= 0 <= ci1["HOUR"][1]) or rho <= 0.4 else "INCONCLUSIVE"
    res["H1"] = dict(claim="CLAIM-SSRN-FINDING-0439", excess_log_volume=ex, excess_log_trades=exn, ci=ci1,
                     spearman_roundness=rho, marks={c: int(arr[c][:, 0].sum()) for c in CATS}, verdict=v1,
                     paper_magnitude="+15.7% volumen, +18.3% trades en horas en punto")
    r2 = {c: h2stat(np.arange(len(S)), c) for c in CATS}
    ci2 = {c: _ci([h2stat(i, c) for i in B]) for c in ("HOUR", "HALF", "TEN")}
    v2 = "CONSISTENT" if ci2["HOUR"][0] > 1 and ci2["TEN"][0] > 1 else \
        "INCONSISTENT" if ci2["HOUR"][1] < 1 or (ci2["HOUR"][0] <= 1 <= ci2["HOUR"][1]) else "INCONCLUSIVE"
    res["H2"] = dict(claim="CLAIM-SSRN-FINDING-0440", kyle_lambda_ratio=r2, ci=ci2, verdict=v2,
                     paper_magnitude="impacto +10% en :00 y :10, +8% en :30")
    # H3
    pbb, pss, pbb_p, pss_p, both = [], [], [], [], 0
    for s in S:
        h = per_session[s]["h3"]
        if not h:
            continue
        o, p = h["orders"], h["prints"]
        a, b = o["bb"] / max(1, o["bb"] + o["bs"]), o["ss"] / max(1, o["ss"] + o["sb"])
        pbb.append(a); pss.append(b); both += int(a > 0.5 and b > 0.5)
        pbb_p.append(p["bb"] / max(1, p["bb"] + p["bs"])); pss_p.append(p["ss"] / max(1, p["ss"] + p["sb"]))
    share = both / max(1, len(pbb))
    mb, ms = float(np.median(pbb)), float(np.median(pss))
    v3 = "CONSISTENT" if mb > 0.5 and ms > 0.5 and share >= 0.8 else "INCONSISTENT" if mb <= 0.5 or ms <= 0.5 else "INCONCLUSIVE"
    res["H3"] = dict(claim="CLAIM-SSRN-FINDING-0168", median_p_buy_after_buy=mb, median_p_sell_after_sell=ms,
                     share_sessions_both_gt_half=share, prints_median_p_bb=float(np.median(pbb_p)),
                     prints_median_p_ss=float(np.median(pss_p)), sell_continuity_gt_buy_share=float(np.mean(np.array(pss) > np.array(pbb))),
                     verdict=v3, paper_magnitude="P[b|b]=0.58, P[s|s]=0.60 (SET 1997)")
    # H4
    d4 = pd.concat([per_session[s]["h4"].assign(session=s) for s in S], ignore_index=True)
    for col in ("absdp", "lnn", "lnsize"):
        d4[col + "_d"] = d4[col] - d4.groupby("session")[col].transform("mean")
        d4[col + "_d"] -= d4.groupby("slot")[col + "_d"].transform("mean")
    for col in ("lnn_d", "lnsize_d"):
        d4[col] = d4[col] / d4[col].std()
    g4 = {s: g[["absdp_d", "lnn_d", "lnsize_d"]].to_numpy() for s, g in d4.groupby("session")}
    def ols(idx):
        M = np.concatenate([g4[S[i]] for i in idx if S[i] in g4])
        X, y = M[:, 1:], M[:, 0]
        return np.linalg.lstsq(X, y, rcond=None)[0]
    b = ols(range(len(S)))
    bb = np.array([ols(i) for i in B])
    ci_n, ci_d = _ci(bb[:, 0]), _ci(bb[:, 0] - bb[:, 1])
    v4 = "CONSISTENT" if ci_n[0] > 0 and ci_d[0] > 0 else "INCONSISTENT" if ci_d[1] < 0 or ci_n[0] <= 0 <= ci_n[1] else "INCONCLUSIVE"
    res["H4"] = dict(claim="CLAIM-SSRN-FINDING-0609", beta_n_trades=float(b[0]), beta_avg_size=float(b[1]),
                     ci_beta_n=ci_n, ci_diff=ci_d, bars=int(len(d4)), verdict=v4,
                     paper_magnitude="numero de trades domina sobre tamano (ASX rate futures)")
    # H5
    g5 = {}
    for s in S:
        d = per_session[s]["h5"]
        if len(d) > 10:
            x = d.oi.to_numpy() - d.oi.mean(); y = d.dp_next.to_numpy() - d.dp_next.mean(); z = d.dp.to_numpy() - d.dp.mean()
            g5[s] = np.array([np.sum(x * y), np.sum(x * x), np.sum(y * y), np.sum(x * z), np.sum(z * z)])
    def corr(idx):
        a = np.sum([g5[S[i]] for i in idx if S[i] in g5], axis=0)
        return a[0] / np.sqrt(a[1] * a[2]), a[3] / np.sqrt(a[1] * a[4])
    c_next, c_now = corr(range(len(S)))
    cb = np.array([corr(i) for i in B])
    ci5 = _ci(cb[:, 0])
    d5 = pd.concat([per_session[s]["h5"] for s in S], ignore_index=True)
    qx = pd.qcut(d5.oi.abs().rank(method="first"), 5, labels=False)
    jump = (d5.dp_next.abs() >= 2)
    v5 = "CONSISTENT" if ci5[0] > 0 else "INCONSISTENT"
    res["H5"] = dict(claim="CLAIM-SSRN-FINDING-0200", corr_oi_next=float(c_next), ci=ci5, corr_oi_same_minute=float(c_now),
                     ci_same_minute=_ci(cb[:, 1]), p_jump_top_quintile=float(jump[qx == 4].mean()),
                     p_jump_bottom_quintile=float(jump[qx == 0].mean()), minutes=int(len(d5)), verdict=v5,
                     paper_magnitude="cualitativo: imbalance alto -> mas market orders y saltos del mid")
    return res


def sha256_file(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def main():
    t0 = time.time()
    ed, cat = _setup_catalog()
    assert HASTA < OLD_HOLDOUT <= ed.HOLDOUT, "particion debe ser pre-holdout"
    ed.check_inputs(*[(i, DESDE, HASTA) for i in INSTRUMENTS])
    rng = np.random.default_rng(SEED)
    results, inputs, sessions_used = {}, {}, {}
    for inst in INSTRUMENTS:
        src = ed.resolve_sources(inst, DESDE, HASTA)
        for ds, fl in sorted({(d, f) for d, f in zip(src.dataset, src.file)}):
            p = ed._path(ds, fl)
            inputs[f"{ds}/{fl}"] = dict(bytes=p.stat().st_size, sha256=sha256_file(p))
        months = pd.period_range(DESDE, HASTA, freq="M")
        per = {}
        for mth in months:
            a, b = str(mth.start_time.date()), str(min(mth.end_time.date(), pd.Timestamp(HASTA).date()))
            df = ed.load_ticks(inst, a, b, columns=["ts_utc_ns", "price_ticks", "volume", "aggressor", "tick_type"])
            if not len(df):
                continue
            df = df[df.tick_type == "trade"]
            assert df.session_date.max() < OLD_HOLDOUT
            for sd, g in df.groupby("session_date", sort=True):
                ts = g.ts_utc_ns.to_numpy(np.int64)
                sec = ct_seconds(ts)
                px = g.price_ticks.to_numpy(np.float64)
                vol = g.volume.to_numpy(np.float64)
                sign = np.where(g.aggressor.to_numpy() == "buy", 1.0, np.where(g.aggressor.to_numpy() == "sell", -1.0, 0.0))
                per[sd] = dict(h12=h12_session(sec, px, vol, sign), h3=h3_session(ts, sign),
                               h4=h4_session(sec, px, vol, sign), h5=h5_session(sec, px, vol, sign))
            print(inst, mth, len(df), "trades", f"{time.time() - t0:.0f}s", flush=True)
            del df
        sessions_used[inst] = sorted(per)
        results[inst] = summarize(inst, per, rng)
        print(json.dumps({k: v.get("verdict") for k, v in results[inst].items() if isinstance(v, dict)}), flush=True)
    claims = {}
    for h in ("H1", "H2", "H3", "H4", "H5"):
        vs = [results[i][h]["verdict"] for i in INSTRUMENTS]
        claims[results[INSTRUMENTS[0]][h]["claim"]] = dict(
            hypothesis=h, per_instrument=dict(zip(INSTRUMENTS, vs)),
            verdict="CONSISTENT_EXPLORATORY" if all(v == "CONSISTENT" for v in vs) else
            "INCONSISTENT_EXPLORATORY" if all(v == "INCONSISTENT" for v in vs) else "INCONCLUSIVE")
    me = Path(__file__).resolve() if "__file__" in globals() else None
    attestation = dict(run_id=RUN_ID, expected_commit=EXPECTED_COMMIT,
                       script_sha256=sha256_file(me) if me and me.exists() else None,
                       catalog_dir=str(cat), resolver_sha256=sha256_file(Path(cat) / "RESOLVER.json"),
                       edgelab_data_sha256=sha256_file(Path(cat) / "edgelab_data.py"),
                       partition=dict(role="EXPLORATION", desde=DESDE, hasta=HASTA,
                                      sessions={i: len(s) for i, s in sessions_used.items()}),
                       holdout_first_trade_date=ed.HOLDOUT, old_holdout=OLD_HOLDOUT,
                       max_session_read={i: s[-1] for i, s in sessions_used.items()},
                       holdout_touched=any(s[-1] >= OLD_HOLDOUT for s in sessions_used.values()),
                       returns_used_for="H2 (lambda), H4 (|dp|), H5 (dp siguiente): descriptivo, sin P&L",
                       pnl_computed=False, tests=10, alpha_per_test=ALPHA, n_boot=NBOOT, seed=SEED,
                       inputs=inputs, dropped_sessions=list(getattr(ed, "DROPPED", [])),
                       runtime_s=round(time.time() - t0, 1))
    (OUT / "results.json").write_text(json.dumps(dict(results=results, claims=claims), indent=1, sort_keys=True, default=float))
    (OUT / "sessions.json").write_text(json.dumps(sessions_used, indent=0))
    (OUT / "execution_attestation.json").write_text(json.dumps(attestation, indent=1, sort_keys=True))
    files = ["results.json", "sessions.json", "execution_attestation.json"]
    manifest = {f: dict(bytes=(OUT / f).stat().st_size, sha256=sha256_file(OUT / f)) for f in files}
    (OUT / "artifact_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    with zipfile.ZipFile(OUT / "output.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in files + ["artifact_manifest.json"]:
            info = zipfile.ZipInfo(f, date_time=(2026, 10, 9, 0, 0, 0))
            z.writestr(info, (OUT / f).read_bytes())
    (OUT / "output.zip.sha256").write_text(sha256_file(OUT / "output.zip") + "  output.zip\n")
    print(json.dumps(claims, indent=1), flush=True)
    print("output.zip", sha256_file(OUT / "output.zip"), f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
