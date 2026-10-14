# BigTrap2 multiframe ML — tickframes, absorción y Kaggle

**Fecha:** 2026-08-11  
**Estado:** plan registrado; no ejecutado; protocolo todavía no congelado  
**Rama:** `research/bigtrap2-multiframe-ml`  
**Base:** `fix/bigtrap2-v252-tick-export@6a858fdc31e1a65bb504c18e74be77d1ed1d78c1`

## Separación de campañas

Esta familia es independiente de PR #11 (`research/bigtrap2-distance-matched-null`). PR #11 conserva su diseño confirmatorio `time:1`, sin barrido de `tick:N`, sin combinaciones multiframe y sin cambios post hoc. La nueva rama no hereda resultados de PR #11 ni los presenta como evidencia de invariancia entre resoluciones.

También queda apilada sobre el fix instrumental v2.5.2 de PR #12 para poder exigir paridad representativa NT8↔Python en barras tick antes de promover resoluciones seleccionadas.

## Pregunta de investigación

Dada toda la información disponible causalmente al cierre de una ventana, ¿las absorciones simultáneas o cercanas detectadas por diferentes tickframes aportan información incremental y estable respecto del mejor tickframe individual?

Ejemplo motivador, no regla preseleccionada: si dentro de una ventana de 60 segundos dos resoluciones `tick:K` detectan absorción compatible en dirección, precio y tiempo, esa confluencia podría tener más fuerza predictiva que una sola detección.

La campaña debe permitir que modelos regulares e interpretables descubran interacciones, pero no puede seleccionar el máximo in-sample ni probar miles de reglas sin corrección de multiplicidad.

## Infraestructura ya disponible

EdgeLab ya permite:

- reconstruir `tick:N` para cualquier `N >= 1` con reinicio por sesión;
- preservar orden por `sequence` y timestamp del último tick;
- construir footprints;
- ejecutar BigTrap2 sobre barras `time` o `tick`;
- incluir `bar_key` en la identidad;
- sobrescribir `bars` por param set;
- cachear barras, footprints y P1A por `bar_spec` dentro de una ejecución;
- probar `tick:5` y `tick:25`.

La limitación a M1 fue metodológica, no una limitación del reconstructor.

## Arquitectura objetivo

```text
ticks canónicos
→ clasificación agresora una sola vez
→ construcción/caché por cada K y sesión
→ eventos y zonas persistidos por K
→ dataset largo auditable
→ ventanas multiframe causales
→ modelos e inferencia con corrección de multiplicidad
```

Costo esperado:

```text
builder: O(R·N)
combinaciones: O(C·Z)
total correcto: O(R·N) + O(C·Z)
```

No se reconstruyen ticks para cada pareja o trío.

## Definición causal mínima

Para una ventana retrospectiva `[t-60s, t]`, sólo puede usarse un evento si:

```text
event.available_at_ns <= t
bar.end_ns <= t
```

Todo target comienza estrictamente después de `t`. Una barra gruesa todavía abierta queda excluida aunque contenga ticks previos al cutoff.

## Datos propuestos

### Tabla larga de eventos

Una fila por absorción y tickframe:

- `session_id`;
- `available_at_ns`;
- `bar_key` y `K`;
- lado;
- geometría;
- volumen y fuerza;
- duración física;
- identidad y procedencia.

### Tabla de ventanas para ML

Una fila por cutoff causal:

- indicadores y recuentos por frame;
- conjunto de frames activos;
- consistencia de dirección;
- dispersión temporal;
- solapamiento y contención geométrica;
- distancia al precio;
- fuerza/volumen agregados;
- volatilidad, actividad, hora y régimen;
- `fold_id` por sesión;
- targets posteriores predefinidos.

## Operadores multiframe candidatos

1. coexistencia dentro de una ventana;
2. solapamiento de zonas;
3. zona fina contenida en una gruesa;
4. confirmación temporal posterior;
5. persistencia entre escalas;
6. roles ordenados `contexto → zona → trigger`;
7. conteo de frames, identidad específica de frames y fuerza marginal.

Estos operadores deben congelarse antes de observar sus outcomes.

