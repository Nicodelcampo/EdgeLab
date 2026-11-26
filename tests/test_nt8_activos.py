"""La tabla de activos de NT8 (FundedSyncAssets) sale de edgelab/costos.py: tick, valor del punto y fricción canónica."""
import re
from pathlib import Path

from edgelab import costos

CS = Path(__file__).resolve().parents[1] / "nt8" / "strategies" / "EdgeLabFundedSyncCore.cs"


def test_tabla_de_activos_igual_a_costos_canonicos():
    s = CS.read_text(encoding="ascii")
    filas = re.findall(r'case FundedSyncActivo\.(\w+): return new FundedSyncAssetSpec\("(\w+)", ([\d.e-]+), ([\d.e-]+), ([\d.e-]+)\);', s)
    assert len(filas) >= 7
    for act, root, tick, pv, fric in filas:
        assert act == root
        assert float(tick) == costos.tick_size(root)
        assert abs(float(pv) - costos.tick_value_usd(root) / costos.tick_size(root)) < 1e-9
        assert abs(float(fric) - round(costos.friccion_rt_ticks(root) * costos.tick_size(root), 4)) < 1e-9
