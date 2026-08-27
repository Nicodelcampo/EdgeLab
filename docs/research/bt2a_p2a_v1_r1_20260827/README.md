# BigTrap2Absorption — P2-A V1-R1 — resultado final

**Fecha:** 2026-08-27  
**Estado:** `COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC`  
**Clasificación:** `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`

Esta carpeta publica en Git la información canónica, los resultados completos agregados, el preflight, la auditoría independiente, las tablas, los logs y las identidades de la ejecución autorizada de P2-A.

## Orden de lectura

1. `final-audit/P2A_RESULT_REPORT.md` — síntesis humana.
2. `final-audit/gate2_p2a_result.json` — payload canónico completo.
3. `final-audit/final_audit.json` — auditoría independiente final.
4. `final-audit/p2a_preflight.json` — preflight fail-closed previo a abrir outcomes.
5. `STATUS.json` — vector de estado y firewall.
6. `CHECKPOINT_INVENTORY.json` — identidad de los 234 checkpoints.
7. `SOURCE_PACKAGE_INVENTORY.json` — inventario SHA-256 de los 251 archivos del paquete fuente.

## Resultado

Se validaron 234/234 sesiones y 28 celdas por sesión: 16 primarias por horizonte de ticks y 12 secundarias por reloj. Tres celdas primarias `K_ABS − N_RAND` quedaron positivas tras Holm sobre la familia congelada de 16; no hubo celdas primarias negativas tras Holm.

Esto sostiene el mecanismo como diagnóstico. **No es P&L realizado, no selecciona un ganador, no convierte automáticamente barreras en SL/TP y no autoriza P2-B, L2/HMM, holdout, edge ni promoción.**

## Procedencia

- Freeze remoto: `d5edeee36114849585567b768e40c061a4d0ef96`.
- Fix operativo del harness: `bdd326dcf59c0ad4db8e84a9e5de7dd2dd65e568`.
- Spec payload: `176ca3e0c37f44823bfe5f8cf64849b55dcf12b5114d930d5ec8776c1566468c`.
- Event Store payload: `feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd`.
- Resultado payload: `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`.
- Paquete fuente: `EdgeLab_BT2A_P2A_Result_V1_R1_2026-08-27.zip`.
- SHA-256 del paquete: `ae55bb7126e74cbedea082465cc4610e4e61acaa860e58918700766c7640bd2b`.

## Checkpoints y artefactos grandes

Los 234 cuerpos de checkpoints y el Event Store Parquet son artefactos regenerables/local-only según la política del repositorio y no se duplican como payloads en Git. Sí quedan comprometidos todos sus índices, hashes y procedencia. `CHECKPOINT_INVENTORY.json` identifica cada checkpoint y `SOURCE_PACKAGE_INVENTORY.json` identifica cada archivo del paquete, por lo que una copia externa puede verificarse sin ambigüedad.

## Aporte al referente

P2-A deja de existir sólo en Notion o en un paquete local: el resultado, la auditoría, el preflight, las tablas, logs, código auxiliar e identidades quedan visibles y auditables en el repositorio, conservando el firewall de P2-B/L2/holdout.