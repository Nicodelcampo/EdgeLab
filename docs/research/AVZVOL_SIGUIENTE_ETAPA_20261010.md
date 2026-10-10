# AVZVOL — siguiente etapa: información incremental antes de P&L

**Estado: diseño y código sintético; ejecución de mercado BLOQUEADA.**
El pedido «Dale con todo» autoriza avanzar con esta preparación. No subsana
lineage/calidad ni convierte un diseño incompleto en autorización de datos.
[Diseño legible por agentes](../../specs/research/avzvol_incremental_design_v1.json).

## Pregunta y alcance

¿El racimo aporta información sobre compresión posterior respecto de una
consolidación SIN racimo comparable en geometría, ocupación y actividad previa?
La ruta es: **custodia → comparación válida → duración/reloj → réplica → utilidad
operativa**. No se busca una celda ganadora ni se implementa ccbus/autonomía.

### Qué ya sabemos y qué no

El [informe publicado](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/docs/research/AVZP2_RACIMO_GRILLA_VOL_RESULTADOS_20261009.md)
reporta O5 controlado negativo en las 23 celdas evaluables. Debilita una rival,
no demuestra causalidad ni rentabilidad. Los contratos de confirmación ya fueron
vistos; una corrección es revisión de desarrollo, no nueva confirmación ciega.
La [auditoría técnica](../infra/AVZVOL_AUDIT_20261010.md) reprodujo el baseline
publicado sin control, NO volvió a validar todos los efectos controlados.
Halló bins sensibles al orden, pesos/pares no reconstruibles y raw lineage pendiente.
O5 es un ratio de rangos en barras de 25 ticks: no volatilidad genérica a tiempo fijo.

## A. Procedencia y revisión del método, antes de outcomes nuevos

Cerrar por cada archivo MNQ realmente consumido: dataset/version/file/SHA,
resolver, code bundle, calendario completo, continuidad, reloj independiente,
selección de contratos líquidos y transformación de quotes/sentinelas.
No inferir consumo desde attachments ni aplicar automáticamente fallos de ES/NQ a MNQ.

Avance documental: [recuperación de candidatos de procedencia](../infra/AVZVOL_LINEAGE_RECOVERY_20261010.md).
Los artefactos recuperados son coherentes, pero no prueban el montaje histórico.
`reviewed_input_pins` permanece vacío y la revisión incluye los 45 días de warmup.

Conservar el original. La revisión tiene identidad de método nueva y debe explicar
cada diferencia: bins por cutpoints externos congelados (`assign_frozen_bins`),
referencia baseline obligatoria, pares, reutilización y pesos. No completar pseudo
faltantes ni deduplicarlos retrospectivamente. No se ejecuta esta revisión con
precios en este lote; sólo fixtures sintéticos.

## B. Comparación incremental con control sin racimo

**Roster antes de outcomes:** censo completo declarado de racimos y consolidaciones
candidatas sin racimo. La regla de enumeración/selección debe congelarse; «no está en
el censo de racimos» no prueba por sí solo ausencia de racimo. La clasificación debe
provenir del detector causal revisado, no del resultado futuro.

- Mismos contrato natural, sesión, celda, franja y signo de tendencia.
- Calipers y escalas externos: ocupación, amplitud, magnitud de tendencia,
  momentum, volumen y duración de ventanas 500/100 previas (incluido t0 conforme
  definición original). Nada aprendido de futuros outcomes ni de confirmación.
- No usar el conocimiento de si sale/rebota para construir el candidato.
- Match por suma de distancias absolutas en escalas congeladas; empate por ID.
  Esta distancia es una propuesta de diseño, no un método ya validado.
- Mínimo/máximo de controles explícitos. Sin soporte: registrar evento y motivo;
  no ampliar calipers ni relajar mínimos para lograr un resultado.
- Un contraste por real soportado; peso igual de cada real, promedio de sus
  controles. Reutilización entre reales permitida y declarada, no independencia.
- IDs por par ligados al digest de política y de las declaraciones de ambos censos
  (hash autoconsistente, no prueba de verdad/calidad upstream). No duplicar controles dentro del set.
- Diagnosticar soporte por estrato, distribuciones/balance y sensibilidad de
  población, antes de calcular contraste. El helper sólo devuelve gap medio en
  unidades de escala; NO calcula SMD, no examina colas y no acepta balance.
- Medir controles contra su propio censo para detectar sesgo de selección.
  Ese segundo contraste todavía NO está implementado; exige endpoints/budget.

Inferencia futura debe respetar sesión, reutilización, solapamiento y dependencias
entre celdas. La muestra de filas evento×celda no es N independiente. Mantener
las 23 celdas previas como paisaje de desarrollo, no 23 réplicas independientes.
El universo formal, potencia, efecto mínimo útil y corrección conjunta se congelan
antes de la nueva ejecución; el helper no calcula p, IC, MDE ni P&L.

## C. Duración, tiempo físico y selección por salida

