# Investigación en cuatro iteraciones — repositorios externos y fábrica generativa

**Rama:** `work/repository-research-iterations`  
**Fecha de apertura:** 2026-08-04  
**Secuencia autorizada:** GPT → Opus → Opus → GPT  
**Estado:** Iteración 1 completa; iteraciones 2–4 pendientes.

## Pregunta corregida

La pregunta ya no es simplemente si un repositorio puede “crear indicadores”. Después de los incidentes de EdgeLab, la pregunta defendible es:

> ¿Qué componentes arquitectónicos pueden reutilizarse para proponer, materializar, auditar y descartar indicadores nuevos sin convertir el ciclo `generar → backtest → modificar` en optimización adaptativa sobre outcomes?

## Restricciones heredadas de EdgeLab

1. El LLM no recibe holdout ni outcomes durante generación.
2. Cada candidato nace como especificación estructurada y content-addressed.
3. Measurement, detector, anchor, outcome y execution permanecen separados.
4. Toda familia declara presupuesto de variantes y multiplicidad antes de correr.
5. Los gates outcome-free incluyen causalidad temporal, determinismo, estabilidad numérica, cobertura, costo y redundancia.
6. Un resultado negativo se conserva; no se borra ni se regenera silenciosamente.
7. La memoria de agentes no puede reinyectar retornos realizados en la fase generativa.
8. El motor Python actual sigue siendo la autoridad de recreación hasta que otra implementación pase paridad.
9. Ningún framework externo se adopta completo por prestigio, estrellas o narrativa.
10. El primer producto es una fábrica limitada de variaciones controladas, no un descubridor ilimitado de alpha.

## Corpus

- https://github.com/TauricResearch/TradingAgents
- https://github.com/freqtrade/freqtrade
- https://github.com/mementum/backtrader
- https://github.com/hummingbot/hummingbot
- https://github.com/ccxt/ccxt
- https://github.com/AI4Finance-Foundation/FinRL
- https://github.com/nautechsystems/nautilus_trader
- https://github.com/Polymarket/polymarket-cli

---

# Iteración 1 — GPT: reevaluación después de los hallazgos de EdgeLab

## Método

Se relevaron los README vigentes y se reevaluó cada proyecto contra seis funciones distintas:

1. generación de especificaciones;
2. ejecución determinista;
3. auditoría de sesgos;
4. lifecycle de órdenes;
5. conectividad/datos;
6. aprendizaje adaptativo.

La separación es obligatoria: que un repositorio resuelva una función no lo convierte en autoridad sobre las demás.

## Hallazgo central

> Ninguno de los ocho repositorios debe convertirse en “el cerebro” de la fábrica. La arquitectura correcta es un plano generativo no autoritativo por encima de un plano determinista y auditable de EdgeLab.

```text
LLM proposal roles
→ IndicatorSpec declarativa
→ compiler/validator determinista
→ gates outcome-free
→ deduplicación semántica
→ preregistro y presupuesto familiar
→ ejecución Python congelada
→ evaluación futura separada
→ evidence record inmutable
```

TradingAgents puede inspirar el primer plano. NautilusTrader, Freqtrade y Hummingbot aportan patrones para el segundo. Ninguno reemplaza el contrato científico.

## 1. TradingAgents

### Qué aporta

- grafo de roles especializados;
- debate bullish/bearish y manager final;
- structured outputs;
- checkpoint/resume;
- decision log persistente;
- soporte multi-modelo.

### Qué cambió respecto de la evaluación inicial

El README vigente reconoce explícitamente no determinismo del LLM y datos live variables. También incorpora memoria que recupera retornos realizados y reflexiones de decisiones previas.

Eso es útil para un agente de trading, pero constituye **contaminación por outcomes** si se reutiliza sin cambios en una fábrica de hipótesis. El componente de memoria no puede entrar en la fase de propuesta de indicadores.

### Uso permitido

Adoptar sólo el patrón de roles:

- proposer;
- critic;
- measurement auditor;
- novelty/dedup reviewer;
- preregistration compiler;
- final gatekeeper.

Todos deben intercambiar objetos estructurados. El agente final no aprueba alpha: sólo decide si la especificación es ejecutable y metodológicamente admisible.

### Uso rechazado

- propagar decisiones de trading como objetivo;
- memoria alimentada con retornos;
- noticias/sentiment live;
- debate libre como sustituto de tests;
- aceptar reproducibilidad “aproximada” en el plano determinista.

**Veredicto:** útil como referencia de orquestación; no sirve como motor científico ni generador autónomo de edge.

## 2. Freqtrade

### Qué aporta

- interfaz concreta de estrategias;
- backtesting y persistencia;
- `lookahead-analysis`;
- `recursive-analysis`;
- hyperopt y FreqAI como ejemplos explícitos de búsqueda adaptativa.

### Relectura crítica

Los dos analizadores son más valiosos para EdgeLab que el motor de backtesting. Pueden inspirar gates obligatorios del compilador de indicadores:

