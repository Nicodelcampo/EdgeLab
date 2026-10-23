"""U1-INDAGA sobre el conductor genérico: oráculo de la anatomía compilada, causalidad, y controles ruido / plantado."""
import numpy as np
import pandas as pd
import pytest

from edgelab.research import grilla_generica as GG, u1_indaga as U


def _bloques(dias=40, seed=1, planta=True):
    rng = np.random.default_rng(seed); t0 = 1_760_000_000 * 10**9
    for d in range(dias):
        n = 23 * 60 * 6; ts = t0 + d * 86400 * 10**9 + np.sort(rng.integers(0, 23 * 3600 * 10**9, n))
        paso = rng.choice([-0.25, 0.0, 0.25], n, p=[.33, .34, .33])
        saltos = rng.random(n) < 0.005; paso[saltos] += rng.choice([-1, 1], saltos.sum()) * rng.integers(60, 160, saltos.sum()) * 0.25
        p = 20000 + np.cumsum(paso)
        if planta:                                                     # reversión hacia el nivel previo al salto (efecto plantado)
            ancla = pd.Series(np.where(saltos, np.r_[p[0], p[:-1]], np.nan)).ffill().fillna(p[0]).to_numpy()
            p = p + np.cumsum(0.006 * (ancla - p)) * 0
            q = np.empty(n); q[0] = p[0]
            for i in range(1, n): q[i] = q[i - 1] + paso[i] + 0.03 * (ancla[i] - q[i - 1])
            p = q
        yield pd.DataFrame(dict(ts_ns=ts, px=np.round(p * 4) / 4, vol=rng.integers(1, 6, n).astype(float), sesion=np.full(n, d), segmento=np.zeros(n, int)))


@pytest.fixture(scope="module")
def ctx_plantado():
    return GG.contexto_m1(_bloques(planta=True), tick=0.25)


def test_anatomia_contra_oraculo_python(ctx_plantado):
    D = U.disparos(ctx_plantado)
    assert len(D) > 20
    h, l, c, v = (ctx_plantado[x] for x in "hlcv")
    for r in D.sample(min(25, len(D)), random_state=0).to_dict("records"):
        d, m, k = int(r["lado"]), int(r["m"]), int(r["k"])
        tE = max([j for j in range(m + 1, k + 1) if (h[j] >= r["E"] - 1e-9 if d == 1 else l[j] <= r["E"] + 1e-9)] or [m + 1])
        js = tE
        while js > m + 1 and not (r["lo"] <= c[js - 1] <= r["hi"]): js -= 1
        assert r["dur_ida"] == tE - js + 1 and r["dur_vuelta"] == k - tE
        assert r["vol_ida"] == pytest.approx(v[js:tE + 1].sum()) and r["vol_vuelta"] == pytest.approx(v[tE + 1:k + 1].sum())


def test_variables_causales_no_cambian_al_cortar_el_futuro(ctx_plantado):
    D = U.disparos(ctx_plantado)
    corte = int(np.quantile(D.k, 0.5)); n = corte + 1
    cx = {k: (v[:n] if isinstance(v, np.ndarray) and len(v) == len(ctx_plantado["c"]) else v) for k, v in ctx_plantado.items()}
    cx["vp_start"] = ctx_plantado["vp_start"][:n + 1]; cx["tstart"] = ctx_plantado["tstart"][:n + 1]
    D2 = U.disparos(cx)
    cols = ["k", "dur_ida", "dur_vuelta", "vol_ida", "vol_vuelta", "fr_ida", "fr_vuelta", "r_vol", "vwap_pos"]
    a = D[D.k <= corte - 5][cols].sort_values(cols[:3]).reset_index(drop=True)
    b = D2[D2.k <= corte - 5][cols].sort_values(cols[:3]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def _correr(planta, monkeypatch):
    monkeypatch.setattr(GG, "B_RW", 40)
    ctx = GG.contexto_m1(_bloques(dias=150, planta=planta, seed=3 if planta else 4), tick=0.25)
    res, _ = GG.correr(U, ctx, modo="DESC", friccion=1.0, extra_adverso=0.5, log=lambda s: None)
    return res


def test_control_ruido(monkeypatch):
    res = _correr(False, monkeypatch)
    assert res["canales"]["total"]["evaluables"] > 1000                       # que el control tenga con qué fallar
    assert res["canales"]["total"]["n_rechazadas_rw"] == 0


def test_control_plantado(monkeypatch):
    res = _correr(True, monkeypatch)
    tot = res["canales"]["total"]
    assert tot["n_rechazadas_rw"] > 0 or tot["nominadas_fdr"] > 0
    assert res["indagacion"]["por_perilla"]["ejecución"]                     # marginales armadas alrededor de BASE
    assert GG.n_celdas(U) == res["celdas"]
