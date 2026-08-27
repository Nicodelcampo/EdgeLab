# Auditoría de publicación de P2-A en el repositorio

**Fecha:** 2026-08-27  
**Veredicto:** `PASS_REPOSITORY_PUBLICATION_READY`

## Validaciones ejecutadas antes de publicar

- SHA-256 del ZIP fuente verificado: `ae55bb7126e74cbedea082465cc4610e4e61acaa860e58918700766c7640bd2b`.
- Los 15 archivos de `final-audit/SHA256SUMS.txt` verificaron `OK`.
- El payload SHA-256 del resultado agregado cerró.
- Los payload SHA-256 de los 234 checkpoints cerraron individualmente.
- Índices exactos `0..233`, sin faltantes ni duplicados.
- Cada checkpoint contiene 16 celdas primarias y 12 secundarias.
- Máxima sesión CME: `20260630`.
- El resultado agregado de `final-audit/` es byte-idéntico al de `p2a-output/`.
- Firewall final: P2-B no ejecutado, L2 outcomes no abiertos, holdout no tocado, sin ganador, edge ni promoción.

## Alcance comprometido en Git

Se publica el payload final completo, ambas familias tabulares, preflight, manifiesto del Event Store, spec congelado, auditoría, entorno, código auxiliar y logs. Los 234 checkpoints quedan registrados uno por uno por sesión, contrato, conteos, tamaño, SHA-256 de archivo y SHA-256 de payload.

## Payloads externos

No se versionan el ZIP binario, el Parquet del Event Store ni los 234 cuerpos de checkpoint. Son artefactos de ejecución regenerables y la política del repositorio los mantiene fuera de Git. Su identidad queda fijada mediante los manifiestos versionados. Esto evita confundir «subir información» con publicar datos de mercado o runtime payloads.

## Alcance epistemológico

`P2_DIAGNOSTIC_MECHANISM_SUPPORTED` sólo afirma que al menos una celda primaria fue positiva contra `N_RAND` después de Holm y ninguna fue negativa bajo el contrato congelado. No demuestra rentabilidad neta ni justifica convertir una barrera P2-A en una orden standalone.

## Aporte al referente

La ejecución P2-A queda reproducible y localizable por hashes en Git sin abrir P2-B, L2/HMM ni el holdout y sin mezclar el resultado con la deriva de alcance de PR #15.