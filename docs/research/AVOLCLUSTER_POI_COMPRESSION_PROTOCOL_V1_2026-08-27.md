# aVolClusterPOI — protocolo V1 original: SUPERSEDED / NO EJECUTAR

**Estado:** `SUPERSEDED_BY_V1_R1_DRAFT_FAIL_CLOSED`  
**Fecha de revisión:** 2026-08-27  
**Reemplazo:** `docs/research/AVOL_BT2_TWO_STAGE_PROTOCOL_V1_R1_DRAFT_2026-08-27.md`

Esta versión quedó invalidada antes de abrir outcomes. Tenía cuatro defectos bloqueantes:

1. fijaba **NQ**, aunque la evidencia, la resolución 60t y el trabajo de BigTrap usado como referencia pertenecen a **GC**;
2. congelaba M1 e ignoraba que 60t fue el candidato target-free seleccionado (con meseta estricta fallida y paridad parcial 123/180);
3. declaraba `FUTURE_PRICE_PATH_ACCESSED=true` sin autorización literal ni ejecución registrada;
4. llamaba “compresión” a una medición que sólo prueba expansión posterior y contaba Delta/BT2/BT2A como si fueran votos independientes.

La spec quedó en `DRAFT_PREAUTHORIZATION_FAIL_CLOSED`; el runner existente rechaza una spec que no tenga estado `FROZEN_METHOD`, por lo que no puede abrir trayectorias futuras bajo esta revisión.

No se ejecutó H1, H2, P&L, holdout, selección de ganador, edge ni promoción.
