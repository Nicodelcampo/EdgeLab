# Reporte de Pre-Auditoría y Cola de Ejecución para los Agentes del Debian (2026-10-29)

- **Estado global de verificación pre-auditoría:** `OK (0 errores)`
- **Módulos experimentales verificados (`preflight` + causalidad):** `3` (`corredor_vol_gaps`, `otr_930_sweep`, `oro_almuerzo_ruptura`)
- **Campañas auditadas (Olas 1–9):** `16`
- **Campañas en `CONTEO` con `ACTA_HOLDOUT.json` y reserva LORD++:** `6` (`CVGAP-NQ, CVGAP-CFD-NQ, U1-RACIMOS-GRILLA-NQ, U1-RACIMOS-GRILLA-ES, U1-ZONAS-BT2-ES, U1-ZONAS-BT2-NQ`)
- **Campañas en `PISTAS_VIVAS` (`n_pistas_vivas == 20`) para canasta de régimen y analizador:** `9` (`CVGAP-ES, CVGAP-CFD-ES, OTR930-NQ, OTR930-ES, OTR930-CFD-NQ, OTR930-CFD-ES, ORO-ALM-GC, ORO-ALM-CFD, U1-6E-GRILLA`)

## 1. Tabla Resumen de las 16 Campañas Auditadas

| Campaña (`cid`) | Familia | Sensor -> Ejecución | Etapa | Fase / Veredicto | `holdout.desde` | Celdas Analizador | Estado Auditoría | Acción Primaria Debian |
|---|---|---|---|---|---:|---:|---|---|
| `CVGAP-NQ` | `CORREDOR_VOL_GAPS_NQ` | `NQ -> NQ` | `CONTEO` | `PENDIENTE` | `20261001` | `3` | `OK` | `AUDITAR_ACTA_Y_EVALUAR_HOLDOUT` |
| `CVGAP-CFD-NQ` | `CORREDOR_VOL_GAPS_CFD_NQ` | `DK:USATECHIDXUSD -> NQ` | `CONTEO` | `PENDIENTE` | `20261001` | `3` | `OK` | `AUDITAR_ACTA_Y_EVALUAR_HOLDOUT` |
| `CVGAP-ES` | `CORREDOR_VOL_GAPS_ES` | `ES -> ES` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `CVGAP-CFD-ES` | `CORREDOR_VOL_GAPS_CFD_ES` | `DK:USA500IDXUSD -> ES` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `OTR930-NQ` | `OTR_930_SWEEP_NQ` | `NQ -> NQ` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `OTR930-ES` | `OTR_930_SWEEP_ES` | `ES -> ES` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `OTR930-CFD-NQ` | `OTR_930_SWEEP_CFD_NQ` | `DK:USATECHIDXUSD -> NQ` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `OTR930-CFD-ES` | `OTR_930_SWEEP_CFD_ES` | `DK:USA500IDXUSD -> ES` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `ORO-ALM-GC` | `ORO_ALMUERZO_RUPTURA_GC` | `GC -> GC` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `ORO-ALM-CFD` | `ORO_ALMUERZO_RUPTURA_CFD` | `DK:XAUUSD -> GC` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |
| `U1-RACIMOS-GRILLA-NQ` | `U1_RACIMOS_GRILLA_NQ` | `NQ -> NQ` | `CONTEO` | `PENDIENTE` | `20261001` | `3` | `OK` | `AUDITAR_ACTA_Y_EVALUAR_HOLDOUT` |
| `U1-RACIMOS-GRILLA-ES` | `U1_RACIMOS_GRILLA_ES` | `ES -> ES` | `CONTEO` | `PENDIENTE` | `20261001` | `2` | `OK` | `AUDITAR_ACTA_Y_EVALUAR_HOLDOUT` |
| `U1-ZONAS-BT2-ES` | `U1_ZONAS_BT2_ES` | `ES -> ES` | `CONTEO` | `PENDIENTE` | `20261001` | `3` | `OK` | `AUDITAR_ACTA_Y_EVALUAR_HOLDOUT` |
| `U1-ZONAS-BT2-NQ` | `U1_ZONAS_BT2_NQ` | `NQ -> NQ` | `CONTEO` | `PENDIENTE` | `20261001` | `3` | `OK` | `AUDITAR_ACTA_Y_EVALUAR_HOLDOUT` |
| `U1-ZONAS-GRILLA-YM` | `U1_ZONAS_GRILLA_YM` | `YM -> YM` | `FIN` | `SIN_REGLA_OPERABLE` | `20261001` | `1` | `OK` | `AUDITAR_ANALIZADOR_DESARROLLO` |
| `U1-6E-GRILLA` | `U1_6E_GRILLA` | `DK:EURUSD -> DK:EURUSD` | `FIN` | `PISTAS_VIVAS` | `20261001` | `20` | `OK` | `AUDITAR_PISTAS_VIVAS_Y_CANASTA_REGIMEN` |

## 2. Protocolo de Auditoría Independiente para los Agentes del Debian (`SV1`)

### Fase A — Verificación Determinista Local (Conductor + Auditor)
1. Ejecutar `python3 tools/auditar_corridas_nube_20261029.py --dinamico` y confirmar `ok_global: true`.
2. Ejecutar `pytest tests/research/test_auditoria_corridas_nube_20261029.py tests/research/test_corredor_vol_gaps.py tests/research/test_otr_930_sweep.py tests/research/test_oro_almuerzo_ruptura.py tests/autopilot/test_auditor_alineacion.py`.

### Fase B — Evaluación de las 6 Nuevas `ACTA_HOLDOUT.json` en `edgelab-holdout-sellado` (`CONTEO` y `HOLDOUT`)
Para cada una de las 6 campañas que superaron las 4 etapas del embudo (`CVGAP-NQ`, `CVGAP-CFD-NQ`, `U1-RACIMOS-GRILLA-NQ`, `U1-ZONAS-BT2-ES`, `U1-ZONAS-BT2-NQ`, `U1-RACIMOS-GRILLA-ES`):
1. Correr `tools/embudo_correr.py` sobre `edgelab-holdout-sellado` desde `holdout.desde = 20261001`.
2. Evaluar si el rendimiento en la ventana disponible de octubre (`20261001..20261026`) se encuentra dentro de la banda esperada según la distribución de desarrollo/OOS (Directiva #6 de canasta de régimen).

### Fase C — Auditoría de Canasta de Régimen (`tools/holdout_canasta.py`) y Analizador (`tools/analizar_embudo.py`) sobre las 9 Campañas en `PISTAS_VIVAS`
Para `CVGAP-ES`, `CVGAP-CFD-ES`, `OTR930-NQ`, `OTR930-ES`, `OTR930-CFD-NQ`, `OTR930-CFD-ES`, `ORO-ALM-GC`, `ORO-ALM-CFD` y `U1-6E-GRILLA` (y `U1-ZONAS-GRILLA-YM` en el analizador):
1. Evaluar la elegibilidad de la canasta de 20 pistas congeladas con `tools/holdout_canasta.py`.
2. Lanzar `python3 tools/analizar_embudo.py lanzar` y `python3 tools/analizar_embudo.py traer` para generar los perfiles completos de desarrollo (`20250805..20260930`).
