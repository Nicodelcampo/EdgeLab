# El motor de clusters cambió — qué hay que re-medir antes de medir nada

> 2026-09-08. El `.cs` pasó de **v1.1.0 a v2.0.0** (reescrito por el agente de
> Antigravity al arreglar el dibujo). No fue sólo render: **cambió la máquina de
> estados**. El espejo Python quedó actualizado a v2.0 en el mismo commit.
> Descubierto al empezar la validación de paridad que pidió Nico.

---

## Los dos indicadores ahora son el mismo

`HFTClusterZonesNQ` (v2.0.0) y `HFTClusterZonesNQDx` difieren en **tres cosas**:
el `Name`, y el flag de logging que uno llama `SoloLogEnVivo` y el otro
`LogOnlyRealtime`. Los 65 parámetros restantes y el motor son idénticos. Por eso
marcan las mismas zonas.

Queda **un solo motor** que espejar, que es una mejora respecto de ayer.

## Por qué no dibujaba ni una zona (la causa real)

Tres cosas, ninguna de las cuales era la que yo había diagnosticado:

1. **`DibujarZonasIndividuales = false`** por default. Las zonas no se pedían.
2. **`RenderZonasDx` sólo recorría las últimas ~120 zonas** (`zones.Count - max(50,
   ClusterLookbackZones)`) y descartaba toda zona nacida antes del borde izquierdo
   visible, porque calculaba `xStart` sin sujetarlo al canvas.
3. **Carrera entre hilos**: `OnBarUpdate` mutaba `zones`/`clusters` mientras `OnRender`
   los recorría. Sin `lock`, eso tira excepción y no dibuja nada.

Antigravity arregló las tres (`syncLock`, culling correcto, flag en `true`) y conservó
la corrección de etiquetas superpuestas, agregándole una guarda de `NaN`.

**Mi diagnóstico anterior —`OcultarInvalidados=true` contra un 99,4 % de invalidación—
era correcto para el motor que produjo ese log, y es irrelevante para el de hoy**: v2
no puede invalidar nada. Queda corregido acá.

## Lo que cambió en el motor

| regla | v1.1.0 | **v2.0.0** |
| :-- | :-- | :-- |
| invalidación | `INVALIDATED` si el precio perfora con < 80 % de capacidad | **eliminada** — el estado existe en el enum, en el filtro de fusión y en las etiquetas, pero **ninguna línea lo asigna** |
| expiración | `bar − start_bar > max_age_bars` | `bar − end_bar >= max_age_bars` |
| consumo | sólo por tick | **dos caminos**: por tick y por barra primaria |
| toque de POC | `|precio − poc| < 0,6` ticks | por tick igual; **por barra `low <= poc <= high`** |
| filtro de fusión | excluye `DEPLETED`/`INVALIDATED` | excluye también `EXPIRED`, **sin flag** |
| `min_density` | 3,0 | **3,5** |
| `max_age_bars` | 800 | **2500** |
| `min_capacity_volume` | 1200 | **400** |
| `capacity_multiplier` | 2,5 | **1,0** |
| `lookback_zones` | 120 | 120 |
| `min_contributing_zones` | 3 | **2** |

## Tres consecuencias que hay que asumir antes de medir

**1. `InvalidationTicks` es un parámetro muerto.** Se declara, se documenta, se escribe
en la línea `# params` del CSV, y no lo lee nadie. Es el mismo caso que
`FallosTolerados`. El censo de parámetros hay que rehacerlo.

**2. El ciclo de vida medido quedó obsoleto.** «99,4 % muere `INVALIDATED`, 0,4 %
agotado, 0,1 % expirado, 4,6 % toca su POC» se midió sobre el log real de v1.0.0/1.1.0.
En v2 esa transición es inalcanzable, así que **la distribución de riesgos competitivos
es otra y todavía no se midió**. El registro MEDIDO/NO MEDIDO ya lo refleja.

**3. El objeto histórico y el objeto en vivo no son el mismo objeto.** Esta es la más
seria y no es un cambio de default:

```csharp
// ActualizarConsumoBarra
if (State == State.Realtime && BarsArray.Length > 1 && CurrentBars[1] > 0)
    return;                       // en vivo se saltea...
```

…pero en histórico **no** se saltea, y la sub-serie de ticks (`BarsInProgress == 1`)
corre igual, llamando a `ActualizarConsumoTick`. Es decir: **en histórico los dos
caminos suman al mismo `VolumeInside`, y en vivo sólo uno.** Un cluster formado sobre
barras históricas se agota aproximadamente al doble de velocidad que uno formado en
vivo.

