# Cobertura de paridad — AACloseOpenDiffs

Portado el 2026-07-26. `kernel_id` inicial `f4fe171dffe1eff3`
(`aacloseopendiffs.py`, `bars.py`, `common.py`).

> **Nota de gobernanza:** la pausa de F9 ("no agregar indicadores hasta ejecutar
> al menos una campaña formal de descubrimiento sobre los 5 existentes") quedó
> satisfecha: **CAMP-001 corrió y cerró** el 2026-07-25.

## Por qué entra al bridge

Es el primer kernel del proyecto cuya salida **no depende del `bar_spec` del
chart primario**. El `.cs` hace `AddDataSeries(BarsPeriodType.Minute, 1)` y
descarta todo lo que no sea `BarsInProgress == 1`: computa siempre sobre M1,
marque uno lo que marque en el chart.

Eso vale por dos motivos:

1. **Operativo**: se ven los mismos gaps de M1 en un chart de 10t, 25t o 1 min.
2. **Metodológico**: elimina el `bar_spec` como dimensión de identidad para este
   indicador. Los otros necesitan un oráculo **por resolución** (el `bar_key`
   entra al `config_id`); acá **un solo oráculo cubre todas**.

La invariante está fijada como test: `test_la_salida_NO_depende_del_bar_spec_del_primario`
compara `time:1`, `time:5`, `tick:10` y `tick:25` y exige geometría idéntica.

## Definición del evento (portada literal)

```
gap = |close(M1 anterior) − open(M1 actual)|          .cs L207-211
se registra si gap >= min_diff_ticks * tick_size
top = max(close_prev, open_curr) · bottom = min(...)
ancla = Times[1][1]  → el timestamp de la M1 ANTERIOR, no la actual
```

**`overlap_at_birth`** es la señal: cuántas zonas vivas se solapan con la nueva
en precio y tiempo, contada **al nacer** y sin lookahead. Arranca en 1. El `.cs`
también incrementa el contador de las zonas viejas, pero ese valor futuro **no se
exporta** — sólo el valor al nacer es usable como feature causal.

Borde de expiración, fijado como test porque es fácil "corregirlo" por error:
`if (ExpiresM1Bar < nueva.StartM1Bar) continue` ⇒ con `expires == start` la zona
vieja **todavía cuenta**.

## Fuera de alcance (declarado)

- `FiltrarPorPercentil` afecta **sólo el dibujo** del `.cs`; la persistencia
  incluye todos los gaps. El kernel exporta todo ⇒ el filtro es `offline`.
- `DetectarExpansiones` es una capa visual aparte (ZigZag) que no produce zonas.
  **No se porta.**

## HALLAZGO — defecto histórico del `.cs` v1.0 (corregido en v1.1)

**Resultado del primer oráculo: FAIL, 1595 zonas apareadas.** Causa raíz: no era
el kernel Python, era el `.cs`.

```csharp
if (gapPts < MinDiffTicks * TickSize) return;      // v1.0
```

NT8 entrega el precio como el `double` del decimal parseado del feed, que en el
**24,3 %** de los niveles de 6E cae 1 ULP **por debajo** de la grilla. Al restar
dos precios consecutivos la diferencia queda apenas por debajo de `1*TickSize` y
el `<` la descarta.

| | |
|---|---|
| predicho | **47,5 %** de los gaps de exactamente 1 tick descartados |
| observado contra el oráculo | **43,5 %** |
| corregido en | **v1.1**, sha256 `5a898da43812fd52bbcf26943a27cf20da0a1572dd318be96b9c42523ac5e9b6` |

Corrección aprobada por Nico el 2026-07-26. La decisión ahora usa
`gapTicks = |PriceToTick(closePrev) − PriceToTick(openCurr)|`; `gapPts` sobrevive
sólo para I/O. Detalle completo en `docs/audits/AUDIT-003_barrido_ulp.md`.

## CUARENTENA TOTAL del histórico pre-v1.1 (Decisión B de Nico, 2026-07-26)

**El histórico anterior a v1.1 no se mergea nunca más.**

### El filtro es ESTRUCTURAL, no de memoria

`edgelab/bridge/quarantine.py`, consultado por `oracle.parse_nt8_log()` **antes
de parsear**. Un archivo de `AACloseOpenDiffs` con `version < 1.1` levanta
`DatosEnCuarentena` con el motivo y el sesgo. No hay que acordarse de excluirlo:
hay que **desactivarlo a propósito** (`allow_quarantined=True`), y eso deja rastro
en el código que lo hace. El escape existe sólo para el forense — leer los datos
sucios para *medir* el defecto es legítimo; usarlos como insumo no.

**Fail-closed**: un archivo del indicador **sin `version=` legible** se trata como
contaminado. La comparación de versiones es numérica por tupla, no lexicográfica
(`"1.10" < "1.9"` como texto sería un bug silencioso el día que haya diez
versiones menores).

### El hueco que hacía falta cerrar en el `.cs` — v1.2

El logger de research **no registraba con qué versión se generó cada fila**. Su
header era `instrument,start_ms,…,m1_bar` y nada más: imposible de filtrar
retroactivamente. Ése es el hueco que dejó pasar el defecto durante todo su
histórico.

**v1.2** agrega `ind_version` **por fila**, no en un header, porque ese archivo
**mergea corridas distintas**: una versión a nivel de archivo sería una
afirmación falsa sobre el contenido mezclado. La constante `IND_VERSION` es una
sola fuente de verdad — la usan el meta del canal de paridad y cada fila del
logger, así que no pueden desincronizarse.

### Material en cuarentena

`archive/cuarentena/aacloseopendiffs_pre_v1.1/` — **se conserva crudo, no se
borra**: es la evidencia de la magnitud del defecto (43,5 % observado).

| archivo | origen | tamaño |
|---|---|---|
| `logger_research_AACloseOpenDiffs_pre_v1.1.csv` | `D:\A  Trading\loggers\AACloseOpenDiffs.csv` | 2,24 MB, 28 055 filas |
| `oracle_AACloseOpenDiffs_6E_0926_v1.0.csv` | `oracles/` | 272 KB |

> El original en `oracles/` **no se pudo borrar**: está abierto por otro proceso
> (NT8). La copia forense está completa y el filtro estructural lo bloquea igual.
> Queda pendiente borrarlo con NT8 cerrado.

### Auditoría de consumidores

Qué consumió el histórico contaminado, hasta el 2026-07-26:

| consumidor | veredicto | fundamento |
|---|---|---|
| `oracles/AACloseOpenDiffs_6E_0926.csv` | **CONTAMINADO** | generado por `.cs` v1.0. En cuarentena |
| `D:\A  Trading\loggers\AACloseOpenDiffs.csv` | **CONTAMINADO** | mergeaba desde v1.0. En cuarentena |
| `runs/nt8_bridge/parity_aacod/` (corrida de paridad) | **CONTAMINADO** | comparó contra el oráculo v1.0. Su `parity_report.json` (FAIL, 1595 apareadas) sólo vale como **evidencia forense del defecto**, no como medida de paridad |
| store — particiones de `AACloseOpenDiffs` | **LIMPIO (vacío)** | **nunca se publicó ninguna**. Verificado: no existe `indicator=AACloseOpenDiffs` bajo `runs/nt8_bridge/campaign_store/` |
| CAMP-001 | **LIMPIO** | corrió sobre **Gaps2**, no tocó este indicador |
| features / vectorbt (F8) | **LIMPIO** | consumen el store por identidad, y el store nunca tuvo estas zonas |
| visor | **LIMPIO** | se alimenta del store |
| `docs/parity_coverage/AACloseOpenDiffs.md`, `AUDIT-003` | **LIMPIO** | citan los números **como defecto medido**, que es su uso correcto |

**Conclusión de la auditoría: la contaminación no se propagó.** El defecto se
detectó en el primer oráculo, antes de que nada se publicara al store, así que
ningún análisis ni feature aguas abajo lo consumió. El único material afectado es
el que ya está en cuarentena.

### Hallazgo del propio escaneo: el kernel Python estaba MAL ETIQUETADO

El escáner marcó `runs/nt8_bridge/parity_aacod/AACloseOpenDiffs_…_events_py.csv`
como contaminado. **Falso positivo con causa real**: el kernel Python **siempre**
comparó el umbral en enteros de tick —nunca tuvo el defecto del `.cs`— pero se
etiquetaba `version=1.0`. El dato estaba bien; la etiqueta estaba mal.

Corregido: el kernel declara **v1.2**, alineado con la semántica que implementa.

> **Consecuencia de identidad**: `kernel_id` pasó de `f4fe171dffe1eff3` a
> **`092df4763c9ebf64`**. Sin impacto — no había ninguna partición publicada con
> el id anterior.

Que el escaneo de cuarentena haya encontrado esto es exactamente para lo que
sirve: un inventario que sólo confirma lo que ya se sabía no habría aportado nada.

### El histórico limpio

**Nace con el export 2 de la sesión de NT8 del 2026-07-26**
(`docs/parity_coverage/SESION_NT8_2026-07-26.md`).

| campo | valor |
|---|---|
| `.cs` | **v1.2**, sha256 `e4f5f17b7a2f29fe85299575a4c4ab45b88b29414cb3ef7547d9616775ed2557` |
| kernel Python | **v1.2**, `kernel_id 092df4763c9ebf64` |
| primer archivo limpio | `oracles/AACloseOpenDiffs_6E_0926_v12.csv` *(pendiente de generar)* |
| logger de research limpio | `D:\A  Trading\loggers\AACloseOpenDiffs.csv`, recreado desde cero con la columna `ind_version` |
| fecha | 2026-07-26 |

Fijado en `tests/bridge/test_cuarentena.py` (13 tests), incluido uno que verifica
que la versión declarada por el `.cs` esté **por encima** del umbral de cuarentena
— si alguien la bajara, sus propios datos entrarían en cuarentena y el test lo
diría antes de gastar un export.

### Consecuencia sobre los datos ya generados — DECLARADA

**Todo dato de `AACloseOpenDiffs` anterior al 2026-07-26 tiene ~47 % de los gaps
de 1 tick faltantes.** No es ruido aleatorio:

- es un sesgo **sistemático hacia los gaps grandes** — la distribución de tamaño
  de gap calculada sobre esos datos está corrida hacia arriba;
- está **correlacionado con el nivel de precio**, porque depende de qué niveles
  caen 1 ULP por debajo de la grilla;
- el logger de research (`D:\A Trading\loggers\AACloseOpenDiffs.csv`) **mergea**
  con lo previo, así que arrastra el defecto en toda su parte histórica.

Qué hacer con ese histórico —regenerarlo o marcarlo como sesgado— **queda
pendiente de decisión de Nico**. Hasta entonces no se usa para estadística de
tamaño de gap.

## Ramas y cobertura

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `gap_floor` | `min_diff_ticks` | O1 | pendiente |
| `lifetime` / `overlap_window` | `extend_bars` | O1 | pendiente |

## Export de paridad — canal NUEVO y separado

El `.cs` ya tenía un logger de research que **mergea** con lo previo y escribe a
una ruta fija. Sirve para acumular, no para comparar. Se agregó un canal
independiente que no lo toca:

- Propiedad **`Ruta CSV de paridad (vacío = off)`**, grupo *Z. EdgeLab*.
- **Nunca appendea ni pisa**: si el archivo existe, abre `_2`, `_3`… La ruta real
  se imprime en la ventana **Output**.
- Escribe `# meta` + header + **una línea por zona al nacer**, con el mismo orden
  de campos que el `HEADER` del kernel Python.

## Pre-registro del PRIMER oráculo

| Campo | Valor |
|---|---|
| `.cs` canónico | `nt8/AACloseOpenDiffs.cs`, sha256 `e85cad63fb0621df320955685d457763296b1908edfa48750dde0cfc5a0fccd6` |
| Instrumento | **6E 09-26** (hay parquet: 2026-06-08 → 2026-07-21) |
| Chart | **cualquiera** — es la gracia. Sugerido **25 Tick**, para que el oráculo pruebe de paso la independencia del `bar_spec` |
| Rango | **2026-07-09 → 2026-07-17** (dentro del parquet, con margen) |
| Params | **defaults**: `MinDiffTicks=1`, `ExtendBars=50`, `FiltrarPorPercentil=false` |
| `Ruta CSV de paridad` | `E:\EdgeLab\oracles\AACloseOpenDiffs_6E_0926.csv` |
| Ventana de comparación | `2026-07-13T22:00:00 → 2026-07-16T21:00:00` UTC (la misma de todos los demás) |

**`FiltrarPorPercentil` debe quedar en `false`**: con el filtro activo el `.cs`
deja de dibujar algunas zonas, pero las sigue persistiendo — y el export de
paridad se escribe **antes** del filtro, así que no afecta. Igual conviene
dejarlo apagado para que lo que se ve coincida con lo que se compara.
