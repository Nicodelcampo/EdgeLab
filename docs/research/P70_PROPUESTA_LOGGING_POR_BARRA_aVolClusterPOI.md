# P-70 — Propuesta de logging por barra en `aVolClusterPOI.cs`

**No aplicada.** Toda modificación del `.cs` se consulta con Nico. Esto es el
pedido escrito para que la decisión sea de una línea.

## El código confirma el mecanismo medido

`nt8/aVolClusterPOI.cs` líneas ~288-331. Dos hechos, leídos de la fuente:

```csharp
// BarsInProgress == 1  (subserie de 1 tick)
double tvol = Volumes[1][0];
long tick = PriceToTick(Closes[1][0]);
tickProfile[tick] = cur + tvol;          // el perfil se acumula ACA
...
// BarsInProgress == 0  (serie primaria, al cerrar la barra)
long lowTick  = PriceToTick(Low[0]);
long highTick = PriceToTick(High[0]);
foreach (KeyValuePair<long, double> kv in tickProfile)
{
    if (kv.Key < lowTick || kv.Key > highTick) continue;  // defensa de borde
    blockCells[kv.Key] = cur + kv.Value;
}
tickProfile.Clear();
```

1. **El perfil vive en una serie distinta de la que lo cierra.** Se acumula en
   la subserie de 1 tick y se vuelca cuando cierra la barra primaria. El orden
   en que NT8 entrega esos dos eventos determina de qué barra es cada tick — y
   ese orden es exactamente lo que el kernel Python no puede reconstruir desde
   el parquet. Es el **lag −1** medido en la FASE 6.
2. **El filtro descarta sin reasignar** (`continue`), con el comentario del
   propio autor: *defensa de borde*. Es la **pérdida sistemática de 0,41 %**
   medida en la FASE 5.

Los dos defectos que el barrido encontró a ciegas están escritos en el código.
Eso cierra el diagnóstico. Lo que no cierra es la **cantidad**: el orden de
entrega entre series no es constante, y esa variabilidad es la firma del residuo
de la FASE 7 (chico, local, sin deriva).

## Qué se pide agregar

Un solo bloque, **aditivo**, justo antes de `tickProfile.Clear()`. No toca
`blockCells`, ni el filtro, ni la decisión, ni las zonas. Sólo escribe.

```csharp
// === Log por barra (aditivo, sin efecto sobre la decision) ===
if (barLogWriter != null)
{
    double profSum = 0, keptSum = 0;
    long profMin = long.MaxValue, profMax = long.MinValue;
    foreach (KeyValuePair<long, double> kv in tickProfile)
    {
        profSum += kv.Value;
        if (kv.Key < profMin) profMin = kv.Key;
        if (kv.Key > profMax) profMax = kv.Key;
        if (kv.Key >= lowTick && kv.Key <= highTick) keptSum += kv.Value;
    }
    barLogWriter.WriteLine(string.Format(CultureInfo.InvariantCulture,
        "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11}",
        CurrentBar,
        Time[0].ToString("yyyy-MM-ddTHH:mm:ss.fff", CultureInfo.InvariantCulture),
        sessionIndex, blockBarCount,
        lowTick, highTick,
        tickProfile.Count, profMin, profMax,
        profSum.ToString("0.######", CultureInfo.InvariantCulture),
        keptSum.ToString("0.######", CultureInfo.InvariantCulture),
        Volume[0].ToString("0.######", CultureInfo.InvariantCulture)));
}
```

Cabecera:

```
bar_index,bar_close_time,session_index,block_bar_count,low_tick,high_tick,
profile_cells,profile_min_tick,profile_max_tick,profile_volume,kept_volume,primary_bar_volume
```

Más una propiedad `BarLogPath` análoga a `DiagBlockExportPath`, con el mismo
patrón de `StreamWriter` + flag de fallo que ya usa el archivo.

## Qué resuelve cada campo

| campo | pregunta que cierra |
|---|---|
| `profile_volume` vs `primary_bar_volume` | si el perfil de la subserie contiene exactamente los ticks de la barra primaria, o corre desfasado — **mide el lag directamente, sin inferirlo** |
| `profile_volume − kept_volume` | cuánto pierde el filtro, barra por barra. Debería sumar los 120.830 contratos de la FASE 5 |
| `profile_cells`, `profile_min/max_tick` | si el perfil se sale del rango de la barra, y por cuánto |
| `bar_index` + `block_bar_count` | ancla la barra de NT8 a la del parquet sin depender del timestamp, que no tiene resolución (51 % de ticks repetidos) |

## Cómo podría refutarse la propuesta

Si `profile_volume == primary_bar_volume` en todas las barras, el lag no existe
y las FASES 4 y 6 midieron un artefacto — el 15,27 % sería coincidencia. Es un
resultado posible y el log lo mostraría de inmediato.

## Costo y riesgo

Escritura pura dentro de un `if` sobre una propiedad vacía por defecto: con
`BarLogPath` sin setear, el indicador se comporta idénticamente al actual. El
riesgo es de rendimiento en el export (un `WriteLine` por barra primaria, el
mismo orden de magnitud que el log de bloque que ya existe).

Una vez aprobado: correr la misma ventana NQ 06-26 120t ya usada
(`avolcluster_v05_NQ0626_120t_DIAG_20260901.csv`) para que el cruce sea contra
el mismo objeto ya medido.
