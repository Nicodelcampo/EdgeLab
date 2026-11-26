"""¿Coincide el calendario de noticias con el movimiento del precio? Verificación target-free sobre ES M1 de NT8.

Para cada evento de `config/noticias/calendario_usd_tier1.csv` mira la ventana de ±10 minutos alrededor de su minuto
(vela que ABRE en el minuto del evento = desfase 0; el índice de NT8 exportado marca la apertura) y mide, minuto a
minuto, el rango (máximo − mínimo) relativo a la mediana del rango de ese mismo minuto del día en las 20 sesiones
previas. Si la hora del calendario es correcta, el mayor salto de la ventana cae en el desfase 0 y es varias veces el
normal. Un evento cuyo pico cae lejos de 0, o cuyo salto en 0 es chico, se lista para revisión.

Placebo: los mismos minutos del día en días sin ningún evento del calendario (mismo mes) dan la tasa de «pico en 0»
por azar (≈ 1/21).

  python tools/verificar_calendario_precio.py --es data/m1nt8/ES_M1_nonadj_utc.parquet --out <carpeta>

No mira resultados de ninguna estrategia ni datos del holdout (corta en 2025-12-31).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from edgelab import noticias  # noqa: E402

VENT = 10          # minutos a cada lado
BASE_DIAS = 20     # sesiones previas para la mediana del rango por minuto del día
HASTA = "2025-12-31"


def matriz_rango(ruta_es: Path) -> pd.DataFrame:
    d = pd.read_parquet(ruta_es, columns=["high", "low"],
                        filters=[("datetime", ">=", pd.Timestamp("2007-11-01")), ("datetime", "<=", pd.Timestamp(HASTA + " 23:59"))])
    r = (d["high"] - d["low"]).astype("float32")
    idx = r.index
    m = pd.DataFrame({"fecha": idx.normalize(), "min": idx.hour * 60 + idx.minute, "r": r.values})
    M = m.pivot_table(index="fecha", columns="min", values="r", aggfunc="first")
    return M.reindex(columns=range(1440))


def ratio(M: pd.DataFrame) -> pd.DataFrame:
    base = M.rolling(BASE_DIAS, min_periods=10).median().shift(1)
    return M / base.replace(0, np.nan)


def ventana(R: pd.DataFrame, fecha: pd.Timestamp, minuto: int) -> np.ndarray | None:
    if fecha not in R.index or minuto - VENT < 0 or minuto + VENT > 1439:
        return None
    w = R.loc[fecha, minuto - VENT: minuto + VENT].to_numpy(dtype=float)
    return None if np.isnan(w[VENT]) or np.isnan(w).sum() > 5 else w


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--es", type=Path, default=ROOT / "data" / "m1nt8" / "ES_M1_nonadj_utc.parquet")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    R = ratio(matriz_rango(a.es))
    cal = noticias.cargar(); cal = cal[cal["impacto"] == "tier1"]
    cal = cal[cal["ts_utc"] <= pd.Timestamp(HASTA + " 23:59", tz="UTC")]
    filas = []
    for _, e in cal.iterrows():
        t = e["ts_utc"].tz_convert(None)
        w = ventana(R, t.normalize(), t.hour * 60 + t.minute)
        if w is None:
            continue
        pico = int(np.nanargmax(w)) - VENT
        filas.append(dict(ts_utc=str(e["ts_utc"]), evento=e["evento"], anio=t.year, ratio0=float(w[VENT]),
                          ratio_max=float(np.nanmax(w)), pico=pico, periodo="2008-2022" if t.year <= 2022 else "2023-2025"))
    F = pd.DataFrame(filas)
    # placebo: días sin evento, mismos minutos del día que los eventos
    dias_evento = set(cal["ts_utc"].dt.tz_convert(None).dt.normalize())
    libres = [d for d in R.index if d not in dias_evento and d.weekday() < 5]
    rng = np.random.default_rng(7)
    plac = []
    for _, e in F.sample(min(3000, len(F)), random_state=7).iterrows():
        t = pd.Timestamp(e["ts_utc"]).tz_convert(None)
        cand = [d for d in libres if abs((d - t.normalize()).days) < 45]
        if not cand:
            continue
        w = ventana(R, cand[rng.integers(len(cand))], t.hour * 60 + t.minute)
        if w is not None:
            plac.append(dict(ratio0=float(w[VENT]), pico=int(np.nanargmax(w)) - VENT))
    P = pd.DataFrame(plac)

    def resumen(g):
        return pd.Series(dict(n=len(g), pico_en_0=round((g.pico == 0).mean(), 3), pico_0_o_1=round(g.pico.isin([0, 1]).mean(), 3),
                              mediana_ratio0=round(g.ratio0.median(), 2), ratio0_mayor_2=round((g.ratio0 > 2).mean(), 3)))
    tabla = F.groupby(["evento", "periodo"]).apply(resumen).reset_index()
    sospechosos = F[(F.periodo == "2008-2022") & ~F.pico.isin([0, 1]) & (F.ratio0 < 1.5)].sort_values("ts_utc")
    por_anio = F[F.periodo == "2008-2022"].groupby("anio").apply(resumen).reset_index()
    a.out.mkdir(parents=True, exist_ok=True)
    res = dict(placebo=resumen(P).to_dict() if len(P) else None,
               por_evento=tabla.to_dict("records"), por_anio=por_anio.to_dict("records"),
               sospechosos=sospechosos.to_dict("records"))
    (a.out / "VERIFICACION_CALENDARIO_PRECIO.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    pd.set_option("display.width", 200)
    print("placebo:", res["placebo"])
    print(tabla.to_string(index=False))
    print(f"sospechosos 2008-2022 (pico fuera de 0/1 y ratio0 < 1,5): {len(sospechosos)} de {int((F.periodo == '2008-2022').sum())}")
    print(sospechosos.groupby("evento").size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
