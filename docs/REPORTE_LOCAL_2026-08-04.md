# Reporte de la máquina operativa — 2026-08-04

> **Autoría y alcance.** Ejecutado por Claude en la computadora operativa
> (Windows, datos reales, entorno canónico). Este documento existe para que la
> sesión de investigación lea evidencia **desde el repositorio** en vez de
> depender de que un humano transporte texto. Todo lo que sigue fue ejecutado,
> no inferido; donde algo no se ejecutó, se dice.
>
> Referente: `docs/NORTH_STAR.md`.

## 1 · Baseline canónico

Entorno reconstruido desde `requirements/core-bridge-dev.lock`
(sha256 `0cb96d720376a3d37cbfaaa94a3dda4d078d4d27206b47077a4cc0b276efaf1f`)
en un worktree limpio, sin tocar el repo original.

```
python        3.12.10        Windows-11-10.0.26200-SP0
numpy 2.4.6   pandas 3.0.3   numba 0.66.0   llvmlite 0.48.0
pyarrow 25.0.0 pydantic 2.13.4 duckdb 1.5.4  polars 1.43.0
pytest 9.1.1  hypothesis 6.158.1  typer 0.27.0
env_digest    6f40af097bc56811
```

### 1.1 Resultados

| HEAD | commit | suite completa |
|---|---|---|
| `86498ac` | feat(research): add fail-closed G2 validation decision | 582 passed, **2 failed**, 37 skipped |
| `f4367a2` | fix(research): fail closed on partial signal-rate census | 584 passed, **2 failed**, 37 skipped |
| `2ff9c19` | rama correctiva rebaseada sobre `f4367a2` | **586 passed, 0 failed**, 37 skipped |

Los dos `failed` son siempre los mismos y son los que la rama correctiva
resuelve (§3). **Con esto queda cerrado el "pytest canónico pendiente"** que
declaraban §13.18–13.25 para todo el stack G2 reconstruido: `NullGenerator`,
bootstrap-t studentizado, PBO/WF por ratio, `G2ValidationDecision` fail-closed,
reconstrucción canónica previa a promoción y guard del censo parcial. Los tests
de esos siete commits pasan en el entorno canónico, no sólo en sandbox.

Comando exacto:

```bash
python -m pytest --basetemp=C:/t -q
```

### 1.2 Por qué `--basetemp=C:/t` (no es cosmético)

En esta máquina `LongPathsEnabled = 0`. Las rutas particionadas del store v2
(`instrument=/contract=/indicator=/kernel_id=/bar_key=/config_id=/run_id=`)
más el prefijo temporal de pytest llegan a **271 caracteres**, sobre el límite
MAX_PATH de 260. Sin `--basetemp` corto, **22 tests fallan y 13 dan error** por
`WinError 206`, y el modo de falla imita "faltan datos". Se refutó esa hipótesis
midiendo: los mismos 38 tests pasan con basetemp corto.

Git tiene `core.longpaths=true` — por eso el checkout funciona — pero Python y
pyarrow no se benefician de esa opción. La corrección de entorno
(`LongPathsEnabled=1`, requiere elevación y reinicio) queda pendiente del lado
del operador; **no se hardcodea `C:/t` en la configuración del proyecto.**

## 2 · Dos riesgos materiales encontrados al preparar el censo

### 2.1 El universo de EXPLORE-001 puede cruzar el holdout

Rangos UTC reales, leídos de los parquets canónicos F2:

```
6E 09-25   2025-07-25 -> 2025-09-15
6E 12-25   2025-09-08 -> 2025-12-15
6E 03-26   2025-12-08 -> 2026-03-16
6E 06-26   2026-03-09 -> 2026-06-15
6E 09-26   2026-06-08 -> 2026-07-21   <== 21 días DENTRO del holdout
```

La frontera sellada es `2026-07-01` (más la cuarentena de INC-005, 07-01 a
07-16). **Un censo ingenuo sobre "todo 6E" leería datos sellados.** El corte
tiene que ser explícito en el manifiesto del censo, no implícito en el loader.

