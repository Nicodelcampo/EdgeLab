#!/usr/bin/env python3
"""Analizador de estrategias (como el Strategy Analyzer de NT8) sobre el simulador sellado y los costos canónicos.

  python tools/analizar.py edgelab.research.estrategias.ejemplo_ruptura_rango 20240102 20260331 --entrada /ruta/datos
  python tools/analizar.py edgelab.research.estrategias.ejemplo_ruptura_rango 20240102 20260331 --kaggle [--cuenta auto]
Registra las variantes en el contador global ANTES de correr; el holdout no se puede pedir. Salida: JSON con el reporte de cada
variante (y las operaciones si es una sola). EXPLORATORIO: lo prometedor va a un pre-registro y al embudo.
"""
import argparse
import importlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.funnel.multiplicity import TrialRegistry  # noqa: E402
from edgelab.research import analizador as A  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("modulo"); ap.add_argument("desde", type=int); ap.add_argument("hasta", type=int)
    ap.add_argument("--entrada", default="/kaggle/input"); ap.add_argument("--kaggle", action="store_true"); ap.add_argument("--cuenta", default="auto")
    ap.add_argument("--salida"); a = ap.parse_args()
    est = importlib.import_module(a.modulo); reg = TrialRegistry(A.REGISTRO)
    if not a.kaggle:
        out = A.analizar(est, a.desde, a.hasta, entrada=a.entrada, registro=reg)
    else:
        from edgelab.research import embudo_runners as ER
        vs = A.variantes(est); h = A.huella(est)
        reg.ensure(f"analizador/{est.FAMILIA}/{h}/{a.desde}-{a.hasta}", est.FAMILIA, len(vs), f"analizador {est.NOMBRE} (Kaggle), {len(vs)} variantes")
        spec = dict(cid=f"AN-{est.NOMBRE}"[:40], experimento=a.modulo, sensor=est.INSTRUMENTO, cuenta_kaggle=a.cuenta)
        k = ER.KaggleRunner(); hd = k.lanzar(spec, "ANALIZAR", dict(desde=a.desde, hasta=a.hasta), [a.desde, a.hasta]); print("lanzado", hd, flush=True)
        while (e := k.estado(hd)) == "running": time.sleep(60)
        if e != "complete": sys.exit(f"el kernel terminó en {e}: {hd}")
        out = k.traer(hd); out["pruebas_acumuladas_familia"] = A.pruebas_de_familia(est.FAMILIA)   # el contador vive acá, no en Kaggle
    txt = json.dumps(out, indent=1, ensure_ascii=False, default=float)
    if a.salida: Path(a.salida).write_text(txt, encoding="utf-8")
    for r in out.get("resultados", []):
        print(json.dumps({k: r.get(k) for k in ("parametros", "n", "neto_total", "media", "ic90_sesiones", "profit_factor", "drawdown_max")}, default=float))
    print(out.get("aviso") or out.get("error"), "| pruebas acumuladas de la familia:", out.get("pruebas_acumuladas_familia"))


if __name__ == "__main__":
    main()
