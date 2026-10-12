# Mandato de EdgeLab: qué edges importan

**Leer antes de proponer, lanzar o interpretar cualquier corrida. Aplica a todo agente, también al autopilot que corre en el Debian.**

## 1. El objetivo
**Ganar más de lo que se invierte en challenges de cuentas fondeadas, en cualquier firma.** No hay una firma fija: el agente busca la cuenta que mejor le calza a cada estrategia (o toma los umbrales de las cuentas y diseña estrategias para superarlos), y lo hace **combinando varias estrategias poco correlacionadas**. Se maximiza el valor esperado neto de cuotas, resets y comisiones por dólar invertido (ROI), con límite inferior del IC > 0 y aporte > 0 sobre el control sin ventaja.

Un efecto estadísticamente significativo **no cumple el objetivo por serlo**. No sirven los edges que sean:
- **chicos**: que no superan el umbral de ninguna cuenta con margen, ya con costos reales (comisión, spread, deslizamiento);
- **inestables**: que dependen de un trimestre, de pocos días extremos o de un régimen que no se repite;
- **sin margen para diversificar**: que no se pueden combinar con otras estrategias (misma señal, mismo horario, mismo activo, alta correlación de P&L).

## 1b. Cuentas, umbrales y universo de corridas (se diseña desde los umbrales)
- **Catálogo de cuentas** (`config/propfirms/`, módulo `edgelab/propfirm/`): Lucid, Apex, Topstep, Tradeify, MyFundedFutures, etc.; cada entrada declara fuente, fecha y si fue verificada por una persona. Las reglas cambian: `tools/propfirm_refresh.py` avisa de cambios (hoy cubre Lucid; ver [`docs/research/PROPFIRM_LUCID_REFERENCIAS_20261013.md`](docs/research/PROPFIRM_LUCID_REFERENCIAS_20261013.md)).
- **Umbral de una cuenta**: para una operación de desvío σ (USD con el tamaño) y costo relativo (costo/σ), la correlación mínima **ρ\*** que debe tener una señal con el retorno siguiente para que la cuenta deje EV ≥ 0, cuota incluida (`docs/research/propfirm_thresholds/THRESHOLDS.md`). Sin cuota verificada no hay umbral válido: el EV de una cuenta gratis es trivialmente positivo.
- **Universo de corridas**: antes de proponer una corrida se pregunta *¿hay alguna cuenta cuyo umbral pueda superar un efecto plausible en esa celda (instrumento × franja × horizonte)?* El mapa `docs/research/propfirm_thresholds/UNIVERSO.md` ordena las celdas por ρ\* mínimo eligiendo tamaño y cuenta. Los efectos intradía reales de las muestras propias rondan |ρ| ≲ 0,12 y los grandes fueron episódicos: las celdas con ρ\* por encima de eso son poco plausibles.
- **Camino inverso**: dada una estrategia (σ y z bruto por operación), `tools/propfirm_match.py` ordena las cuentas del catálogo por EV y aporte.
- Reglas de conducta que cambian el diseño (ejemplo Lucid; cada firma tiene las suyas): sin límite de tiempo en la evaluación (decide P(objetivo antes del piso)); consistencia del 40-60 % (el mayor día ≤ esa fracción del beneficio) que castiga los edges de pocos días grandes; intradía estricto (cierre antes de 15:45 CT); prohibido HFT, microscalping y **cobertura entre cuentas** (dos estrategias en cuentas distintas no pueden estar en lados opuestos del mismo instrumento a la vez); 10 cuentas de evaluación y 5 fondeadas.
- Un participante **sin ventaja** pasa poco y paga la cuota: toda estrategia se compara contra ese control (techo geométrico L/(T+L) = 40 %; con costos reales y 1 contrato ≈ 3,5 % con brackets de USD 100 y ≈ 0 con brackets chicos).

## 2. Por qué
Un challenge impone reglas duras (objetivo de ganancia, drawdown máximo que suele ser de tipo *trailing*, a veces límite de pérdida diaria, días mínimos y tiempo máximo, a veces consistencia). Una estrategia sola, con rachas y drawdown, rara vez los supera de forma confiable; **varias estrategias pequeñas, estables y poco correlacionadas suavizan la curva y aumentan la probabilidad de pase**. Lo que importa es la **probabilidad de pasar y de sostener la cuenta**, no el p-valor de un efecto.

## 3. Criterios de utilidad (se evalúan con P&L NETO de costos)
Definidos en `config/autopilot/mandate.json` (valores propuestos; ver §7) e implementados en `edgelab/autopilot/mandate.py`:
1. **Neto positivo y resistente a costos** (sigue positivo con costos × 1,5).
2. **Compatibilidad con las reglas de la cuenta elegida**: intradía (p. ej. cierre antes de 15:45 CT), sin HFT/microscalping, consistencia (el mayor día ≤ 40-60 % del beneficio), sin posiciones opuestas a otras estrategias de la cartera.
2b. **Frecuencia** suficiente (≥ 10 operaciones/mes) para llegar al objetivo en el plazo.
3. **Estabilidad temporal**: ≥ 4 trimestres observados y ≥ 70 % de ellos positivos; no depende de los 5 mejores días (≤ 50 % del P&L); no depende de un solo trimestre (siempre mirar «sin el mejor trimestre»).
4. **Diversificación**: correlación absoluta del P&L diario ≤ 0,30 con las estrategias ya aceptadas; meta de ≥ 3 estrategias independientes.
5. **Drawdown compatible** con el límite del challenge (drawdown máximo ≤ objetivo de ganancia).
6. **Probabilidad de pase y ROI** (simulación por remuestreo de días con las reglas de la cuenta elegida; cuenta de referencia en `mandate.json`): ≥ 15 % para una estrategia sola y ≥ 50 % para el portafolio.

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
0. **Diseñar el universo desde los umbrales**: priorizar celdas donde el ρ\* requerido sea plausible.
1. Pasar pistas válidas a **forma operable con P&L neto** y simular el challenge.
2. **Diversificar**: cada estrategia nueva se mide contra el portafolio aceptado (correlación de P&L diario).
3. Estabilidad antes que tamaño: mejor +2 pb estable en 6 trimestres que +10 pb en uno.
4. Solo después, refinar mecanismos.

## 7. Lo que debe confirmar Nico (el agente no lo decide)
- **Cuotas, resets y reglas reales** de las cuentas del catálogo (hoy `verified: false`): sin cuotas verificadas el ROI y los umbrales son orientativos. El agente no decide cuál firma usar; propone la de mejor ajuste y vos confirmás.
- Los **umbrales** del §3 (propuestos por el agente).
- Si hay límites por instrumento (micros o minis) y por cuenta para el sizing.
Este documento, `mandate.json` y `mandate.py` están en el manifiesto de **archivos protegidos**: el agente no puede cambiar su propio objetivo; si se modifican, el ciclo se detiene hasta que un humano lo revise.
