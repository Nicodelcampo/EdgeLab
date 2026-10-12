# Mandato de EdgeLab: qué edges importan

**Leer antes de proponer, lanzar o interpretar cualquier corrida. Aplica a todo agente, también al autopilot que corre en el Debian.**

## 1. El objetivo
Encontrar estrategias **intradía de futuros que sirvan para superar challenges de cuentas fondeadas y para operar esas cuentas**, y hacerlo **combinando varias estrategias poco correlacionadas**.

Un efecto estadísticamente significativo **no cumple el objetivo por serlo**. No sirven los edges que sean:
- **chicos**: que no sobreviven a los costos reales (comisión, spread, deslizamiento) con margen;
- **inestables**: que dependen de un trimestre, de pocos días extremos o de un régimen que no se repite;
- **sin margen para diversificar**: que no se pueden combinar con otras estrategias (misma señal, mismo horario, mismo activo, alta correlación de P&L).

## 2. Por qué
Un challenge impone reglas duras (objetivo de ganancia, drawdown máximo que suele ser de tipo *trailing*, a veces límite de pérdida diaria, días mínimos y tiempo máximo, a veces consistencia). Una estrategia sola, con rachas y drawdown, rara vez los supera de forma confiable; **varias estrategias pequeñas, estables y poco correlacionadas suavizan la curva y aumentan la probabilidad de pase**. Lo que importa es la **probabilidad de pasar y de sostener la cuenta**, no el p-valor de un efecto.

## 3. Criterios de utilidad (se evalúan con P&L NETO de costos)
Definidos en `config/autopilot/mandate.json` (valores propuestos; ver §7) e implementados en `edgelab/autopilot/mandate.py`:
1. **Neto positivo y resistente a costos** (sigue positivo con costos × 1,5).
2. **Frecuencia** suficiente (≥ 10 operaciones/mes) para llegar al objetivo en el plazo.
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
- Las **reglas reales del challenge** (firma, tamaño de cuenta, objetivo, drawdown y tipo, límite diario, días mínimos/máximos, consistencia, contratos máximos, horarios obligatorios de cierre). `config/autopilot/mandate.json` trae valores de EJEMPLO.
- Los **umbrales** del §3 (propuestos por el agente).
- Si hay límites por instrumento (micros o minis) y por cuenta para el sizing.
Este documento, `mandate.json` y `mandate.py` están en el manifiesto de **archivos protegidos**: el agente no puede cambiar su propio objetivo; si se modifican, el ciclo se detiene hasta que un humano lo revise.
