# Kaggle M1 — sello del holdout y validación del dataset (2026-08-14)

**Autor**: auditor externo (sandbox target-free).
**Insumo normativo**: `contrato_kaggle_v2` (estado declarado `DRAFT_NON_EXECUTABLE`), `kaggle_panorama`.
**Objeto**: dataset privado `nicolasbuttaro/edgelab-cme-futures-universe`, Versión 1 (17,97 GB, 57 archivos, 728 columnas declaradas por Kaggle).
**Alcance de esta entrega**: código ejecutable + hallazgos medidos. No se corrió todavía ningún notebook en Kaggle.

---

## 0. Resumen ejecutivo

Antes de analizar nada, el contrato exige verificar identidad, presupuesto y firewall. Cuatro hallazgos bloquean que la Versión 1 sea el **dataset exploratorio** del contrato, y uno de ellos habría contaminado silenciosamente todo el análisis si se hubiera implementado el sello como se propuso originalmente (corte UTC).

| # | Hallazgo | Regla del contrato | Estado |
|---|---|---|---|
| H-1 | Un corte en `2026-07-01T00:00:00Z` deja pasar ticks del **trade date 2026-07-01** (holdout). Medido: **871 filas** en un solo contrato de 1,13 M ticks | "bloquear por `session_key` y `session_date` en America/Chicago, no sólo por un timestamp UTC" | **corregido en código** |
| H-2 | La Versión 1 contiene físicamente filas de holdout (los contratos 09-26 llegan hasta fines de agosto de 2026) | "el holdout debe estar FÍSICAMENTE ausente del dataset exploratorio"; STOP: "cualquier fila holdout: invalidar toda la versión" | **bloqueante** |
| H-3 | 17,97 GB vs presupuesto de **10 GB**; 57 archivos top-level vs presupuesto de **20** (y vs el límite documentado de Kaggle de 50) | "input privado v1 ≤ 10 GB comprimidos", "archivos top-level ≤ 20" | **ABSTAIN_CAPACITY** |
| H-4 | Ticks crudos subidos con M0 sin cerrar (no existe `DATA_LICENSE_DECISION.md`) | "No subir ticks crudos hasta resolver licencia y política de datos" | **bloqueante (P-07)** |

El dataset es privado, lo que reduce el riesgo de H-4 a exposición cero de terceros, pero no cierra M0: la política aplica al acto de subir, no a la visibilidad.

---

## 1. H-1 — el corte UTC es un leak, y está medido

Globex abre la sesión del trade date **D** a las **17:00 CT de D-1**. Un corte por timestamp UTC en `2026-07-01T00:00:00Z` (= 2026-06-30 19:00 CT) conserva las dos primeras horas de la sesión del 1-jul, que es holdout.

Medición sobre el parquet canónico `6E_09-26_ticks.parquet` (sha256 `1311bc5e…`, 1.131.047 ticks, el mismo archivo con el que se cerró P-16):

| Regla de corte | Filas conservadas |
|---|---|
| corte UTC ingenuo (`ts < 2026-07-01T00:00Z`) | 1.128.049 |
| regla de sesión de Chicago (`trade_date ≤ 2026-06-30`) | 1.127.178 |
| **diferencia = leak que el corte UTC habría dejado pasar** | **871** |

871 ticks son suficientes para contaminar la última sesión de entrenamiento y, por transitividad, cualquier estadístico de normalización que se calcule sobre "todo el histórico disponible". El contrato lo cataloga como condición de invalidación de la versión completa, no como detalle.

Implementación: `edgelab/kaggle/sessions_cme.py` deriva el trade date desde la **tzdata del sistema** (transiciones DST obtenidas por bisección al segundo, sin reglas hardcodeadas) y `edgelab/kaggle/seal.py` corta por trade date, reporta filas cortadas por fecha y exige el token explícito `M8_HOLDOUT_OPENED_ONCE` para abrir el holdout. Sin token, `assert_no_leak` levanta excepción: **fail-closed**.

