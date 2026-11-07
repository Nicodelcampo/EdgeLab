#!/usr/bin/env python3
"""Walk-forward H-REG-1 congelado en PREREGISTRO_HREG1_WALKFORWARD_20261107.md.

No abre el holdout: sólo usa series diarias ya publicadas con sesiones <= 2026-09-30.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from statistics import mean, stdev

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "docs/research/regimen_corto_20261106/series_diarias_regimen_20261106.json"
N_MIN = 8
K = 3
B = 200
SEMILLA = 20261107


def _r_dia(c: dict) -> float:
    return float(c.get("r", c["m"] * c["n"]))


def _suma(regla: dict, meses: set[str] | None, antes_de: str | None = None) -> tuple[int, float]:
    n = 0
    r = 0.0
    for dia, c in regla["celdas"].items():
        if not c.get("n"):
            continue
        if meses is not None and dia[:6] not in meses:
            continue
        if antes_de is not None and dia >= antes_de:
            continue
        n += int(c["n"])
        r += _r_dia(c)
    return n, r


def _meses(reglas: list[dict]) -> list[str]:
    vistos = {d[:6] for r in reglas for d in r["celdas"]}
    return sorted(vistos)


def _dedup(cands: list[tuple[float, int, str, dict]]) -> list[dict]:
    """cands: (puntaje, n_ops, nombre, regla), mayor puntaje gana; empate por n y por nombre."""
    mejor: dict[tuple, tuple] = {}
    for puntaje, n_ops, nombre, regla in cands:
        clave = (regla.get("familia"), regla.get("instrumento"))
        anterior = mejor.get(clave)
        nuevo = (puntaje, n_ops, nombre)
        if anterior is None or nuevo > anterior[0]:
            mejor[clave] = (nuevo, regla)
    return [v[1] for v in mejor.values()]


def _rop(reglas: list[dict], mes: str) -> tuple[int, float]:
    n = 0
    r = 0.0
    for regla in reglas:
        nn, rr = _suma(regla, {mes})
        n += nn
        r += rr
    return n, (r / n if n else float("nan"))


def _t(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    sd = stdev(xs)
    if sd <= 1e-12:
        return None
    return mean(xs) / (sd / (len(xs) ** 0.5))


def evaluar(reglas: list[dict], w: int, primera_h: str, ultima_h: str, semilla: int = SEMILLA) -> dict:
    meses = [m for m in _meses(reglas) if "202508" <= m <= "202609"]
    rng = random.Random(semilla)
    filas = []
    d_azar, d_est = [], []
    for i, h in enumerate(meses):
        if h < primera_h or h > ultima_h:
            continue
        if i < w:
            continue
        w_meses = set(meses[i - w : i])
        elegibles = []
        for r in reglas:
            n_w, r_w = _suma(r, w_meses)
            if n_w < N_MIN:
                continue
            n_hist, r_hist = _suma(r, None, antes_de=h + "01")
            elegibles.append((r, n_w, r_w, n_hist, r_hist))
        mom = _dedup([(r_w, n_w, r["regla"], r) for r, n_w, r_w, _nh, _rh in elegibles])
        if len(mom) < K:
            filas.append({"h": h, "valida": False, "n_tras_dedup": len(mom)})
            continue
        top = sorted(mom, key=lambda r: (_suma(r, w_meses)[1], _suma(r, w_meses)[0], r["regla"]), reverse=True)[:K]
        est_pool = _dedup([(rh, nh, r["regla"], r) for r, _nw, _rw, nh, rh in elegibles])
        est = sorted(est_pool, key=lambda r: (_suma(r, None, h + "01")[1], _suma(r, None, h + "01")[0], r["regla"]), reverse=True)[:K]
        n_m, rop_m = _rop(top, h)
        n_e, rop_e = _rop(est, h)
        rops_azar = []
        for _ in range(B):
            muestra = rng.sample(mom, K)
            _n, rop = _rop(muestra, h)
            if _n:
                rops_azar.append(rop)
        rop_a = mean(rops_azar) if rops_azar else float("nan")
        fila = {
            "h": h,
            "valida": bool(n_m and n_e and rops_azar),
            "elegidas": [r["regla"] for r in top],
            "estatica": [r["regla"] for r in est],
            "n_ops": n_m,
            "rop": None if not n_m else round(rop_m, 4),
            "rop_azar": None if not rops_azar else round(rop_a, 4),
            "rop_estatica": None if not n_e else round(rop_e, 4),
        }
        if fila["valida"]:
            d_azar.append(rop_m - rop_a)
            d_est.append(rop_m - rop_e)
            fila["delta_azar"] = round(d_azar[-1], 4)
            fila["delta_estatica"] = round(d_est[-1], 4)
        filas.append(fila)
    def _bloque(xs: list[float]) -> dict:
        return {
            "n": len(xs),
            "media": None if not xs else round(mean(xs), 4),
            "t": None if _t(xs) is None else round(_t(xs), 3),
        }
    ba, be = _bloque(d_azar), _bloque(d_est)
    pasa = (
        ba["media"] is not None and be["media"] is not None
        and ba["media"] > 0 and be["media"] > 0
        and ba["t"] is not None and be["t"] is not None
        and ba["t"] >= 2 and be["t"] >= 2
    )
    return {"ventanas": filas, "delta_azar": ba, "delta_estatica": be, "pasa": pasa, "semilla": semilla, "B": B}


def main() -> None:
    data = json.loads(SERIES.read_text(encoding="utf-8"))
    pool = data["series_cand"]
    primario = evaluar(pool, 3, "202511", "202609")
    secundario = evaluar(pool, 2, "202510", "202609")
    out = {"primario_W3H1": primario, "secundario_W2H1": secundario}
    dest = ROOT / "docs/research/regimen_corto_20261106/resultado_hreg1_walkforward.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "W3H1": {k: primario[k] for k in ("delta_azar", "delta_estatica", "pasa")},
        "W2H1": {k: secundario[k] for k in ("delta_azar", "delta_estatica", "pasa")},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
