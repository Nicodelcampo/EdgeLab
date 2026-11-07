from __future__ import annotations

import importlib
import numpy as np

from edgelab.research import grilla_generica as GG, grilla_masiva as GM
from edgelab.research.grilla_masiva import Perilla
from tools import regimen_estructural_diagnostico as RED


def test_tensor_sesiones_rapido_paridad_exacta():
    rng = np.random.default_rng(20261106)
    P = [Perilla("a", 4, "grupo"), Perilla("b", 5, "ge"), Perilla("ej", 3, "grupo")]
    forma = tuple(p.tamano_celdas() for p in P)
    n_ops = 1200
    idx = [rng.integers(0, 4, size=n_ops), rng.integers(0, 5, size=n_ops), rng.integers(0, 3, size=n_ops)]
    ses_op = rng.choice([20260105, 20260106, 20260107, 20260108, 20260109], size=n_ops)
    net = rng.normal(-0.15, 1.2, size=n_ops)
    net[rng.integers(0, n_ops, size=40)] = np.nan
    ok = np.isfinite(net)
    net0 = net.copy()
    for e in np.unique(idx[-1][ok]):
        m = ok & (idx[-1] == e)
        net0[m] -= net[m].mean()

    S_fast, S0_fast, C_fast, ses_u, forma_out = RED._tensor_sesiones_rapido(P, idx, ok, ses_op, net, net0)
    assert forma_out == forma

    n_c = int(np.prod(forma))
    S_ref = np.zeros((len(ses_u), n_c))
    S0_ref = np.zeros_like(S_ref)
    C_ref = np.zeros_like(S_ref)
    for j, s_id in enumerate(ses_u):
        msk = ok & (ses_op == s_id)
        s_t, _q, c_t = GM.tensor(P, idx, np.where(msk, net, np.nan))
        S_ref[j] = s_t.ravel()
        C_ref[j] = c_t.ravel()
        s0, _q0, _c0 = GM.tensor(P, idx, np.where(msk, net0, np.nan))
        S0_ref[j] = s0.ravel()

    np.testing.assert_allclose(S_fast, S_ref, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(S0_fast, S0_ref, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(C_fast, C_ref, rtol=1e-12, atol=1e-12)


def test_mascara_baja_friccion_todos_los_modulos():
    modulos = [
        "edgelab.research.absorcion_climax",
        "edgelab.research.comex_cierre_oro",
        "edgelab.research.eod_momentum",
        "edgelab.research.estructura_hhll",
        "edgelab.research.impulso_post_macro",
        "edgelab.research.kalman_fade",
        "edgelab.research.overnight_inventario",
        "edgelab.research.rango_asia0100",
        "edgelab.research.rango_preapertura",
        "edgelab.research.segundo_intento",
        "edgelab.research.tau_tendencia",
        "edgelab.research.vwap_dual_iman",
        "edgelab.research.vwap_rev",
        "edgelab.research.wm_fixing",
    ]
    for m_name in modulos:
        exp = importlib.import_module(m_name)
        ej = list(exp.EJECUCIONES)
        m_ej = RED.mascara_baja_friccion_ejecuciones(m_name, ej)
        assert m_ej.dtype == bool and len(m_ej) == len(ej)
        assert 1 <= int(m_ej.sum()) < len(ej)
        forma = (3, 4, len(ej))
        m_full = RED.mascara_celdas_baja_friccion(forma, m_name, ej)
        assert len(m_full) == 3 * 4 * len(ej)
        assert int(m_full.sum()) == 3 * 4 * int(m_ej.sum())
