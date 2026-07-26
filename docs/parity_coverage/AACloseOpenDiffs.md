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