Consecuencia de tamaño, no sólo de higiene: descontando `09-26` posterior a la
frontera quedan **~235 días hábiles** entre 2025-07-25 y 2026-06-30 para llenar
las **200 sesiones** que declara la ESPEC. El margen es de ~35 días. Cualquier
regla de exclusión (feriados, cobertura incompleta, `HORIZONTE_NO_CONTINUO`)
consume ese margen rápido. **Conviene declarar antes de correr qué pasa si el
universo elegible cae por debajo de 200**, porque descubrirlo a mitad de camino
invita a relajar un criterio después de ver los datos.

### 2.2 Conflicto de estimando entre la ESPEC y la enmienda G2

`docs/predictions/ESPEC_TEST_EXPLORE-001.md` §1.3 declara como primario:

```
UNIDAD: el DÍA.  PESO: equal-weight POR DÍA.
p_global = mean_d p_dia(d)
```

`docs/amendments/G2-2026-08-03_estimando_y_autoridad.md` §2.3 **prohíbe
explícitamente como primaria** esa misma forma funcional:

```
mean_d(u_d / v_d)
...
p_favorable
```

**No parece un error de ninguno de los dos.** Cada uno justifica bien su
elección para su propia pregunta: la ESPEC evita pseudo-replicación (20 zonas
del mismo día comparten régimen y no son 20 observaciones); la enmienda persigue
el dinero, que se acumula por trade y no por día. Es exactamente el problema de
*informative cluster size*: promedio-por-participante y promedio-por-cluster son
**estimandos distintos**, y se elige por objetivo de inferencia (§4).

Pero por eso mismo **el límite tiene que quedar escrito**: que EXPLORE-001 pase
con `p_global` **no** constituye evidencia G2. Sin esa frontera declarada, un
EXPLORE positivo puede leerse como `statistically_supported`, que es
precisamente lo que §2.3 existe para impedir.

## 3 · Rama correctiva pendiente de integración

`fix/capture-probe-v2-contract`, rebaseada sobre `f4367a2`:

```
8d35807  fix(nt8): CaptureEventProbeV2 declara version en el meta de captura
2ff9c19  audit(ulp): medir y sellar la clasificacion de agresor de CaptureEventProbeV2
```

**`8d35807`** — el `.cs` se agregó sin el token `version=`, incumpliendo la regla
permanente. Se declara `IND_VERSION = "2.1"` (consistente con el encabezado del
archivo y con `schema=event_capture_raw_v2_1`) y se emite en la metadata con el
formato `# key=value` **de este artefacto**: el parser de `capture_tsv.py`
(líneas 121–128) exige esa forma, y el `# meta indicator=...,version=...` de los
EventLog CSV produciría una clave con espacio. `version=` y `schema=` se mueven
por separado: uno versiona el instrumental, el otro el contrato de columnas.

**`2ff9c19`** — AUDIT-002 no tenía caso para el probe, así que sus dos
comparaciones de agresor quedaban sin triaje. Se **midió**, no se razonó:

```
aggressor buy  (price >= ask)   0.00%   0 flips / 5001 niveles
aggressor sell (price <= bid)   0.00%   0 flips / 5001 niveles
```

Modelado con `offset_ticks=0`, **no `None`**: el empate no es un caso de borde
acá — un trade exactamente al ask es el caso *normal* de un buy agresivo, así que
se mide el escenario decisivo en vez de declararlo inmune por medio tick. Da cero
porque `price`, `bid` y `ask` son los tres precios de grilla del mismo snapshot
del feed, sin aritmética, y ambas representaciones son estrictamente monótonas en
el índice de tick. **Las comparaciones no se modificaron y no se introdujo
ninguna tolerancia.** Triaje sellado como `INMUNE_MONOTONO` (47 → 49 entradas).

Nota de revisión: la primera escritura del baseline JSON reformateó las 194
líneas (LF contra el CRLF del archivo). Se detectó, se verificó
programáticamente que **0 entradas históricas quedaron modificadas**, y se
reescribió preservando CRLF, indent y ausencia de newline final. El diff final
es **puramente aditivo: 8 inserciones, 0 borrados**.

### 3.1 Tercer defecto: el `.cs` no era compilable (CRLF)

