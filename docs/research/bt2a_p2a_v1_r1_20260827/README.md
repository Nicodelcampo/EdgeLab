# BigTrap2Absorption — P2-A V1-R1 — resultado final

**Fecha:** 2026-08-27  
**Estado:** `COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC`  
**Clasificación:** `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`  
**Publicación en Git:** `COMPLETE`

Esta carpeta publica la información auditable de la ejecución autorizada de P2-A sin versionar datos CME, el Event Store Parquet, el ZIP binario ni los 234 cuerpos completos de checkpoint.

## Orden de lectura

1. `final-audit/P2A_RESULT_REPORT.md` — síntesis humana.
2. `result/reconstruct_gate2_p2a_result.py` — reconstrucción del resultado agregado completo desde los nueve fragmentos JSON versionados.
3. `final-audit/final_audit.json` — snapshot semántico de la auditoría independiente.
4. `final-audit/p2a_preflight.json` — snapshot semántico del preflight fail-closed.
5. `STATUS.json` — estado y firewall.
6. `checkpoints/complete/manifest.json` — inventario completo y verificable de los 234 checkpoints.
7. `source-package/complete/manifest.json` — inventario completo y verificable de los 251 archivos del paquete fuente.
8. `provenance/` — entorno, worker, logs y hashes del paquete fuente.

## Resultado

Se validaron 234/234 sesiones y 28 celdas por sesión: 16 primarias por horizonte de ticks y 12 secundarias descriptivas por reloj. Tres celdas primarias `K_ABS − N_RAND` quedaron positivas tras Holm sobre la familia congelada de 16; no hubo celdas primarias negativas tras Holm.

Esto sostiene el mecanismo como diagnóstico. **No es P&L realizado, no selecciona un ganador, no convierte barreras en SL/TP y no autoriza P2-B, L2/HMM, holdout, edge ni promoción.**

## Reconstrucción verificable

### Resultado agregado

```sh
cd result
python reconstruct_gate2_p2a_result.py > gate2_p2a_result.json
```

Payload esperado:

```text
296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28
```

### Inventario de checkpoints

```sh
cd checkpoints/complete
sh reconstruct.sh
```

El script verifica:

```text
checkpoint_inventory_all.csv.gz sha256 = a01026fd94c8ea48f08620764c71a27cfe8ddf89fdb19fcc4f88f537f88d63de
checkpoint_inventory_all.csv    sha256 = 3d916f53f113a788149923cb15fab88e9aeb75772aa85b1d44a7966d590f85da
records = 234
indices = 0..233
max CME session = 20260630
```

Los CSV `checkpoint_inventory_000_019.csv` a `checkpoint_inventory_040_059.csv` son una vista humana inicial; el inventario completo de 234 registros es el reconstruible de `checkpoints/complete/`.

### Inventario del paquete fuente

```sh
cd source-package/complete
sh reconstruct.sh
```

El script verifica:

```text
file_inventory_all.csv.gz sha256 = be6d317ac7ba23f61416d509796ddfb48714a22b5c5bf3061b00daf6b19f4720
file_inventory_all.csv    sha256 = 611f2f567bf5da42d74e9bd99d755e56f89a00709e552061134e0506010dbf5e
records = 251
```

## Identidad de las representaciones Git

- Los transportes de ambos inventarios y los archivos de `provenance/` fueron contrastados por tamaño y Git blob contra los bytes locales.
- `final-audit/final_audit.json`, `p2a_preflight.json`, `event_store_run_manifest.json` y `bt2a_gate2_first_passage_v1.json` son **snapshots JSON semánticos Git-native**: conservan el mismo objeto JSON, pero no se afirma identidad byte a byte con el archivo del ZIP.
- `primary_family.csv` y `secondary_clock_family.csv` son snapshots tabulares Git-native con LF. Los CSV del paquete fuente usan CRLF; filas y valores son iguales, pero sus hashes de archivo son distintos por finales de línea.
- Los hashes exactos de los archivos del paquete fuente están en `provenance/source-package/SHA256SUMS.txt` y no deben atribuirse a un snapshot Git-native reformateado.

## Procedencia

- Freeze remoto: `d5edeee36114849585567b768e40c061a4d0ef96`.
- Fix operativo del harness: `bdd326dcf59c0ad4db8e84a9e5de7dd2dd65e568`.
- Spec payload: `176ca3e0c37f44823bfe5f8cf64849b55dcf12b5114d930d5ec8776c1566468c`.
- Event Store payload: `feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd`.
- Resultado payload: `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`.
- Paquete fuente: `EdgeLab_BT2A_P2A_Result_V1_R1_2026-08-27.zip`.
- SHA-256 del paquete: `ae55bb7126e74cbedea082465cc4610e4e61acaa860e58918700766c7640bd2b`.

## Artefactos deliberadamente externos

Los 234 cuerpos de checkpoints, el Event Store Parquet, el ZIP y los datos CME son regenerables o de custodia externa conforme a la política del repositorio. Git contiene resultados agregados, contratos/snapshots, tablas, procedencia e inventarios suficientes para resolver y verificar cualquier copia externa por hash.
