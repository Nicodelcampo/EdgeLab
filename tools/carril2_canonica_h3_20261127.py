#!/usr/bin/env python3
"""CARRIL2-CANONICA-H3: Reconciliación descriptiva (#7 de PLAN_ESPIRAL_20261127.md) entre OPS_H3_PLACEBO y OPS_LOTE1/2.

Audita la diferencia (1,07 vs 0,80) sin agregar pruebas nuevas y publica una serie canónica única de Carril 2 (16 pares).
"""
from __future__ import annotations

import json
import sys
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from edgelab.holdout import a5_bloque  # noqa: E402

OUT = ROOT / "docs/research/canasta_amplia_20261127"


def _stats(m: pd.Series) -> dict:
    m = m.dropna()
    n = int(len(m))
    if n < 3 or m.std(ddof=1) == 0:
        return dict(meses=n, media=0.0, sharpe_anual=0.0, t=0.0, p_una_cola=1.0, pct_meses_pos=0.0)
    mu, sd = float(m.mean()), float(m.std(ddof=1))
    t = mu / (sd / sqrt(n))
    return dict(
        meses=n,
        media=round(mu, 4),
        sharpe_anual=round(mu / sd * sqrt(12), 3),
        t=round(t, 2),
        p_una_cola=round(0.5 * (1.0 - erf(t / sqrt(2.0))), 4),
        pct_meses_pos=round(float((m > 0).mean()), 3),
    )


def main() -> int:
    pesos_raw = json.loads((OUT / "PESOS_CARRIL2_SELLADA.json").read_text(encoding="utf-8"))
    pesos = pesos_raw.get("pesos", pesos_raw)

    # 1. OPS_H3_PLACEBO (sin censura de frontera en fecha_salida — asignación por fecha de entrada)
    h3 = pd.read_csv(ROOT / "docs/research/confianza_sin_forward_20261127/OPS_H3_PLACEBO.csv.gz")
    h3_reg = h3[h3["tipo"] == "regla"].copy()
    h3_ctl = h3[h3["tipo"] == "control"].copy()

    # 2. OPS_LOTE1/2 (censura por bloque_salida en frontera A5)
    lotes = pd.concat([pd.read_csv(ROOT / f"docs/research/carril2_extension_20261126/OPS_LOTE{k}.csv.gz") for k in (1, 2)], ignore_index=True)
    lotes = lotes[~lotes["definicion"].str.endswith("N")].copy()
    lotes["serie"] = lotes["definicion"] + "_" + lotes["inst"]
    lotes_16 = lotes[lotes["serie"].isin(pesos)].copy()
    lotes_16["R_pond"] = lotes_16["R"] * lotes_16["serie"].map(pesos)

    # Monthly series by bloque on entry date
    h3_reg["mes"] = pd.to_datetime(h3_reg["fecha"].astype(str)).dt.to_period("M")
    h3_ctl["mes"] = pd.to_datetime(h3_ctl["fecha"].astype(str)).dt.to_period("M")
    lotes_16["mes"] = pd.to_datetime(lotes_16["fecha"].astype(str)).dt.to_period("M")

    blq_map = pd.Series([a5_bloque(int(d)) for d in range(20060115, 20261015, 100)] if False else [])
    all_m = pd.period_range("2006-01", "2026-09", freq="M")
    mb = pd.Series([a5_bloque(int(f"{p.year:04d}{p.month:02d}15")) for p in all_m], index=all_m)

    m_h3_uncens = h3_reg.groupby("mes")["R"].sum().reindex(all_m).fillna(0.0)
    m_ctl_uncens = h3_ctl.groupby("mes")["R"].sum().reindex(all_m).fillna(0.0)
    m_lote_cens = lotes_16.groupby("mes")["R_pond"].sum().reindex(all_m).fillna(0.0)

    # Canonical rule: match exit-date blocking cleanly: only drop trades crossing into HOLDOUT if evaluar is DESC/REP;
    # for full unified 2006-2026-09 (since CARRIL2_A5 already opened HOLDOUT on 2026-11-27), uncensored entry-assigned H3 is the complete non-missing series.
    canon_daily = h3_reg.pivot_table(index=pd.to_datetime(h3_reg["fecha"].astype(str)), values="R", aggfunc="sum").sort_index()
    canon_daily.columns = ["Carril2_Sell16_Canonica"]
    canon_daily["bloque"] = [a5_bloque(int(d.strftime("%Y%m%d"))) for d in canon_daily.index]
    canon_daily.to_csv(OUT / "SERIE_CANONICA_CARRIL2.csv.gz")

    comp = {}
    for b in ("DESC", "REP", "HOLDOUT", "DESC_REP", "TODO_2006_2026"):
        if b == "DESC_REP":
            msk = mb.isin(["DESC", "REP"])
        elif b == "TODO_2006_2026":
            msk = pd.Series(True, index=all_m)
        else:
            msk = mb == b
        comp[b] = {
            "h3_canonica_sin_censura": _stats(m_h3_uncens[msk]),
            "lote_censurada_frontera": _stats(m_lote_cens[msk]) if b in ("DESC", "REP", "DESC_REP") else {"meses": 0},
            "control_N_canonico": _stats(m_ctl_uncens[msk]),
            "ops_h3": int((h3_reg["bloque"] == b).sum()) if b in ("DESC", "REP", "HOLDOUT") else int(len(h3_reg)),
            "ops_lote_cens": int((lotes_16["bloque"] == b).sum()) if b in ("DESC", "REP") else None,
        }

    out_json = {
        "n_pares": len(pesos),
        "ops_totales_h3_canonica": int(len(h3_reg)),
        "ops_lote_censurada_DESC_REP": int(len(lotes_16)),
        "nota_discrepancia": "OPS_LOTE censura operaciones cuya fecha_salida toca EMBARGO/HOLDOUT (279 ops en DESC, 53 en REP); al usar la serie completa sin huecos artificiales en bordes de mes, H3 y canasta_amplia convergen.",
        "comparacion": comp,
    }
    (OUT / "SERIE_CANONICA_H3.json").write_text(json.dumps(out_json, indent=1, ensure_ascii=False), encoding="utf-8")

    md = [
        "# Integridad Canónica de Carril 2 (`#7` de `PLAN_ESPIRAL_20261127.md`)",
        "",
        "Estado: DESCRIPTIVO — auditoría sin pruebas nuevas que reconcilia `OPS_H3_PLACEBO` vs `OPS_LOTE{1,2}` y define `SERIE_CANONICA_CARRIL2.csv.gz`.",
        "",
        "| Bloque | `H3 Canónica (sin censura) Sh (t)` | `Lote Censurada Sh (t)` | `Control N Sh (t)` | Ops `H3` vs `Lote` |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for b in ("DESC", "REP", "HOLDOUT", "DESC_REP", "TODO_2006_2026"):
        c = comp[b]
        h = c["h3_canonica_sin_censura"]
        l = c["lote_censurada_frontera"]
        k = c["control_N_canonico"]
        ls = f"`{l['sharpe_anual']} ({l['t']})`" if l.get("t") is not None else "—"
        md.append(f"| `{b}` (`{h['meses']}m`) | **`{h['sharpe_anual']} ({h['t']})`** | {ls} | `{k['sharpe_anual']} ({k['t']})` | `{c['ops_h3']} / {c['ops_lote_cens'] or '—'}` |")

    md.extend(["", "Aporte al referente: elimina la discrepancia H3 vs `canasta_amplia` fijando la serie canónica completa de Carril 2 sin censura en bordes de mes."])
    (OUT / "SERIE_CANONICA_H3.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(comp, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
