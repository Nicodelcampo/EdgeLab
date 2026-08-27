# BigTrap2Absorption — Puerta 2-B económica GC v1

- **Fecha:** 2026-08-27
- **Estado:** `FROZEN_PREAUTHORIZATION`
- **Preparación:** `P2B_SPEC_PREPARATION=true`
- **Ejecución:** `P2B_RUN=false`
- **Holdout:** `HOLDOUT_TOUCHED=false`

## Alcance

P2-B convierte el soporte diagnóstico de P2-A en una medición económica sobre
`K_ABS`. Se evalúan las 16 celdas `B ∈ {5,9,18,30}` ×
`H ∈ {25,50,100,250}`. Las tres celdas positivas de P2-A (`9×25`, `30×100`,
`30×250`) son sólo anotaciones; no reciben prioridad ni seleccionan un ganador.

## Justificación económica

P2-A respaldó un mecanismo, no una estrategia ni P&L realizado. P2-B mide
expectativa neta después de comisión, spread y slippage con reglas congeladas y
sin abrir el holdout.

## Cómo podría refutarse

Falla si una implementación independiente no reproduce fills causales, familia
completa, costos, exclusiones macro, límites de sesión, concurrencia, hashes o
replay determinista. También falla si preflight lee precios/P&L, si entra una
fila del holdout o si se presenta una celda como ganadora.

## Identidad de origen

- Resultado P2-A: `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`.
- Event Store: `feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd`.
- Muestra: cinco contratos GC, 234 sesiones, `20250804`–`20260630`.
- Holdout: `2026-07-01`–`2026-12-31`.

## Semántica de ejecución

La señal existe al cierre de barra. La entrada usa el primer tick canónico
estrictamente posterior. La banda `100–250 ms` es diagnóstica, no un segundo
retraso. El target favorable es límite a `+B`; el adverso es stop-market a
`−B`, con gaps al primer precio observado; el timeout sale market en `H` o al
fin de sesión. Hay una posición simultánea por celda y se persisten rechazos.

## Costos congelados

| Componente RT | Base | Adverso |
|---|---:|---:|
| Comisión + tasas | 0,5 t / $5 | 0,5 t / $5 |
| Spread | 1,0 t / $10 | 1,0 t / $10 |
| Slippage | 2,0 t / $20 | 4,0 t / $40 |
| **All-in** | **3,5 t / $35** | **5,5 t / $55** |

```text
commission_ticks = 5 / 10 = 0,5
all_in_ticks      = spread + slippage + commission_ticks
net_ticks         = gross_ticks - all_in_ticks
net_usd           = net_ticks × $10
```

## Sesiones y RTH

La autoridad es `HARD_CME` del Event Store. Para no desplazar una hora la
muestra, se conserva el rollover del repositorio a las 17:00 CT y la sesión
negociable `17:00–16:00 CT`, con mantenimiento `16:00–17:00 CT`. Se informa RTH
`07:20–12:30 CT` como intervalo `[inicio,fin)`.

## Calendario macro oficial congelado

Research oficial delimitó la muestra a `2025-08-04`–`2026-06-30` y publicó:

```text
specs/bt2a_macro_calendar_gc_20250804_20260630_v1.json
```

Contiene 26 anuncios reales dentro de la ventana:

| Tipo | Conteo | Hora oficial |
|---|---:|---|
| FOMC | 7 | 14:00 ET |
| CPI | 10 | 08:30 ET |
| NFP / Employment Situation | 9 | 08:30 ET |

Cada hora fue convertida a UTC con las reglas DST de `America/New_York`. La
exclusión es `[release_utc, release_utc+5 minutos)`. Las fuentes rectoras son el
calendario del Federal Reserve y los schedules/archives de BLS.

El archivo incorpora las anomalías oficiales del lapse de apropiaciones:

- CPI septiembre 2025: retrasado al `2025-10-24`;
- CPI octubre 2025: cancelado, sin recolección;
- NFP septiembre 2025: retrasado al `2025-11-20`;
- NFP octubre 2025: sin release standalone;
- NFP noviembre 2025: retrasado al `2025-12-16`;
- NFP enero 2026: retrasado al `2026-02-11`;
- CPI enero 2026: retrasado al `2026-02-13`.

El SHA-256 de los bytes del calendario debe calcularse en el checkout limpio y
quedar citado textualmente en la autorización:

```powershell
$CAL = "specs/bt2a_macro_calendar_gc_20250804_20260630_v1.json"
$SHA = (Get-FileHash $CAL -Algorithm SHA256).Hash.ToLower()
```

## Inferencia

Cada sesión CME pesa igual. Se usan 10.000 réplicas bootstrap y sign-flip, con
Holm sobre 16 celdas por escenario. Una celda es robusta sólo si base y adverso
tienen límite inferior positivo y `p_Holm≤0,05`. No se elige la mejor celda.

## Preflight

```powershell
python tools/run_bt2a_p2b_gc_economic.py `
  --event-store-dir E:\EdgeLab\bt2a_event_store `
  --data-dir E:\EdgeLab\gc_parquets `
  --macro-calendar specs\bt2a_macro_calendar_gc_20250804_20260630_v1.json `
  --macro-calendar-sha256 $SHA `
  --preflight-only
```

Preflight no parsea precios ni calcula P&L. La ejecución requiere el token
separado `AUTHORIZE_BT2A_P2B_GC_ECONOMIC_V1`.

```text
P2B_RUN=false
PNL_ACCESSED=false
FUTURE_PRICE_PATH_ACCESSED=false
HOLDOUT_TOUCHED=false
WINNER_SELECTED=false
EDGE_DECLARED=false
```

## Aporte al referente

El calendario elimina una entrada externa pendiente y vuelve reproducible el
blackout FOMC/CPI/NFP sobre toda la muestra GC sin abrir P2-B ni el holdout.
