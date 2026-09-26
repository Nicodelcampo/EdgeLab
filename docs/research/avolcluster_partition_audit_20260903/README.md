# Auditoría de partición — la muestra de 10 barras no se sostiene a escala

Fecha: 2026-09-03 · Kaggle, 19 s · `AUDIT_NO_CODE_CHANGED`
Rama auditada: `research/avolcluster-nq-parity-oracle-20260901`, commit
`6f4e32f9a17e11a46849fe607729cf834b11e2a9`
BARPROFILE sha256 `98556ded…f9cae` (233.601 filas, el mismo del manifiesto)
Kernel: `notebooks/kaggle/avolcluster_partition_audit/audit_entry.py`

## Qué se auditó

La certificación de paridad se apoya en una partición nueva —conteo estricto de
120 transacciones por barra con resync al inicio de sesión, en
`build_resolved_tick_bars`— cuya evidencia declarada es:

> *"10 de 10 barras de muestra auditadas contra `BARPROFILE` coincidieron de forma
> 100,00 % idéntica en Low y High"*

Este kernel corre la misma comparación sobre **las 233.601 barras**, no sobre 10.
Reconstruyó exactamente 233.601 barras, así que el conteo global cierra.

## Resultado — 89,81 %, no 100 %

| campo | coincidencia exacta |
|---|---:|
| `low_tick` | 92,64 % |
| `high_tick` | 92,62 % |
| `primary_bar_volume` | 92,04 % |
| **los tres a la vez** | **89,81 %** (209.791 de 233.601) |

**23.810 barras difieren.** Y no son desvíos de un tick: la distribución de
`Δlow` tiene 216.399 ceros pero **11.239 barras con `|Δ| > 6`**, con colas casi
simétricas. El error de volumen llega a 991 contratos en una sola barra.

## El mecanismo: deriva intra-sesión que el resync corrige

Aciertos por decil de posición del bar dentro de su sesión:

| decil | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| aciertos | 97,27 % | 95,18 % | 94,74 % | 94,22 % | 92,15 % | 90,17 % | 90,05 % | 89,13 % | 82,10 % | **73,07 %** |

Monótono. Primeras 200 barras de sesión: **98,73 %**. Resto: **89,38 %**.

La partición arranca alineada en cada frontera de sesión —el resync funciona— y
**se va separando a lo largo de la sesión** hasta perder uno de cada cuatro bars
al final. Es deriva acumulativa, exactamente lo que un paso fijo de 120 ticks no
puede corregir si NT8 no avanza siempre de a 120 transacciones del parquet.

Esto también explica por qué una muestra de 10 dio 100 %: en el 97 % del arranque
de sesión, diez barras seguidas coinciden sin esfuerzo.

## Qué queda en pie y qué no

**No se refuta la certificación de zonas** (201/203). Este resultado es sobre
*barras primarias*, y las zonas viven en el ~2 % de bloques donde hay creación;
pueden concentrarse en tramos donde la partición acierta, o la geometría del
cluster puede ser robusta al desvío. Eso hay que medirlo, no suponerlo.

**Sí se refuta la afirmación tal como está escrita.** «100,00 % idéntica en Low y
High» no es cierto sobre la población: es 92,6 %, y la muestra que lo respaldaba
estaba sesgada por construcción hacia el tramo fácil.

**Y aparece un dato nuevo**: la deriva es intra-sesión y monótona. En la FASE 7 de
la otra línea el error de celdas era *plano* a lo largo de la sesión. Son dos
cantidades distintas —celdas del perfil contra barras primarias— pero la
diferencia de forma es información: el perfil y la barra primaria se desalinean
con leyes distintas.

## Consecuencia para el gate

El gate de paridad debe declarar su **estimand**: sobre qué población y a qué
nivel vale cada porcentaje. Hoy conviven, sin distinguirse:

- 100 % de decisión de bloque **sobre input igual** (no valida el footprint),
- 99,01 % de zonas emparejadas sobre **203 zonas**,
- **89,81 % de barras primarias** sobre 233.601 — el que faltaba.

## Cómo podría refutarse esta auditoría

Si el desvío viniera de una convención de zona horaria o del recorte de ticks del
parquet, y no de la partición, casi todas las barras fallarían con el mismo signo
y el acierto sería ~0 %. Da 89,81 % con estructura monótona en la sesión: es un
defecto de partición, no un corrimiento global.
