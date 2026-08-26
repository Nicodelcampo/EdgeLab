# 02 — Puerta 2 BT2A: contrato first-passage y ejecución

**Estado:** `PROPOSED_POST_OUTCOME_DIAGNOSTIC_NOT_FROZEN`  
**Outcomes abiertos por este trabajo:** no.

## 1. Distinción necesaria

La infraestructura estadística G2 más completa vive en:

```text
fix/g2-a1-calibration-hardening
3c06e9c0ebebf0f37125c306e8bda02ff2f07e4a
```

Incluye nulo de campaña, bootstrap-t, PBO/CSCV, DSR, calendario, walk-forward,
sensibilidad y promoción fail-closed. Ese shell presupone que ya existen trades y P&L.
Gate 1 sólo produjo excursiones. Por eso:

```text
Puerta 2 BT2A = construye orden temporal y ejecución
G2 genérico     = audita estadísticamente el P&L ya construido
```

No se conecta `d_hat` directamente a G2.

## 2. Input autorizado

La fuente primaria son los eventos regenerados con el runtime congelado de Gate 1:

```text
edgelab/research/all5_runtime/*
edgelab/research/bt2_gate1_all5.py
sample registry de 234 sesiones
```

El Event Store nocturno de Antigravity no es input autorizado hasta reconciliarse 1:1
por contrato, sesión y evento. Sus conteos brutos difieren de la población elegible de
Gate 1 y su fill no aplica las exclusiones del contrato formal.

## 3. P2-A — carrera de primer pasaje

### 3.1 Orden y fill

```text
orden = (ts_utc_ns, source_row)
fill = primera fila estrictamente posterior a la señal
frontera CME = dura
```

Se excluye con causa nombrada:

```text
NO_EXECUTION_TICK
FILL_CROSSES_SESSION
HORIZON_CROSSES_SESSION
```

### 3.2 Outcomes

Por evento, barrera y horizonte:

```text
TP_FIRST
SL_FIRST
TIMEOUT
```

Campos mínimos:

```text
event_id, arm, contract, cme_session
direction
signal_ts_utc_ns, signal_source_row
fill_ts_utc_ns, fill_source_row, fill_price_ticks
target_ticks, stop_ticks
horizon_ticks, horizon_seconds
outcome
first_touch_ts_utc_ns, first_touch_source_row
ticks_to_touch, seconds_to_touch
cap_driver
```

`TIMEOUT` no se elimina. Puede deberse a ticks, reloj o borde de sesión.

### 3.3 Familia preexistente

Para no inventar barreras mirando el resultado BT2A se hereda la grilla de
`H-GC-BT2-1_PREREGISTRO.md`:

```text
B = {5, 9, 18, 30} ticks
H_ticks = {25, 50, 100, 250}
H_seconds = {5, 30, 120}
```

Las 16 celdas `B × H_ticks` forman una familia Holm. Los horizontes de reloj son
sensibilidad. El techo Gate 1 de 2.000 ticks/900 segundos se conserva sólo como límite
diagnóstico.

La grilla era anterior a la corrida all5, pero la muestra ya tiene outcomes abiertos:
la primera corrida seguirá siendo post-outcome.

### 3.4 Estimando

```text
score_fp = +1  TP_FIRST
           -1  SL_FIRST
            0  TIMEOUT

theta_fp_session = mean(score_fp dentro de sesión)
theta_fp = mean(theta_fp_session con igual peso por sesión)
```

Se publican también incidencias de los tres outcomes y tiempo hasta toque. La tasa de
acierto condicionada a resueltos es descriptiva; no reemplaza al estimando que incluye
censura.

## 4. Brazos y comparaciones

```text
K_ABS
N_RAND
K_ABS_SHUFFLE
K_BT2
```

Primaria:

```text
K_ABS - N_RAND
```

Secundarias:

```text
K_ABS - K_ABS_SHUFFLE
K_ABS - K_BT2
```

BT2 conserva una comparación de no-inferioridad separada; no se interpreta un IC que
cruza cero como equivalencia.

## 5. Inferencia

- unidad de inferencia: sesión CME;
- igual peso por sesión;
- bootstrap de sesiones completas, mínimo 10.000 réplicas;
- eventos solapados no son IID;
- Holm sobre las 16 celdas primarias;
- publicación completa de negativas, timeouts y celdas sin potencia;
- semillas y repeticiones congeladas;
- ningún parámetro elegido por el máximo observado.

## 6. P2-B — ejecución económica

Usa `docs/execution_simulator_spec.md`:

- long entra al ask; short al bid;
- primer step estrictamente posterior;
- niveles desde el fill;
- target/stop/time stop/sesión/borde de datos;
- slippage y comisión desglosados;
- identidad aditiva de costos.

### Concurrencia

```text
una posición simultánea
first executable signal wins
señal con posición abierta = rejected(position_open)
```

P2-A etiqueta todos los eventos para medir mecanismo. P2-B ejecuta la política no
superpuesta y publica trades más rechazos.

### Escenarios

```text
ideal   = diagnóstico
base    = 1 tick de slippage por pata + comisión plena
adverso = 2 ticks por pata + comisión plena
severo  = 3 ticks por pata + comisión plena
```

La comisión GC debe confirmarse con estados de cuenta antes de una decisión en USD.

### Estimandos económicos

```text
theta_exec_trade   = P&L neto por trade, agregado con igual peso por sesión
theta_exec_signal  = P&L neto por señal elegible, incluyendo rechazo como 0
```

Publicar ambos impide que una configuración mejore artificialmente al rechazar más.

## 7. Uso del sweep de 99 configuraciones

El sweep nocturno es target-free por diseño, pero pertenece al universo antiguo de
152/133 sesiones, cuatro contratos y archivos `.Last.txt`. No redefine Gate 1 all5.

Regla:

```text
headline congelado = única configuración primary
99 configs          = sensibilidad target-free
```

Está prohibido formar `99 configs × 16 barreras` y elegir el máximo. Si se estudia esa
superficie completa, se publica como exploratoria, paga multiplicidad y no promociona.

## 8. Integración con G2 genérico

Orden:

1. reproducir eventos Gate 1;
2. resolver first-passage;
3. ejecutar P2-B;
4. fijar familia exacta de configuraciones;
5. aplicar G2 calibrado;
6. mantener promoción bloqueada en all5;
7. confirmar una configuración congelada en sesiones nuevas.

## 9. Etiquetas permitidas en all5

```text
P2_DIAGNOSTIC_MECHANISM_SUPPORTED
P2_DIAGNOSTIC_MECHANISM_NOT_SUPPORTED
P2_DIAGNOSTIC_EXECUTION_POSITIVE
P2_DIAGNOSTIC_EXECUTION_NEGATIVE
P2_DIAGNOSTIC_INCONCLUSIVE
```

Prohibidas:

```text
CONFIRMATORY_PASS
EDGE_DECLARED
PROMOTED
```

## 10. Definición de implementación terminada

- kernel first-touch con golden tests;
- checkpoints atómicos por sesión;
- identidad exacta de eventos/inputs/código;
- reconciliación con Gate 1;
- P2-A y P2-B separados;
- costos y rechazos persistidos;
- reportes completos y hashes;
- autorización explícita antes de abrir los nuevos outcomes.
