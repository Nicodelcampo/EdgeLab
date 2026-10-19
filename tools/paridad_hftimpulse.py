#!/usr/bin/env python3
"""Paridad NT8 ↔ Python de HFTImpulseZones_P.

El CSV trae, por ventana evaluada, las **tres series enteras que decidieron**
(`closes`, `highs`, `lows`) junto con el resultado de NT8. Con eso Python
reconstruye todo sin ticks y sin parquet, y se compara campo por campo.

## Dos capas, y la segunda es la que importa

**A. Ventana.** Se recalcula cada ventana con `evaluate_impulse_window` y se
comparan desplazamiento, recorrido, eficiencia, volumen, decisión, dirección y
geometría de la zona. Es aritmética entera pura: debería dar exacto.

**B. Cadena de racha.** Se recorren las filas en orden reconstruyendo el estado
—dirección, conteo de ráfagas no solapadas, desplazamiento acumulado, emisión de
señal— y se compara contra `burst_dir`, `burst_count`,
`burst_displacement_ticks` e `is_signal` de NT8.

La capa B es la que vale: la ventana es una función sin memoria y equivocarse ahí
es difícil, pero la racha es **estado acumulado** —el conteo no solapado, el corte
por dirección, por distancia y por sesión, y la regla de una señal por racha— y
ese estado es exactamente donde dos implementaciones se separan sin que se note.

## Lo que NO valida

No valida que Python reconstruya las mismas barras desde el parquet. Eso es otra
capa y su techo conocido es 89,81 %
(`docs/research/avolcluster_partition_audit_20260903/`).

Uso:
    python tools/paridad_hftimpulse.py <csv_de_nt8> [--json salida.json]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edgelab.bridge.indicators.parity_first import (  # noqa: E402
    IMPULSE_DEFAULTS, evaluate_impulse_window)

CAMPOS_VENTANA = ("decision", "direction", "displacement_ticks", "path_ticks",
                  "efficiency_bps", "zone_lower_tick", "zone_upper_tick")
CAMPOS_RACHA = ("burst_dir", "burst_count", "burst_displacement_ticks", "is_signal")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _serie(texto):
    return [int(x) for x in (texto or "").split("|") if x.strip()]


def _num(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return v


def comparar(csv_path: Path, max_ejemplos: int = 20) -> dict:
    # utf-8-sig: HFTImpulseZones_P escribia con BOM (Encoding.UTF8), y con BOM la
    # linea de meta no empieza por "# meta", asi que pasaba a ser la cabecera y el
    # archivo entero se leia mal -- en silencio, dando 0 ventanas.
    lineas = csv_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    meta = {}
    for parte in next((l for l in lineas if l.startswith("# meta")), "").lstrip("#").split(","):
        k, _, v = parte.partition("=")
        if k.strip():
            meta[k.strip()] = v.strip()

    p = dict(IMPULSE_DEFAULTS)
    for clave, col in (("window_bars", "window_bars"),
                       ("min_displacement_ticks", "min_displacement_ticks"),
                       ("min_efficiency_bps", "min_efficiency_bps"),
                       ("min_window_volume", "min_window_volume"),
                       ("zone_height_ticks", "zone_height_ticks"),
                       ("min_bursts_for_signal", "min_bursts_for_signal"),
                       ("max_bars_between_bursts", "max_bars_between_bursts"),
                       ("min_burst_displacement_ticks", "min_burst_displacement_ticks")):
        if col in meta:
            p[clave] = int(meta[col])
    w = p["window_bars"]

    filas = list(csv.DictReader([l for l in lineas if not l.startswith("# meta")]))

    n = 0
    ventana_ok = 0
    dif_ventana = {c: 0 for c in CAMPOS_VENTANA}
    ejemplos = []

    # --- estado de la cadena de racha, reconstruido de cero ---
    racha_ok = 0
    dif_racha = {c: 0 for c in CAMPOS_RACHA}
    b_dir = 0
    b_count = 0
    b_disp = 0
    last_bar = None
    emitida = False
    ses_prev = None
    senales_py = 0
    senales_nt8 = 0

    for fila in filas:
        closes = _serie(fila.get("closes"))
        highs = _serie(fila.get("highs"))
        lows = _serie(fila.get("lows"))
        if len(closes) != w:
            continue
        tiene_ohlc = len(highs) == w and len(lows) == w
        n += 1

        bar = _num(fila.get("window_index"))
        ses = fila.get("session_index")
        vol = _num(fila.get("window_volume")) or 0
        # el volumen no viene por barra; se reparte para respetar el umbral, que
        # sólo mira la suma. Si min_window_volume es 0 (default) da igual.
        vols = [vol // w] * w
        vols[-1] += vol - sum(vols)

        py = evaluate_impulse_window(closes, highs if tiene_ohlc else closes,
                                     lows if tiene_ohlc else closes, vols, p)

        difs = {}
        for campo in CAMPOS_VENTANA:
            if campo in ("zone_lower_tick", "zone_upper_tick") and not tiene_ohlc:
                continue          # sin highs/lows la geometría no es verificable
            v_nt8 = _num(fila.get(campo))
            v_py = py.get(campo)
            if campo == "decision":
                v_nt8 = (fila.get("decision") or "").strip()
                v_py = str(v_py)
            if campo in ("zone_lower_tick", "zone_upper_tick") and v_nt8 is None:
                v_py = None if py["decision"] != "CREATE" else v_py
            if v_nt8 != v_py:
                difs[campo] = {"nt8": v_nt8, "python": v_py}
                dif_ventana[campo] += 1
        if difs:
            if len(ejemplos) < max_ejemplos:
                ejemplos.append({"window_index": fila.get("window_index"),
                                 "capa": "ventana", "difs": difs})
        else:
            ventana_ok += 1

        # ---- cadena de racha ----
        if ses_prev is not None and ses != ses_prev:
            b_dir = b_count = b_disp = 0
            last_bar = None
            emitida = False
        ses_prev = ses

        senal_py = 0
        if py["decision"] == "CREATE":
            if last_bar is None or bar - last_bar >= w:
                sigue = (b_dir == py["direction"] and last_bar is not None
                         and bar - last_bar <= p["max_bars_between_bursts"])
                if sigue:
                    b_count += 1
                    b_disp += py["displacement_ticks"]
                else:
                    b_dir = py["direction"]
                    b_count = 1
                    b_disp = py["displacement_ticks"]
                    emitida = False
                last_bar = bar
                if (not emitida and b_count >= p["min_bursts_for_signal"]
                        and b_disp >= p["min_burst_displacement_ticks"]):
                    emitida = True
                    senal_py = 1

        esperado = {"burst_dir": b_dir, "burst_count": b_count,
                    "burst_displacement_ticks": b_disp, "is_signal": senal_py}
        difs_r = {}
        for campo in CAMPOS_RACHA:
            v_nt8 = _num(fila.get(campo))
            if v_nt8 != esperado[campo]:
                difs_r[campo] = {"nt8": v_nt8, "python": esperado[campo]}
                dif_racha[campo] += 1
        senales_py += senal_py
        senales_nt8 += 1 if _num(fila.get("is_signal")) == 1 else 0
        if difs_r:
            if len(ejemplos) < max_ejemplos:
                ejemplos.append({"window_index": fila.get("window_index"),
                                 "capa": "racha", "difs": difs_r})
        else:
            racha_ok += 1

    def pct(a, b):
        return round(a / b, 6) if b else None

    veredicto = ("EXACT" if n and ventana_ok == n and racha_ok == n else
                 "MISMATCH" if n else "SIN_DATOS")

    return {
        "schema": "hftimpulse_parity_v1",
        "estimand": ("paridad sobre input igual: se recalcula cada ventana con las "
                     "series closes/highs/lows que NT8 exporto, y se reconstruye la "
                     "cadena de racha de cero. NO valida la reconstruccion de barras "
                     "desde el parquet."),
        "oraculo": str(csv_path), "oraculo_sha256": sha256(csv_path),
        "meta_nt8": meta, "params_usados": p,
        "n_ventanas": n,
        "capa_A_ventana_identicas": ventana_ok,
        "capa_A_pct": pct(ventana_ok, n),
        "capa_A_diferencias": {k: v for k, v in dif_ventana.items() if v},
        "capa_B_racha_identicas": racha_ok,
        "capa_B_pct": pct(racha_ok, n),
        "capa_B_diferencias": {k: v for k, v in dif_racha.items() if v},
        "senales_nt8": senales_nt8, "senales_python": senales_py,
        "ejemplos_de_diferencia": ejemplos,
        "veredicto": veredicto,
        "outcomes_accessed": False, "holdout_accessed": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    a = ap.parse_args(argv)
    if not a.csv.exists():
        print(f"no existe: {a.csv}", file=sys.stderr)
        return 2
    rep = comparar(a.csv)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    print(f"ventanas             : {rep['n_ventanas']}")
    print(f"capa A (ventana)     : {rep['capa_A_ventana_identicas']} "
          f"({(rep['capa_A_pct'] or 0):.4%})")
    print(f"capa B (racha)       : {rep['capa_B_racha_identicas']} "
          f"({(rep['capa_B_pct'] or 0):.4%})")
    print(f"senales NT8 / Python : {rep['senales_nt8']} / {rep['senales_python']}")
    print(f"veredicto            : {rep['veredicto']}")
    for k in ("capa_A_diferencias", "capa_B_diferencias"):
        if rep[k]:
            print(f"\n{k}:")
            for c, v in sorted(rep[k].items(), key=lambda x: -x[1]):
                print(f"  {c:<28} {v}")
    for e in rep["ejemplos_de_diferencia"][:5]:
        print(f"  [{e['capa']}] ventana {e['window_index']}: "
              f"{json.dumps(e['difs'], ensure_ascii=False)}")
    return 0 if rep["veredicto"] == "EXACT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
