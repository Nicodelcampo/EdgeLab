#!/usr/bin/env python3
"""BONOS-RATIOS (pre-registro docs/research/bonos_ratios_20261127/PREREGISTRO.md): ¿el ratio ley NY / ley local de bonos argentinos con
el mismo flujo vuelve a su media? Medición sin P&L sobre los diarios de data912 (data/bonos_ar/, PROCEDENCIA.json).

  python tools/bonos_ratios.py medir        # DESC y REP de A5; los meses HOLDOUT no se leen

Medida principal (decidida antes): con el log-ratio r_t = ln(GD_t / AL_t) y su media móvil de 20 ruedas m_t (ruedas t−20..t−1),
desvío d_t = r_t − m_t. Regresión de Δ = r_{t+6} − r_{t+1} (salta una rueda: el rebote entre puntas y los cierres no sincrónicos sólo
afectan al primer día) sobre d_t. Reversión ⇔ pendiente < 0. Error estándar por bloques móviles de 20 ruedas (bootstrap, 2.000).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
DATA = ROOT / "data/bonos_ar"; OUT = ROOT / "docs/research/bonos_ratios_20261127"; PRE = "docs/research/bonos_ratios_20261127/PREREGISTRO.md"
PARES = {"GD30/AL30": ("GD30", "AL30"), "GD35/AL35": ("GD35", "AL35"), "GD38/AE38": ("GD38", "AE38"), "GD41/AL41": ("GD41", "AL41")}
L, SALTO, H = 20, 1, 5
REGIMENES = {"2021-09→2023-11": ("2021-09-01", "2023-11-30"), "2023-12→2025-04": ("2023-12-01", "2025-04-13"), "2025-04→2026-11": ("2025-04-14", "2026-11-30")}
COSTO_RT_PCT = 0.32 + 0.04   # spread de las dos patas (AL30 0,09 %, GD30 0,22 % en la foto de data912) + derechos 0,01 % × 4 lados (ida y vuelta)


def _serie(a: str, b: str) -> pd.DataFrame:
    A = pd.read_parquet(DATA / f"{a}.parquet"); B = pd.read_parquet(DATA / f"{b}.parquet")
    d = pd.concat([A.c.rename("ga"), B.c.rename("gb"), A.v.rename("va"), B.v.rename("vb")], axis=1).dropna()
    d = d[(d.va > 0) & (d.vb > 0)]
    d["r"] = np.log(d.ga / d.gb); d["m"] = d.r.shift(1).rolling(L).mean(); d["s"] = d.r.shift(1).rolling(L).std()
    d["dev"] = d.r - d.m; d["fut"] = d.r.shift(-(SALTO + H)) - d.r.shift(-SALTO)
    from edgelab.holdout import a5_bloque
    d["bloque"] = [a5_bloque(int(x.strftime("%Y%m%d"))) for x in d.index]
    sell = (~d.bloque.isin(["DESC", "REP"])).astype(int)
    d["limpio"] = (sell.shift(1).rolling(L).max() == 0) & (sell[::-1].rolling(SALTO + H + 1).max()[::-1] == 0)   # ventana pasada y futura sin meses sellados
    d["bloque_fut"] = d.bloque.where(d.limpio, "SELLADO")
    return d


def _pendiente(x: pd.DataFrame, B=2000, seed=11) -> dict:
    x = x.dropna(subset=["dev", "fut"]); n = len(x)
    if n < 60: return dict(n=n)
    X, Y = x.dev.to_numpy(), x.fut.to_numpy(); b = np.polyfit(X, Y, 1)[0]
    rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, min(s + L, n)) for s in rng.integers(0, n - L, n // L + 1)])[:n]
        bs.append(np.polyfit(X[idx], Y[idx], 1)[0])
    se = float(np.std(bs)); t = b / se if se > 0 else 0.0
    from math import erf, sqrt
    vida = float(np.log(2) / -np.log(1 + b / H)) if -1 < b / H < 0 else None      # vida media aproximada en ruedas (b sobre H ruedas)
    return dict(n=n, pendiente=round(float(b), 4), se=round(se, 4), t=round(float(t), 2), p_una_cola=round(0.5 * (1 + erf(t / sqrt(2))), 4),
                vida_media_ruedas=None if vida is None else round(vida, 1),
                desvio_tipico_pct=round(float(x.dev.std() * 100), 3), desvio_2sd_pct=round(float(2 * x.dev.std() * 100), 3),
                rebote_lag1=round(float(np.corrcoef(x.r.diff().dropna().iloc[1:], x.r.diff().dropna().shift(1).iloc[1:])[0, 1]), 3))


def medir() -> int:
    from registro_global import exigir_contada
    exigir_contada(PRE); OUT.mkdir(parents=True, exist_ok=True); res = {}
    for nombre, (a, b) in PARES.items():
        d = _serie(a, b); ok = d.bloque_fut.isin(["DESC", "REP"]) & d.bloque.isin(["DESC", "REP"])
        r = dict(primaria_DESC=_pendiente(d[ok & (d.bloque == "DESC")]), replica_REP=_pendiente(d[ok & (d.bloque == "REP")]))
        r["por_regimen_DESC_REP"] = {k: _pendiente(d[ok & (d.index >= v[0]) & (d.index <= v[1])]) for k, v in REGIMENES.items()}
        r["sin_salto_DESC"] = _pendiente(d[ok & (d.bloque == "DESC")].assign(fut=lambda z: z.r.shift(-H) - z.r))
        r["costo_rt_pct"] = COSTO_RT_PCT
        res[nombre] = r
    from edgelab.research.a5 import bh
    ps = {k: v["primaria_DESC"].get("p_una_cola", 1.0) for k, v in res.items()}
    nom = bh(list(ps.values()), q=0.10)
    for (k, _), s in zip(ps.items(), nom): res[k]["nominada_BH_DESC"] = bool(s)
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    for k, v in res.items():
        print(k, "DESC", v["primaria_DESC"], "\n   REP", v["replica_REP"], "\n   BH", v["nominada_BH_DESC"])
    return 0


if __name__ == "__main__":
    sys.exit({"medir": medir}[sys.argv[1]]())
