# aVolClusterPOI + BigTrap — modelo científico de dos etapas V1-R1 (borrador fail-closed)

- **Estado:** `DRAFT_PREAUTHORIZATION_FAIL_CLOSED`
- **Instrumento:** GC
- **Detector candidato:** aVolClusterPOI 60t, p98, no p95
- **Outcomes:** cerrados
- **Holdout 2026-07-01→2026-12-31:** sellado
- **P&L / edge / promoción:** fuera de alcance

## 1. Qué conserva y qué corrige de la intuición

La intuición útil es separar dos preguntas:

```text
aVolClusterPOI: ¿DÓNDE cambia la distribución de movimiento?
Microestructura: ¿HACIA DÓNDE, si existe información direccional causal?
```

Pero deben retirarse dos afirmaciones fuertes:

- un cluster anómalo no prueba que “una institución colocó un bloque”; sólo observa concentración de volumen fuera de lo habitual para ese horario;
- el precio no “debe” expandir. La hipótesis falsable es que la distribución de expansión futura se desplaza respecto de controles comparables.

Además, el detector vigente usa percentil empírico **98**, no 95. El lenguaje “resorte comprimido” sólo queda permitido si se demuestra una firma de compresión previa; un rango posterior grande, por sí solo, demuestra expansión condicional, no compresión.

## 2. Estado real del instrumento

Lo ya medido es target-free:

- 60t ganó frente a 1m/3m/5m/185t/305t en autocorrelación y homocedasticidad;
- real/placebo de estructura fue aproximadamente 55×;
- la meseta estricta declarada falló;
- la paridad 60t es parcial: 123/180 = 68,3%;
- el lifecycle Python aún no reproduce de forma canónica FIRST_TOUCH/INVALIDATED;
- el extractor de 1.544 eventos sobre cinco contratos es prototipo, no Event Store confirmatorio.

Por eso este documento profundiza y preregistra, pero **no autoriza ejecutar H1/H2**.

## 3. DAG temporal y unidad de análisis

```text
historia previa -> zona creada Z -> primer toque T -> features as-of M -> trayectoria futura Y
```

- Z debe crearse y quedar disponible antes de T.
- La barra creadora nunca puede ser el toque.
- M sólo usa información publicada hasta el cierre de la barra M1 del toque.
- Y empieza después de la decisión; la futura ejecución debe anclarse al primer tick canónico estrictamente posterior.
- Unidad: primer toque OFF_PRICE, máximo uno por zona.
- Zonas que tocan en la misma barra/contrato se colapsan con una regla determinista antes de ver Y.

## 4. Etapa 1 — Localización: expansión no direccional

Pregunta:

> ¿Un primer toque causal de una zona aVol 60t precede más expansión no direccional que momentos comparables sin toque?

Primario H=30 M1:

```text
Range30 = max(high[t+1:t+30]) - min(low[t+1:t+30])
Scale30 = mediana del true range M1 de t-30 a t-1
Y30     = log1p(Range30 / max(Scale30, 1 tick))
D_i     = Y30_touch - mean(Y30_control_1..20)
```

Controles N_RAND:

- hasta 20 por evento;
- mismo contrato y bucket de 30 minutos;
- otra sesión CME;
- volatilidad previa comparable;
- ventana completa;
- sin toque aVol dentro de un blackout de 60 barras;
- muestreo determinista sin reemplazo;
- mínimo cinco controles y match rate mínimo 80%.

Inferencia: igual peso por sesión CME, Wild Cluster Bootstrap Rademacher, 9.999 réplicas. H={5,15,60} es secundario con Holm y nunca rescata H=30.

### La parte que falta para poder decir “compresión”

Debe congelarse antes de outcomes un estimando previo, por ejemplo:

```text
Compression_i = rango/velocidad de los últimos 5 minutos antes del toque
                dividido por el de los 25 minutos anteriores
```

comparado con los mismos controles. Si H1 expansión pasa pero esta firma no, la conclusión permitida es “localización de expansión”, no “resorte comprimido”.

## 5. Etapa 2 — Dirección: microestructura causal

Pregunta:

> Condicionado a un primer toque elegible, ¿las features disponibles al cierre predicen el signo del primer pasaje mejor que un nulo simétrico y un shuffle temporal?

### 5.1 Delta de absorción

`Delta <= -2` sólo es interpretable si significa un **z-score causal**, no dos contratos crudos. Regla simétrica propuesta:

- `delta_z <= -2`, penetración y desplazamiento neto bajista no mayor a 1 tick → LONG;
- `delta_z >= +2`, penetración y desplazamiento neto alcista no mayor a 1 tick → SHORT.

La fórmula de `delta_z`, el historial y el timestamp de disponibilidad deben quedar congelados y testeados.

