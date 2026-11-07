"""H-REG-2: el tercil del rango de la sesión previa, observable antes de operar.

El mapa de familias está congelado en
docs/research/regimen_corto_20261106/PREREGISTRO_HREG2_AMPLITUD_20261107.md.
Este módulo no elige el tercil mirando el P&L.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
SERIES = RAIZ / "docs" / "research" / "regimen_corto_20261106" / "series_diarias_regimen_20261106.json"
RANGOS = RAIZ / "docs" / "research" / "regimen_corto_20261106" / "rangos_sesion_preholdout.json"
SALIDA = RAIZ / "docs" / "research" / "regimen_corto_20261106" / "resultado_hreg2_amplitud.json"

MAPA = {"RANGO_PREAPERTURA": 0, "COMPRESION_NR": 0, "ABSORCION_CLIMAX": 2}
VENTANA = 20
B = 200
SEMILLA = 20261107
N_MIN_FILTRADO = 30
N_MIN_ELEGIBLE = 90
HOLDOUT = "20261001"


def estado_tercil(rangos_por_dia: dict, ventana: int = VENTANA) -> dict:
    """Tercil de la sesión previa contra las `ventana` sesiones anteriores al día que se opera."""
    dias = sorted(d for d in rangos_por_dia if d < HOLDOUT)
    valores = [float(rangos_por_dia[d]) for d in dias]
    out = {}
    for i in range(ventana, len(dias)):
        ventana_previa = np.asarray(valores[i - ventana:i], float)
        ayer = ventana_previa[-1]
        q1, q2 = np.quantile(ventana_previa, [1.0 / 3.0, 2.0 / 3.0])
        if ayer <= q1:
            tercil = 0
        elif ayer <= q2:
            tercil = 1
        else:
            tercil = 2
        out[dias[i]] = tercil
    return out


def _acumular(reglas, estado_por_inst, mapa=MAPA):
    r_todo = n_todo = r_filtro = n_filtro = 0.0
    por_regla = []
    for regla in reglas:
        familia = str(regla.get("familia", "")).upper()
        if familia not in mapa:
            continue
        inst = regla.get("instrumento")
        estado = estado_por_inst.get(inst)
        if not estado:
            por_regla.append({"regla": regla["regla"], "familia": familia, "instrumento": inst, "estado": "sin_rango"})
            continue
        quiero = mapa[familia]
        rt = nt = rf = nf = 0.0
        for dia, celda in regla.get("celdas", {}).items():
            if dia >= HOLDOUT or dia not in estado:
                continue
            r = float(celda["m"]) * float(celda["n"])
            n = float(celda["n"])
            rt += r
            nt += n
            if estado[dia] == quiero:
                rf += r
                nf += n
        r_todo += rt
        n_todo += nt
        r_filtro += rf
        n_filtro += nf
        por_regla.append({
            "regla": regla["regla"],
            "familia": familia,
            "instrumento": inst,
            "tercil": quiero,
            "n": nt,
            "n_filtrado": nf,
            "rop": (rt / nt) if nt else None,
            "rop_filtrado": (rf / nf) if nf else None,
        })
    delta = None
    if n_todo and n_filtro:
        delta = (r_filtro / n_filtro) - (r_todo / n_todo)
    return {
        "delta": delta,
        "n": n_todo,
        "n_filtrado": n_filtro,
        "rop": (r_todo / n_todo) if n_todo else None,
        "rop_filtrado": (r_filtro / n_filtro) if n_filtro else None,
        "por_regla": por_regla,
    }


def _permutar(estado_por_inst, rng):
    out = {}
    for inst, estado in estado_por_inst.items():
        dias = list(estado)
        etiquetas = [estado[d] for d in dias]
        rng.shuffle(etiquetas)
        out[inst] = dict(zip(dias, etiquetas))
    return out


def evaluar(reglas, rangos_por_inst, *, semilla=SEMILLA, b=B, n_min_filtrado=N_MIN_FILTRADO, n_min_elegible=N_MIN_ELEGIBLE):
    estado = {inst: estado_tercil(dias) for inst, dias in rangos_por_inst.items()}
    obs = _acumular(reglas, estado)
    rng = np.random.default_rng(semilla)
    nulos = []
    for _ in range(b):
        nulos.append(_acumular(reglas, _permutar(estado, rng))["delta"])
    validos = [x for x in nulos if x is not None]
    delta = obs["delta"]
    if delta is None or not validos:
        p = None
    else:
        p = (1 + sum(1 for x in validos if x >= delta)) / (len(validos) + 1)
    completo = all(r.get("estado") != "sin_rango" for r in obs["por_regla"]) and bool(obs["por_regla"])
    pasa = bool(
        completo
        and delta is not None
        and p is not None
        and delta > 0
        and p <= 0.05
        and obs["n"] >= n_min_elegible
        and obs["n_filtrado"] >= n_min_filtrado
    )
    return {
        "delta": delta,
        "p": p,
        "pasa": pasa,
        "completo": completo,
        "n": obs["n"],
        "n_filtrado": obs["n_filtrado"],
        "rop": obs["rop"],
        "rop_filtrado": obs["rop_filtrado"],
        "por_regla": obs["por_regla"],
        "B": b,
        "semilla": semilla,
        "mapa": MAPA,
    }


def main():
    series = json.loads(SERIES.read_text(encoding="utf-8"))
    rangos = json.loads(RANGOS.read_text(encoding="utf-8"))
    out = evaluar(series["series_cand"], rangos)
    SALIDA.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("delta", "p", "pasa", "completo", "n", "n_filtrado", "rop", "rop_filtrado")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
