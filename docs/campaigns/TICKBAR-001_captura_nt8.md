# TICKBAR-001 — instrucciones EXACTAS de captura en NT8

Para Nico. Se hace **en la misma sesión** que el oráculo v2 de BigTrap2, en una
sola pasada. Toma pocos minutos.

## Orden de la sesión (no cambiar)

1. **BigTrap2 v2** — es el que valida `PRED-001` bit a bit. Va primero.
2. **HFTZones2 v2.1** — su primer oráculo.
3. **TickBarDiag** — la ventana de diagnóstico de TICKBAR-001 (esto).
4. VolTicksPOC2 y aVolCellPOI2 — sin cambios de código, pueden salir igual.

## Instalación del indicador de diagnóstico

Copiar **`E:\EdgeLab\nt8\TickBarDiag.cs`** a:

```
C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\TickBarDiag.cs
```

**Reemplazar in place. No dejar copias dentro de `bin\Custom`** (NT8 compila todo
el árbol; así se rompió la compilación de HFTZones2 el 2026-07-25). El archivo ya
viene en CRLF y **sin** región generada: NT8 la genera sola al compilar.

Compilar con **F5**. No debería dar errores; si da, pasarme el texto exacto.

## Captura

| Campo | Valor |
|---|---|
| Instrumento | **6E 09-26** |
| Tipo de barra | **25 Tick** (el mismo del oráculo O4 que dio FAIL) |
| Días a cargar | pocos — alcanza con **1 o 2 días**; sólo se registran 150 barras |
| `Barras de warm-up a descartar` | **20** (default) |
| `Barras a registrar` | **150** (default) |
| `Ruta del CSV` | `E:\EdgeLab\oracles\tickbar_diag_25t_6E_0926.csv` |

### Nombre del archivo — cambió en v1.1 (incidente 2026-07-25)

**El `.cs` decide el nombre final, no vos.** A la ruta que pongas le agrega la
resolución resuelta del chart, y si ese archivo ya existe abre el índice
siguiente:

```
ruta que ponés :  E:\EdgeLab\oracles\tickbar_diag_6E_0926.csv
25 Tick escribe:  E:\EdgeLab\oracles\tickbar_diag_6E_0926__Tick25.csv
10 Tick escribe:  E:\EdgeLab\oracles\tickbar_diag_6E_0926__Tick10.csv
si repetís 25t :  ...__Tick25_2.csv
```

El indicador imprime la ruta real en la ventana **Output** de NT8 (`New → Output`).

**Por qué.** La v1.0 sobrescribía la ruta tal cual. Al cambiar el chart de 25
Tick a 10 Tick sin tocar la ruta, NT8 dispara `DataLoaded` y **pisó** la captura
de 25t con datos de 10 ticks: quedaron dos archivos idénticos, uno mal rotulado,
y el clasificador devolvió un `BAR_BUILDER_MISMATCH` **falso** (comparaba barras
Python de 25 contra barras NT8 de 10). Con el sufijo automático eso es imposible.
Tampoco se appendea nunca — el otro modo de falla, el que mezcló tres corridas
en un oráculo el 2026-07-24. Los dos quedan cerrados.

`tools/tickbar_diag.py` además **frena** si el ledger declara una resolución
distinta de la que se le pide comparar, en vez de producir un resultado falso.

Después, repetir **exactamente igual** con **10 Tick**. Las dos capturas juntas
permiten verificar que la causa —y luego el fix— son **generales** y no un parche
atado a `N=25`.

## Qué mirar antes de mandármelo

- La primera línea debe decir `# meta indicator=TickBarDiag,version=1.0`.
- La segunda debe mostrar `bars_period=Tick,bars_value=25` (o `10`).
- Debe haber filas que empiezan con `E,` (eventos) y con `B,` (barras).
- Debería haber ~150 filas `B,` y unos pocos miles de `E,`.

## Qué hago yo cuando llegue

```bash
python tools/tickbar_diag.py oracles/tickbar_diag_25t_6E_0926.csv --parquet data/nt8/6E/6E_09-26_ticks.parquet --contract "6E 09-26" --tick-n 25
```

Devuelve **una** clasificación: `STREAM_MISMATCH` (H1) / `BAR_BUILDER_MISMATCH`
(H2) / `ATTRIBUTION_MISMATCH` (H3) / `MIXED_MISMATCH` (H4) / `NO_MISMATCH`.

**Recién con esa clasificación se diseña el fix**, con su predicción falsable
previa. Está prohibido arreglar antes de clasificar (TICKBAR-001 §6) — es la
lección del ULP: el diagnóstico preciso convirtió 101 diffs en una predicción
bit a bit.
