#!/usr/bin/env python3
"""Escribe README_AGENTES.md de la release con tablas calculadas a partir de las partes por activo.

Uso: python tools/make_agent_readme.py --release D:/.../release_20261014 --census D:/.../census --commit <sha>
Debe correr ANTES de finalize_release.py (que fija su SHA-256 en el manifiesto).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

NAMES = {"ES": "E-mini S&P 500", "NQ": "E-mini Nasdaq-100", "MES": "Micro E-mini S&P 500", "MNQ": "Micro E-mini Nasdaq-100",
         "YM": "E-mini Dow", "MYM": "Micro E-mini Dow", "RTY": "E-mini Russell 2000", "GC": "Oro (Gold)", "MGC": "Micro Oro",
         "ZB": "Bono del Tesoro 30 años", "6E": "Euro FX", "6B": "Libra esterlina", "6J": "Yen japonés", "MBT": "Micro Bitcoin"}
STATUS_TXT = {
    "SELECTED": "incluida", "NO_ELIGIBLE": "sin contrato elegible (ningún candidato cumple la política en D-1)",
    "UNDETERMINED": "indeterminada (un competidor relevante no tiene dato en D-1)",
    "EXCLUDED_SELECTED_CONTRACT_HAS_NO_DATA": "el contrato elegido no tiene datos en la sesión"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--commit", default="?")
    ap.add_argument("--release-id", default="liquid_release_20261014")
    a = ap.parse_args()
    root, parts = Path(a.release), Path(a.release) / "metadata" / "parts"
    assets, pol, dec, runs = {}, {}, [], []
    for f in sorted(parts.glob("*_asset.json")):
        inst = f.name.split("_")[0]
        d = json.loads(f.read_text(encoding="utf-8"))
        assets[inst], pol[inst] = d["info"], d["policy"]
        dec.append(pd.read_parquet(parts / f"{inst}_decisions.parquet"))
        runs.append(pd.read_parquet(parts / f"{inst}_runs.parquet"))
    dec, runs = pd.concat(dec), pd.concat(runs)
    ch = pd.read_parquet(Path(a.census) / "chosen_sources.parquet").set_index(["contract", "trade_date"])
    tz = pd.read_csv(Path(a.census) / "tz_groups.csv")
    tzc = tz["verdict"].value_counts().to_dict()
    csum = json.loads((Path(a.census) / "summary.json").read_text(encoding="utf-8"))
    sel = dec[dec["status"] == "SELECTED"].copy()
    sel["assurance"] = [ch["assurance"].get((c, d)) for c, d in zip(sel["contract"], sel["trade_date"])]
    L = [f"# EdgeLab — Release líquida de ticks CME · `{a.release_id}`", "",
         "> **ESTADO: `CANDIDATE_NOT_RESEARCH_APPROVED`.** Esto NO es un certificado de datos, NO autoriza research ni promoción, y la política de liquidez",
         "> es una **propuesta sin aprobar**. Leé este archivo entero antes de abrir un Parquet. Privado; sin redistribución. **Holdout (trade date ≥ 2026-10-01) no incluido y no se debe leer.**", "",
         "## 1. Qué es", "",
         "Un Parquet de ticks (trades con bid/ask) **por activo** (`data/<ACTIVO>_ticks.parquet`), construido desde los exports originales de NinjaTrader con:", "",
         "- **solo sesiones con liquidez**: en cada sesión CME (17:00→16:00 Chicago) está únicamente el **contrato líder** elegido de forma causal con datos de la sesión anterior (D-1); las sesiones sin contrato elegible se **omiten y quedan registradas** con su motivo;",
         "- **contratos saneados**: huso UTC verificado contra el calendario CME, bloques duplicados con corrimiento horario descartados con evidencia, y una sola fuente adjudicada por (contrato, sesión);",
         "- **precios reales de cada contrato, sin ajustes ni empalmes**: el salto de precio en cada roll se conserva; `contract` y `regime_id` identifican el contrato de cada fila;",
         "- **trazabilidad por fila**: `source_id` (índice en `metadata/source_manifest.parquet`, con SHA-256 del archivo de origen) y `source_row` (fila dentro de ese archivo).", "",
         "## 2. Qué NO es (límites declarados)", "",
         "- No certifica que los ticks sean idénticos a los del feed histórico de CME: el export viene de la base de NinjaTrader (conexión `Simulation`). El huso sí se verificó **contra el calendario**, no contra el feed.",
         "- No hay calendario histórico oficial de CME: el calendario de sesiones es **derivado de los datos** (`metadata/calendar_derived.parquet`). Feriados y cierres tempranos se infieren de que todos los activos operan poco o nada; un hueco de export de todo el universo no se distingue de un feriado.",
         "- Los límites de liquidez (`metadata/liquidity_policy.json`) son una **propuesta** calibrada descriptivamente; `approved_by` es `null` hasta que Nico los apruebe.",
         "- No hay profundidad de libro ni capacidad/fills certificados. Quote/agresor son los del tick (regla de quotes v1); book locked/cruzado queda `aggressor = 0`.",
         "- No se calculó ningún retorno, P&L ni resultado económico. Esta release no es evidencia de edge.", "",
         "## 3. Contenido", "",
         "| activo | descripción | contratos | sesiones incluidas | rango (trade date) | filas | tamaño | sesiones desde parquet derivado |", "|---|---|---:|---:|---|---:|---:|---:|"]
    for inst, info in assets.items():
        s = sel[sel["instrument"] == inst]
        nder = int((s["assurance"] == "PARQUET_DERIVED_ORIGINAL_NOT_AVAILABLE").sum())
        L.append(f"| {inst} | {NAMES.get(inst, '')} | {runs[runs.instrument == inst]['contract'].nunique()} | {info['sessions']} | {info['first_trade_date']} → {info['last_trade_date']} | {info['rows']:,} | {info['bytes'] / 1e9:.2f} GB | {nder} |")
    L += ["", "`sesiones desde parquet derivado`: el original de texto no está en esta máquina; se usó el parquet derivado que ya circulaba. Ver `metadata/MISSING_EXPORTS.md`.", "",
          "## 4. Esquema `liquid_tick_v1`", "", "| columna | tipo | significado |", "|---|---|---|",
          "| `ts_utc_ns` | int64 | instante UTC en ns (huso verificado) |", "| `root` | dict | raíz del activo (`ES`, `NQ`, …) |",
          "| `price_ticks` | int64 | precio de la operación dividido por el tick (`tick_size` en `instrument_specs.json`) |",
          "| `bid_ticks`, `ask_ticks` | int64 | quote al momento del trade en ticks; `-1` si no hay quote válido |",
          "| `volume` | int64 | contratos |", "| `aggressor` | int8 | +1 compra (px ≥ ask), −1 venta (px ≤ bid), 0 sin clasificar (locked/cruzado/sin quote) |",
          "| `contract` | dict | **contrato real de la fila** (p. ej. `ES 12-25`) |", "| `regime_id` | int16 | contador de contrato líder del activo; cambia en cada roll |",
          "| `trade_date` | int32 | fecha de trading CME yyyymmdd (la sesión que cierra ese día 16:00 CT) |",
          "| `outside_regular` | bool | tick en la pausa 16-17 CT o fuera del horario estándar: **se conserva marcado, no se borra**. Los consumidores de research deben filtrarlo (`outside_regular == False`) salvo que declaren lo contrario |",
          "| `source_id` | int16 | índice en `source_manifest.parquet` (SHA-256 del archivo de origen) |", "| `source_row` | int64 | número de fila (0-based) dentro de la fuente |",
          "| `release_row` | int64 | orden consolidado dentro del activo. **No es la secuencia del exchange** |", "",
          "Cada *row group* abarca una sola fecha de trading (estadísticas `trade_date` min = max). Las sesiones largas pueden ocupar varios row groups.", "",
          "## 5. Cómo leerla (sin violar el holdout)", "", "```python",
          "from edgelab.data.liquid_release.release_reader import read_asset", "t = read_asset('<carpeta de la release>', 'ES', 20260105, 20260320)   # pyarrow.Table",
          "t = t.filter(pc.equal(t['outside_regular'], False))                                  # horario regular", "```", "",
          "`read_asset` verifica manifiesto, tamaño y SHA-256; selecciona row groups por estadísticas de `trade_date`; y **se detiene (STOP)** si el rango toca el holdout, si falta una estadística o si un row group cruza el borde pedido. Pedir sesiones completas.", "",
          "## 6. Cómo se eligió el contrato de cada sesión (política causal)", "",
          "Para la sesión S: se toma D-1 (sesión anterior del calendario), se enumeran **todos** los contratos del activo que podían competir, y se elige el de **mayor volumen negociado en horario regular de D-1** entre los que cumplan los límites absolutos. El roll es monótono (nunca se vuelve a un vencimiento anterior) y el cruce es estricto (desempate: el vencimiento más cercano). Nada de S ni posterior interviene.", "",
          "Si el contrato elegido no tiene datos en S, **no se cambia de contrato**: la sesión se excluye. Si un competidor no tiene dato en D-1 y su volumen reciente no es despreciable (> 1 % del líder), la decisión queda **indeterminada** y la sesión se excluye. Si es despreciable, se sigue pero **la suposición queda escrita** en `selection_decisions.parquet` (`assumptions`).", "",
          "Límites propuestos por activo (10 % de la mediana del líder diario en volumen y ticks; spread típico ≤ 3 × la mediana):", "",
          "| activo | volumen mín. D-1 | ticks mín. D-1 | spread típico máx. (ticks) |", "|---|---:|---:|---:|"]
    for inst, p in pol.items():
        L.append(f"| {inst} | {p['min_prev_volume']:,.0f} | {p['min_prev_ticks']:,} | {p['max_prev_spread_p50_ticks']:g} |")
    L += ["", "## 7. Sesiones que NO están (y por qué)", "", "Una fila por sesión del calendario en `metadata/selection_decisions.parquet` y `metadata/excluded_sessions.parquet`.", "",
          "| activo | sesiones del calendario | incluidas | " + " | ".join(STATUS_TXT[k] for k in list(STATUS_TXT)[1:]) + " |", "|---|---:|---:|" + "---:|" * (len(STATUS_TXT) - 1)]
    for inst in assets:
        d = dec[dec["instrument"] == inst]
        vc = d["status"].value_counts()
        L.append(f"| {inst} | {len(d)} | {int(vc.get('SELECTED', 0))} | " + " | ".join(str(int(vc.get(k, 0))) for k in list(STATUS_TXT)[1:]) + " |")
    L += ["", "La primera sesión de cada activo no tiene D-1 verificable y no se incluye; tampoco se rellena ningún hueco.", "",
          "## 8. Defectos de los exports y qué se hizo", "",
          "| hallazgo | evidencia | tratamiento |", "|---|---|---|",
          f"| Huso | de {len(tz)} grupos de fuentes: {tzc.get('UTC_VERIFIED', 0)} calzan con UTC (violación del calendario CME ≈ 1e-6; ART violaría 4–12 %) con cambio de horario correcto, {tzc.get('INSUFFICIENT_EVIDENCE', 0)} sin ticks suficientes, {tzc.get('UTC_WITH_ANOMALIES', 0)} con anomalías puntuales (MBT desde mayo 2026) y {tzc.get('NOT_VERIFIED', 0)} no verificado (NQ 09-26 nativo, explicado abajo) | `ts_utc_ns` = sello del export; `metadata/tz_verdicts.csv` |",
          f"| Bloques copiados con +3 h (NQ 09-26, export nativo, 17-jun → 2-jul) | {csum['dup_blocks']} bloques idénticos fila a fila a otro 3 h antes, fuera del horario real de mercado; {csum['dup_copy_ticks']:,} ticks. Es la causa de la cuarentena `edgelab-ticks-nq-preholdout/6` | la copia se descarta (`metadata/dup_blocks.parquet`); el original queda intacto |",
          "| Huecos del export nativo (p. ej. ES 25-jun: 20 min sin ticks en la hora más activa) | el re-export por día cubre esos minutos | se elige por sesión la fuente con más minutos activos y menor hueco; empates: export por día (con manifiesto y SHA) > nativo > parquet derivado. Conflictos en `metadata/source_conflicts.parquet` |",
          "| Diferencias chicas entre exportaciones del mismo contrato (mediana: 1 tick por hora) | 97 % de las horas son idénticas | misma regla; se registra |",
          "| MBT cambió de calendario (~mayo 2026: ticks en fines de semana y fuera de 17-16 CT) | 1–2 % de los ticks desde junio 2026, igual en todas las fuentes | se conservan marcados `outside_regular`; MBT necesita calendario propio |",
          "| Sesión 'domingo' con volumen 1/2 que provocó el roll prematuro de ES | ticks previos a la apertura del domingo | no forman sesión: sólo cuentan sesiones del calendario con horario regular |", "",
          "## 9. Qué falta", "", "`metadata/MISSING_EXPORTS.md` lista, por activo, contrato y rango de fechas, los exports que faltan (P0 = excluyen sesiones; P1 = suben la garantía de procedencia).", "",
          "## 10. Reglas de uso", "",
          "- **No leer sesiones con `trade_date` ≥ 2026-10-01.** No hay holdout en estos archivos y no hay que reintroducirlo.",
          "- Costos de ejecución por instrumento: **no transportar** la fricción de un activo a otro.",
          "- No mezclar con spot/CFD de Dukascopy ni con series de otro proveedor dentro de un mismo análisis (decisión del 28-sep: NT8 es el proveedor canónico hacia adelante).",
          "- Cualquier research sobre esto exige manifiesto aprobado, presupuesto de hipótesis y STOP antes de P&L (ver `AGENTS.md` y `CLAUDE.md` del repo).", "",
          "## 11. Metadatos (`metadata/`)", "", "| archivo | contenido |", "|---|---|",
          "| `selection_decisions.parquet` | una fila por sesión de calendario: estado, contrato, candidatos y medidas de D-1, suposiciones |",
          "| `session_index.parquet` | lo anterior más filas escritas, fuente y garantía de procedencia |", "| `excluded_sessions.parquet` | sólo las sesiones omitidas, con motivo |",
          "| `contract_runs.parquet` | tramos contiguos por contrato, `regime_id`, fuente |", "| `source_manifest.parquet` | cada archivo de origen: SHA-256, bytes, filas, tipo |",
          "| `liquidity_policy.json` | límites por activo (propuesta) |", "| `instrument_specs.json` | tick y valor por tick |", "| `calendar_derived.parquet` | estado de cada día por activo (OPEN/SHORT/CLOSED/MISSING_EXPORT) |",
          "| `tz_verdicts.csv` | veredicto de huso por grupo de fuentes |", "| `dup_blocks.parquet`, `source_conflicts.parquet` | duplicados y conflictos entre fuentes adjudicados |",
          "| `verification.json` | resultado del verificador independiente |", "| `MISSING_EXPORTS.md`, `missing_exports.csv` | exports pendientes |", "",
          "## 12. Reproducción", "", f"Código en el repo `Nicodelcampo/EdgeLab`, rama `data/liquid-release-20261014`, commit `{a.commit}`. Orden: `tools/scan_nt8_sources.py` → `tools/scan_parquet_sources.py` → `tools/build_census.py` → `tools/build_release.py` → `tools/make_agent_readme.py` → `tools/finalize_release.py` → `tools/verify_release.py`. Informe completo: `docs/infra/LIQUID_RELEASE_20261014.md`.", ""]
    (root / "README_AGENTES.md").write_text("\n".join(L), encoding="utf-8")
    print("README escrito", len(L), "líneas")


if __name__ == "__main__":
    main()