Eso toca directamente lo que viene: las capturas que Nico va a mandar son de un chart
donde **conviven los dos regímenes** —el pasado con doble conteo, las últimas barras
sin él—, y cualquier oráculo exportado por reproducción histórica mide el régimen de
doble conteo.

El espejo lo reproduce tal cual, porque su trabajo es parecerse al oráculo y no
arreglarlo. Pero **antes de medir conviene decidir si el `.cs` se corrige**, y esa es
una decisión de Nico: cambia qué es el objeto.

## Estado del espejo

`edgelab/bridge/indicators/hftclusterzones.py` **v2.0**. Conserva los dos motores:

- `RESEARCH_DEFAULTS` — v1.x, el único que reproduce el log de eventos existente.
- `MOTOR_V2` — el `.cs` de hoy, defaults y semántica.

Los interruptores nuevos (`invalidacion_activa`, `expira_desde`, `expira_inclusive`,
`consumo_por_barra`) hacen la diferencia explícita en vez de esconderla en un default.
Doce tests nuevos clavan cada regla, incluido el del doble conteo, que documenta el
comportamiento del `.cs` sin bendecirlo.

## Especificación del oráculo de clusters (Nico lo exporta)

**`NQ 06-26`, miercoles 3 → jueves 11 de junio de 2026, chart de 25 ticks.**

Nico marcó que el `06-26` vence en junio y que la ventana podía estar tocando el
roll. Medido sobre el volumen diario del parquet, tenía razón — y el corte es nítido:

| sesión | volumen | vs. mediana |
| :-- | --: | --: |
| … 3 al 11 de junio | 621 k – 1.057 k | **113 % – 192 %** |
| 12 de junio | 415 k | 75 % |
| 15 de junio | 148 k | **27 %** |
| 16 de junio | 75 k | **14 %** |
| 17 de junio | 35 k | 6 % |
| 18 de junio | 5,5 k | 1 % |

El contrato vence el 19 y el volumen se va al `09-26` a partir del 12. Las siete
sesiones del **3 al 11** están todas **por encima de la mediana del contrato**, e
incluyen las dos de mayor volumen de toda su vida (5 y 9 de junio). No hay
contaminación de roll.

Cierra **dos** huecos del registro con una sola corrida: la paridad de la capa de
clusters (nunca tuvo oráculo) y la paridad sobre **NQ** (el certificado vigente es
sobre ES 09-26).

### Y de paso: las corridas de la campaña incluyeron sesiones muertas

Buscando el roll apareció que **3 de las 50 sesiones de H2 no eran sesiones
operables**: 2026-05-25 (22,7 % de la mediana — feriado), 2026-06-15 (26,9 %) y
2026-06-16 (13,6 %), las dos últimas ya post-roll. Entraron a la medición como una
sesión cualquiera.

Ninguno de los runners filtra por liquidez. H2 ya está anulada por escala, así que
esto no cambia una conclusión, pero **la próxima corrida tiene que excluirlas** y hace
falta una compuerta de sesión reutilizable. Queda anotado en el registro.

| | |
| :-- | :-- |
| contrato | `NQ 06-26` — el mismo de toda la campaña |
| datos en NT8 | 2026-03-31 → 2026-06-18, 67 días |
| parquet | 2026-03-12 → 2026-06-18 |
| holdout | empieza el **2026-07-01**: la ventana queda 3 semanas antes |

Parámetros: **todos en default**, salvo cuatro.

| parámetro | valor | por qué |
| :-- | :-- | :-- |
| `SoloLogEnVivo` | **false** | en `true` no escribe nada en histórico (línea 1623) |
| `EnableDbLogging` | true | |
| `DbPath` | `C:\LoggerHFT\data\oraculo_clusters_NQ0626_20260908.sqlite` | archivo nuevo: no tocar el oráculo certificado |
| `EnableEventCsv` + `EventLogPath` | true / `...\oraculo_clusters_NQ0626_20260908.csv` | el flujo de eventos es el censo as-of |

Hacen falta las **dos** tablas del mismo run: `hft_zones` y `hft_clusters`. La de
zonas sirve de control — su motor no cambió (`ProcesarSweeps` es idéntico byte a byte
entre v1.1.0 y v2.0.0), así que si las zonas no dan EXACT, el problema es del arnés y
no de los clusters.

**Advertencia sobre lo que ese oráculo mide:** al reproducir histórico corren los dos
caminos de consumo, así que el `volume_inside` que quede grabado es el del régimen de
**doble conteo**. El espejo lo reproduce con `consumo_por_barra=True`, pero la
paridad va a certificar el objeto histórico, no el que se ve en vivo.

---

**Aporte al referente:** evita certificar paridad contra un espejo que describía un
motor retirado, y deja identificado —antes de gastar una sola medición— que el objeto
histórico y el objeto en vivo difieren por construcción.