### 5.2 BigTrap como evidencia direccional

BigTrap debe separarse en capas:

1. **selección temporal/geométrica**: dónde/cuándo aparece el evento;
2. **dirección**: `trapped_buyers -> SHORT`, `trapped_sellers -> LONG` usando el campo `dir`, nunca color o nombre ambiguo;
3. **mecanismo P2-A**: ya mostró asimetría diagnóstica en tres celdas Holm-positivas, sin P&L;
4. **diagnóstico económico P2-B**: si algún día se autoriza, sólo evalúa una política standalone acotada;
5. **rol condicional aVol**: un voto contemporáneo dentro de una localización definida por otra familia.

Un resultado standalone negativo no refutaría su uso contextual; uno positivo no probaría una estrategia completa.

### 5.3 No contar dos veces el mismo flujo

Delta, BigTrap2 y BigTrap2Absorption comparten tape, agresor y geometría de desplazamiento. No son tres sensores independientes. Para el primario:

- `BT2` y `BT2A` se deduplican en un único voto TRAP;
- conflicto BT2 vs BT2A = voto TRAP nulo;
- Delta + TRAP forman una familia FLOW y cuentan como máximo una familia;
- VWAP/Value Area as-of forma CONTEXT;
- mientras no exista un tercer sensor independiente preregistrado, el compuesto primario exige FLOW y CONTEXT presentes y concordantes.

La regla raw “2 de 3” se conserva sólo como análisis exploratorio con multiplicidad y ablaciones; no puede sostener lenguaje de confirmación independiente.

### 5.4 Contexto simétrico y as-of

- debajo de VAL y VWAP → LONG;
- encima de VAH y VWAP → SHORT;
- dentro de value o señales mixtas → abstención.

VWAP/VA deben ser expanding/as-of o provenir de la sesión completa anterior. Usar VAH/VAL finales de la sesión del toque sería look-ahead.

### 5.5 First Passage

- decisión al cierre M1 del toque;
- ancla ejecutable futura: primer tick canónico estrictamente posterior;
- barrera simétrica causal `B=max(1, ceil(pre_touch_vol_ticks))` en el borrador;
- horizonte H=30 M1;
- target favorable primero = +1, adverso primero = -1;
- ambos dentro de la misma barra M1 = 0 ambiguo;
- ninguno = 0 censurado.

La inversión Mirror sobre el mismo path es una identidad algebraica útil para verificar signos, no un nulo independiente. La evidencia inferencial debe venir del shuffle preregistrado de direcciones dentro de contrato×sesión y del bootstrap clusterizado.

## 6. Abstención y denominadores

Cada primer toque elegible debe persistirse aunque no dispare:

- FLOW ausente;
- CONTEXT ausente;
- conflicto;
- ventana incompleta;
- feature no as-of;
- barrera inválida;
- sin controles suficientes.

Se reportan población total, elegible, activada, abstenciones por causa, balance LONG/SHORT, sesiones y cobertura. Nunca se calcula precisión sólo sobre supervivientes sin mostrar el embudo.

## 7. Clasificación conjunta

| H1 expansión | H2 dirección | etiqueta permitida |
|---|---|---|
| no | no | `NO_TWO_STAGE_SUPPORT` |
| sí | no | `LOCALIZATION_EXPANSION_ONLY` |
| no | sí | `DIRECTION_WITHOUT_SPRING_SUPPORT` |
| sí | sí | `TWO_STAGE_MECHANISM_SUPPORTED` |

Ninguna etiqueta significa edge neto. Costos sólo corresponden después de congelar una política ejecutable completa.

## 8. Bloqueos antes de congelar R1

1. resolver o acotar formalmente paridad 60t y lifecycle;
2. construir Event Store aVol canónico y ligar hashes/sesiones;
3. decidir el uso de split C sin reoptimizar;
4. congelar fórmula de delta_z y Value Area as-of;
5. implementar deduplicación BT2/BT2A y familia FLOW;
6. corregir el shuffle para excluir sesiones no permutables tanto del observado como del nulo;
7. congelar la firma pre-touch requerida para usar “compresión”;
8. ejecutar red-team del contrato y recién después emitir hash y token de autorización.

Token futuro reservado, no consumido:

```text
AUTHORIZE_AVOL_BT2_TWO_STAGE_PATH_DIAGNOSTIC_V1_R1
```

## 9. Firewalls actuales

```text
SPEC_STATUS=DRAFT_PREAUTHORIZATION_FAIL_CLOSED
FUTURE_PRICE_PATH_ACCESSED=false
PNL_ACCESSED=false
HOLDOUT_TOUCHED=false
WINNER_SELECTED=false
EDGE_DECLARED=false
PROMOTION_ELIGIBLE=false
```
