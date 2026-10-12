# Mandato de EdgeLab: qué edges importan

**Leer antes de proponer, lanzar o interpretar cualquier corrida. Aplica a todo agente, también al autopilot que corre en el Debian.**

## 1. El objetivo
Encontrar estrategias **intradía de futuros que sirvan para superar challenges de cuentas fondeadas y para operar esas cuentas**, y hacerlo **combinando varias estrategias poco correlacionadas**.

Un efecto estadísticamente significativo **no cumple el objetivo por serlo**. No sirven los edges que sean:
- **chicos**: que no sobreviven a los costos reales (comisión, spread, deslizamiento) con margen;
- **inestables**: que dependen de un trimestre, de pocos días extremos o de un régimen que no se repite;
- **sin margen para diversificar**: que no se pueden combinar con otras estrategias (misma señal, mismo horario, mismo activo, alta correlación de P&L).

## 1b. La cuenta de referencia: Lucid
Las reglas de referencia son las de **Lucid** (centro de ayuda público, crawl del 2026-10-13; ver [`docs/research/PROPFIRM_LUCID_REFERENCIAS_20261013.md`](docs/research/PROPFIRM_LUCID_REFERENCIAS_20261013.md)). Extraídas por el agente, **sin verificar por una persona**. Lo que más pesa en el diseño de estrategias:
- **Sin límite de tiempo** en la evaluación: decide P(llegar al objetivo antes del piso), no el tiempo. 50K: objetivo 3.000, piso (MLL) 2.000 con drawdown de **fin de día**, que se bloquea en saldo inicial + 100 al superar 52.100.
- **Consistencia 50 %** en LucidFlex/Daily (60 % Black; Pro la exige solo en los retiros, 40 %): el mayor día no puede pasar de esa fracción del beneficio. **Castiga los edges que ganan en pocos días grandes.**
- **Estrictamente intradía:** posiciones cerradas antes de las 15:45 CT (16:45 ET). Máx. 4 minis o 40 micros en 50K.
- **Prohibido:** HFT, microscalping (> 50 % de ganancias en operaciones de ≤ 5 s) y **cobertura entre cuentas** (posiciones opuestas en cuentas del mismo usuario): al combinar estrategias en cuentas distintas, **no pueden estar en lados opuestos del mismo instrumento al mismo tiempo**. Se permiten hasta 10 cuentas de evaluación y 5 fondeadas.
- Un participante **sin ventaja** pasa poco: techo geométrico 40 % (L/(T+L)) y, con 1 contrato y costos reales, ≈ 3,5 % con brackets de USD 100, ≈ 16 % con USD 200 y ≈ 0 con brackets chicos (los costos se comen todo). **Toda estrategia debe compararse contra ese control sin ventaja** (módulo `edgelab/propfirm`).

## 2. Por qué
Un challenge impone reglas duras (objetivo de ganancia, drawdown máximo que suele ser de tipo *trailing*, a veces límite de pérdida diaria, días mínimos y tiempo máximo, a veces consistencia). Una estrategia sola, con rachas y drawdown, rara vez los supera de forma confiable; **varias estrategias pequeñas, estables y poco correlacionadas suavizan la curva y aumentan la probabilidad de pase**. Lo que importa es la **probabilidad de pasar y de sostener la cuenta**, no el p-valor de un efecto.

## 3. Criterios de utilidad (se evalúan con P&L NETO de costos)
Definidos en `config/autopilot/mandate.json` (valores propuestos; ver §7) e implementados en `edgelab/autopilot/mandate.py`:
1. **Neto positivo y resistente a costos** (sigue positivo con costos × 1,5).
2. **Compatibilidad con las reglas de Lucid**: intradía (cerrada antes de 15:45 CT), sin HFT/microscalping, consistencia del 50 % (el mayor día ≤ 50 % del beneficio), sin posiciones opuestas a otras estrategias de la cartera.
2b. **Frecuencia** suficiente (≥ 10 operaciones/mes) para llegar al objetivo en el plazo.
3. **Estabilidad temporal**: ≥ 4 trimestres observados y ≥ 70 % de ellos positivos; no depende de los 5 mejores días (≤ 50 % del P&L); no depende de un solo trimestre (siempre mirar «sin el mejor trimestre»).
4. **Diversificación**: correlación absoluta del P&L diario ≤ 0,30 con las estrategias ya aceptadas; meta de ≥ 3 estrategias independientes.
5. **Drawdown compatible** con el límite del challenge (drawdown máximo ≤ objetivo de ganancia).
6. **Probabilidad de pase** (simulación por remuestreo de días con las reglas del challenge): ≥ 15 % para una estrategia sola y ≥ 50 % para el portafolio.

Además de lo anterior rige todo lo de siempre: pre-registro, multiplicidad (contador global y alpha-investing), réplica en datos no usados, holdout cerrado, sin P&L ni promoción sin autorización.

## 4. Niveles (tier) que todo resultado debe llevar
- **A — candidata a challenge**: válida estadísticamente **y** cumple todos los criterios de utilidad.
- **B — prometedora**: válida, con forma operable, pero falla algún criterio; se estudia cómo corregirlo o combinarla.
- **C — información**: efecto posible o real sin forma operable aún, o chico/inestable. Sirve de ingrediente o filtro; **nunca se presenta como edge**.
- **D — descartada o artefacto.**

Hoy **no hay ninguna estrategia en nivel A**. La pista de GC (último 30 min) es **C**: significativa pero episódica (un trimestre y días de crash), sin P&L neto ni diversificación evaluados.

## 5. Cómo lo usa el agente
- **Selección de candidatas**: la puntuación se multiplica por un peso de utilidad (`tradeable` 1,0 · `bridgeable` 0,6 · `info` 0,3). Se prefieren estudios que terminan en una regla operable evaluable neta de costos y que agregan **diversificación** (otro activo, otra franja horaria, otra lógica) por sobre el refinamiento de un efecto ya conocido.
- **Interpretación**: todo informe dice el tier. «Pasó Holm» no es éxito; es solo validez estadística.
- **Cuando una pista llega a C sin camino a B**, el agente lo dice y la archiva en vez de gastar más cómputo.
- **Presupuesto**: no se gasta alfa ni cómputo en información pura salvo que sea ingrediente explícito de una estrategia (filtro de régimen, condición de entrada).
- **Honestidad**: no se maquillan resultados chicos ni se eligen ventanas para que pasen; los negativos y los tier C/D se conservan.

## 6. Qué mira el agente primero (prioridades)
1. Pasar pistas válidas a **forma operable con P&L neto** y simular el challenge.
2. **Diversificar**: cada estrategia nueva se mide contra el portafolio aceptado (correlación de P&L diario).
3. Estabilidad antes que tamaño: mejor +2 pb estable en 6 trimestres que +10 pb en uno.
4. Solo después, refinar mecanismos.

## 7. Lo que debe confirmar Nico (el agente no lo decide)
- **Qué producto de Lucid usás** (Flex, Pro, Daily, Black, Direct), el tamaño de cuenta y el **precio** (no está en el centro de ayuda). `config/autopilot/mandate.json` trae LucidFlex 50K extraído por el agente; `config/propfirms/catalogo_lucid_50k.json` trae Flex y Pro, con `verified: false`.
- Los **umbrales** del §3 (propuestos por el agente).
- Si hay límites por instrumento (micros o minis) y por cuenta para el sizing.
Este documento, `mandate.json` y `mandate.py` están en el manifiesto de **archivos protegidos**: el agente no puede cambiar su propio objetivo; si se modifican, el ciclo se detiene hasta que un humano lo revise.
