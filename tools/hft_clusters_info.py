#!/usr/bin/env python3
"""HFT-CLUSTERS-INFO: construir y lanzar los kernels (docs/research/hft_clusters_u1_20261110/PREREGISTRO_E0_E_INFORMACION.md).
  python tools/hft_clusters_info.py e0                     # paso sin retornos (4 activos, DESC)
  python tools/hft_clusters_info.py e0b                    # E0-b sin retornos: 40 definiciones (más zonas, ancho mínimo), equilibrio potencia/fricción
  python tools/hft_clusters_info.py rebotes                # 7 definiciones de rebote (D0–D6) con los clusters del E0-b en NQ y ES
  python tools/hft_clusters_info.py info                   # paso de información en DESC con la definición que eligió el E0
  python tools/hft_clusters_info.py rep                    # réplica abr → sep (sólo si el paso info pasó; una vez)
  python tools/hft_clusters_info.py traer e0|info|rep      # baja el resultado a la carpeta de la familia
Agregar --solo-construir para no lanzar. La definición del paso info sale de HFTC_e0.json (campo `eleccion`), nunca a mano.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools/kaggle_grilla"))
DIR = ROOT / "docs/research/hft_clusters_u1_20261110"
MODULOS = ["edgelab/holdout.py", "edgelab/research/fuentes_ticks.py", "edgelab/bridge/indicators/hftzones_nq.py",
           "edgelab/bridge/indicators/hftzones_nq_rangos_pct_v2.py",
           "edgelab/research/hft_clusters_info.py", "edgelab/research/hft_rebotes.py"]
DATASET = "nicolasbuttaro/edgelab-liquid-ticks-20261014"


def construir(modo: str) -> Path:
    from construir_kernel import construir as K
    src = (ROOT / "tools/kaggle_grilla/hft_clusters_info_main.py").read_text(encoding="utf-8").replace('MODO = "e0"', f'MODO = "{modo}"', 1)
    if modo == "rebotes":                                              # clusters del E0-b (equilibrio potencia/fricción); YM y GC fuera
        eq = json.loads((DIR / "HFTC_e0b.json").read_text(encoding="utf-8"))["equilibrio"]
        el = {i: ["Z_CERT", eq[i]["elegida"]["cluster"]] for i in ("NQ", "ES") if eq.get(i, {}).get("elegida")}
        src = src.replace("DEFS = {}", "DEFS = " + json.dumps(el), 1)
    elif modo not in ("e0", "e0b"):
        el = json.loads((DIR / "HFTC_e0.json").read_text(encoding="utf-8"))["eleccion"]
        if not el: raise SystemExit("el E0 no eligió ninguna definición: el paso de información no se corre")
        src = src.replace("DEFS = {}", "DEFS = " + json.dumps({i: [v["zona"], v["cluster"]] for i, v in sorted(el.items())}), 1)
    tmp = ROOT / f"tools/kaggle_grilla/_hft_clusters_info_{modo}_main.py"; tmp.write_text(src, encoding="utf-8")
    out = ROOT / f"tools/kaggle_grilla/kernel_hft_clusters_info_{modo}.py"
    try: K(str(tmp.relative_to(ROOT)), str(out), MODULOS)
    finally: tmp.unlink()
    return out


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; slug = lambda m: f"nicolasbuttaro/hft-clusters-info-{m}-20261110"
    k = lambda *x: subprocess.run([sys.executable, str(ROOT / "tools/kaggle_kernel.py"), *x], capture_output=True, text=True).stdout
    if a[0] == "traer":
        for ext in ("json", "csv"): print(k("output", "--slug", slug(a[1]), "--file", f"HFTC_{a[1]}.{ext}", "--out", str(DIR / f"HFTC_{a[1]}.{ext}")).strip())
        return
    out = construir(a[0]); print("construido", out.relative_to(ROOT))
    if "--solo-construir" not in sys.argv:
        print(k("push", "--slug", slug(a[0]), "--title", f"hft clusters info {a[0]} 20261110", "--script", str(out), "--dataset", DATASET)[-300:])


if __name__ == "__main__":
    main()
