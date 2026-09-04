# HFTImpulseZones_P v1.1 — señales por racha de ráfagas, y render SharpDX

Fecha: 2026-09-03 · pedido de Nico: *"que los clusters de más acumulación de
ráfagas seguidas sean señales alcistas o bajistas útiles para EdgeLab"*.

Archivos: `nt8/HFTImpulseZones_P.cs` ·
`edgelab/bridge/indicators/parity_first.py::detect_burst_signals` ·
`tests/bridge/test_burst_signals.py` (9 tests).

## El problema con contar ráfagas de la manera obvia

La ventana de impulso es **deslizante**: en cada barra evalúa las últimas `W`.
Durante un mismo movimiento eso dispara en muchas barras consecutivas. Si se
cuentan todas, un tramo recto de 24 barras produce una «racha de 13 ráfagas» que
no es más mercado — es **el mismo impulso contado trece veces**.

Por eso la definición tiene dos reglas, y las dos son la diferencia entre una
señal y un artefacto de conteo:

1. **Sólo cuentan ráfagas no solapadas.** Una ráfaga nueva cuenta sólo si empieza
   después de que terminó la anterior (`>= WindowBars`).
2. **Una señal por racha.** Se emite la primera vez que la racha cruza los dos
   umbrales. Si sigue creciendo, queda registrado pero no genera señal nueva: una
   racha es un evento, no varios. Sin esto la población quedaría dominada por las
   rachas largas, que contarían muchas veces cada una.

La racha se corta por cambio de dirección, por exceder `MaxBarsBetweenBursts`, o
en la **frontera de sesión** — no cruza sesiones.

## La señal

Hay señal cuando la racha llega a `MinBurstsForSignal` ráfagas **y** el
desplazamiento acumulado llega a `MinBurstDisplacementTicks`. Publica: barra,
sesión, dirección, conteo de ráfagas, desplazamiento acumulado, barra de origen
de la racha, la zona de la ráfaga que disparó y su eficiencia.

Todo entero y sin reloj, igual que el resto del indicador: el 51 % de los ticks
de NQ comparte timestamp, así que cualquier medida de velocidad es
irreproducible por construcción.

## Los tres parámetros de la racha

| parámetro | default | qué controla |
|---|---:|---|
| `MinBurstsForSignal` | 3 | cuántas ráfagas no solapadas hacen falta |
| `MaxBarsBetweenBursts` | 40 | cuánto puede pasar entre ráfagas sin cortar la racha |
| `MinBurstDisplacementTicks` | 48 | desplazamiento acumulado mínimo |

Una semántica que es fácil leer al revés y queda fijada en un test:
**`MinBurstsForSignal` no controla cuántas señales genera una racha** —siempre es
una— sino **qué rachas califican y en qué momento disparan**. Bajarlo a 1 hace
que cada racha dispare en su primera ráfaga en vez de en la tercera; agranda la
población porque entran rachas que nunca habrían llegado a tres, no porque las
largas cuenten más veces.

## Lo que esto NO es

**Es una población de eventos, no una predicción.** El indicador no mira retornos
y nada acá afirma que las señales anticipen nada. Medir si tienen valor económico
exige manifiesto de campaña, número efectivo de hipótesis y el STOP del proyecto.

Y antes de eso hace falta el nulo correcto: si la distribución de señales es
indistinguible de la que produce un nulo que respeta la **misma tasa y el mismo
agrupamiento temporal**, la racha no informa sobre el estado del mercado y sólo
está contando volatilidad. Ese es el primer test que corresponde, no un P&L.

## Render SharpDX

Mismo tratamiento que `AVolZoneSimple`: las zonas son datos (`List<Zone>`) y
`OnRender` recorre sólo las visibles, culled contra `ChartBars.FromIndex/ToIndex`.
Los brushes se crean en `OnRenderTargetChanged` y se liberan **siempre** ahí y en
`Terminated` — el render target se recrea al redimensionar o cambiar de pantalla.
`AntialiasMode.Aliased` durante el dibujo, restaurado en `finally`.

### Dónde se marca la señal, y por qué importa

**La señal se dibuja en la barra donde disparó**, que es la del cierre de la
ventana — con una línea vertical de panel completo más un bloque sólido sobre la
zona.

La primera versión la marcaba en el **borde izquierdo de la zona**, y eso estaba
mal: la zona se dibuja hacia atrás porque describe *de dónde arrancó* el impulso,
así que su borde izquierdo está `WindowBars − 1` barras antes de la decisión.
Visualmente daba a entender que la señal había disparado antes de lo que
disparó — justo la confusión que arruina una lectura de timing.

