"""docs/cartera/CANASTAS_VIGENTES.md se genera de los archivos operativos: si alguien cambia una canasta sin regenerarlo, falla."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "tools"))


def test_canastas_vigentes_al_dia():
    import canastas_vigentes as CV
    assert CV.SALIDA.read_text(encoding="utf-8") == CV.render(), "regenerar: python tools/canastas_vigentes.py --write"
