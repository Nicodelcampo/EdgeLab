"""Paridad `.cs` <-> kernel Python con clave **relativa a la sesion**.

Por que existe, aparte de `verify_layer_parity.py`:

    Ese harness indexa por numero de cubeta ACUMULADO desde el ancla. Como los dos
    lados cuentan corrido, **una sola diferencia de un tick desalinea todo lo
    posterior** y la cobertura se desploma aunque las sesiones siguientes sean
    identicas. Medido: GC 04-26 dio 1,3 % de cobertura y GC 06-26 10,3 %, con
    39 de 50 sesiones de conteo de ticks IDENTICO.

    Los dos lados reinician la particion de 25 ticks en cada corte de sesion — por eso
    hay cubeta residual al cierre. Entonces `(trade_date, cubeta_dentro_de_la_sesion)`
    es una clave que **se recupera despues de cada divergencia** en vez de arrastrarla.

No reemplaza al otro harness: lo complementa. El acumulado sigue siendo la prueba mas
dura; esta mide cuanto del kernel se puede verificar cuando esa prueba se rompe por un
tick.

Uso:
    python tools/verify_parity_by_session.py --csv <oraculo> --tape <cinta> \
        [--out-json <ruta>] [--no-filtro-horario]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from edgelab.bridge.cme_hours import filter_cme_week  # noqa: E402
from edgelab.bridge.indicators.bigtrap2absorption import DEFAULTS, run as run_abs  # noqa: E402
from edgelab.bridge.ticks import TickSeries  # noqa: E402

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_DST_OUT_2025 = int(datetime(2025, 11, 2, 7, 0, tzinfo=timezone.utc).timestamp())
_DST_IN_2026 = int(datetime(2026, 3, 8, 8, 0, tzinfo=timezone.utc).timestamp())


def _trade_date(ts_ns: np.ndarray) -> np.ndarray:
    """Trade date CME (la sesion arranca 17:00 CT del dia anterior), como YYYYMMDD int."""
    s = ts_ns // 1_000_000_000
    off = np.where((s < _DST_OUT_2025) | (s >= _DST_IN_2026), -5 * 3600, -6 * 3600)
    loc = s + off + 7 * 3600
    out = np.empty(loc.size, dtype=np.int64)
    for i, v in enumerate(loc):
        out[i] = int(datetime.fromtimestamp(int(v), tz=timezone.utc).strftime("%Y%m%d"))
    return out


def leer_oraculo(path: pathlib.Path) -> tuple[dict, dict]:
    """Devuelve `(meta, {trade_date: [cubetas en orden]})` desde el export del `.cs`."""
    meta: dict = {}
    por_sesion: dict[str, list] = collections.defaultdict(list)
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.startswith("# meta"):
            meta = dict(x.split("=", 1) for x in ln[6:].strip().split(",") if "=" in x)
            continue
        q = ln.split("|")
        if len(q) != 4:
            continue
        if q[2] == "BARRA_PROCESADA":
            d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
            por_sesion[d["td"]].append({"largo": int(d["largo"]),
                                        "residual": d["residual"] == "True"})
        elif q[2] == "ABS_SCORE":
            d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
            td = None  # ABS_SCORE no trae td; se aparea por orden con BARRA_PROCESADA
            _ = td
    return meta, dict(por_sesion)


def leer_oraculo_scores(path: pathlib.Path) -> dict:
    """`{trade_date: [dict de ABS_SCORE en orden]}`, apareando por el td de la BARRA previa."""
    por_sesion: dict[str, list] = collections.defaultdict(list)
    td_actual = None
    for ln in path.read_text(encoding="utf-8").splitlines():
        q = ln.split("|")
        if len(q) != 4:
            continue
        if q[2] == "BARRA_PROCESADA":
            d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
            td_actual = d["td"]
        elif q[2] == "ABS_SCORE" and td_actual is not None:
            d = dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
            por_sesion[td_actual].append(d)
    return dict(por_sesion)


def cargar_cinta(path: pathlib.Path, tick_size: float, filtrar: bool):
    ts, px, bid, ask, vol = [], [], [], [], []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for ln in f:
            p = ln.rstrip("\n").split(";")
            if len(p) < 5:
                continue
            s = p[0]
            d = datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]),
                         int(s[9:11]), int(s[11:13]), int(s[13:15]), tzinfo=timezone.utc)
            ts.append(int((d - EPOCH).total_seconds()) * 1_000_000_000 + int(s[16:23]) * 100)
            px.append(round(float(p[1]) / tick_size))
            bid.append(round(float(p[2]) / tick_size))
            ask.append(round(float(p[3]) / tick_size))
            vol.append(float(p[4]))
    serie = TickSeries(
        ts_ns=np.array(ts, dtype=np.int64),
        price_ticks=np.array(px, dtype=np.int64),
        bid_ticks=np.array(bid, dtype=np.int64),
        ask_ticks=np.array(ask, dtype=np.int64),
        volume=np.array(vol, dtype=np.float64),
        sequence=np.arange(len(ts), dtype=np.int64),
        tick_size=tick_size)
    detalle = None
    if filtrar:
        serie, detalle = filter_cme_week(serie, report=True)
    return serie, detalle


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=pathlib.Path, required=True)
    ap.add_argument("--tape", type=pathlib.Path, required=True)
    ap.add_argument("--tick-size", type=float, default=0.10)
    ap.add_argument("--out-json", type=pathlib.Path, default=None)
    ap.add_argument("--no-filtro-horario", action="store_true")
    a = ap.parse_args()

    print(f"[*] oraculo {a.csv.name}", flush=True)
    meta, _ = leer_oraculo(a.csv)
    scores_cs = leer_oraculo_scores(a.csv)
    modo = meta.get("score_mode")
    assert modo, "el export no declara score_mode"
    print(f"    score_mode={modo}  sesiones={len(scores_cs)}", flush=True)

    print(f"[*] cinta {a.tape.name}", flush=True)
    serie, det = cargar_cinta(a.tape, a.tick_size, not a.no_filtro_horario)
    if det:
        print(f"    filtro horario CME: {det['descartados']} descartados, "
              f"{det['conservados']} conservados", flush=True)

    print("[*] kernel", flush=True)
    p = dict(DEFAULTS)
    p["ScoreMode"] = modo
    res = run_abs(serie, params=p)

    # Cubetas de Python agrupadas por trade date, en orden
    py_ev = [e.split("|") for e in res.get("events", [])]
    py_scores = [dict(x.split("=", 1) for x in q[3].split(";") if "=" in x)
                 for q in py_ev if len(q) == 4 and q[2] == "ABS_SCORE"]
    ts_py = np.array([int(datetime.strptime(d["t_start"][:26], "%Y-%m-%dT%H:%M:%S.%f")
                          .replace(tzinfo=timezone.utc).timestamp() * 1e9) for d in py_scores],
                     dtype=np.int64)
    td_py = _trade_date(ts_py)
    por_sesion_py: dict[str, list] = collections.defaultdict(list)
    for d, td in zip(py_scores, td_py):
        por_sesion_py[str(td)].append(d)

    campos = ("signed_flow", "d_ticks", "a_score", "n_ticks", "a_thr", "a_pass", "n_hist")
    rep = {"oraculo": a.csv.name, "cinta": a.tape.name, "score_mode": modo,
           "filtro_horario": not a.no_filtro_horario,
           "filtro_detalle": det, "por_sesion": {}, "resumen": {}}

    comunes = sorted(set(scores_cs) & set(por_sesion_py))
    solo_cs = sorted(set(scores_cs) - set(por_sesion_py))
    solo_py = sorted(set(por_sesion_py) - set(scores_cs))

    n_ident = 0
    agg = {c: [0, 0] for c in campos}
    print(f"\n  {'sesion':<10} {'.cs':>7} {'py':>7} {'estado':<12} campos exactos")
    for td in comunes:
        A, B = scores_cs[td], por_sesion_py[td]
        if len(A) != len(B):
            rep["por_sesion"][td] = {"cs": len(A), "py": len(B), "estado": "CONTEO_DISTINTO"}
            print(f"  {td:<10} {len(A):>7} {len(B):>7} {'conteo dif':<12} -")
            continue
        det_s = {}
        for c in campos:
            ok = sum(1 for x, y in zip(A, B) if _igual(c, x.get(c), y.get(c)))
            det_s[c] = f"{ok}/{len(A)}"
            agg[c][0] += ok
            agg[c][1] += len(A)
        todo = all(det_s[c] == f"{len(A)}/{len(A)}" for c in campos)
        n_ident += todo
        rep["por_sesion"][td] = {"cs": len(A), "py": len(B),
                                 "estado": "EXACTA" if todo else "PARCIAL", **det_s}
        print(f"  {td:<10} {len(A):>7} {len(B):>7} {'EXACTA' if todo else 'parcial':<12} "
              + " ".join(f"{c}={det_s[c]}" for c in campos if det_s[c] != f"{len(A)}/{len(A)}")
              or "")

    rep["resumen"] = {
        "sesiones_comunes": len(comunes),
        "sesiones_exactas": n_ident,
        "sesiones_solo_cs": solo_cs,
        "sesiones_solo_py": solo_py,
        "por_campo": {c: {"exactas": agg[c][0], "total": agg[c][1],
                          "pct": round(100 * agg[c][0] / agg[c][1], 4) if agg[c][1] else None}
                      for c in campos},
        "veredicto": ("PARIDAD_POR_SESION_EXACTA" if n_ident == len(comunes) and comunes
                      else f"PARCIAL {n_ident}/{len(comunes)}"),
    }
    print("\n" + "=" * 74)
    print(f"  sesiones comparables : {len(comunes)}")
    print(f"  sesiones EXACTAS     : {n_ident}/{len(comunes)}")
    print(f"  solo en el .cs       : {len(solo_cs)}  {solo_cs[:6]}")
    print(f"  solo en Python       : {len(solo_py)}  {solo_py[:6]}")
    print("  por campo, sobre las sesiones de igual conteo:")
    for c in campos:
        v = rep["resumen"]["por_campo"][c]
        if v["total"]:
            print(f"    {c:<12} {v['exactas']:>8}/{v['total']:<8} {v['pct']:>8.4f} %")
    print(f"\n  -> {rep['resumen']['veredicto']}")

    if a.out_json:
        a.out_json.write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n  artefacto: {a.out_json}")
    return 0


def _igual(campo: str, x, y) -> bool:
    if x is None or y is None:
        return False
    if campo in ("a_pass",):
        return str(x) == str(y)
    try:
        fx, fy = float(x), float(y)
    except ValueError:
        return str(x) == str(y)
    if fx != fx and fy != fy:      # NaN == NaN para este proposito
        return True
    return abs(fx - fy) <= 1e-9 * max(1.0, abs(fx), abs(fy))


if __name__ == "__main__":
    raise SystemExit(main())
