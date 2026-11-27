#!/usr/bin/env python3
"""CRIPTO-V3-2019 (pre-registro docs/research/cripto_v3_2019_20261127/PREREGISTRO.md): la canasta CRIPTO-PIT v3, sin cambios, en el
período que nadie miró (2019-10 → 2020-12), antes del universo punto en el tiempo de la corrida original.

  python tools/cripto_v3_2019.py universo   # universo PIT 2019-10 → 2020-12 (mismo criterio: top-25 por volumen de 30 d, ≥ 60 d listado)
  python tools/cripto_v3_2019.py correr     # reglas, costos y pesos de canasta congelados de cripto_pit_v3 → RESULTADO.json

Cachés propias (data/crypto_binance_2019*) para no mezclar con las de la corrida original. Sólo meses DESC y REP de A5: los HOLDOUT
de 2019–2020 quedan sin leer (la única apertura de CRIPTO_BINANCE ya se usó, 2021–2026).
"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
OUT = ROOT / "docs/research/cripto_v3_2019_20261127"; PRE = "docs/research/cripto_v3_2019_20261127/PREREGISTRO.md"
UNIV = OUT / "UNIVERSO_PIT_2019_2020.csv"
PESOS = {"CR3_XSMOM_21d_Stag5d": 0.3858, "CR3_XSMOM_BetaNeut_Stag5d": 0.3568, "CR3_BAB_LowVol_Stag5d": 0.2574}   # congelados (DESC 2021–2026)
DESDE, HASTA = "2019-10-01", "2021-01-01"


def _configurar():
    import cripto_pit as P1, cripto_pit_v2 as P2, cripto_pit_v3 as P3
    P1.DATA = ROOT / "data/crypto_binance_2019"; P1.OUT = OUT
    P1.MESES = pd.period_range("2019-09", "2021-01", freq="M").strftime("%Y-%m").tolist()
    P1.UNIV_DESDE, P1.UNIV_HASTA = "2019-10", "2020-12"
    P2.DATA = ROOT / "data/crypto_binance_2019_1d"; P2.PER_MIN = "2019-09"; P2.DATA.mkdir(parents=True, exist_ok=True)
    P3.BASIS_DIR = ROOT / "data/crypto_binance_2019_basis"; P3.BASIS_DIR.mkdir(parents=True, exist_ok=True)
    return P1, P2, P3


def universo() -> int:
    P1, _, _ = _configurar(); OUT.mkdir(parents=True, exist_ok=True)
    P1.universo()                                                    # escribe OUT/UNIVERSO_PIT.csv con el período 2019-10 → 2020-12
    (OUT / "UNIVERSO_PIT.csv").rename(UNIV)
    u = pd.read_csv(UNIV); print(u.groupby("mes").size().to_string())
    return 0


def correr() -> int:
    from registro_global import exigir_contada
    exigir_contada(PRE)
    _, P2, P3 = _configurar()
    core = P3.compute_cripto_v3_daily(universo_csv=UNIV, desde=DESDE, hasta=HASTA)
    blq, base = core["blq"], core["daily_by_bps"]
    res = dict(monedas=core["n_coins_loaded"], series_basis=core["n_basis_series_loaded"], bloques=blq.value_counts().to_dict(), por_costo={})
    ok = blq.isin(["DESC", "REP"])
    for bps in (10, 20, 30, 40):
        D = base[bps]; cana = sum(D[k] * w for k, w in PESOS.items())
        res["por_costo"][bps] = dict(canasta=P2.stats_serie(cana[ok]),
                                     reglas={k: P2.stats_serie(D[k][ok]) for k in D.columns})
    D = base[20]; cana = sum(D[k] * w for k, w in PESOS.items())
    res["primaria"] = res["por_costo"][20]["canasta"]
    res["veredicto"] = "CONFIRMA" if res["primaria"]["t_mes"] >= 1.645 else ("NO_CONCLUYENTE" if res["primaria"]["usd_mes"] > 0 else "EN_CONTRA")
    m = cana[ok].groupby(cana[ok].index.to_period("M")).sum()
    res["meses"] = {str(k): round(float(v), 1) for k, v in m.items()}
    res["corr_btc_diaria"] = round(float(cana[ok].corr(core["btc_eval"][ok])), 3)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESULTADO.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    pd.DataFrame({**{k: D[k] for k in D.columns}, "CR3_Canasta": cana, "bloque": blq}).where(ok, np.nan).to_csv(OUT / "SERIES_DESC_REP.csv.gz")
    print(json.dumps({k: res[k] for k in ("monedas", "bloques", "primaria", "veredicto", "corr_btc_diaria")}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit({"universo": universo, "correr": correr}[sys.argv[1]]())