Al correr el verificador obligatorio antes de pedir la compilación, `f4367a2`
falló:

```
[FAIL] nt8/CaptureEventProbeV2.cs
   FAIL  363 saltos LF sin CR: NT8 anexará una región duplicada
```

El archivo tenía **0 CRLF y 355 LF sueltos** y era el **único `.cs` del repo**
en ese estado; los otros seis son CRLF puro (926, 918, 892, 748, 638, 299). Es
el modo de falla que documenta `nt8/README.md`: NT8 no reconoce su propia región
generada, **anexa una segunda** y la compilación revienta — así se rompió el
2026-07-25.

**El defecto era PREEXISTENTE**, no introducido por la rama correctiva: ya
estaba en `f4367a2` antes de tocar el archivo. La hipótesis es que se escribió
en sandbox (LF) y nunca hizo el viaje de ida y vuelta por NT8, que sí lo habría
normalizado.

Corregido en `2f300f7`, junto con el formato del meta: se había emitido como dos
líneas `# indicator=` + `# version=`, y `check_nt8_cs.py` exige
`meta indicator=X,version=Y` — el formato de los otros seis. Se unificó a esa
forma; el parser de `capture_tsv.py` la tolera igual.

### 3.2 Instalación y compilación en NT8 — VERIFICADAS

La instalación real de NT8 en esta máquina está en
`%USERPROFILE%\OneDrive\Documentos\NinjaTrader 8\` (carpeta **redirigida a
OneDrive y en español**), no en `Documents\`. La ruta sin redirección existe
pero contiene un solo `.cs` ajeno al proyecto; **apuntar ahí instala en el vacío
y el indicador nunca se actualiza.** Queda anotado porque es una trampa
silenciosa para cualquier instrucción futura.

Procedimiento ejecutado, conforme a `nt8/README.md`:

1. respaldo del instalado en
   `C:\ProyectosQuant\_baselines\nt8_cs_backup\CaptureEventProbeV2.cs.20260804T032136Z.bak`,
   **fuera de `bin\Custom`**;
2. reemplazo in place por la copia canónica de `2f300f7`;
3. compilación por el operador desde el NinjaScript Editor.

Evidencia de que compiló (artefacto, no declaración):

```
NinjaTrader.Custom.dll   reconstruida 2026-08-04 00:26 local
log del día              0 errores CS####
verificador sobre el instalado:
  [WARN] meta=CaptureEventProbeV2=2.1, 419 líneas CRLF, 1 clase
  warn: trae 1 región generada  <- ESPERADO en la copia instalada;
        el warn aplica a la copia canónica del repo, que tiene 0
```

El `WARN` es correcto y no es un problema: NT8 **regeneró su región al
compilar**, que es exactamente lo que debe pasar del lado instalado.

**Lo que esto todavía NO prueba:** que una captura nueva sea válida. La
verificación pendiente es que el próximo `.tsv` traiga
`# meta indicator=CaptureEventProbeV2,version=2.1` en el header y que audite sin
deuda de schema.

## 4 · Contraste de la enmienda G2 con literatura externa

Búsqueda hecha para asistir la decisión de aprobar o rechazar. Resultado por
decisión:

| Decisión de la enmienda | Veredicto | Fundamento |
|---|---|---|
| DSR `>= 0.95` (§6) | **correcta; el umbral viejo estaba roto** | El DSR es una *probabilidad*. `> 0` se satisface trivialmente siempre: no era un umbral laxo, era ninguno. `>= 0.95` es la lectura estándar de Bailey & López de Prado. |
| Retirar el MCPT universal (§4) | **correcta y bien fundada** | Romano & Tirlea (2022): los tests de permutación son exactos bajo intercambiabilidad pero **no son nivel-α** con dependencia; la validez se recupera sólo con estadístico studentizado bajo mixing. Exigir `null_id` + generador por campaña es la respuesta correcta. |
| Ratio-de-totales primaria + equal-weight como sensibilidad (§2, §13.7) | **correcta** | Literatura de *informative cluster size*: los dos estimandos difieren (>10% documentado) y se elige por objetivo de inferencia. Para una estrategia, el trade es la unidad económica. Reportar ambos y tratar la divergencia como advertencia es la práctica recomendada. |
| PPW 2009 para largo de bloque | **referencia correcta** | Es la corrección de Patton–Politis–White (2009) al algoritmo de Politis–White (2004), tras Nordman (2008). Citar la corregida y no la original es un detalle fácil de errar. |
| Bootstrap-t sobre percentil (§3.2) | **respaldado** | Ya refutado empíricamente en el repo (64% i.i.d., 80% estacionario, ningún `b` superó 80%); la literatura coincide en que el percentil sub-cubre con dependencia. |

