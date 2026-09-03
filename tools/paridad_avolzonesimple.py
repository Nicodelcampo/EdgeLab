#!/usr/bin/env python3
"""Paridad NT8 ↔ Python de AVolZoneSimple, capa 1: el algoritmo.

El CSV que escribe `nt8/AVolZoneSimple.cs` incluye el **perfil crudo del bloque**
(columna `cells`) junto con la decisión que NT8 tomó. Eso permite validar el
algoritmo **sin ticks y sin parquet**: se alimenta el kernel de Python con las
mismas celdas que vio NT8 y se comparan las dos decisiones, campo por campo.

## Qué prueba y qué NO prueba

**Prueba** que las dos implementaciones del algoritmo son la misma función:
ventana más angosta, aritmética entera, desempates, umbral de concentración,
clasificación respecto del cierre.

**No prueba** que Python reconstruya el mismo perfil desde los ticks del parquet.
Eso es la capa 2 y es un problema distinto —y conocido: la partición de barras de
NT8 se reproduce al 89,81 % (`docs/research/avolcluster_partition_audit_20260903/`)
porque los dos flujos de ticks no son idénticos transacción por transacción.

Confundir las dos capas es exactamente el defecto que se le señaló a la
certificación de aVolClusterPOI: `KERNEL_PARITY_ON_EQUAL_INPUT` al 100 % no dice
nada sobre el footprint. Por eso este script **declara su estimand en el reporte**
y se niega a llamarse «paridad» a secas.

Uso:
    python tools/paridad_avolzonesimple.py <csv_de_nt8> [--json salida.json]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edgelab.bridge.indicators.avolzonesimple import detect_block  # noqa: E402

CAMPOS = ("decision", "lower_tick", "upper_tick", "zone_ticks", "zone_volume",
          "block_volume", "block_ticks", "concentration", "side", "distance_ticks")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_meta(linea: str) -> dict:
    """Los parámetros con los que corrió NT8 vienen en la línea `# meta`.

    Se leen de ahí y NO se asumen: correr el kernel con otros parámetros que los
    del oráculo mediría dos cosas distintas y llamaría a eso una diferencia.
    """
    meta = {}
    for parte in linea.lstrip("#").split(","):
        k, _, v = parte.partition("=")
        k = k.strip()
        if k:
            meta[k] = v.strip()
    return meta


def parse_cells(texto: str) -> dict:
    celdas = {}
    for parte in (texto or "").split("|"):
        if not parte:
            continue
        t, _, v = parte.partition(":")
        try:
            celdas[int(t)] = int(float(v))
        except ValueError:
            pass
    return celdas


def _num(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return v


def comparar(csv_path: Path, max_ejemplos: int = 25) -> dict:
    texto = csv_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    meta_linea = next((l for l in texto if l.startswith("# meta")), "")
    meta = parse_meta(meta_linea)
    params = dict(
        bars_per_block=int(meta.get("bars_per_block", 10)),
        area_share_pct=int(meta.get("area_share_pct", 30)),
        max_zone_ticks=int(meta.get("max_zone_ticks", 12)),
        min_concentration=int(meta.get("min_concentration", 1500)),
    )

    filas = [l for l in texto if not l.startswith("# meta")]
    total = 0
    iguales = 0
    por_campo = {c: 0 for c in CAMPOS}
    por_decision = {}
    ejemplos = []

    for fila in csv.DictReader(filas):
        celdas = parse_cells(fila.get("cells", ""))
        if not celdas:
            continue
        total += 1
        close_tick = _num(fila.get("close_tick"))
        py = detect_block(celdas, params, close_tick)

        d_nt8 = (fila.get("decision") or "").strip()
        por_decision.setdefault(d_nt8, {"n": 0, "iguales": 0})
        por_decision[d_nt8]["n"] += 1

        difs = {}
        for campo in CAMPOS:
            v_nt8 = _num(fila.get(campo))
            v_py = py.get(campo)
            if campo in ("decision", "side"):
                v_nt8 = (fila.get(campo) or "").strip() or None
                v_py = v_py or None
            # NT8 deja vacías las columnas que no aplican; se comparan como None
            if v_nt8 != v_py:
                difs[campo] = {"nt8": v_nt8, "python": v_py}
                por_campo[campo] += 1

        if difs:
            if len(ejemplos) < max_ejemplos:
                ejemplos.append({"block_seq": fila.get("block_seq"),
                                 "bar_index": fila.get("bar_index"),
                                 "n_celdas": len(celdas), "difs": difs})
        else:
            iguales += 1
            por_decision[d_nt8]["iguales"] += 1

    veredicto = ("EXACT" if total and iguales == total else
                 "NEAR_EXACT" if total and iguales / total >= 0.999 else
                 "MISMATCH" if total else "SIN_DATOS")

    return {
        "schema": "avolzonesimple_kernel_parity_v1",
        "estimand": ("paridad del ALGORITMO sobre input igual: se alimenta el kernel "
                     "Python con las celdas que NT8 escribió. NO valida la "
                     "reconstrucción del perfil desde los ticks del parquet."),
        "oraculo": str(csv_path),
        "oraculo_sha256": sha256(csv_path),
        "meta_nt8": meta,
        "params_usados": params,
        "n_bloques": total,
        "n_identicos": iguales,
        "pct_identicos": round(iguales / total, 6) if total else None,
        "diferencias_por_campo": {k: v for k, v in por_campo.items() if v},
        "por_decision_nt8": por_decision,
        "ejemplos_de_diferencia": ejemplos,
        "veredicto": veredicto,
        "outcomes_accessed": False,
        "holdout_accessed": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--max-ejemplos", type=int, default=25)
    a = ap.parse_args(argv)

    if not a.csv.exists():
        print(f"no existe: {a.csv}", file=sys.stderr)
        return 2

    rep = comparar(a.csv, a.max_ejemplos)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(rep, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")

    print(f"bloques         : {rep['n_bloques']}")
    print(f"identicos       : {rep['n_identicos']} ({(rep['pct_identicos'] or 0):.4%})")
    print(f"veredicto       : {rep['veredicto']}")
    print(f"params (del CSV): {rep['params_usados']}")
    if rep["diferencias_por_campo"]:
        print("\ndiferencias por campo:")
        for k, v in sorted(rep["diferencias_por_campo"].items(), key=lambda x: -x[1]):
            print(f"  {k:<18} {v}")
        print("\nprimeros casos:")
        for e in rep["ejemplos_de_diferencia"][:5]:
            print(f"  bloque {e['block_seq']} (bar {e['bar_index']}, "
                  f"{e['n_celdas']} celdas): {json.dumps(e['difs'], ensure_ascii=False)}")
    print("\nOJO: esto valida el ALGORITMO sobre input igual, no la reconstruccion "
          "del perfil desde los ticks. Ver el campo `estimand` del JSON.")
    return 0 if rep["veredicto"] in ("EXACT", "NEAR_EXACT") else 1


if __name__ == "__main__":
    raise SystemExit(main())