- detectar uso de información futura;
- detectar dependencia de warmup/longitud inicial;
- comparar outputs bajo prefijos crecientes;
- declarar unstable tail.

Hyperopt no debe controlar el loop generativo. Es precisamente el patrón que EdgeLab debe contener: muchas variantes evaluadas contra el mismo outcome y selección de la ganadora.

**Veredicto:** prioridad alta para auditorías de look-ahead y recursividad; no para gobernar la búsqueda.

## 3. NautilusTrader

### Qué aporta

- runtime event-driven determinista;
- mismo modelo temporal entre research y live;
- ticks, quotes, bars, order book y custom data;
- indicadores en Python/Rust;
- precision types;
- separación Python control plane / Rust data plane;
- adapters, cache y message bus;
- fuerte disciplina de supply chain y testing.

### Relectura crítica

Es la referencia arquitectónica más cercana al problema real de EdgeLab: evitar que investigación y ejecución interpreten el tiempo de manera diferente. El incidente TICKBAR-001 muestra que “mismo stream” no garantiza “misma atribución”; un runtime con reloj y eventos explícitos es una referencia útil.

Pero adoptar el engine completo ahora introduciría una segunda migración antes de cerrar paridad, universo y EXPLORE-001. Además, Windows ofrece un modo de precisión distinto para los wheels Python, por lo que una comparación debe fijar plataforma y representación numérica.

### Spike permitido

Construir un micro-oráculo aislado:

- una única especificación simple;
- ticks 6E ya limpios;
- mismo orden, timestamps y sesión;
- comparar barras, snapshots y lifecycle contra EdgeLab;
- sin outcomes ni ejecución real.

**Veredicto:** prioridad 1 como referencia de runtime/paridad; adopción total rechazada por ahora.

## 4. Hummingbot

### Qué aporta

- separación entre scripts, controllers y executors;
- executors autocontenidos para lifecycle de órdenes;
- paper trading;
- conectores REST/WebSocket;
- Condor como harness de IA conectado a ejecución determinista;
- CLI scriptable con outputs y exit codes estables.

### Relectura crítica

La distinción controller/executor encaja con una separación que EdgeLab todavía necesita reforzar:

```text
señal/claim predictivo ≠ política de órdenes ≠ lifecycle de ejecución
```

No debe usarse para crear indicadores de 6E. Sí puede inspirar un `ExecutionPolicySpec` separado y una máquina de estados auditable para órdenes, fills, cancelaciones y triple barrier.

**Veredicto:** prioridad alta para lifecycle y frontera IA/ejecución; no para generación de indicadores.

## 5. Backtrader

### Qué aporta

- composición simple de indicators/lines;
- resampling/replay;
- custom indicators;
- broker simulation y analyzers.

### Relectura crítica

Es una referencia histórica útil para ergonomía de una DSL pequeña. No es una base adecuada para la autoridad científica actual: su arquitectura y ecosistema son anteriores a muchos controles que EdgeLab necesita. Modos como cheat-on-open/close demuestran que el motor debe hacer visible la semántica temporal en la especificación, no esconderla en flags.

**Veredicto:** estudiar la ergonomía de composición; no adoptar el runtime.

## 6. CCXT

### Qué aporta

- normalización REST/WebSocket;
- modelo común de exchanges;
- errores y rate limiting;
- amplio soporte multi-lenguaje.

### Relectura crítica

CCXT es un adaptador. No genera indicadores, no valida hipótesis y no resuelve ejecución histórica. Integrarlo al núcleo de EdgeLab mezclaría venue connectivity con measurement. Para 6E/CME no es el camino principal.

**Veredicto:** sólo boundary adapter para futuras campañas crypto/prediction markets.

## 7. FinRL

### Qué aporta

- separación environment/agent/application;
- pipeline train-test-trade;
- Gym-style environments;
- múltiples algoritmos y benchmarks.

### Relectura crítica

El repositorio clásico se declara educativo y dirige producción hacia FinRL-X. El loop RL maximiza reward mediante interacción repetida: es el extremo opuesto a una primera fábrica científica con presupuesto de variantes y outcomes cerrados.

Su aporte relevante es el contrato explícito de environment y la necesidad de separar estado, acción, reward y transición. El agente adaptativo queda fuera hasta tener simulator fidelity, execution policy y evaluación nested/holdout.

**Veredicto:** laboratorio posterior de políticas; no usar en la etapa generativa.

## 8. Polymarket CLI

### Qué aporta

- JSON estable para scripts/agentes;
- errores estructurados y exit codes;
- operaciones read-only separadas de firmas/wallet;
- comandos explícitos para CLOB y posiciones.

### Relectura crítica

Es experimental y pertenece a otro venue. No aporta creación de indicadores. Sí aporta un patrón de seguridad: lectura sin credenciales, escritura autenticada y contratos CLI que un agente puede invocar sin parsear UI.

**Veredicto:** referencia para una futura CLI de EdgeLab, no para el motor de investigación.

