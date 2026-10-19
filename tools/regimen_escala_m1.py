"""Etapa 0 en escala mayor (decisión de Nico, 2026-10-06): ¿persiste la tendencia (eficiencia) o la dirección en barras
de 5–60 minutos? Datos: M1 de NT8 (E:\\DatosNT8\\m1_history), serie del contrato líder por calendario de roll (8 días
antes del 3er viernes del mes de vencimiento), holdout excluido (>= 2026-09-30 22:00 UTC). Target-free respecto del P&L.
Para cada escala (5, 15, 30, 60 min) y ventana N (barras):
- autocorrelación del retorno de la ventana con la ventana siguiente (persistencia de DIRECCIÓN);
- autocorrelación de la eficiencia E_N (persistencia de TENDENCIA) contra un nulo de incrementos permutados en la sesión;
- autocorrelación de la amplitud, cruda y desestacionalizada por franja horaria.
Uso: python tools/regimen_escala_m1.py ES"""
import glob
import json
import os
import sys
import datetime as dt

import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\EdgeLab-gex")
from edgelab.regimes import state as S  # noqa: E402

ROOT = r"E:\DatosNT8\m1_history"
HOLDOUT = pd.Timestamp("2026-09-30 22:00", tz="UTC")
SCALES = (5, 15, 30, 60)
NWIN = (6, 12, 24)


def third_friday(y, m):
    d = dt.date(y, m, 15)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def leader_series(inst):
    parts = []
    for d in sorted(glob.glob(os.path.join(ROOT, inst + "_*"))):
        c = os.path.basename(d)
        if not os.path.isdir(d):
            continue
        m, y = int(c[-5:-3]), 2000 + int(c[-2:])
        roll = pd.Timestamp(third_friday(y, m) - dt.timedelta(days=8), tz="America/Chicago")
        prev_m = m - 3 if m > 3 else m + 9
        prev_y = y if m > 3 else y - 1
        start = pd.Timestamp(third_friday(prev_y, prev_m) - dt.timedelta(days=8), tz="America/Chicago")
        fs = sorted(glob.glob(os.path.join(d, "*.m1.utc.csv")))
        if not fs:
            continue
        x = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
        x["t"] = pd.to_datetime(x.time_utc, utc=True)
        ct = x.t.dt.tz_convert("America/Chicago")
        x = x[(ct >= start) & (ct < roll)]
        parts.append(x[["t", "open", "high", "low", "close", "volume"]])
    s = pd.concat(parts).drop_duplicates("t").sort_values("t")
    s = s[s.t < HOLDOUT].reset_index(drop=True)
    ct = s.t.dt.tz_convert("America/Chicago")
    s["session"] = ((s.t - pd.Timedelta(seconds=1)).dt.tz_convert("America/Chicago") + pd.Timedelta(hours=7)).dt.date
    return s


def resample(s, minutes):
    g = s.set_index("t").groupby("session")
    out = []
    for ses, x in g:
        r = x.resample("%dmin" % minutes, label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        r["session"] = ses
        out.append(r)
    b = pd.concat(out)
    b["clock"] = b.index.tz_convert("America/Chicago").hour * 60 + b.index.tz_convert("America/Chicago").minute
    return b


def ac(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1]) if ok.sum() > 30 else float("nan"), int(ok.sum())


def analyze(b, N, rng):
    cl = b.close.to_numpy(float)
    send = pd.factorize(b.session)[0].astype(np.int64)
    n = len(cl)
    t = np.arange(N, n - N, N)
    same = (send[t - N] == send[t]) & (send[t] == send[np.minimum(t + N, n - 1)])
    t = t[same]
    r0 = cl[t] - cl[t - N]; r1 = cl[t + N] - cl[t]
    ret_ac, nret = ac(r0, r1)
    E = S.efficiency(cl, send, N)
    e_ac, _ = ac(E[t], E[t + N])
    nul = []
    for _ in range(3):
        cn = S.null_close(cl, send, rng)
        En = S.efficiency(cn, send, N)
        nul.append(ac(En[t], En[t + N])[0])
    hi = pd.Series(b.high.to_numpy(float)).rolling(N).max().to_numpy()
    lo = pd.Series(b.low.to_numpy(float)).rolling(N).min().to_numpy()
    A = hi - lo
    a_ac, _ = ac(np.log(A[t] + 1e-9), np.log(A[t + N] + 1e-9))
    med = pd.Series(np.log(A + 1e-9)).groupby(b.clock.to_numpy()).transform("median").to_numpy()
    Ad = np.log(A + 1e-9) - med
    ad_ac, _ = ac(Ad[t], Ad[t + N])
    # dirección condicionada a tendencia: autocorrelación de retornos sólo cuando E_t está en el tercio superior
    q = np.nanquantile(E[t], 2 / 3)
    hiE = E[t] > q
    ret_ac_trend, n_tr = ac(r0[hiE], r1[hiE])
    return dict(N=N, ventanas=nret, ac_retorno=ret_ac, ac_retorno_si_tendencia=ret_ac_trend, n_tendencia=n_tr,
                ac_eficiencia=e_ac, ac_eficiencia_nulo=float(np.nanmean(nul)), ac_amplitud=a_ac, ac_amplitud_desest=ad_ac,
                se_aprox=1 / np.sqrt(max(nret, 1)))


def main(inst):
    s = leader_series(inst)
    print(inst, "M1 filas", len(s), s.t.min(), "->", s.t.max(), "sesiones", s.session.nunique(), flush=True)
    rng = np.random.default_rng(20261006)
    res = {}
    for m in SCALES:
        b = resample(s, m)
        for N in NWIN:
            r = analyze(b, N, rng)
            res["%dmin_N%d" % (m, N)] = r
            print("%3d min N=%2d (%5.0f min) | ret_ac %+.3f (tend %+.3f) | E_ac %+.3f nulo %+.3f | amp_ac %.3f desest %.3f | n %d se %.3f"
                  % (m, N, m * N, r["ac_retorno"], r["ac_retorno_si_tendencia"], r["ac_eficiencia"], r["ac_eficiencia_nulo"],
                     r["ac_amplitud"], r["ac_amplitud_desest"], r["ventanas"], r["se_aprox"]), flush=True)
    return res


if __name__ == "__main__":
    inst = sys.argv[1] if len(sys.argv) > 1 else "ES"
    out = main(inst)
    json.dump(out, open(os.path.join(r"E:\EdgeLab-gex\docs\research", "regimen_escala_%s.json" % inst), "w"), indent=1)
