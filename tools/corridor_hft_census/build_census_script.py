"""Arma el kernel de Kaggle del censo corredor x HFT: Pasada 2 + DET_NT8 + dev addon (sin main_dev) + port HFT Flat + census_addon.
Uso: python tools/corridor_hft_census/build_census_script.py <salida.py>"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P2 = ROOT / "tools" / "corridor_pass2"
src = (P2 / "edgelab_es_corridor_pass2_falsification_v4_sym.py").read_bytes()
assert hashlib.sha256(src).hexdigest() == "10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec", "Pasada 2 modificada"
text = src.decode("utf-8").replace("\r\n", "\n")
tail = 'if __name__ == "__main__":\n    main()'
base = text.rstrip()[: -len(tail)]

start = base.index("@njit(cache=False)\ndef detect_zones_session_strict_numba(")
end = base.index("@njit(cache=False)", start + 10)
nt8 = base[start:end].replace("def detect_zones_session_strict_numba(", "def detect_zones_nt8_numba(", 1)
a = "    tr = np.zeros(n, dtype=np.float64)\n"
nt8 = nt8.replace(a, a + "    rg = np.zeros(n, dtype=np.float64)\n    c0 = 0\n    rsum = 0.0\n", 1)
b = "            atr[i] = tr[i]\n        else:"
assert b in nt8
nt8 = nt8.replace(b, "            atr[i] = tr[i]\n            rg[i] = high[i] - low[i]\n            c0 = i\n            rsum = rg[i]\n            atr[i] = max(rg[i], tick_size)\n        else:", 1)
c = "            atr[i] = tr[i] * k_atr + atr[i - 1] * (1.0 - k_atr)\n"
assert c in nt8
nt8 = nt8.replace(c, "            rg[i] = high[i] - low[i]\n            rsum += rg[i]\n            if i - c0 >= atr_period:\n                rsum -= rg[i - atr_period]\n            cntw = min(i - c0 + 1, atr_period)\n            atr[i] = rsum / cntw\n", 1)

addon = (P2 / "corridor_dev_events_addon.py").read_text(encoding="utf-8").replace("\r\n", "\n")
addon = addon[: addon.index("def main_dev():")]       # sin el main de la fase D

hftsrc = (ROOT / "edgelab" / "bridge" / "kernels" / "hftzones_es_pure_v2_flat.py").read_text(encoding="utf-8").replace("\r\n", "\n")
hftsrc = hftsrc.replace("from __future__ import annotations\n", "")
hftsrc = hftsrc.replace("def run(", "def hft_run(").replace("class Params", "class HFT_Params").replace("Params()", "HFT_Params()").replace("Optional[Params]", "Optional[HFT_Params]").replace("params: Params", "params: HFT_Params")
census = (Path(__file__).parent / "census_addon.py").read_text(encoding="utf-8").replace("\r\n", "\n")
out = base + "\n\n# ===== DET_NT8 =====\n" + nt8 + "\n# ===== DEV ADDON (sin main) =====\n" + addon + "\n# ===== PORT HFT (Flat) =====\n" + hftsrc + "\n" + census + "\n\nmain_census()\n"
Path(sys.argv[1]).write_text(out, encoding="utf-8", newline="\n")
print("OK", len(out), hashlib.sha256(out.encode()).hexdigest())
