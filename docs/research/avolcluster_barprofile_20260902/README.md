# aVolClusterPOI — FASE 9: los dos defectos confirmados por NT8 mismo

Fecha: 2026-09-02 · instrumentación P-70 (`BarProfileLogPath`), autorizada por Nico
Fuente: `data/nt8_oracles/avolcluster_NQ_120t_BARPROFILE_20260903.csv`
sha256 `e6b19eb36854387833c7dd7b37001732f405b0f93ed4fe6cb559432cd1794672`
NQ SEP26, 120 ticks/barra, 19 sesiones, **66.418 barras**.

Esta es la primera medición que **no pasa por el kernel Python ni por el parquet**:
son los números internos de NT8 sobre sí mismo. Confirma las dos causas que las
fases F2–F8 habían inferido a ciegas, y refuta la forma en que se las modeló.

## Confirmación 1 — el lag existe, y es un DESPLAZAMIENTO puro

| | |
|---|---|
| `profile_volume == primary_bar_volume` | **20.975 de 66.418 (31,58 %)** |
| perfil menor que la barra | 22.599 (34,03 %) |
| perfil mayor que la barra | 22.844 (34,39 %) |
| \|diferencia\| mediana / media / máx | 1 / 4,24 / 601 |
| **total perfil vs total barras** | 8.644.556 vs 8.644.557 — **ratio 1,000000** |

Dos tercios de las barras tienen un perfil que **no es el de su propia barra**.
El desvío es simétrico y el total cierra exacto: **no se pierde ni se inventa
volumen, se corre de barra**. La predicción central de la FASE 6 queda confirmada
con el dato en vez de con la inferencia.

## Confirmación 2 — el filtro `Low/High` pierde volumen

| | |
|---|---|
| barras donde el filtro descarta | 5.841 (8,79 %) |
| volumen perdido | 26.762 (**0,3096 %** del perfil) |
| `kept/primary` | **0,996904** |
| perfil por debajo del `Low` de la barra | 2.874 barras |
| perfil por encima del `High` | 2.969 barras |

La FASE 5 había medido, sobre **otro contrato y otra ventana**, un déficit de
0,41 % (ratio 0,9959) comparando NT8 contra el parquet. Acá NT8 se mide contra
sí mismo y da 0,31 % (0,9969). Mismo orden, mismo signo, dos vías independientes.

## Refutación — el lag NO es de un tick, y por eso F6 tenía techo

El desvío consecutivo dentro de la sesión:

- correlación `d(i)` vs `d(i+1)` = **−0,4411**
- 39,66 % de los pares tienen signo opuesto; **16,38 % cancelan exacto**
- el desvío **acumulado vuelve a cero al cierre de cada sesión**: los 19 cierres
  dan entre −17 y +18 sobre ~450.000 contratos por sesión

Pero el acumulado **intra**-sesión vaga hasta 601 contratos antes de volver. O
sea: la frontera del perfil y la de la barra **se separan y se reencuentran**, con
una deriva variable, no con un offset fijo.

Eso explica exactamente por qué la FASE 6 se clavó en 15,27 %: un lag constante
de −1 tick es la primera aproximación de una deriva variable acotada. También
explica la firma de la FASE 7 — error chico, local, sin tendencia a lo largo de
la sesión.

## Estado de la paridad: sigue NO VALIDADA, pero ahora es un problema resoluble

Lo que cambió: el desplazamiento por barra dejó de ser desconocido y pasó a ser
**observable**. Con `profile_volume`, `profile_cells` y `profile_min/max_tick` por
barra, la frontera real de NT8 se puede **resolver** contra los ticks del parquet
—buscar el rango de ticks cuyo volumen y rango de precio coinciden— en vez de
adivinarla. Eso convierte la paridad en un problema de alineación con solución,
no en una búsqueda de hipótesis.

**Lo que falta es una sola corrida**, porque esta se hizo sobre NQ SEP26 y el
parquet disponible es de NQ 06-26:

1. Data Series: **NQ 06-26**, Type Tick, Value **120**, `End date` ~12/06/2026,
   días suficientes para cubrir la ventana.
2. `Bar Profile Log Path` seteado.
3. **`Diag Block Export Enabled = true`** y `Diag Block Export Path` seteado — en
   esta corrida quedó en `false` y el CSV de bloques no se escribió; hace falta
   para cruzar celdas contra celdas.

## Nota de gobernanza

La ventana corrida (25 días al 2026-09-02) cae dentro del holdout. El firewall
admite explícitamente el holdout para validaciones **target-free**: paridad,
determinismo, geometría, integridad. Esta medición es contabilidad de volumen
interna de NT8: no toca retornos, no elige umbrales, no seleccciona candidatos.
El cruce que falta se hace sobre 06-26, que es pre-holdout.

## Cómo podría refutarse

La predicción falsable declarada en la propuesta P-70 era: si
`profile_volume == primary_bar_volume` en todas las barras, el lag no existe y el
15,27 % de la FASE 6 fue coincidencia. Se cumple en el 31,58 % de las barras, no
en todas — el lag existe. La refutación no se materializó.
