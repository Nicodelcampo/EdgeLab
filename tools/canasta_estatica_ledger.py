"""Libro de la canasta estática PREAPERTURA-ES, PREAPERTURA-NQ, DRC-YM-4.

Lee la serie publicada. No recomputa ticks y no abre el holdout.
"""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SERIES = RAIZ / "docs" / "research" / "regimen_corto_20261106" / "series_diarias_regimen_20261106.json"
SALIDA = RAIZ / "docs" / "research" / "regimen_corto_20261106" / "ledger_canasta_estatica.json"
NOMBRES = ("PREAPERTURA-ES", "PREAPERTURA-NQ", "DRC-YM-4")
OOS = ("20260401", "20260930")
HOLDOUT = "20261001"


def _suma(celdas, desde=None, hasta=None):
    r = n = 0.0
    dias = 0
    for dia, celda in celdas.items():
        if dia >= HOLDOUT:
            raise SystemExit(f"la serie publicada tiene holdout en {dia}")
        if desde and dia < desde:
            continue
        if hasta and dia > hasta:
            continue
        r += float(celda["m"]) * float(celda["n"])
        n += float(celda["n"])
        dias += 1
    return {"r": r, "n": n, "rop": (r / n) if n else None, "dias": dias}


def ledger(reglas):
    por_nombre = {r["regla"]: r for r in reglas}
    faltan = [n for n in NOMBRES if n not in por_nombre]
    if faltan:
        raise SystemExit(f"faltan reglas en la serie: {faltan}")
    miembros = []
    r = n = ro = no = 0.0
    for nombre in NOMBRES:
        regla = por_nombre[nombre]
        completo = _suma(regla["celdas"])
        oos = _suma(regla["celdas"], *OOS)
        r += completo["r"]
        n += completo["n"]
        ro += oos["r"]
        no += oos["n"]
        miembros.append({
            "regla": nombre,
            "familia": regla["familia"],
            "instrumento": regla["instrumento"],
            "celda_coord": regla["celda_coord"],
            "completo": completo,
            "oos_202604_202609": oos,
        })
    return {
        "nombres": list(NOMBRES),
        "miembros": miembros,
        "completo": {"r": r, "n": n, "rop": (r / n) if n else None},
        "oos_202604_202609": {"r": ro, "n": no, "rop": (ro / no) if no else None},
        "recomputado_contra_ticks": False,
        "holdout_abierto": False,
    }


def main():
    series = json.loads(SERIES.read_text(encoding="utf-8"))
    out = ledger(series["series_cand"])
    SALIDA.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"completo": out["completo"], "oos": out["oos_202604_202609"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
