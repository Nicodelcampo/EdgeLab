"""U1-COMBO E0: causalidad, conteo, base as-of, oráculo del núcleo compilado."""
import numpy as np
import pandas as pd

from edgelab.research import u1_combo_e0 as C

T = np.arange(1, 601, dtype=np.int64) * 60
G, VIDA = 1.0, 30000.0


def ctx(n=600, c=100.0):
    p = np.full(n, float(c))
    return dict(t=T[:n], o=p, h=p + 1, l=p - 1, c=p, ses=np.arange(n) // 100 + 20250805, seg=np.zeros(n, np.int64))


def nb(zi, lo, hi, fin, src, A=1, B=1, R=2.0, V=500.0, Am=9.0):
    return C._areas_nb(np.array(zi, np.int64), np.array(lo, float), np.array(hi, float), np.array(fin, np.int64), np.array(src, np.int64),
                       T.astype(float), np.ones(len(T)), A, B, R, V, Am, G, VIDA)


def test_conteo_exige_a_y_b_por_fuente():
    args = ([20, 21, 22], [100.0, 100.5, 100.2], [100.3, 100.8, 100.6], [500] * 3, [0, 0, 1])
    assert nb(*args, A=2, B=1)[0].tolist() == [22]
    assert len(nb(*args, A=3, B=1)[0]) == 0
    assert len(nb(*args, A=1, B=2)[0]) == 0


def test_conteo_respeta_rango_ventana_y_amplitud():
    assert len(nb([20, 21], [100, 110], [100.5, 110.5], [500, 500], [0, 1])[0]) == 0
    assert len(nb([20, 21], [100, 100.1], [100.5, 100.6], [500, 500], [0, 1], R=1.0)[0]) == 1
    assert len(nb([20, 80], [100, 100.1], [100.5, 100.6], [500, 500], [0, 1], V=30.0)[0]) == 0
    assert len(nb([20, 21], [100, 100.1], [101.5, 100.6], [500, 500], [0, 1], Am=1.0)[0]) == 0


def test_dos_marcas_pegadas_cuentan_una():
    m = nb([20, 21, 30, 31], [100, 100.1, 100.2, 100.3], [100.4, 100.5, 100.6, 100.7], [500] * 4, [0, 1, 0, 1])[0]
    assert m.tolist() == [21]


def test_zona_vencida_no_cuenta():
    assert len(nb([20, 21], [100, 100.1], [100.4, 100.5], [21, 500], [0, 1])[0]) == 0


def test_oraculo_con_empates():
    r = np.random.default_rng(3); no_vacios = 0
    for _ in range(150):
        k = int(r.integers(2, 45)); zi = np.sort(r.integers(15, 300, k)); lo = r.integers(0, 12, k) * 0.25 + 100
        hi = lo + r.integers(0, 6, k) * 0.25; fin = zi + r.integers(1, 200, k); src = r.integers(0, 2, k)
        a = r.choice([1.0, 2.0], len(T)); a[:5] = np.nan
        p = (int(r.integers(1, 3)), int(r.integers(1, 3)), float(r.choice([0.5, 1, 2])), float(r.choice([20, 100])), float(r.choice([1, 3])))
        x = C._areas_nb(zi.astype(np.int64), lo, hi, fin.astype(np.int64), src.astype(np.int64), T.astype(float), a, *p, G, VIDA)
        y = C.areas_py(zi, lo, hi, fin, src, T.astype(float), a, *p, G, VIDA)
        assert list(zip(x[0].tolist(), x[1].tolist(), x[2].tolist())) == y
        no_vacios += bool(y)
    assert no_vacios > 30


def test_causal_zona_no_se_adelanta_por_truncar_ns():
    t = T[:10]
    Z = pd.DataFrame(dict(t_ns=[int(t[3]) * 10**9 + 500_000_000], lo=[1.0], hi=[2.0], t_fin_ns=[int(t[6]) * 10**9 + 1]))
    I = C.indexar(Z, t)
    assert I["zi"][0] == 4 and I["zfin"][0] == 7


def test_causal_futuro_no_cambia_areas_pasadas():
    r = np.random.default_rng(1); n = 80; zi = np.sort(r.integers(15, 500, n)); lo = 100 + r.integers(0, 20, n) * 0.25; hi = lo + 0.5
    fin = zi + 100; src = r.integers(0, 2, n); corte = 250; a = np.ones(len(T))
    a2 = a.copy(); a2[corte + 1:] = 50.0
    p = (1, 1, 3.0, 100.0, 9.0, G, VIDA)
    x = C._areas_nb(zi, lo, hi, fin, src, T.astype(float), a, *p); k = zi <= corte
    y = C._areas_nb(zi[k], lo[k], hi[k], fin[k], src[k], T.astype(float), a2, *p)
    assert len(y[0]) and x[0][x[0] <= corte].tolist() == y[0].tolist()


def test_atr_no_mira_adelante():
    r = np.random.default_rng(0); c = 100 + r.normal(size=60).cumsum(); h, l = c + 1, c - 1
    a = C.atr(h, l, c); b = C.atr(h[:40], l[:40], c[:40])
    assert np.array_equal(a[:40], b, equal_nan=True) and np.isnan(a[12]) and np.isfinite(a[13])


def cfd_nq():
    cfd = ctx(20); nq = ctx(20); cfd["c"] = 100.0 + np.arange(20.0); nq["c"] = 150.0 + 3 * np.arange(20.0)
    return cfd, nq


def test_base_es_as_of_creacion():
    cfd, nq = cfd_nq()
    Z, d = C.trasladar(pd.DataFrame(dict(t_ns=[int(T[5]) * 10**9], lo=[10.0], hi=[11.0])), cfd, nq)
    base = nq["c"][5] - cfd["c"][5]
    assert d == 0 and Z.lo[0] == 10.0 + base and Z.hi[0] == 11.0 + base


def test_base_entre_velas_usa_la_anterior_y_no_la_futura():
    cfd, nq = cfd_nq()
    Z, _ = C.trasladar(pd.DataFrame(dict(t_ns=[int(T[5]) * 10**9 + 30 * 10**9], lo=[10.0], hi=[11.0])), cfd, nq)
    assert Z.lo[0] == 10.0 + nq["c"][5] - cfd["c"][5]


def test_base_vencida_o_cruzando_segmento_se_descarta():
    cfd, nq = cfd_nq(); nq = {k: v[:6] for k, v in nq.items()}
    Z, d = C.trasladar(pd.DataFrame(dict(t_ns=[int(T[15]) * 10**9], lo=[1.0], hi=[2.0])), cfd, nq)
    assert len(Z) == 0 and d == 1
    cfd, nq = cfd_nq(); nq["seg"] = (np.arange(20) >= 6).astype(np.int64)
    assert len(C.trasladar(pd.DataFrame(dict(t_ns=[int(T[5]) * 10**9 + 10 * 10**9], lo=[1.0], hi=[2.0])), cfd, nq)[0]) == 0


def _par():
    cx = ctx(); cx["ses"] = np.arange(600) // 10 + 20250805; n = 40; idx = 20 + np.arange(n) * 14
    A = pd.DataFrame(dict(t_ns=T[idx] * 10**9, lo=100.0 + 3 * np.arange(n), hi=100.5 + 3 * np.arange(n)))
    return cx, C.preparar(cx, dict(X=A, Y=A.assign(t_ns=A.t_ns + 60 * 10**9, lo=A.lo + 0.1, hi=A.hi + 0.1))), n


def test_censo_umbrales_30_areas_20_sesiones():
    cx, segs, n = _par()
    r = C.censar_par(cx, segs, "X", "Y", dict(A=(1,), B=(1,), R=(3.0,), V=(100.0,), Am=(5.0,)))
    d = r["detalle"][0]
    assert d["areas"] == n and d["sesiones"] == n and r["evaluables"] == r["evaluables_unicas"] == 1 and r["degeneradas"] == 0
    assert not {"pnl", "ret", "neto"} & set(d)


def test_duplicada_y_degenerada():
    cx, segs, _ = _par()
    r = C.censar_par(cx, segs, "X", "Y", dict(A=(1, 9), B=(1,), R=(3.0, 4.0), V=(100.0,), Am=(5.0,)))
    assert r["combinaciones"] == 4 and r["duplicadas"] == 1 and r["degeneradas"] == 2 and r["evaluables_unicas"] == 1


def test_cortes_salen_de_los_datos():
    cx = ctx()
    A = pd.DataFrame(dict(t_ns=T[20:300:5] * 10**9, lo=100.0, hi=100.5)); B = A.assign(t_ns=A.t_ns + 60 * 10**9)
    c = C.cortes_par(C.preparar(cx, dict(X=A, Y=B)), "X", "Y")
    assert c["n_pares"] > 0 and c["A"][0] >= 1 and c["R"] and c["V"]


def test_ventana_fija():
    assert (C.DESDE, C.HASTA) == (20250805, 20260331)
