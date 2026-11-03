"""Motor offline de salidas en R (tools/salidas_r.py): stop primero en la misma vela, BE, objetivo y re-denominación del stop corto."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import salidas_r as S  # noqa: E402

TR = dict(f=[0.2, 1.2, 0.5], a=[-0.3, -0.2, -1.1], c=[0.1, 0.9, -1.0], objetivo_R=2.0, friccion_R=0.05)


def test_politicas_basicas():
    assert S.simular(TR, {}) == -1.05                                   # la regla: toca el stop en la 3.ª vela
    assert S.simular(TR, {"objetivo": 1}) == 0.95                       # objetivo 1R en la 2.ª
    assert S.simular(TR, {"be": 1}) == -0.05                            # BE tras 1,2R de máximo: sale en 0
    assert abs(S.simular(TR, {"stop": 0.5}) + 1.1) < 1e-12              # stop a la mitad: −1R del riesgo nuevo + fricción ×2
    assert S.simular(TR, {"tiempo": 2}) == 0.85                         # cierre de la 2.ª vela


def test_stop_gana_en_la_misma_vela():
    tr = dict(f=[2.5], a=[-1.2], c=[0.0], objetivo_R=2.0, friccion_R=0.0)
    assert S.simular(tr, {}) == -1.0 and len(S.politicas()) == 29