Conservar O5 original como endpoint de revisión: rango de 200 barras posteriores
a la salida dividido por rango de 200 barras ANTERIORES A LA PRIMERA ZONA del
racimo, no anteriores a t0. La ventana pasada queda fuera del evento. No reemplazar
ese denominador ni elegir el endpoint que salga mejor. Agregar, con protocolo aprobado, horizontes físicos y curva acotada para
separar menor recorrido de distinta velocidad de negociación. No dar por constante
el tiempo ni el volumen de una barra de 25 transacciones.

O5 es condicional a una salida y horizonte posterior observables. Enumerar también
sin salida, sin horizonte completo y cierres de sesión; no seleccionar silenciosamente
sólo casos completos. Publicar la población condicional y límites. No imputar
outcomes ni cruzar sesiones para rellenar. La regla exacta de censura aún está pendiente.
Menor rango medio no prueba menores colas ni reversión operable; diagnósticos de
colas y comparabilidad deben estar en el presupuesto antes de mirarlos.

## D. Réplica nueva, sólo con fuentes certificadas

Identificar exposición histórica por dataset/ventana/endpoint. Fechas no usadas en
esta campaña no son automáticamente vírgenes en todo EdgeLab. No abrir holdout
ni cambiar su inicio por documentos más recientes. Una futura prueba NQ con MNQ
no son dos mercados independientes (comparten subyacente). ES sería transferencia
a otro subyacente, no confirmación automática; ES/NQ actuales siguen bloqueados.
No seleccionar la celda de réplica por el mejor resultado histórico.

## E. Un uso económico, después de B–D

Primero evaluar si la variable mejora información/predicción frente al benchmark
fuera de muestra. Sólo después: una regla existente congelada, con/sin contexto,
misma población/intents y costos/quotes/latencia revisados. Evitar diseñar a la vez
entrada, salida, stop y objetivo. No se implementa ningún replay económico aquí.
Si el match explica O5, archivar atribución al racimo; actividad/consolidación queda
como explicación candidata, no como edge validado por descarte. No detectar
un efecto no prueba ausencia: exigir precisión respecto del efecto mínimo útil
y declarar insuficiencia de potencia cuando corresponda.

## Literatura y memoria que motivan, no certifican

- [Lección BigTrap2](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/artifacts/hippocampus/research_history_ledger.jsonl):
  exigir control sin zona con geometría equivalente. Registrada PROPOSED/LOW.
- [Lección selección del control](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/artifacts/hippocampus/ipc_20260926.jsonl):
  comprobar el control en su propio censo; PROPOSED/LOW, no axioma certificado.
- Duong, Fang, Kalev, [Order Imbalance, Order Book Slope and the Volume-Volatility
  Relation](https://ssrn.com/abstract=1716874): separar número de trades/tamaño;
  futuros ASX, no prueba transferida a MNQ.
- Muravyev/Picard, [Does Trade Clustering Reduce Trading Costs?](https://ssrn.com/abstract=2496669):
  periodicidades en acciones no autorizan asumir mejora de liquidez/costos en MNQ.
- Malyshkin/Bakhramov, [Market Dynamics vs. Statistics](https://ssrn.com/abstract=2748679):
  discusión de excitación/relajación y ambigüedad soporte/atractor; profundidad de
  libro NASDAQ no equivale a nuestros racimos de volumen ejecutado.

No incorporar mecánicamente claims extraídos por LLM. Se observó incluso un nombre
de archivo que no coincide con el título del texto (`0063`); verificar identidad,
mercado, datos y pasaje antes de usar una referencia. No se audita todo SSRN aquí.

## Qué corre hoy sin token ni mercado

Con el wheel del lote instalado conforme a [ENVIRONMENT](../ENVIRONMENT.md):

```bash
python tools/avzvol_design_smoke.py
python tools/avzvol_design_smoke.py --purpose research
python -m pytest -q tests/test_avzvol_design.py
```

El primero usa sólo datos inventados y umbrales de fixture, NO parámetros de mercado.
El segundo devuelve STOP (exit 2) antes de cargar incluso el fixture. No acepta
archivos externos, genera kernels ni descarga/abre mounts. El API puro acepta
covariables declaradas, no autentica fechas/pins/calidad ni autoriza construirlas.
Su comprobación de fechas es conservadora, no un firewall de sesiones CME.

Resultado del helper: `DESIGN_ONLY_UNADJUDICATED`; calidad, aprobación, balance,
censo completo, inferencia y sesgo siguen falsos/no verificados. Población:
**reales soportados**, nunca todos los reales por omisión. IDs de todo el censo
suministrado quedan enumerados, incluso si no fueron seleccionados.

[Propuesta de episodio](../../config/research/avzvol_design_episode_20261010.json):
PROPOSED/LOW, **no ingresada al ledger**. No modificar memoria histórica para
promover una hipótesis. La integración futura exige episodio autenticado y artefactos.

## Condiciones para pasar a mercado

El JSON mantiene `null` en pins, política/calipers, aceptación de soporte/balance,
horizontes, censura, presupuesto y autoridad. Son bloqueos, no defaults implícitos.
Se debe aprobar y fijar una spec ejecutable nueva con evidencia independiente.
Este diseño NO implementa un runner ni garantiza bloqueo de scripts legacy.
