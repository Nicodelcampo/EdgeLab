"""Construye el script de Kaggle de la Adenda D: Pasada 2 (sin su main) + variante de detector DET_NT8 + adenda + main_dev().

DET_NT8 = detector de Pasada 2 con ATR := SMA(Range, AtrPeriod) como en nt8/user_indicators/EmaCorridorTrend.cs (rangeAvg).
Uso: python tools/corridor_pass2/build_dev_script.py <salida.py>
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = (HERE / "edgelab_es_corridor_pass2_falsification_v4_sym.py").read_bytes()
assert hashlib.sha256(SRC).hexdigest() == "10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec", "Pasada 2 modificada"
text = SRC.decode("utf-8").replace("\r\n", "\n")

tail = 'if __name__ == "__main__":\n    main()'
assert text.rstrip().endswith(tail)
base = text.rstrip()[: -len(tail)]

start = base.index("@njit(cache=False)\ndef detect_zones_session_strict_numba(")
end = base.index("@njit(cache=False)", start + 10)
fn = base[start:end]
nt8 = fn.replace("def detect_zones_session_strict_numba(", "def detect_zones_nt8_numba(", 1)

a = "    tr = np.zeros(n, dtype=np.float64)\n"
assert a in nt8
nt8 = nt8.replace(a, a + "    rg = np.zeros(n, dtype=np.float64)\n    c0 = 0\n    rsum = 0.0\n", 1)
b = "            atr[i] = tr[i]\n        else:"
assert b in nt8, "bloque init ATR no encontrado"
nt8 = nt8.replace(b, "            atr[i] = tr[i]\n            rg[i] = high[i] - low[i]\n            c0 = i\n            rsum = rg[i]\n            atr[i] = max(rg[i], tick_size)\n        else:", 1)
c = "            atr[i] = tr[i] * k_atr + atr[i - 1] * (1.0 - k_atr)\n"
assert c in nt8, "linea ATR EMA no encontrada"
nt8 = nt8.replace(c, "            rg[i] = high[i] - low[i]\n            rsum += rg[i]\n            if i - c0 >= atr_period:\n                rsum -= rg[i - atr_period]\n            cntw = min(i - c0 + 1, atr_period)\n            atr[i] = rsum / cntw\n", 1)

addon = (HERE / "corridor_dev_events_addon.py").read_text(encoding="utf-8").replace("\r\n", "\n")
out = base + "\n\n# ===== DET_NT8: ATR = SMA(Range) =====\n" + nt8 + "\n" + addon + "\n\nmain_dev()\n"
Path(sys.argv[1]).write_text(out, encoding="utf-8", newline="\n")
print("OK", len(out), hashlib.sha256(out.encode()).hexdigest())