---

## 2. H-2 — la Versión 1 no puede ser el dataset exploratorio

Los contratos `*_09-26` cubren hasta su vencimiento (septiembre de 2026) y el bundle se construyó con datos hasta la fecha de build (14-ago-2026). Es decir: **julio y agosto de 2026 están dentro del archivo**, y el holdout contractual es 2026-07-01 → 2026-12-31.

El sello en código evita el leak *en el análisis*, pero el contrato pide además ausencia **física**. Remediación propuesta (a decidir por Nico):

1. **V1 queda como `raw_custody`**: privada, no analítica, en cuarentena documentada. No se adjunta a ningún notebook formal.
2. **`edgelab-cme-research-v2`**: derivadas únicamente (`events_long`, `windows_ml`, `targets_long`, `folds_*`, diccionarios), construidas con el sello aplicado, ≤ 10 GB, ≤ 20 entradas top-level, particiones de 128–512 MB.
3. El holdout se materializa aparte y **no se sube** hasta M8.

Mientras eso no exista, el veredicto de `01_dataset_validation` sobre V1 es `SEAL_ENFORCED_BUT_HOLDOUT_PRESENT`: se puede medir integridad, no se puede pre-registrar un análisis.

---

## 3. H-3 — presupuesto excedido

`inventory.budget_gates` implementa los cuatro gates y devuelve `ABSTAIN_CAPACITY` si alguno falla. Sobre los números publicados por Kaggle para V1: 17,97 GB (límite contractual 10) y 57 archivos top-level (límite contractual 20; límite documentado de la plataforma 50). El upload existe de todas formas, así que se reporta la **discrepancia** entre la documentación de Kaggle y el comportamiento observado, sin afirmar cuál es la regla vigente.

Pendiente de reconciliación con dato duro, no con inferencia: local declara **56 contratos / 16,74 GB**, Kaggle muestra **57 archivos / 17,97 GB**. `728 = 56 × 13` sugiere que Kaggle cuenta 13 columnas por archivo (contra 8 en el esquema canónico) y que hay un archivo extra. El notebook 00 identifica el archivo 57 por censo de footer en vez de suponerlo.

---

## 4. H-4 — gate legal M0

`00_contract_and_environment` incluye el gate `G4_legal_M0`: busca `DATA_LICENSE_DECISION.md` y falla si no está. Es la traducción ejecutable de P-07. Hoy falla.

---

## 5. Evidencia de que el código mide bien

Dos pruebas corridas en el sandbox del auditor, ambas sin fallos.

**(a) Self-test de bordes** (`sessions_cme` + `seal`): 7 casos de frontera de trade date, incluido `2026-06-30 17:00 CT → 20260701 (HOLDOUT)`; tabla de transiciones DST 2015-2035 derivada de tzdata; minutos desde apertura y pausa de mantenimiento 16:00–17:00 CT; token inválido rechazado; `assert_no_leak` verde sobre el tramo sellado.

**(b) Paridad streaming ↔ batch** (`tools/sandbox/kaggle_streaming_parity.py`): el mismo archivo procesado en 143, 12, 3 y 1 batches contra el cálculo en memoria. **28 claves de integridad, 594 claves de actividad, 66 trade dates y el sello completo: idénticos en los cuatro tamaños.** Sin esta prueba, el camino que corre en Kaggle (por batches, obligado por el presupuesto de 20 GB de RSS) no sería auditable contra nada.

### Integridad medida del contrato canónico (6E 09-26, 90 días)

