# INC-007 — Tres autoridades estadísticas incompatibles podían emitir veredictos distintos

**Fecha de detección:** 2026-08-03  
**Estado:** contenido; remediación en curso.  
**Severidad:** alta. La cadena de promoción no impone una única semántica estadística.  
**Referente:** `docs/NORTH_STAR.md`, sha256 `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`.

## Resumen

EdgeLab tiene tres stacks estadísticos que responden preguntas distintas y no
existe una autoridad ejecutable que impida promover con el stack incorrecto:

1. `edgelab/audit.py` + `validation/harness.py` + `validation/gauntlet.py`;
2. `edgelab/research/g2.py`;
3. `edgelab/research/explore.py` + `edgelab/stats/*`.

El problema no es duplicación estética. Los stacks difieren en estimando,
métrica de selección, PBO, DSR, walk-forward, nulo y unidad de dependencia.
Dos callers pueden analizar el mismo candidato y emitir decisiones incompatibles.

## Cómo se detectó

Durante la quinta iteración de auditoría se reconstruyeron desde Git:

- `docs/NORTH_STAR.md`;
- `docs/edge_validation_contract.md`;
- `docs/ESPEC_TEST_EXPLORE-001.md`;
- campañas y resultados históricos;
- implementaciones y tests de los tres stacks;
- cronología de commits de G2, estimando diario y ESPEC.

La cronología fue decisiva:

```text
2026-07-21  entra el stack legado de audit/gauntlet
2026-07-25  se implementa g2.py
2026-07-28  se implementa Diseño B: tasa favorable promedio por día
2026-08-01  ESPEC cambia la primaria a expectativa neta por trade contra cero
```

`estimando_diario.py` implementa correctamente una especificación anterior,
pero no la primaria vigente. Sus referencias a `ESPEC_TEST_EXPLORE-001.md §1.3`
ya no apuntan a una sección existente.

## Causa raíz

La regla de promoción vive en prosa, pero no existe un registro estructurado que
exija una `G2ValidationDecision` ligada a `campaign_id`, `run_id` y `config_id`.

Cada subsistema evolucionó localmente:

- el stack legado siguió produciendo reportes;
- G2 implementó cinco gates sin consumidor end-to-end;
- EXPLORE construyó piezas inferenciales antes de cerrar el estimando final;
- `EDGES_DISCOVERED.md` conservó un candidato externo anterior a la gobernanza.

Ninguna capa quedó autorizada explícitamente como única escritora del estado
`statistically_supported`.

## Defectos materiales confirmados

### 1. MCPT de G2 no prueba expectativa positiva

`g2.mcpt()` permuta el orden de sesiones. La suma total es invariante a esa
permutación, por lo que la implementación usa la suma de la primera mitad de
sesiones. El gate resultante prueba concentración temporal temprana, no
expectativa positiva.

El test positivo planta `+1` en la primera mitad y `-1` en la segunda: suma
cero. En cambio, un retorno `+1` uniforme en todas las sesiones produce
`p = 1.0`. El gate rechaza el mejor caso económico y aprueba como efecto un
patrón de suma cero concentrado al principio.

### 2. DSR contractual degenerado

`DSR_MIN = 0.0` y el PASS exige sólo `dsr > 0`. DSR es una probabilidad; un
valor positivo infinitesimal supera ese gate. El stack legado contiene
`DSR_PASS = 0.95`, pero `gauntlet.report()` tampoco incorpora DSR a la lista de
causas de muerte.

### 3. PBO no tiene métrica única

- G2 selecciona configs mediante suma de performance y usa `S = 8`.
- El stack legado selecciona por Sharpe y usa `S = 10`.

El contrato exige una métrica primaria única del manifiesto, pero ninguna API
la impone a ambos stacks.

### 4. Walk-forward puede seleccionar frecuencia

`g2.walk_forward()` acumula suma por fold. Si los folds tienen cantidades de
trades distintas, el ganador puede ser el que opera más, no el de mayor
expectativa neta por trade.

### 5. EXPLORE no está compuesto

`explore.correr()` valida el preregistro y retorna la spec, pero todavía no
ejecuta el estudio completo. `estimando_diario.py` acepta conteos binarios de
objetivos; la ESPEC vigente exige outcomes continuos de P&L neto por trade.