La distinción, dicha una vez: **la zona mira al pasado, la decisión ocurre al
final**. El CSV nunca tuvo el problema (`bar_close_time_utc` siempre fue la barra
de la decisión); era sólo el dibujo.

### La flecha, y dónde apunta

Cada señal lleva una **flecha direccional** —arriba si es alcista, abajo si es
bajista— con la **punta en la apertura de la primera vela POSTERIOR a la señal**,
más una marca fina horizontal en ese mismo precio.

La elección del ancla no es estética. Ese es **el primer precio disponible después
de la decisión**: dibujar ahí deja explícito que la señal no se opera en la barra
que la generó. Un marcador puesto sobre la barra de la señal invita a leer una
entrada que no existió, y ese es el modo más barato de fabricarse una ventaja
inexistente.

La flecha se dibuja recién cuando esa barra existe, así que no hay lookahead: la
señal ya está decidida y cerrada antes de que aparezca.

Detalle de render: la `PathGeometry` del triángulo se crea y se libera en la misma
llamada —una que sobreviva al frame filtra memoria de GPU— y el antialiasing pasa
a `PerPrimitive` sólo para el triángulo, porque las diagonales salen dentadas en
el `Aliased` que necesitan los rectángulos de zona.

Nuevos: `ExtendBars` (20), `MaxZonesRendered` (2000), `SignalColor`,
`ArrowSizePixels` (6).

## Export

El CSV suma seis columnas: `burst_dir`, `burst_count`,
`burst_displacement_ticks`, `burst_first_bar`, `is_signal`, `signal_seq`. Una
fila por ventana evaluada, `CREATE` y `ABSTAIN`, así que la población es
auditable completa y no sólo donde hubo señal.

La meta declara `bursts_counted=non_overlapping` y `signal_scope=one_per_streak`
para que la convención viaje con el dato.

## Paridad medida: EXACTA en las dos capas

Corrida de NT8 del 2026-09-03: **NQ SEP26, 5 ticks/barra, 3 días**, defaults
(12 / 16 t / 6000 bps / 3 ráfagas / 40 barras / 48 t). Oráculo
`data/nt8_oracles/hftimpulse_NQ_20260903.csv`, sha256 `73452fa5…5b14` (126 MB).
Reporte: `parity_v1.json`. Comando:

```
python tools/paridad_hftimpulse.py data/nt8_oracles/hftimpulse_NQ_20260903.csv
```

| | |
|---|---:|
| ventanas evaluadas | **365.795** |
| capa A — ventana | **365.795 (100,0000 %)** |
| capa B — cadena de racha | **365.795 (100,0000 %)** |
| señales NT8 / Python | **566 / 566** |

La capa B es la que valía: el estado se reconstruye de cero —conteo no solapado,
cortes por dirección, por distancia y por sesión, y una señal por racha— y
coincide fila por fila. Las 566 señales son las mismas, una por una.

### El defecto que casi pasa en silencio

La primera corrida dio **0 ventanas** y veredicto `SIN_DATOS`. Causa: este
indicador escribía el CSV **con BOM** (`Encoding.UTF8`), mientras `AVolZoneSimple`
usa `UTF8Encoding(false)`. Con el BOM adelante la línea de meta ya no empieza por
`# meta`, así que pasaba a ser la cabecera y el archivo entero se leía mal.

**No falló: devolvió vacío.** Es la peor forma de fallar, porque un vacío se
confunde con «no había nada que medir». Corregido en las dos puntas: el lector
tolera BOM (`utf-8-sig`) y el `.cs` escribe sin él, igual que los otros dos
indicadores.

Queda como recordatorio de por qué el validador se prueba **primero contra
errores inyectados**: si sólo se hubiera probado contra un archivo bueno, este
caso habría pasado como «no hay diferencias».

## Cómo podría refutarse el diseño

- **Que las ráfagas no solapadas sigan siendo el mismo movimiento**: si al subir
  `WindowBars` la tasa de señales no baja proporcionalmente, la separación por
  `>= WindowBars` no está aislando movimientos distintos.
- **Que la racha no agregue nada sobre la ráfaga suelta**: si la población con
  `MinBurstsForSignal=3` se comporta igual que con `=1` en cualquier medición
  posterior, la acumulación no aporta y el parámetro es decorativo.
