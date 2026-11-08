"""CANASTA-GLOBAL: elige reglas estables de varios instrumentos con señal plantada (p chico) y no inventa con ruido (p grande)."""
import numpy as np

from edgelab.research import canasta_global as CG, grilla_masiva as GM, regimen_offline as RO


def _cubo(seed, mu, n=4000):
    r = np.random.default_rng(seed)
    dias = np.array([20250805 + i for i in range(0, 200)]); dias = dias[(dias % 100) <= 28]
    ses = np.sort(r.choice(dias, n)); idx = np.stack([r.integers(0, 3, n), r.integers(0, 2, n)], 1)
    net = r.normal(np.where(idx[:, 0] == 1, mu, 0.0), 1.0)
    return RO.Cubo(f"c{seed}", [GM.Perilla("a", 3, "grupo"), GM.Perilla("b", 2, "grupo")], idx, ses, net)


def test_senal_y_ruido(monkeypatch):
    monkeypatch.setattr(CG, "MIN_OPS", 30)
    con = [(f"c{s}", inst, (lambda s=s: _cubo(s, 0.35))) for s, inst in zip(range(3), ("NQ", "ES", "YM"))]
    r = CG.correr(con, B=60, seed=1)
    assert len(r["reglas"]) >= 3 and r["p_seleccion"] <= 0.05 and len({x["instrumento"] for x in r["reglas"]}) >= 3
    ruido = [(f"c{s}", inst, (lambda s=s: _cubo(s, 0.0))) for s, inst in zip(range(10, 13), ("NQ", "ES", "YM"))]
    assert CG.correr(ruido, B=60, seed=1)["p_seleccion"] > 0.05


def test_exigencia_de_frecuencia(monkeypatch):
    """Con un piso de operaciones por sesión que ninguna regla alcanza, la canasta queda vacía (p = 1)."""
    monkeypatch.setattr(CG, "MIN_OPS", 30); monkeypatch.setattr(CG, "OPS_SESION_REGLA", 50.0)
    con = [(f"c{s}", inst, (lambda s=s: _cubo(s, 0.35))) for s, inst in zip(range(3), ("NQ", "ES", "YM"))]
    r = CG.correr(con, B=20, seed=1)
    assert r["reglas"] == [] and r["p_seleccion"] == 1.0
