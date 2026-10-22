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
