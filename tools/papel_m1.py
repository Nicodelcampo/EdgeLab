#!/usr/bin/env python3
"""Reglas de papel (config/cartera/altas.json) CONGELADAS, re-medidas sobre M1 de Dukascopy 2012–2026 (fuente M1DK, 2026-11-15).
Pre-registro: docs/research/papel_m1_20261115/PREREGISTRO.md. Etapa ANALIZAR_REGLA del embudo (mismo módulo, mismas celdas y cortes).

  python tools/papel_m1.py lanzar VALIDACION|LARGO [FICHA ...]   # VALIDACION = 2025-08 → 2026-09 (comparable con ticks reales de NQ)
  python tools/papel_m1.py traer                                  # baja lo terminado a docs/research/papel_m1_20261115/resultados/
  python tools/papel_m1.py local FICHA SENSOR D0-D1 [D0-D1 ...]  # en la máquina con M1 real de futuros (SENSOR M1NT8:NQ, datos de tools/datos.py)
  python tools/papel_m1.py largo FICHA [SENSOR]                    # mapa y encendido por régimen (enmienda 1), con la guarda K48
  python tools/papel_m1.py validacion [SENSOR]                    # criterio de la fuente POR CÓDIGO (a5.calibrar_por_sesion) -> VALIDACION*.json
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


def _pref(sen):
    return "" if sen.endswith("NQ_M1_dukas") else (sen[5:].split("_")[0] + "__" if sen.startswith("M1DK:") else "FUT" + sen.replace(":", "_") + "__")


def local(fid, sensor, periodos):
    """La regla congelada en la máquina sobre M1 real de futuros de NT8 (`M1NT8:<inst>`), con la copia local verificada de
    `tools/datos.py` y el mismo `etapas.ejecutar` que el kernel (LocalRunner). Escribe resultados/<pref><ficha>_<d0>_<d1>.json."""
    from edgelab.research.embudo_runners import LocalRunner
    from edgelab.research.fuentes_ticks import bloques_m1nt8, TICK_FUTURO, TICK_M1NT8_EXTRA
    from datos import ruta
    if not sensor.startswith("M1NT8:"): raise SystemExit("local: sólo M1NT8:<inst>")
    inst = sensor[6:]; d = ruta("M1NT8")
    run = LocalRunner({sensor: lambda a, b, spec: bloques_m1nt8(inst, int(a), int(b), d)}, {sensor: TICK_FUTURO.get(inst) or TICK_M1NT8_EXTRA[inst]},
                      acta_requerida=False)
    f = _ficha(fid); r = f["regla"]; spec = dict(r["spec"], sensor=sensor, ejecucion=sensor, cid=f"PF{sensor}-{fid}"[:30], datasets_extra=[])
    params = dict(celdas=r.get("celdas") or [r["celda"]], cortes=r.get("cortes") or {}, tope=r.get("tope"), operaciones=True)
    (OUT / "resultados").mkdir(parents=True, exist_ok=True)
    for p in periodos:
        a, b = map(int, p.split("-")); h = run.lanzar(spec, "ANALIZAR_REGLA", params, (a, b))
        dst = OUT / "resultados" / f"{_pref(sensor)}{fid}_{a}_{b}.json"
        dst.write_text(json.dumps(dict(run.traer(h), sensor=sensor, desde=a, hasta=b, local=True), indent=1, default=float), encoding="utf-8"); print("local", dst.name)


def validacion(sensor="M1DK:NQ_M1_dukas"):
    """K43 (2026-11-18): el veredicto de la fuente lo da el criterio único `a5.calibrar_por_sesion` (≥ 30 sesiones comunes, mismo signo,
    |diferencia| ≤ 1 EE combinado, corr > 0,5), no una tabla escrita a mano.
    K47 (2026-11-18): la serie de M1 se agrega con LA MISMA función que la ficha (`cartera.papel.canasta_por_sesion`: suma de las
    celdas / número de celdas). La v1 y la primera v2 promediaban sólo las celdas que operan y comparaban unidades distintas: ASIA
    «duplicaba» a los ticks sin que el motor tuviera nada que ver (en ticks reales, agregada igual que M1, también da el doble)."""
    import pandas as pd
    from edgelab.research import a5 as A5
    from edgelab.cartera.papel import canasta_por_sesion
    out = {}
    for fid in FICHAS:
        f = _ficha(fid); od = f["ops_desarrollo"]; od = json.loads(od) if isinstance(od, str) else od
        t = pd.DataFrame(od, columns=["ses", "v"]).groupby("ses").v.sum(); t = t[(t.index >= 20250801) & (t.index <= 20260929)]
        r = OUT / "resultados" / f"{_pref(sensor)}{fid}_20250801_20260929.json"
        if not r.exists(): out[fid] = dict(calibra=False, motivo=f"sin resultado {sensor}"); continue
        O = json.loads(r.read_text(encoding="utf-8"))["operaciones"]
        m = dict(canasta_por_sesion(zip(O["ses"], O["neto"]), len(f["regla"].get("celdas") or [1])))
        out[fid] = A5.calibrar_por_sesion({int(k): float(v) for k, v in t.items()}, m)
    dst = OUT / ("VALIDACION.json" if sensor.endswith("NQ_M1_dukas") else f"VALIDACION_{_pref(sensor).strip('_')}.json")
    dst.write_text(json.dumps(dict(criterio="a5.calibrar_por_sesion", agregacion="cartera.papel.canasta_por_sesion", sensor=sensor, fichas=out),
                              indent=1, default=float), encoding="utf-8")
    for k, v in out.items(): print(k, "CALIBRA" if v["calibra"] else "NO", {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items()})


def largo(fid, sensor="M1DK:NQ_M1_dukas"):
    """Enmienda 1 del pre-registro (mapa y encendido por régimen) como comando, no como script suelto. Canasta con la función de la
    ficha (K47), variables de `papel_regimen` con D1/H1 del CFD de Dukascopy (las de la v1) y la guarda de causalidad K48 con las horas
    reales de entrada. Escribe LARGO_<ficha>.json."""
    import glob, pandas as pd
    from edgelab.research import macro_literatura as ML, papel_regimen as PR
    from edgelab.cartera.papel import canasta_por_sesion
    f = _ficha(fid); k = len(f["regla"].get("celdas") or [1]); filas, t = [], []
    for x in sorted(glob.glob(str(OUT / "resultados" / f"{_pref(sensor)}{fid}_*.json"))):
        O = json.loads(Path(x).read_text(encoding="utf-8")).get("operaciones") or {}
        filas += list(zip(O.get("ses", []), O.get("neto", []))); t += list(O.get("t", []))
    s = pd.Series(dict(canasta_por_sesion(filas, k))); s.index = pd.to_datetime(s.index.astype(str), format="%Y%m%d")
    V = PR.variables(ML.leer(str(ROOT / "data/sqx_barras/NQ_M1_dukas_D1.csv")), ML.leer(str(ROOT / "data/sqx_barras/NQ_M1_dukas_H1.csv")))
    tramos = {n: s[(s.index >= a) & (s.index <= b)] for n, a, b in (("2012-2019", "2012", "2019-12-31"), ("2020-2023", "2020", "2023-12-31"),
              ("2024-2025.07", "2024", "2025-07-31"), ("2025.08-2026.09", "2025-08", "2026-09-30"))}
    out = dict(ficha=fid, sensor=sensor, causales=PR.causales(t),
               tramos={n: dict(n=int(len(x)), media=round(float(x.mean()), 2) if len(x) else None,
                               ee=round(float(x.std(ddof=1) / len(x) ** .5), 2) if len(x) > 1 else None) for n, x in tramos.items()},
               mapa=PR.mapa(s, V, t_entradas=t), encendido=PR.encendido(s, V, t_entradas=t))
    (OUT / f"LARGO_{fid}.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8"); print(json.dumps(out, default=float))


if __name__ == "__main__":
    a = sys.argv[1:]
    {"lanzar": lambda: lanzar(a[1], a[2:]), "traer": traer, "validacion": lambda: validacion(*a[1:2]), "local": lambda: local(a[1], a[2], a[3:]), "largo": lambda: largo(*a[1:3])}[a[0]]()
