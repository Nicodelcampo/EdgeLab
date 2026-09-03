# Paridad aVolClusterPOI — índice y estado real

**Última actualización: 2026-09-03.** Este archivo existe porque hubo **dos líneas
de trabajo en paralelo sobre el mismo problema**, en ramas distintas, y cada una
dejó su propio documento de estado. Leer sólo uno da una imagen coherente y
equivocada — es la falla que describe `docs/AVISO_DIVERGENCIA_DE_RAMAS_2026-08-06.md`.

## Las dos líneas

| | línea A — diagnóstico | línea B — certificación |
|---|---|---|
| rama | `foundation/f0b-compatibility-probe` | `research/avolcluster-nq-parity-oracle-20260901` |
| último commit | ver `git log` | `6f4e32f` |
| instrumento | NQ SEP26 (F9) / NQ 06-26 (F2–F8) | NQ 06-26 |
| documento | `PARIDAD_AVOLCLUSTERPOI_ESTADO_2026-09-02.md` | `PARIDAD_AVOLCLUSTERPOI_NQ0626_20260902.md` |
| veredicto propio | paridad NO validada, 15,27 % de bloques | paridad certificada: 100 % / 100 % / 99,01 % |

**Las dos ramas están divergidas**: `foundation` tiene 67 commits que la otra no
tiene; la otra tiene 14 que `foundation` no tiene. **Falta decidir el merge.**

## Qué aporta cada una, sin duplicar

La línea A **diagnosticó** la causa: el perfil se acumula en la subserie de 1 tick
y se vuelca al cerrar la barra primaria, y el volcado descarta lo que cae fuera
de `[Low[0], High[0]]`. Ambos defectos leídos en el `.cs`, y luego confirmados con
la instrumentación P-70 que esta línea agregó al indicador (`BarProfileLogPath`).

La línea B **corrigió el puente** y midió el resultado: alineación al inicio de
sesión CME, partición por conteo estricto de 120 transacciones, y aislamiento de
`tick_bar_idx` en los footprints.

**Se confirman entre sí en lo estructural.** La línea A midió sobre NQ SEP26 que
sólo el 31,58 % de las barras tiene `profile_volume == primary_bar_volume`, con
desvío simétrico y masa conservada. La línea B midió lo mismo sobre NQ 06-26:
27,85 %, simétrico, total cerrando a 1 contrato de 30 millones. Réplica
independiente en dos contratos distintos.

## Tres reservas abiertas sobre la certificación

Ninguna la refuta; las tres acotan qué quedó demostrado.

1. **Las capas no miden la misma población.** La capa 1 (100 %) es paridad
   *sobre input igual*: alimenta al kernel Python con los bloques del propio NT8,
   así que valida clustering, percentil y geometría, **no** la construcción del
   footprint. Su propio documento lo dice (`KERNEL_PARITY_ON_EQUAL_INPUT`). La
   capa 3 (99,01 %) se mide sobre **203 zonas**, que salen de 482 creaciones en
   23.339 bloques — cerca del 2 % de la población. La línea A medía celdas
   exactas por bloque sobre los 22.507. No se contradicen y no son comparables.

2. **La partición se validó con 10 barras de 233.601.** Es el cambio que sostiene
   toda la certificación y su evidencia declarada es *"10 de 10 barras de muestra"*.
   **En auditoría**: `notebooks/kaggle/avolcluster_partition_audit/`, que corre la
   misma comparación sobre las 233.601 filas.

3. **`build_resolved_tick_bars` no hace lo que su nombre dice.** Lee
   `profile_volume` y **nunca lo usa**: la partición es un paso fijo de 120 ticks
   con resync al inicio de sesión. Además toma `e_ns` del propio CSV de NT8, así
   que el `TIMESTAMP_DIFF = 0 ms` de la capa 3 es en parte definicional — los
   cierres de barra no se calculan, se copian del oráculo. Lo falsable de esa
   partición es la geometría: `low_tick`, `high_tick`, `primary_bar_volume`.

## Dos huecos de procedencia

- El `.cs` con `BarProfileLogPath` **sólo existe en `foundation`**. Los CSV que
  certifican la paridad los produjo código que la rama de la certificación no
  contiene.
- `BARPROFILE_20260902.csv` (18.458.398 bytes) y `DIAG_BLOCKS_20260902.csv`
  (23.790.732) **no están en git**. Están en el dataset de Kaggle
  `nicolasbuttaro/edgelab-avolcluster-nq-oracle`, con tamaños idénticos a los del
  manifiesto — la procedencia verifica, pero la evidencia que sostiene el gate
  vive fuera del árbol.

## Qué falta

1. Resultado de la auditoría de partición (en curso).
2. Decisión de merge entre las dos ramas.
3. Si la auditoría pasa: declarar el gate con su estimand explícito — *sobre qué
   población* y *a qué nivel* (zona, bloque o celda) vale cada porcentaje.