| Métrica | Valor | Lectura |
|---|---|---|
| ts monótono no decreciente | sí, 0 pasos hacia atrás | OK |
| `sequence` única y estrictamente creciente | 1.131.047 / 0 duplicados | OK |
| cotizaciones válidas | 100 % | OK |
| quotes cruzados | 0 | OK |
| trades dentro del quote | 100 % (551.065 al bid, 579.995 al ask) | OK |
| spread ≤ 0 | 14 filas | mercado bloqueado (`bid == ask`), no cruzado |
| timestamps duplicados | 752.267 (66,5 %) | la fuente es de **resolución milisegundo**; `sequence` desempata |
| gap máximo | 209.274 s (58,1 h) | fin de semana + back month ilíquido |
| sesiones (trade dates) | 66 | 0 sábados, 0 domingos |
| cobertura de minutos | 11 completas / 28 parciales / 27 escasas | rampa de liquidez del back month → **justifica la regla de roll** |

Ese último renglón es un resultado, no un defecto: 6E 09-26 en abril es back month y casi no negocia. Confirma que el universo **debe** analizarse por contrato activo (roll) y no como serie continua ingenua, y que la batería P-14/P-15 ("0 minutos faltantes en horario activo") sólo tiene sentido aplicada al front month.

---

## 6. Mapeo del plan al pipeline congelado del contrato

El contrato ya fija los nombres de los notebooks. El plan de trabajo se mapea así, sin inventar etapas nuevas:

| Notebook del contrato | Contenido | Estado |
|---|---|---|
| `00_contract_and_environment` | identidad, licencia, hashes, censo por footer, presupuesto, pre-screen de holdout | **commiteado** |
| `01_dataset_validation` | schema, causalidad, firewall, calendario empírico, cuarentena | **commiteado** |
| `02_capacity_benchmark` | RAM, runtime, tamaños, lineage medidos, no estimados | pendiente |
| `03_single_frame_baseline` | OOF del baseline pre-registrado | pendiente |
| `04_single_frame_landscape` | 17 frames, selección sólo interna | pendiente |
| `05_restricted_multiframe` | pares sobrevivientes, si fueron habilitados | pendiente |
| `90_audit_and_export` | manifiesto, candidate cards, abstenciones | pendiente |

---

## 7. Reproducción

```bash
# sandbox del auditor
cd /data/replica
python3 tools/sandbox/kaggle_streaming_parity.py   # exit 0 = paridad exacta

# Kaggle (internet OFF, Save & Run All)
# adjuntar: dataset de ticks + code dataset con el paquete edgelab
python3 notebooks/kaggle/00_contract_and_environment.py
python3 notebooks/kaggle/01_dataset_validation.py
```

Identidad del código medida en el sandbox (git-blob sha1, comparable con `git ls-files -s edgelab/kaggle/`):

| Módulo | blob sha1 | bytes |
|---|---|---|
| `edgelab/kaggle/__init__.py` | `09c9be9b09519dbc9cbe5d4edce57763ddce3a84` | 569 |
| `edgelab/kaggle/identity.py` | `77395791cb4c992f8cd75a1f53be34b952d07ff8` | 6383 |
| `edgelab/kaggle/integrity.py` | `2b17d0e7eb154b54dadc53e3b15ff2efa3c5d811` | 7244 |
| `edgelab/kaggle/seal.py` | `c0aff45a19fe6a856c2b9afb9b2777b2f7796a6f` | 6890 |
| `edgelab/kaggle/sessions_cme.py` | `57c5d24faa9a048b5ae2d325078af526d645dbe4` | 6168 |

Si el blob del repo no coincide con estos, el código que se auditó no es el que corre.

---

## 8. Decisiones que requieren a Nico

1. **Remediación de H-2**: ¿V1 pasa a `raw_custody` y se construye `research-v2` con derivadas? (recomendado)
2. **M0 / P-07**: aportar la fuente de los términos de licencia para poder cerrar el gate legal.
3. **Presupuesto**: aceptar `ABSTAIN_CAPACITY` sobre V1 y trabajar contra el dataset derivado.
4. **Regla de roll**: se propone volumen diario con desempate por open interest y fechas oficiales de CME como fallback; queda para el pre-registro.
