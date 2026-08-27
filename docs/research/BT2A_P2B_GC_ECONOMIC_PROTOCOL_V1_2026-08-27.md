# BigTrap2Absorption — Puerta 2-B económica GC v1

- **Fecha:** 2026-08-27
- **Estado:** `FROZEN_PREAUTHORIZATION`
- **Preparación:** `P2B_SPEC_PREPARATION=true`
- **Ejecución:** `P2B_RUN=false`
- **Holdout:** `HOLDOUT_TOUCHED=false`

## Alcance

P2-B convierte el soporte diagnóstico de P2-A en una medición de ejecutabilidad
económica sobre `K_ABS`. Se evalúa la familia primaria completa de 16 celdas:

- barreras `B ∈ {5, 9, 18, 30}` ticks;
- horizontes `H ∈ {25, 50, 100, 250}` observaciones de tick.

Las tres celdas positivas de P2-A (`9×25`, `30×100`, `30×250`) quedan anotadas,
pero no reciben prioridad, peso ni tratamiento especial. No se selecciona un
ganador.

## Justificación económica

P2-A respaldó un mecanismo direccional, no una estrategia ni P&L realizado. El
objetivo rector exige expectativa neta después de comisión, spread y slippage.
P2-B mide esa distancia usando reglas y costos congelados antes de una corrida,
sin abrir el holdout.

## Cómo podría refutarse

El protocolo queda refutado si una implementación independiente no reproduce:

1. fills causales estrictamente posteriores a la señal;
2. las 16 celdas, sin omisiones post-outcome;
3. la identidad aditiva de costos;
4. la exclusión macro y los límites de sesión;
5. la política de una posición simultánea;
6. los hashes de inputs y checkpoints;
7. el mismo resultado al repetir con iguales bytes.

También falla si preflight lee precios/P&L, si entra una fila del holdout o si se
presenta una celda como ganadora.

## Identidad de origen

- P2-A: `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`.
- Resultado P2-A: `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`.
- Event Store: `feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd`.
- Muestra: cinco contratos GC, 234 sesiones, máxima sesión `20260630`.
- Holdout sellado: `2026-07-01`–`2026-12-31`.

## Semántica de ejecución

### Entrada

La señal existe al cierre de su barra de confirmación. La referencia de entrada
es el primer tick canónico estrictamente posterior según `(ts_utc_ns,
source_row)`. Un tick simultáneo nunca puede llenar la orden. La banda de
`100–250 ms` se reporta como diagnóstico de latencia; no se aplica además como
un segundo retraso, porque eso cobraría dos veces el mismo supuesto `t+1`.

### Salidas

- target favorable: límite a `+B` ticks desde el ancla de entrada sin costos;
- stop adverso: stop-market a `−B`; un salto se llena en el primer precio
  observado, aunque sea peor;
- timeout: market en la observación `H` o en el último tick de la sesión;
- si target y stop fueran alcanzables en una observación agregada, gana el stop;
- una única posición puede estar abierta por celda; gana la primera señal
  ejecutable y todos los rechazos quedan persistidos.

Esta interpretación separa correctamente `B` (distancia bilateral) de `H`
(horizonte de observaciones). `H` no se convierte en un nivel de stop.

## Costos congelados

GC usa tick de `0,10` puntos y valor de `$10`.

| Componente RT | Base | Adverso |
|---|---:|---:|
| Comisión + exchange/NFA/clearing | 0,5 t / $5 | 0,5 t / $5 |
| Spread asumido | 1,0 t / $10 | 1,0 t / $10 |
| Slippage entrada | 1,0 t / $10 | 2,0 t / $20 |
| Slippage salida | 1,0 t / $10 | 2,0 t / $20 |
| **Fricción all-in** | **3,5 t / $35** | **5,5 t / $55** |

La cifra suministrada de `2,5 ticks/$25` es comisión más slippage base. Al sumar
el spread congelado de un tick, la fricción all-in que resta el estimador es
`3,5 ticks/$35`. No se oculta ni se cuenta dos veces.

```text
commission_ticks = commission_rt_usd / tick_value_usd = 5 / 10 = 0,5
all_in_ticks      = spread_ticks + slippage_entry + slippage_exit + commission_ticks
net_ticks         = gross_ticks - all_in_ticks
net_usd           = net_ticks × 10 × 1 contrato
```

## Sesiones y RTH

La autoridad de partición es `HARD_CME` del Event Store. La ventana suministrada
`18:00–17:00 CT` coincide por reloj con la expresión habitual en ET, no CT. Para
no desplazar la sesión una hora, se conserva el rollover del repositorio a las
17:00 CT y la sesión negociable de GC `17:00–16:00 CT`, con mantenimiento
`16:00–17:00 CT`. El reporte separa RTH `07:20–12:30 CT`, intervalo
`[inicio, fin)`.

## Exclusiones macro

Se excluyen señales cuyo timestamp cae en `[release, release+5 minutos)` para
`FOMC`, `CPI` o `NFP`. El calendario debe cumplir
`bt2a_macro_calendar_v1` y su SHA-256 debe quedar unido al preflight y a la
autorización. La spec no inventa fechas no suministradas: calendario ausente o
sin hash produce `ABSTAIN`.

Ejemplo mínimo:

```json
{
  "schema": "bt2a_macro_calendar_v1",
  "events": [
    {"event_id": "CPI-2026-06", "event_type": "CPI", "release_utc": "2026-06-10T12:30:00Z"}
  ]
}
```

## Estimandos e inferencia

Por celda y escenario se conservan:

- neto por trade y por señal elegible, en ticks y USD;
- conteos de señales, exclusiones macro, trades y rechazos por concurrencia;
- desglose full-session y RTH;
- razones de salida y latencia observada.

La unidad inferencial es la sesión CME y cada sesión pesa igual. Se generan IC
percentiles del 95% y tests sign-flip de 10.000 réplicas, con Holm sobre las 16
celdas por escenario. Una celda es robusta sólo si base y adverso tienen límite
inferior positivo y `p_Holm≤0,05`. Base positiva pero adverso no positivo se
clasifica como sensible a costos.

Ninguna regla selecciona la mejor celda. La etiqueta global sólo puede afirmar
que existe al menos una celda robusta dentro de la familia completa.

## Preflight y autorización

El modo seguro es:

```powershell
python tools/run_bt2a_p2b_gc_economic.py `
  --event-store-dir E:\EdgeLab\bt2a_event_store `
  --data-dir E:\EdgeLab\gc_parquets `
  --macro-calendar E:\EdgeLab\macro_gc_v1.json `
  --macro-calendar-sha256 SHA256_CONGELADO `
  --preflight-only
```

Preflight verifica contrato, rama/worktree, Event Store, 234 checkpoints,
registros, archivos y calendario. No parsea valores de precio ni calcula P&L.
Una corrida exige además el token separado:

```text
AUTHORIZE_BT2A_P2B_GC_ECONOMIC_V1
```

Hasta recibirlo se mantienen:

```text
P2B_RUN=false
PNL_ACCESSED=false
FUTURE_PRICE_PATH_ACCESSED=false
HOLDOUT_TOUCHED=false
WINNER_SELECTED=false
EDGE_DECLARED=false
```

## Aporte al referente

El contrato transforma el mecanismo de P2-A en una prueba neta reproducible y
conservadora, cobrando todos los costos GC sin sesgo de selección y sin consumir
el holdout ni declarar una estrategia ganadora.
