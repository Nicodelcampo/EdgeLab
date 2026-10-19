# F2.9 — mecánicas chequeadas contra BigTrap2.cs (v2.5.2)

Fuente: `BigTrap2.cs` adjunto 2026-08-13. No es el kernel Python 2.2; es el indicador NT8.

## Confirmado, línea por línea

| Afirmación de F2.9 | Veredicto | Dónde |
|---|---|---|
| `Calculate = OnBarClose` | PASS | SetDefaults |
| La barra creadora no toca su zona | PASS | `EmitirBarra`: `UpdateZones` **antes** de `ProcessBar` |
| Buy/sell: ask/bid, si no tick rule; primer tick sin quotes → buy | PASS | nota 3 |
| Diagonal: `ask[r]/max(bid[r-1],1)`, `bid[r]/max(ask[r+1],1)` | PASS | `ProcessBar` |
| AggressiveSide: volumen = solo agresor (`a` o `b`) | PASS | `contribBuy`/`contribSell` |
| Trapped buyers = agresión **ask** **estrictamente encima** del close | PASS | `rowHalfTick > closeHalfTick` |
| Trapped sellers = agresión **bid** **estrictamente debajo** | PASS | `rowHalfTick < closeHalfTick` |
| Empate fila==close excluido de **ambos** lados | PASS | comentario `tie_excluded_both_sides` |
| Close comparado en enteros de medio tick, no double | PASS | `closeHalfTick` |
| `WickZonePct=30`, `UseWickFilter=true` | PASS | defaults |
| `ImbalanceRatio=3`, `MinTrapVolume=30`, `MinExportVolume=1` | PASS | defaults |
| TRAP se emite desde MinExportVolume; zona sólo si `vol >= MinTrapVolume` | PASS | `EmitSide` |
| Geometría: half-tick pad `lo*TickSize - TickSize/2` | PASS | `ZoneLoPrice` / `EmitSide` |
| CloseThrough: bull muere si `close > techo`; bear si `close < piso` | PASS | `UpdateZones` |
| `MaxAgeBars=2000`, `MaxTouches=0` | PASS | defaults |
| Una barra puede emitir **los dos** lados | PASS | dos `EmitSide` |
| Visuales (TopPercent/AutoScale/Outlier) no son analíticos | PASS | nota 10 |

## Corrección obligatoria: “mecha” ≠ mecha de la vela

```text
wickHiFloor = High - range * WickZonePct/100
wickLoCeil  = Low  + range * WickZonePct/100
```

Con 30% eso es:

- buyers: centro de fila en el **30% superior del rango High−Low**;
- sellers: centro de fila en el **30% inferior del rango**.

No es `(High − max(Open,Close))`. Si el close está cerca del high, la banda de buyers se achica o desaparece aunque la mecha superior de la vela sea chica. Si el close está abajo, hay mucho espacio “arriba del close ∩ top 30%”.

`S0` de F2.9 queda como **proxy OHLC declarado**, no como el predicado del kernel. El predicado fiel es: existe fila calificada en la banda extrema del rango y del lado estricto del close.

El filtro de mecha usa `rowPrice` en double; el lado vs close usa enteros de medio tick. Esa asimetría es del `.cs`, no nuestra.

## Cosas que F2.9 **no** debe atribuir al kernel

- `P_mode` (`d=2`, ancho 1) es un probe de research. El kernel usa el span de filas calificadas.
- `S2` (close no central) no está en el indicador.
- `sesionNoConfiable` existe en NT8 y **suprime creación** hasta la próxima sesión. El kernel Python de F2.7/F2.8 no implementa esa rotura.
- Versión del `.cs` leído: **2.5.2** (secuenciador OHLCV, `LogEventAt`). El runner de research usa el traductor Python 2.2.

## Implicación para F2.9

El prior “BigTrap2 marca barras con agresión de un lado, en el extremo del rango, del lado opuesto al close” **sí** está en el indicador. El prior “marca velas con mecha larga de libro de texto” **no**. La escalera OHLC tiene que hablar de **banda extrema del rango + close descentrado**, no de mecha japonesa.