La cobertura existente del bootstrap se verificó para `np.mean`, no para el
estimando productivo con clusters de tamaño variable. `fixed_b.py` genera
funcionales y una compuerta, pero no implementa la inferencia completa.

### 6. Bug matemático independiente

`edgelab/stats/fixed_b.py::_cdf_binomial()` tiene ramas de frontera incorrectas:

- para `p = 0`, `P(X <= k)` debe ser 1 para todo `k >= 0`;
- para `p = 1`, debe ser 0 si `k < n` y 1 si `k = n`.

## Resolución del estimando

La pregunta económica vigente es:

```text
E_trade = sum(PnL neto de trades) / numero de trades
```

El trade es la unidad del estimando; la sesión/día es la unidad de dependencia.
La inferencia debe remuestrear sesiones completas y recomputar en cada réplica:

```text
theta* = sum_d sum_i pnl_di / sum_d n_d
```

Dar el mismo peso a cada día activo responde otra pregunta. Se conserva como
sensibilidad, no como primaria. El P&L diario y drawdown EOD siguen siendo
secundarios obligatorios de operabilidad.

## Impacto sobre resultados históricos

### CAMP-001

No cambia. Cerró negativo en G1 con 0/48 configuraciones de expectativa neta
positiva. G2 no se ejecutó porque no había candidato positivo, lo cual fue
correcto.

### Asian Range Breakout

La performance histórica no queda refutada por este incidente. Su clasificación
en `EDGES_DISCOVERED.md` no satisface la gobernanza vigente y debe migrarse a
`external_candidate` hasta reproducirla bajo una campaña y una decisión G2
canónicas.

### EXPLORE-001

No existe una ejecución formal que revertir. La ESPEC está incompleta y el
runner no compone todavía la inferencia.

### Holdout

Este incidente no aporta evidencia de una nueva apertura o contaminación del
holdout. No se debe mezclar con INC-002, INC-005 o INC-006.

## Contención inmediata

Hasta que exista el registro ejecutable de promociones:

1. ningún resultado nuevo puede recibir `statistically_supported`;
2. ningún reporte de `validation/gauntlet.py` constituye una promoción;
3. ningún resultado parcial de `g2.py` constituye una promoción;
4. ningún resultado de EXPLORE constituye una promoción sin runner completo,
   evidencia persistida y decisión fail-closed;
5. no se corre búsqueda sobre retornos sin manifiesto y aprobación, conforme a
   `CLAUDE.md`.

Esta contención no relaja ningún gate y no mira resultados para elegir una
semántica favorable.

## Remediación

1. Crear `PromotionRegistry` estructurado.
2. Exigir `campaign_id`, `run_id`, `config_id` y `G2ValidationDecision PASS`
   para todo estado `>= statistically_supported`.
3. Enmendar el contrato antes de cambiar semántica:
   - expectativa neta por trade;
   - cluster sesión/día;
   - DSR 0.95;
   - métrica única para PBO y walk-forward;
   - generador nulo preregistrado por campaña.
4. Sustituir el MCPT roto; no parchearlo cambiando el estadístico observado.
5. Implementar cobertura sintética del estimando real.
6. Consolidar DSR/PBO/WF en una API única.
7. Corregir `_cdf_binomial` y agregar tests de frontera.
8. Migrar ARB como `external_candidate` preservando la evidencia histórica.
9. Ejecutar tests unitarios, suites por dominio y suite completa antes del PR.

## Qué no cambia este commit

Este incidente registra y contiene. No modifica umbrales, resultados, estados,
holdout, kernels ni parquets. Los cambios semánticos requieren enmienda
versionada y tests separados.

**Tests ejecutados para este commit:** ninguno; cambio documental.  
**Resultados borrados:** ninguno.

## Regla permanente derivada

> Una regla de promoción escrita en prosa no es una barrera. Sólo cuenta como
> control cuando una estructura validada impide materializar el estado inválido.

## Aporte al referente

Impide tratar diagnósticos incompatibles como evidencia equivalente y evita que
un candidato avance hacia capital real sin responder una única pregunta de
expectativa neta, dependencia y robustez.
