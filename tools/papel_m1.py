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
SENSOR = __import__("os").environ.get("PAPEL_M1_SENSOR", "M1DK:NQ_M1_dukas")   # otros mercados: M1DK:SP_M1_dukas, M1DK:DJ_M1_dukas
TRAMOS = {"COMPLETO": [(20120120, 20260929)], "FUTURO": [(20250805, 20260925)], "VALIDACION": [(20250801, 20260929)], "LARGO": [(20120120, 20191231), (20200101, 20231231), (20240101, 20250731)]}
OUT = ROOT / "docs/research/papel_m1_20261115"; REG = OUT / "lanzados.jsonl"


def _ficha(fid):
    return next(x for x in json.loads((ROOT / "config/cartera/altas.json").read_text(encoding="utf-8"))["fichas"] if x["id"] == fid)


def lanzar(tramo, fichas):
    run = KaggleRunner(owner="nicolasbuttaro")
    for fid in fichas or FICHAS:
        f = _ficha(fid); r = f["regla"]; spec = dict(r["spec"], sensor=SENSOR, ejecucion=SENSOR, cid=(f"PM1-{fid}" if SENSOR.endswith("NQ_M1_dukas") else (f"PM1{SENSOR[5:7]}-{fid}" if SENSOR.startswith("M1DK:") else f"PF{SENSOR}-{fid}"))[:30], datasets_extra=[])
        params = dict(celdas=r.get("celdas") or [r["celda"]], cortes=r.get("cortes") or {}, tope=r.get("tope"), operaciones=True)
        solo = [tuple(map(int, x.split("-"))) for x in __import__("os").environ.get("PAPEL_M1_PERIODOS", "").split(",") if x]
        for p in (solo or TRAMOS[tramo]):
            h = run.lanzar(spec, "ANALIZAR_REGLA", params, p)
            with REG.open("a", encoding="utf-8") as fh: fh.write(json.dumps(dict(ficha=fid, tramo=tramo, periodo=p, handle=h, sensor=SENSOR)) + "\n")
            print("lanzado", fid, p, h)


def traer():
    run = KaggleRunner(owner="nicolasbuttaro"); (OUT / "resultados").mkdir(parents=True, exist_ok=True)
    for L in [json.loads(x) for x in REG.read_text(encoding="utf-8").splitlines() if x.strip()]:
        sen = L.get("sensor", "M1DK:NQ_M1_dukas"); pre = "" if sen.endswith("NQ_M1_dukas") else (sen[5:].split("_")[0] + "__" if sen.startswith("M1DK:") else "FUT" + sen + "__")
        dst = OUT / "resultados" / f"{pre}{L['ficha']}_{L['periodo'][0]}_{L['periodo'][1]}.json"
        if dst.exists(): continue
        e = run.estado(L["handle"]); print(L["ficha"], L["periodo"], e)
        if e == "complete": dst.write_text(json.dumps(run.traer(L["handle"]), indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    a = sys.argv[1:]
    lanzar(a[1], a[2:]) if a[0] == "lanzar" else traer()
