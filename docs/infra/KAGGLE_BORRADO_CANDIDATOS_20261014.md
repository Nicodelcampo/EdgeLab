# Candidatos a borrar en Kaggle (2026-10-14) — NO se borró nada

Estado: PROPUESTA (nada se borró; decide Nico)  
Fecha: 2026-10-14

Yo no puedo borrar datasets de forma permanente; esta lista y los comandos son para que los ejecutes vos. Un borrado en Kaggle **no se puede deshacer**.
Antes de borrar: la release `edgelab-liquid-ticks-20261014` (v4) debe estar publicada y verificada, y conviene guardar la copia local comprimida (ver limpieza de la PC).

**Advertencia de reproducibilidad:** hay 248 kernels de campañas anteriores. Algunos leen estos datasets como entrada; si los borrás, esos kernels no se pueden volver a ejecutar tal cual (los resultados y actas viven en el repo, y no se pierden). No revisé cuáles kernels dependen de cuáles datasets.

Comando: `kaggle datasets delete nicolasbuttaro/<slug>` (pide confirmación).

## Nivel 1 — defecto comprobado o derivado bloqueado (recomendado borrar)
Total: 2.8 GB

| dataset | GB | etiqueta | nota |
|---|---:|---|---|
| `edgelab-es-nq-aggregates-20261009` | 1.72 | DERIVADO-BLOQUEADO | Barras 1/30/60 s construidas con el resolver v15 (roll ES prematuro, máscara retrospectiva). Regenerar desde l |
| `edgelab-ticks-nq-preholdout` | 1.10 | CUARENTENA | NQ_09-26_ticks.parquet (v6): 363.601 trades dentro de la pausa 16-17 CT. Causa raíz: bloques del export nativo |

## Nivel 2 — reemplazado por la release (borrar si aceptás perder reproducibilidad de campañas viejas)
Total: 18.2 GB

| dataset | GB | etiqueta | nota |
|---|---:|---|---|
| `edgelab-ticks-nt8-canonical` | 5.26 | REEMPLAZADO | MES/MNQ/MYM/RTY/YM (+ES/NQ/YM en partes). Incompleto en MNQ 12-26 (falta 17-sep y corta el 28-sep). Sin selecc |
| `edgelab-ticks-nt8-reexport-20261005` | 3.98 | REEMPLAZADO | Re-export 23 contratos jul-sep 2026. Sin selección causal de contrato ni calendario verificado. |
| `edgelab-ticks-mnq-preholdout` | 2.58 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-es-preholdout` | 1.33 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-nt8-historical-missing-20261001` | 1.23 | REEMPLAZADO | ES/NQ/6B/6E/6J/ZB parquet-only. Contiene el roll ES prematuro (domingo 2025-10-05) y huecos del export nativo. |
| `edgelab-ticks-mes-preholdout` | 1.19 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-es-nq-2026q3-ext` | 0.65 | REEMPLAZADO | ES/NQ jul-sep 2026. NQ_09-26 hereda bloques duplicados +3h del export nativo (17-jun a 2-jul). |
| `edgelab-mgc-nt8-raw-parquet-20261002` | 0.61 | REEMPLAZADO | MGC en bruto (precios decimales, sin agresor). MGC saneado y líquido está en la release. |
| `edgelab-ticks-gc-preholdout` | 0.38 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-nq-nt8-2026q3-l2ctx` | 0.32 | CONTEXTO-L2 | Contextos L2 de NQ. Los NQ_*_ticks_ext que contiene los reemplaza la release. |
| `edgelab-ticks-ym-preholdout` | 0.22 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-6e-preholdout` | 0.14 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-zb-preholdout` | 0.11 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-6j-preholdout` | 0.10 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-6b-preholdout` | 0.06 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-ticks-mbt-preholdout` | 0.05 | REEMPLAZADO | Rebanadas parciales por contrato; corte 2026-06-30. |
| `edgelab-l2-gc-bookmap-audit-20260921` | 0.04 | CONTEXTO-L2 | Auditoría L2 de GC 08-26 (2 sesiones). |

## Nivel 3 — spot/CFD de Dukascopy, no es CME (datos válidos pero de otro mercado; decidí vos si los querés)
Total: 11.9 GB

| dataset | GB | etiqueta | nota |
|---|---:|---|---|
| `edgelab-dukascopy-nq-usatech` | 2.99 | SPOT | USATECH CFD. No es NQ de CME. |
| `edgelab-dukascopy-xauusd-ticks-m1` | 2.61 | SPOT | XAUUSD spot. No es GC de CME. |
| `edgelab-dukascopy-es-usa500` | 1.68 | SPOT | USA500 CFD. No es ES de CME. |
| `edgelab-dukascopy-6j-usdjpy` | 1.38 | SPOT | USDJPY spot. No es 6J de CME. |
| `edgelab-dukascopy-ym-usa30` | 1.37 | SPOT | USA30 CFD. No es YM de CME. |
| `edgelab-dukascopy-6b-gbpusd` | 0.94 | SPOT | GBPUSD spot. No es 6B de CME. |
| `edgelab-dukascopy-6e-eurusd` | 0.89 | SPOT | EURUSD spot. No es 6E de CME. |

## Qué NO está en ninguna lista
`edgelab-liquid-ticks-20261014` (release vigente), `edgelab-data-catalog` (entrada), los 4 de código y los 10 de archivo (casi no pesan: 0,3 GB).