## Grilla inicial propuesta, no congelada

```text
[5, 8, 10, 13, 16, 21, 25, 32, 40,
 50, 64, 75, 100, 128, 150, 200, 256]
```

`tick:1` queda fuera del inicio por riesgo de degeneración de la lógica de vela/footprint. Primero se ejecutan frames individuales; sólo después se habilitan pares y tríos bajo reglas congeladas.

## Modelos candidatos

1. regresión logística regularizada como baseline;
2. Explainable Boosting Machine para efectos e interacciones interpretables;
3. LightGBM/XGBoost/CatBoost para no linealidad;
4. RuleFit o árboles pequeños para traducir hallazgos a reglas auditables.

Todas las predicciones relevantes deben ser out-of-fold. SHAP o feature importance sirven para diagnóstico, no prueban causalidad ni autorizan selección.

## Validación

- sesiones como unidad de partición;
- CV purgada y embargo cuando corresponda;
- holdout 2026-07-01→2026-12-31 no adjunto al entorno exploratorio;
- comparación incremental contra el mejor single-frame;
- permutaciones dentro de sesión;
- estabilidad de signo y magnitud entre folds;
- SPA/StepM, max-T o procedimiento equivalente pre-registrado;
- PBO/CSCV para riesgo de selección;
- búsqueda de mesetas contiguas de K, no máximos aislados;
- publicación del landscape completo y de abstenciones.

## Horizontes

Deben coexistir dos lecturas:

1. semántica nativa por barras de cada frame;
2. horizonte comparable por tiempo físico o ticks futuros.

No se comparan resoluciones como si `max_age_bars=2000` representara la misma duración física en todas.

## Papel de Kaggle

Kaggle será laboratorio de análisis, no fuente canónica ni sustituto de EdgeLab:

```text
EdgeLab: ticks → barras → footprints → eventos → features auditables
Kaggle: features → modelos → interacciones → candidatos
EdgeLab/NT8: reproducción → gates → auditoría → eventual validación
```

Preferencia inicial: Dataset privado con features derivadas, folds, manifests y hashes; no subir ticks crudos hasta verificar la licencia del proveedor. El holdout no debe adjuntarse al Notebook.

## Fases y esfuerzo orientativo

### Prototipo

- 20–30 sesiones;
- 8 tickframes;
- single-frame y pares aprendidos;
- tres targets;
- CV por sesión;
- dataset derivado y Notebook reproducible.

Estimación: 12–20 horas de trabajo activo.

### Campaña formal

- 201 sesiones pre-holdout;
- grilla congelada;
- individuales, luego pares/tríos;
- modelos interpretables y boosting;
- multiplicidad, estabilidad y auditoría independiente.

Estimación: 45–80 horas, 6–10 iteraciones multimodelo y 2–12 horas de cómputo por campañas principales.

## Gates previos a resultados

1. benchmark de tiempo y RAM del builder actual;
2. clasificación agresora única y procesamiento por sesión;
3. representación compacta y caché content-addressed;
4. soporte de oráculos por `(indicator, bar_key)`;
5. tests de causalidad, sesión, volumen, determinismo y timestamps;
6. paridad representativa sugerida en `tick:5, 10, 25, 50, 100, 200`;
7. protocolo, targets, folds y multiplicidad congelados;
8. licencia de datos y política de Kaggle resueltas.

## Prohibiciones

- no agregar esta campaña post hoc a PR #11;
- no tocar holdout para diseño o selección;
- no ejecutar P&L ni optimizar targets/stops;
- no elegir el mejor K por máximo aislado;
- no usar barras abiertas;
- no reconstruir ticks por combinación;
- no tratar feature importance como evidencia;
- no promover una regla antes de reproducción local, gates y auditoría;
- no mergear ni abrir outcomes por el mero hecho de que el Notebook encuentre una interacción.

## Próxima acción autorizada

Escribir el protocolo y spec ejecutables y correr únicamente benchmarks estructurales sobre datos de research. No calcular endpoints predictivos hasta congelar targets, folds, operadores multiframe, multiplicidad y criterios de abstención.
