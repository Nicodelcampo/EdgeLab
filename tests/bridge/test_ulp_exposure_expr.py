"""Las formas de expresion de precio que ulp_sweep triaje por lectura quedan MEDIDAS (tools/ulp_exposure_expr.py)."""
import importlib.util
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "tools" / "ulp_exposure_expr.py"
spec = importlib.util.spec_from_file_location("ulp_expr", P)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_tick_binario_exacto_no_tiene_exposicion_en_ninguna_forma():
    for fn in (m.A, m.B, m.C, m.D, m.E):
        bad, tot = fn(0.25)
        assert tot > 0 and bad == 0, fn.__name__


def test_tick_no_binario_expone_los_umbrales_aritmeticos_pero_no_las_formas_inmunes():
    assert m.A(0.1)[0] > 0 and m.B(0.1)[0] > 0
    for fn in (m.C, m.D, m.E):
        assert fn(0.1)[0] == 0, fn.__name__
