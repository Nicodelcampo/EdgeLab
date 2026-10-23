"""El kernel committeado de la grilla masiva (lo lanza el autopilot: la guarda exige script committeado) debe ser exactamente
el que sale de reconstruirlo con los módulos actuales. Si falla: python tools/kaggle_areas/construir_kernel.py tools/kaggle_areas/kernel_areas.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "kaggle_grilla"))
from construir_kernel import construir  # noqa: E402


def test_kernel_areas_al_dia(tmp_path):
    out = tmp_path / "k.py"
    construir("tools/kaggle_areas/areas_main.py", str(out), ["edgelab/research/areas_expansion.py", "edgelab/research/areas_expansion_run.py"])
    assert out.read_bytes() == (ROOT / "tools/kaggle_areas/kernel_areas.py").read_bytes(), "kernel_areas.py desactualizado: reconstruirlo"


def test_grilla_configurable_y_conteo():
    from edgelab.research import areas_expansion as AX
    base = AX.configurar(None); n0 = AX.n_celdas()
    try:
        g = AX.configurar({"NS": [4, 2], "XS": [0.3, 0.6]})
        assert g["NS"] == (2, 4) and g["XS"] == (0.6, 0.3)                      # XS de mayor a menor como en la spec
        assert AX.n_celdas() == n0 // 3 * 2 // 3 * 2
        import pytest
        with pytest.raises(ValueError): AX.configurar({"ZZ": [1]})
    finally:
        AX.configurar({k: list(v) for k, v in base.items()})
    assert AX.n_celdas() == n0 == 995328


def test_configurar_llega_a_eventos_y_disparos():
    """Bug 2026-10-23: `eventos(ns=NS)` y `disparos(xs=XS)` fijaban el default al definirse; GRILLA no los cambiaba."""
    import numpy as np
    from edgelab.research import areas_expansion as AX
    base = AX.configurar(None)
    try:
        AX.configurar({"NS": [2, 4], "XS": [0.6]})
        Z = dict(zi=np.array([], np.int64), zlo=np.array([]), zhi=np.array([]), zfin=np.array([], np.int64))
        assert set(AX.eventos(Z, np.arange(5.0), 1.0)) == {(n, w) for n in (2, 4) for w in AX.WS}
        c = np.r_[np.full(5, 10.0), np.linspace(12, 30, 20), np.linspace(30, 10.5, 30)]
        out = AX.disparos((0, 9.0, 10.0, None), c + 0.1, c - 0.1, c, np.arange(len(c)) * 60.0)
        assert out and {d["xi"] for d in out} == {0}
    finally:
        AX.configurar({k: list(v) for k, v in base.items()})


def test_kernel_u1_indaga_al_dia(tmp_path):
    sys.path.insert(0, str(ROOT / "tools" / "kaggle_grilla"))
    from construir_kernel_experimento import construir_experimento
    out = tmp_path / "k.py"; construir_experimento("edgelab/research/u1_indaga.py", str(out))
    assert out.read_bytes() == (ROOT / "tools/kaggle_grilla/kernel_u1_indaga.py").read_bytes(), "reconstruir kernel_u1_indaga.py"


def test_kernel_u1_cruzado_al_dia(tmp_path):
    sys.path.insert(0, str(ROOT / "tools" / "kaggle_grilla"))
    from construir_kernel import construir
    from construir_kernel_experimento import BASE
    out = tmp_path / "k.py"
    construir("tools/kaggle_grilla/u1_cruzado_main.py", str(out), BASE + ["edgelab/research/u1_indaga.py", "edgelab/research/u1_cruzado.py"])
    assert out.read_bytes() == (ROOT / "tools/kaggle_grilla/kernel_u1_cruzado.py").read_bytes(), "reconstruir kernel_u1_cruzado.py"