### 4.1 Observación que sí modifica el contrato

El piso `MIN_STUDENTIZED_SESSIONS = 160` es **conservador y está bien**: las
reglas de dedo sitúan en ~40–50 clusters el umbral por debajo del cual la
inferencia cluster-robusta no es confiable.

Pero la literatura documenta que los intervalos studentizados con cluster
bootstrap **siguen sub-cubriendo**, típicamente 86–94% para nominal 95% — y la
medición del propio repo lo confirma: peor celda **91,5%**, colas pesadas
92–92,5%.

Esto es decisión-relevante porque el gate primario es **`cota inferior del IC > 0`**.
Un IC nominal 95% que cubre ~92% tiene una cota inferior **algo más optimista de
lo que declara**, así que el gate primario pasaría un poco más seguido de lo que
el 95% sugiere. No invalida el método —lo midieron, no lo escondieron, y fijaron
el piso donde su propio criterio del 90% se sostenía—, pero **el contrato debería
declarar la cobertura efectiva medida (~92% en el peor escenario) en vez de
dejar leer la cota inferior como exacta.**

Sugerencia concreta: agregar esa declaración al §3.2 como enmienda mínima, y que
entre junto con la aprobación.

### 4.2 Estado de aprobación según la propia §12

De los nueve criterios de la enmienda, esta corrida cierra **el #7**
(suite específica y completa en entorno canónico). Verificar la implementación
era necesario, no suficiente. Los demás corresponden a la sesión de
investigación y al operador.

## 5 · Fuentes consultadas

- Bailey & López de Prado — *The Deflated Sharpe Ratio* — https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Romano & Tirlea — *Permutation Testing for Dependence in Time Series* — https://arxiv.org/pdf/2009.03170
- Patton, Politis & White (2009) — *Correction to "Automatic Block-Length Selection for the Dependent Bootstrap"* — https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf
- MacKinnon — *Cluster-Robust Inference: A Guide to Empirical Practice* — https://arxiv.org/pdf/2205.03285
- *Using Cluster Bootstrapping to Analyze Nested Data With a Few Clusters* — https://pmc.ncbi.nlm.nih.gov/articles/PMC5965657/
- *Bootstrap in cluster randomised trials: simulation results* — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC535558/
- Kahan et al. — *Informative cluster size in cluster-randomised trials* — https://journals.sagepub.com/doi/10.1177/17407745231186094
- *Estimands in cluster trials: target of inference and consequences for analysis choice* — https://academic.oup.com/ije/article/52/1/116/6677192

## 6 · Lo que este reporte NO afirma

- No aprueba la enmienda G2. Cierra un criterio de nueve.
- No ejecutó el censo de tasa de señales sobre las 200 sesiones.
- No seleccionó H1–H3 ni propuso hipótesis.
- No tocó holdout, gates, umbrales, resultados históricos ni el capture TSV.
- No afirma que exista una captura válida con el probe nuevo: el `.cs` compila
  (§3.2), pero **el TSV que hay en `oracles/` sigue siendo el del build viejo**,
  con 140 valores centinela y `schema_ok=False`. Hace falta re-capturar.
- No afirma cobertura exacta 95% para el IC primario (§4.1).

**Aporte al referente:** el stack estadístico reconstruido pasa de "escrito y
verificado en sandbox" a "verificado en el entorno canónico con datos reales
disponibles", y se documentan dos riesgos —cruce de holdout y conflicto de
estimando— que habrían aparecido recién durante o después del censo.
