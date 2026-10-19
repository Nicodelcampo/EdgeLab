# Resultado contextos L2 MES y MNQ (4 climas) — ambos STOP por inestabilidad de semillas (2026-09-30)

Protocolo `PROTOCOLO_CONTEXTOS_L2_ES_MES_MNQ_20260929.md` + enmienda 1 (carga de archivos solapados). Target-free.
Reportes: `artifacts/l2_contexts/{MES,MNQ}/gate_report.json` (locales).

| | MES (17+33 ses.) | MNQ (17+35 ses.) | Umbral |
|---|---|---|---|
| Cobertura evaluación | 1,00 | 1,00 | ≥ 0,99 |
| Acuerdo semillas global | **0,557** | **0,714** | ≥ 0,80 |
| calm / normal / volatile | 0,60 / 0,24 / 0,11 | 0,98 / 0,45 / 0,31 | ≥ 0,80 |
| Sólo-hora (acierto vs mayoría) | 0,811 vs 0,810 | 0,349 vs 0,563 | < 0,90 |
| Máx. concentración 2 h | 0,54 (normal) | 0,20 (volatile) | ≤ 0,80 |
| Minutos eval.: calm / normal / volatile / toxic | 36.366 / 63 / 469 / 7.991 | 26.992 / 9.550 / 2.300 / 9.122 | |

**Veredicto: MES y MNQ sin climas** (STOP). MES repite el patrón de ES (casi todo calm; normal/volatile vacíos). MNQ
reparte mejor los estados y calm es muy estable (0,98), pero normal/volatile no. No se cambian parámetros ni split.
Extracción MNQ: 52 sesiones sin anomalías de libro (< 1.300 minutos elegibles en ninguna). La capa *toxic* (binaria) no
se evaluó en MES/MNQ: exigiría el pre-registro de estabilidad temporal que se hizo en ES y NQ.
