# Handoff para el agente del Debian (SV1), 2026-10-30

Estado: VIGENTE
Fecha: 2026-10-30

Estado leído por SSH: SV1 en 0f3a5466, HEAD sin rama, 3 archivos modificados y 23 sin seguimiento (26 en total), PAUSE activo desde 2026-10-30 01:09. Release objetivo: 9000dcd7 (53 commits por delante al escribir esto).

## Qué cambió y debe saber
- PR #155: el 404 de Kaggle recién lanzado ya no bloquea CONTEO.
- PR #157: HOLDOUT_VENTANAS restaurado.
- PR #158: canasta_regimen no confirma estrategias perdedoras con poco N; confirmar_canasta.
- PR #163: lectura sellada con tick por activo, entorno del kernel en LocalRunner, ruta de actas, canasta por sesión.
- PR #164: simular_cierre y columnas t_fill y t_exit en operaciones.
- PR #165: índice de docs.
- PR #160 y #161: canasta de 12, ANULADA.
- PR #166: pre-registro vigente en docs/research/canasta_7_20261030/PREREGISTRO.md.
- Auditoría de la sesión: PR #162, abierto, docs/research/auditoria_sesion_20261030/.

## Reglas al retomar
- No abrir holdout ni correr CONTEO de la canasta hasta tener calentamiento de zonas, ruta sellada y test de LocalRunner.
- No quitar PAUSE sin orden de Gonza o Nico.
- Los manifiestos holdout-conteo locales son conteo, sin P&L: conservarlos y reportarlos.
- Las reglas excluidas (BT2-ES, U1-ES, RACIMOS-ES, BT2-NQ, ZONAS-ES) no vuelven a la canasta.
- Librerías de la Ola 10 sin conectar a ciclo.py; no asumir que corren.
- Parche V2 de filtros: no aplicar tools/auditar_equity_filtros_y_nt8.py ni usar gestor_canastas_regimen para promover.
- Datos del release líquido: CANDIDATE_NOT_RESEARCH_APPROVED.

## Pendiente de investigación (no lo hace el Debian)
HFT2 NQ y ES, U1-COMBO, PRERANGE-HFT (PR #159), control de retornos barajados.
