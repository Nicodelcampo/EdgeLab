# Auditoría de publicación de P2-A en el repositorio

**Fecha:** 2026-08-27  
**Veredicto:** `PASS_REPOSITORY_PUBLICATION_COMPLETE`

## Auditoría científica previa

- ZIP fuente: `ae55bb7126e74cbedea082465cc4610e4e61acaa860e58918700766c7640bd2b`.
- Los 15 archivos listados por el paquete en `SHA256SUMS.txt` verificaron `OK` antes de publicar.
- El payload SHA-256 del resultado agregado cerró.
- Los 234 payload SHA-256 de checkpoints cerraron individualmente.
- Índices exactos `0..233`, sin faltantes ni duplicados.
- Cada checkpoint contiene 16 celdas primarias y 12 secundarias.
- Máxima sesión CME: `20260630`.
- El resultado agregado de `final-audit/` fue byte-idéntico al de `p2a-output/` dentro del paquete validado.
- Firewall final: P2-B no ejecutado, outcomes L2 no abiertos, holdout no tocado, sin ganador, edge ni promoción.

## Auditoría de transporte Git

- Se reparó el tramo `part06` del inventario de checkpoints; la versión repetitiva accidental quedó reemplazada por siete segmentos exactos de 1.000 bytes.
- Los 17 segmentos actuales del inventario de checkpoints coinciden por tamaño y Git blob con la fuente local.
- La concatenación lexicográfica preserva exactamente el stream base64 original; el manifest fija hashes por segmento, gzip y CSV.
- Los 16 segmentos del inventario del paquete fuente coinciden por tamaño y Git blob con la fuente local.
- La reconstrucción esperada produce 234 registros de checkpoints y 251 registros de paquete.
- `environment.txt`, `p2a_batch_worker.py`, `run_p2a_parallel.log`, `finalize.log`, `finalize.err`, `worker_even.log`, `worker_odd.log` y el `SHA256SUMS.txt` del paquete coinciden por tamaño y Git blob con la fuente local.
- `finalize.err` es deliberadamente un archivo vacío de cero bytes, con SHA-256 estándar `e3b0c442...`.

## Resultado agregado en Git

El resultado completo está dividido por barrera en `result/`. `reconstruct_gate2_p2a_result.py` recompone las 16 celdas primarias y las 12 secundarias y fija el payload:

```text
296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28
```

No se usa una referencia a un `final-audit/gate2_p2a_result.json` inexistente.

## Política de identidad explícita

No se atribuye falsamente el SHA-256 del archivo fuente a una copia reformateada:

- Los cuatro JSON auxiliares de `final-audit/` son snapshots semánticos Git-native; el objeto JSON se conserva, pero el whitespace no es contractual.
- Las dos tablas CSV de Git están normalizadas a LF; las fuentes del ZIP usan CRLF. Las filas y los valores son iguales, pero sólo `provenance/source-package/SHA256SUMS.txt` registra los hashes exactos del paquete.
- El informe Markdown de Git es una representación legible; la identidad exacta del archivo fuente queda igualmente en el manifest del paquete.

## Payloads deliberadamente externos

No se versionan el ZIP binario, el Parquet del Event Store, datos CME ni los 234 cuerpos de checkpoint. Su identidad queda fijada por manifiestos e inventarios completos. Esto cumple `visibility_means_manifest_not_payload = true` y evita introducir datos de mercado o payloads de runtime en Git.

## Alcance epistemológico

`P2_DIAGNOSTIC_MECHANISM_SUPPORTED` sólo afirma que al menos una celda primaria fue positiva contra `N_RAND` después de Holm y ninguna fue negativa bajo el contrato congelado. No demuestra rentabilidad neta ni justifica convertir una barrera P2-A en una orden standalone.

## Firewall

```text
P2A_OUTCOMES_OPENED       = true
P2B_RUN                   = false
L2_OUTCOMES_OPENED        = false
HOLDOUT_TOUCHED           = false
WINNER_SELECTED           = false
EDGE_DECLARED             = false
CONFIRMATORY_ELIGIBLE     = false
PROMOTION_ELIGIBLE        = false
```
