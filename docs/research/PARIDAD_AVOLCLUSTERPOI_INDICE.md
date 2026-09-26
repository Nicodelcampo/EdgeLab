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

2. **La partición se validó con 10 barras de 233.601 — y AUDITADA da 89,81 %.**
   Acta: `avolcluster_partition_audit_20260903/`. Sobre las 233.601 filas, `low`
   92,64 %, `high` 92,62 %, volumen 92,04 %, los tres a la vez **89,81 %**. El
   error **crece monótono dentro de la sesión** (decil 0: 97,27 % → decil 9:
   73,07 %): el resync alinea en cada frontera y la partición se separa después.
   La muestra de 10 daba 100 % porque el arranque de sesión acierta al 97 %.
   No refuta las 201/203 zonas —es otra población— pero sí la afirmación tal
   como está escrita.

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

1. **Declarar el estimand del gate.** Hoy conviven sin distinguirse tres números
   que miden cosas distintas: 100 % de decisión de bloque *sobre input igual*
   (no valida el footprint), 99,01 % sobre **203 zonas**, y **89,81 % sobre
   233.601 barras primarias** — el que faltaba y ahora existe.
2. **Medir si las zonas caen en tramos donde la partición acierta.** Es la
   pregunta que decide si el 99,01 % sobrevive al 89,81 %: hay que medirla, no
   suponerla en ninguna de las dos direcciones.
3. **Decisión de merge entre las dos ramas.**
