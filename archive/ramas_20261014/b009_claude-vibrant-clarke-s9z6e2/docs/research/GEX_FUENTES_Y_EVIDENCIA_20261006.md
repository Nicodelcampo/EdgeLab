# GEX (gamma exposure de dealers) — fuentes verificadas, evidencia y encaje en EdgeLab (2026-10-06)

Estado: **INVESTIGACIÓN, nada ejecutado sobre retornos.** Complementa la información que Nico trajo de otra IA
(2026-10-05). Todo lo de abajo se verificó contra la fuente el 2026-10-06 salvo donde dice "a verificar".

## 1. Fuentes free: qué hay de verdad
| Fuente | Qué trae | Historia | Causalidad | Uso permitido |
|---|---|---|---|---|
| **SqueezeMetrics** `squeezemetrics.com/monitor/static/DIX.csv` | Diario: precio SPX, DIX, **GEX neto (un número)** | **2011-05-02 → 2026-10-02**, 3.879 días | EOD (OI de cierre): usable para la sesión **siguiente** | Descarga pública ofrecida por el sitio |
| **SquawkFlow** `github.com/dhawalc/spx-gamma-levels` (`data/daily/*.json`) | Diario SPX: spot, net_gex, zero_gamma_flip, call_wall, put_wall, vol_trigger, abs_gamma_strike, régimen, **`oi_settle_date`** | **Sólo desde 2026-07-28** (50 archivos; repo creado 2026-08-26) | Explícita (`oi_settle_date` = OI del día previo) | CC BY 4.0 (atribución) |
| **FirmTape** `firmtape.com/sessions`, `/session/YYYY-MM-DD` | Por sesión: OHLC, zero_gamma_flip, call_resistance, put_support, ATM IV, percentil de net gamma, cruces del flip | **1.115 sesiones, 2022-04-14 → 2026-10-02** | **No causal tal como se publica**: los niveles de la ficha describen la sesión cerrada (la ficha dice "el cierre quedó X sobre el flip") | **Bajar el archivo en bloque está prohibido** (Términos, 30-sep-2026; `robots.txt` bloquea `/api/` y `/snapshots/`). Libre para leer y repasar a mano; el dataset completo es pago |
| CBOE delayed + scripts (`GMestreM/gex_data` MIT, `VandersonTorres/gamma-exposure-indicator` Apache-2.0) | Cálculo propio desde la cadena del día | **Sólo hacia adelante** (lo que uno archive) | Total (uno controla la hora) | Libre |

Conclusiones:
- **Historia larga, gratis y causal: sólo el GEX neto diario de SqueezeMetrics** (sin walls). Alcanza para la
  pregunta más respaldada por la literatura: *¿el signo/nivel del gamma de dealers cambia el comportamiento intradía?*
- **Walls y flip con historia: no hay fuente free y causal.** SquawkFlow empieza en julio-2026 (casi todo cae en el
  holdout o justo antes); FirmTape no permite bajarlo y sus niveles son de la sesión ya cerrada. Para walls históricas
  causales hace falta cadena de opciones histórica (EOD con OI): pago (CBOE DataShop, ORATS, OptionMetrics; precios
  y cobertura **a verificar**) o construirla hacia adelante desde hoy.
- **Para el visor** sí sirven: SquawkFlow (desde jul-2026, con fecha de OI) y, a mano, FirmTape para mirar días.

## 2. Evidencia académica (lo que justifica estudiarlo)
- **Baltussen, Da, Lammers, Martens (JFE 2021), "Hedging demand and market intraday momentum"**: en más de 60
  futuros (1974-2020) el retorno del día predice la última media hora; para el índice, el efecto **existe cuando el
  gamma neto es negativo y crece cuanto más negativo**. Encaje directo: régimen diario ex-ante = signo del GEX.
- **Barbon y Buraschi, "Gamma Fragility"**: gamma agregado negativo + iliquidez → momentum intradía; gamma positivo
  → reversión. Más fuerte en subyacentes menos líquidos; asociado a flash crashes.
- **0DTE** (literatura 2023-2026; p. ej. "0DTEs: Trading, Gamma Risk and Volatility Propagation", "Does gamma survive
  the close?"): hoy gran parte del gamma vence en el día; el GEX de OI de cierre **no ve** esas posiciones, que se
  abren y cierran intradía. El GEX diario es un mapa de estructura, no el flujo en vivo.
- **Crítica al "GEX naive"**: todo GEX público asume dealers largos en calls y cortos en puts; el OI no dice quién
  está corto. Fondos vendedores de puts o rachas de compra minorista de calls invierten el signo real. Es un modelo,
  no un reporte de posición.

## 3. Encaje en EdgeLab (propuesta, no congelada)
Familia nueva **GEX-1** (se registra antes de estudiarse; no transporta nada de otras familias).
Espacio de eventos/estados (regla de población: enumerar antes de congelar):
- **Estado diario (ex-ante):** signo y percentil del GEX neto del día previo (SqueezeMetrics). ← candidato principal.
- Estado continuo intradía: distancia del precio al flip / a las walls (sólo con niveles causales).
- Eventos: toque de call wall / put wall, cruce del flip, ruptura vs. rechazo de wall.
Cadena: **información target-free primero** (¿con GEX < 0 el rango intradía, la autocorrelación de retornos de 5-30
min y la continuación de la última media hora son mayores que con GEX > 0?), después P&L bruto, después neto.
Instrumentos: ES/MES (subyacente directo del SPX); NQ con cautela (el GEX es de SPX, no de NDX).
Datos: ES/MES NT8 + spot USA500 Dukascopy desde 2023 (para potencia, con sus limitaciones). Holdout desde
2026-10-01 fuera. Conecta con la idea de regímenes: H-REG-2 (régimen diario condicional) con GEX como variable de
estado.
Cómo podría refutarse: la diferencia condicional (GEX<0 vs >0) en rango/autocorrelación/continuación no supera el
nulo (permutación de la etiqueta GEX entre días, por bloques) con MDE publicado; o desaparece al controlar por la
volatilidad realizada previa (GEX negativo suele coincidir con volatilidad alta: confusor principal).

## 4. Visor (próximo paso técnico, target-free)
`viewer/nt8_bridge/index.html` + bundles: agregar un array `levels[]` por sesión (call_wall, put_wall, flip,
vol_trigger) desde SquawkFlow, convertido SPX→ES con el basis disponible **antes** de la sesión, con
`available_utc` = publicación (después del cierre del día del OI). Sólo dibuja; no calcula señales.

## Fuentes
- SqueezeMetrics monitor — https://squeezemetrics.com/monitor/dix
- SquawkFlow spx-gamma-levels — https://github.com/dhawalc/spx-gamma-levels
- FirmTape (archivo y términos) — https://firmtape.com/ · https://firmtape.com/terms
- Baltussen et al. 2021 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365
- Barbon y Buraschi — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454
- 0DTE y gamma — https://www.researchgate.net/publication/377984312_0DTEs_Trading_Gamma_Risk_and_Volatility_Propagation
- Does gamma survive the close? — https://www.sciencedirect.com/science/article/pii/S1544612326008093
- Crítica al GEX naive — https://dn12448583.substack.com/p/your-gex-chart-is-a-model-not-a-position
