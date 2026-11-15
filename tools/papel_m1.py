#!/usr/bin/env python3
"""Reglas de papel (config/cartera/altas.json) CONGELADAS, re-medidas sobre M1 de Dukascopy 2012–2026 (fuente M1DK, 2026-11-15).
Pre-registro: docs/research/papel_m1_20261115/PREREGISTRO.md. Etapa ANALIZAR_REGLA del embudo (mismo módulo, mismas celdas y cortes).

  python tools/papel_m1.py lanzar VALIDACION|LARGO [FICHA ...]   # VALIDACION = 2025-08 → 2026-09 (comparable con ticks reales de NQ)
  python tools/papel_m1.py traer                                  # baja lo terminado a docs/research/papel_m1_20261115/resultados/
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from edgelab.research.embudo_runners import KaggleRunner  # noqa: E402

FICHAS = ("ASIA-NQ-CANASTA", "OTR930-NQ-CANASTA", "TORI-NQ-R-PAPEL", "RANGO0100-NQ-CANASTA")
SENSOR = "M1DK:NQ_M1_dukas"
TRAMOS = {"VALIDACION": [(20250801, 20260929)], "LARGO": [(20120120, 20191231), (20200101, 20231231), (20240101, 20250731)]}
OUT = ROOT / "docs/research/papel_m1_20261115"; REG = OUT / "lanzados.jsonl"


def _ficha(fid):
    return next(x for x in json.loads((ROOT / "config/cartera/altas.json").read_text(encoding="utf-8"))["fichas"] if x["id"] == fid)


def lanzar(tramo, fichas):
    run = KaggleRunner(owner="nicolasbuttaro")
    for fid in fichas or FICHAS:
        f = _ficha(fid); r = f["regla"]; spec = dict(r["spec"], sensor=SENSOR, ejecucion=SENSOR, cid=f"PM1-{fid}"[:30], datasets_extra=[])
        params = dict(celdas=r.get("celdas") or [r["celda"]], cortes=r.get("cortes") or {}, tope=r.get("tope"), operaciones=True)
        for p in TRAMOS[tramo]:
            h = run.lanzar(spec, "ANALIZAR_REGLA", params, p)
            with REG.open("a", encoding="utf-8") as fh: fh.write(json.dumps(dict(ficha=fid, tramo=tramo, periodo=p, handle=h)) + "\n")
            print("lanzado", fid, p, h)


def traer():
    run = KaggleRunner(owner="nicolasbuttaro"); (OUT / "resultados").mkdir(parents=True, exist_ok=True)
    for L in [json.loads(x) for x in REG.read_text(encoding="utf-8").splitlines() if x.strip()]:
        dst = OUT / "resultados" / f"{L['ficha']}_{L['periodo'][0]}_{L['periodo'][1]}.json"
        if dst.exists(): continue
        e = run.estado(L["handle"]); print(L["ficha"], L["periodo"], e)
        if e == "complete": dst.write_text(json.dumps(run.traer(L["handle"]), indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    a = sys.argv[1:]
    lanzar(a[1], a[2:]) if a[0] == "lanzar" else traer()