## Ranking corregido por componente

1. **NautilusTrader:** runtime determinista, reloj, eventos y micro-oráculo.
2. **Freqtrade:** gates de look-ahead y recursividad.
3. **Hummingbot:** controllers/executors y lifecycle de órdenes.
4. **TradingAgents:** orquestación de roles, sólo detrás de firewall outcome-free.
5. **Backtrader:** ergonomía/composición de indicadores.
6. **FinRL:** contratos de environment y políticas, mucho más adelante.
7. **CCXT:** conectividad aislada.
8. **Polymarket CLI:** interfaz scriptable y separación read/write.

El ranking no mide calidad general. Mide utilidad para el cuello de botella actual de EdgeLab.

## Arquitectura provisional resultante

### Plano A — Propuesta no autoritativa

- LLM proposer produce `IndicatorSpec`.
- critic busca equivalencias, grados de libertad y narrativa causal excesiva.
- measurement auditor exige inputs observables y error model.
- novelty reviewer compara árbol/AST normalizado contra catálogo.
- preregistration compiler asigna familia, presupuesto y muerte.

### Plano B — Autoridad determinista

- schema validation;
- compilación a funciones permitidas;
- causal/prefix test;
- recursive/warmup test;
- determinism replay;
- complexity budget;
- missing-data behavior;
- cost estimate;
- event-time and available-time audit;
- content hash;
- ejecución bajo commit/entorno/dataset manifest.

### Plano C — Evaluación separada

- censo outcome-free;
- selección/freeze de hipótesis;
- apertura de outcome autorizada;
- multiplicidad de toda la familia;
- ejecución y costos en objetos separados;
- claim/evidence/invalidation persistentes.

## Primer spike recomendado

No construir agentes todavía. Construir primero una `IndicatorSpec v0` capaz de expresar sólo:

- inputs permitidos;
- transformaciones causales;
- ventana/lookback;
- warmup;
- estado incremental;
- condición de emisión;
- dirección opcional;
- abstención;
- metadata de medición;
- complejidad;
- familia y parent spec.

Usar tres familias deliberadamente simples:

1. transformaciones de rango/volatilidad;
2. intensidad/imbalance observable sin etiquetas mecanísticas;
3. geometría y velocidad de aproximación.

El spike termina si no puede demostrar determinismo, causalidad por prefijo y deduplicación semántica. No se miran outcomes.

## Hipótesis falsables para las iteraciones siguientes

### R1
Una DSL pequeña puede representar la mayoría de variaciones útiles sin permitir código arbitrario.

**Muerte:** más de 30% de los candidatos legítimos requieren escapes Python no auditables.

### R2
Separar proposer LLM de compiler determinista reduce errores sin reducir excesivamente diversidad.

**Muerte:** el compiler rechaza >80% por defectos triviales o admite violaciones conocidas.

### R3
AST/canonical form detecta duplicados que nombres y descripciones no detectan.

**Muerte:** equivalencias algebraicas simples siguen produciendo identidades distintas.

### R4
Gates inspirados en Freqtrade detectan causalidad futura y recursividad inestable antes de outcomes.

**Muerte:** la batería de spike-in atraviesa los gates.

### R5
Un micro-oráculo Nautilus puede reproducir una especificación elemental de EdgeLab sin divergencia temporal.

**Muerte:** no puede fijarse una semántica común de eventos/timestamps/sesión sin adaptar el indicador.

## Handoff — Iteración 2 (Opus)

Opus debe intentar refutar esta arquitectura, no expandirla narrativamente.

Tareas:

1. inspeccionar código, no sólo README, de TradingAgents graph/checkpoint/memory;
2. inspeccionar implementación y límites de `lookahead-analysis` y `recursive-analysis` en Freqtrade;
3. inspeccionar indicator lifecycle y clock/event ordering de NautilusTrader;
4. inspeccionar controller/executor boundaries de Hummingbot/Condor;
5. buscar modos de falla donde la DSL parezca causal pero use futuro indirecto;
6. proponer una matriz de ataques y criterios de muerte;
7. no mirar outcomes de EdgeLab;
8. registrar commit, paths y conclusiones negativas.

Salida requerida: sección “Iteración 2 — Opus” en este archivo y reconciliación en Notion.

## Handoff — Iteración 3 (Opus)

Tomar la crítica de Iteración 2 y diseñar el contrato mínimo ejecutable:

- `IndicatorSpec v0`;
- canonical AST;
- capability sandbox;
- gates y spike-ins;
- manifests;
- separación proposal/evaluation;
- plan de implementación limitado.

No implementar el loop adaptativo ni abrir outcomes.

## Handoff — Iteración 4 (GPT)

Auditar las cuatro iteraciones y decidir:

- qué se afirma;
- qué se rechaza;
- qué queda abierto;
- qué spike se autoriza;
- qué dependencias externas no se adoptan;
- qué criterios matan la fábrica.

La síntesis final debe ser más corta que las iteraciones y no ocultar desacuerdos.
