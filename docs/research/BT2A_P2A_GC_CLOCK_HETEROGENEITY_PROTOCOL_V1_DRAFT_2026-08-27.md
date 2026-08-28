# BT2A P2-A GC — heterogeneidad horaria V1 (borrador fail-closed)

**Estado:** `DRAFT_PREAUTHORIZATION_FAIL_CLOSED`  
**Fecha:** 2026-08-27  
**Instrumento:** GC  
**Alcance:** diagnóstico post-outcome, previo a costos, sin selección de horario operativo.

## Corrección científica importante

La familia `secondary_clock_family` ya publicada en P2-A no divide el día por horarios. Sus 12 celdas son cuatro barreras por tres **horizontes cronológicos de 5, 30 y 120 segundos**. Por eso no puede responder si el mecanismo cambia entre Asia, Europa, RTH y post-RTH.

Esta corrida crea una familia nueva y separada. No modifica P2-A, no modifica P2-B V1 y no reinterpreta sus resultados.

## Pregunta

> ¿El contraste direccional bruto `K_ABS − N_RAND` de las tres celdas positivas de P2-A cambia entre cuatro fases institucionales de la sesión de GC?

No se pregunta cuál es “la mejor hora”. Las tres celdas padre ya fueron identificadas mirando outcomes, por lo que todo el análisis horario es post-selección y generador de hipótesis.

## Población e identidad

- 234 sesiones CME continuas pre-holdout.
- Cinco contratos GC.
- `K_ABS = 16.940`, `K_BT2 = 5.262`.
- Event Store canónico: `feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd`.
- Resultado P2-A padre: `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`.
- Última sesión admitida: `20260630`.
- Holdout `2026-07-01`–`2026-12-31`: cerrado.

## Celdas padre

Se usan únicamente como anotación post-outcome:

1. `B=9, H=25 ticks`;
2. `B=30, H=100 ticks`;
3. `B=30, H=250 ticks`.

No se vuelve a buscar sobre las 16 celdas y no se elige una ganadora.

## Fases congelables

Reloj `America/Chicago`, reglas DST IANA, intervalos `[inicio, fin)`:

| Fase | Horario CT |
|---|---:|
| `ASIA_ETH` | 17:00–01:00 |
| `EUROPE_PRE_RTH` | 01:00–07:20 |
| `GC_RTH` | 07:20–12:30 |
| `POST_RTH` | 12:30–16:00 |

El mantenimiento 16:00–17:00 queda excluido. La fase se asigna con `fill_ts_utc_ns`, es decir, con el primer tick canónico estrictamente posterior a la señal.

## Blackout macro

La población primaria excluye CPI, NFP y FOMC desde el instante de publicación incluido hasta cinco minutos después excluido. Se liga byte a byte al calendario:

`5f1a484858c7d0bdd997f7f6dafef014bae2f13debdb5bcce937d74257cbd9ca`

Se excluyen tanto eventos `K_ABS` como anclas `N_RAND`. Los eventos macro se cuentan, pero sus outcomes no forman otra familia oculta.

## Estimando

Para sesión `s`, celda padre `c` y fase `p`:

```text
D[s,c,p] = media(score_FP de K_ABS)
           - mediana_b(media(score_FP de N_RAND_b))
```

`score_FP = +1` para `TP_FIRST`, `−1` para `SL_FIRST` y `0` para `TIMEOUT`.

Los controles `N_RAND` conservan el contrato de P2-A:

- misma sesión CME;
- mismo bin Chicago de 30 minutos;
- mismo `cap_driver` de Gate 1;
- misma fase;
- fuera del blackout macro;
- muestreo determinista sin reemplazo;
- 10.000 replicaciones;
- exclusión de la propia ancla.

El contraste horario fijo es:

```text
H[s,c,p] = D[s,c,p] - media(D[s,c,q] para las tres fases q distintas de p)
```

La sesión debe aportar la fase evaluada y las otras tres fases. Así el estimando no cambia según qué fases estén disponibles. Una sesión-fase sin eventos no vale cero: queda ausente. Una sesión-fase sin capacidad de matching se abstiene con motivo persistido.

## Inferencia

- Unidad: sesión CME.
- Peso: igual por sesión.
- Método: Webb six-point wild cluster bootstrap.
- Replicaciones: 10.000.
- Alternativa: bilateral.
- Familia primaria: `3 celdas × 4 fases = 12`.
- Multiplicidad: Holm sobre las 12 comparaciones.
- Cobertura mínima: 117 sesiones por contraste.

Las 12 estimaciones de nivel por fase se publican sólo como descriptivas. Una fase no se selecciona automáticamente aunque su contraste sea el mayor.

## Regla de clasificación

- `P2A_POST_SELECTION_CLOCK_HETEROGENEITY_SIGNAL`: familia completa y al menos un contraste fase-vs-rest con IC95 que excluye cero y `p_Holm12 ≤ 0,05`.
- `P2A_POST_SELECTION_NO_CLOCK_HETEROGENEITY_SIGNAL`: familia completa y cero contrastes que cumplen.
- `P2A_CLOCK_HETEROGENEITY_INCONCLUSIVE`: familia incompleta, identidad inválida o cobertura insuficiente.

Ninguna etiqueta autoriza `BEST_WINDOW`, cambia P2-B, demuestra rentabilidad, declara edge ni habilita promoción.

## Preflight y ejecución

El preflight:

- valida el spec P2-A padre;
- recalcula la identidad del Event Store;
- exige los 234 checkpoints y los cinco Parquet;
- valida el calendario macro;
- verifica Python 3.12.14 y el lock;
- no lee valores de precio ni calcula outcomes.

Comando de preflight:

```bash
python tools/run_bt2a_p2a_gc_clock_heterogeneity.py \
  --event-store-dir /ruta/event-store \
  --data-dir /ruta/gate1-parquets \
  --preflight-only
```

La ejecución permanecerá bloqueada hasta que el spec se congele en un commit revisado y se emita por separado:

```text
AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1
```

Después de una autorización válida:

```bash
python tools/run_bt2a_p2a_gc_clock_heterogeneity.py \
  --event-store-dir /ruta/event-store \
  --data-dir /ruta/gate1-parquets \
  --output-dir /ruta/salida-clock-v1 \
  --run-all \
  --authorization-token AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1

python tools/run_bt2a_p2a_gc_clock_heterogeneity.py \
  --event-store-dir /ruta/event-store \
  --data-dir /ruta/gate1-parquets \
  --output-dir /ruta/salida-clock-v1 \
  --finalize \
  --authorization-token AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1
```

Los checkpoints permiten reanudar. Un checkpoint existente pero ligado a otro spec produce abstención.

## Firewalls actuales

```text
NEW_ANALYTICAL_FAMILY_EXECUTED = false
FUTURE_PRICE_PATH_ACCESSED_BY_PREPARATION = false
PNL_ACCESSED = false
P2B_RUN = false
L2_OUTCOMES_OPENED = false
HOLDOUT_TOUCHED = false
WINNER_SELECTED = false
EDGE_DECLARED = false
PROMOTION_ELIGIBLE = false
```
