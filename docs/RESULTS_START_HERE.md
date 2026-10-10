# Resultados: qué se puede reutilizar y qué necesita revisión

**No hay un certificado global de ausencia de sesgo.** Conservar resultados,
negativos y manifiestos originales. Esta entrada organiza su revisión: no
reescribe el ledger, no abre holdout y no transforma una incertidumbre en
invalidación formal.

## Autoridad y alcance

1. La campaña original fija spec, universo, particiones y presupuesto.
2. La corrida debe vincular versión exacta del notebook/código con sus outputs
   y fuentes realmente consumidas. Datasets adjuntos no prueban consumo.
3. Verificar bytes y reproducibilidad no certifica calendario, continuidad,
   liquidez, causalidad de la selección ni significancia ajustada por selección.
4. Registrar el dictamen/revisión como evidencia separada, con dependencias.
   [Memoria](COMPONENT_MEMORY.md) conserva la historia; no adjudica sesgo.
5. Usar `invalidation.py` para errores de medición probados y dependencias
   identificadas. No sembrar una invalidación sólo porque falta un manifiesto.

## Revisión acotada disponible

### Kernels MNQ: AVZVOL k1, AVZGRID k1 y HFTRET-MNQ k1

[Snapshot estático con SHA del source y referencias de línea](infra/KAGGLE_LEGACY_LINEAGE_20261010.json).
Se inspeccionó el código devuelto por `get_notebook_info`, **sin ejecutarlo**.
No es una auditoría de todos los kernels ni vincula ese source con cada
artefacto histórico. Las fechas de ejecución de listados y metadata no bastan
para esa vinculación; hace falta versión/run/output exactos.

- Los tres sources declaran **MNQ**. No atribuirles el problema de roll de ES
  o la cuarentena de un archivo NQ por el nombre del indicador o los datasets
  que tengan adjuntos.
- Seleccionan sesiones con `ed.sessions` y una fuente por contrato por mayor
  cantidad de sesiones. Reconstruir qué resolver, versión y archivos se
  consumieron realmente; no asumir que el catálogo montado era v15.
- El adaptador ordena timestamps si retroceden, elimina 16–17 CT y sustituye
  cotizaciones ausentes por sentinelas. Falta enlazar una revisión de esas
  transformaciones y registrar conteos, identidad original y motivos.
  No eliminar más datos ni reconstruir cotizaciones por conjetura.
- El cierre calculado por días hábiles no sustituye un calendario histórico
  revisado con feriados y cierres anticipados.
- AVZVOL/AVZGRID usan `SPEC=25` en el builder, aunque conservan `TICKS_BAR=50`
  y una descripción de 50t. Reconciliar el manifiesto original antes de
  reutilizar resultados. Un comentario no gobierna el parámetro ejecutado.
- HFTRET usa `hash(c)` como semilla. Sin congelación verificable de
  `PYTHONHASHSEED`, esa semilla puede cambiar entre procesos. Es un riesgo de
  reproducibilidad; **no prueba por sí solo sesgo económico**. No retocar sus
  outputs históricos: una futura corrección necesita identificador de corrida
  nuevo, semilla explícita estable y preregistro.
- `EDGELAB_CODE_COMMIT` en AVZVOL es una etiqueta declarada; no prueba que
  todo el código importado ni los datos correspondan a ese commit.

Estado: **requieren revisión de lineage antes de uso confirmatorio**.
No se calcularon retornos ni nuevos contrastes para cuantificar el efecto.

### MGC EMA: evidencia histórica con límites propios

[Campaña original](research/mgc_ema_20261002/README.md).
Conservar su holdout **2026-04-01**, no ampliarlo a octubre por el catálogo
ES/NQ. La campaña documenta `TICKBAR-001`: el artefacto que descartaba colas
de sesión fue invalidado y reemplazado por otro que conserva barras parciales.
No rehabilitar artefactos anteriores por tener hashes válidos. La campaña
sigue siendo discovery/exploratoria, no un edge promovido; la normalización
UTC/canonicalización upstream tampoco queda certificada por esta revisión.

### Infraestructura ES/NQ

[Entrada de datos](KAGGLE_START_HERE.md) ·
[Roll ES y reparación upstream pendiente](infra/KAGGLE_ROLL_SELECTION_20261010.md).
El ingreso técnico de agregados al Hipocampo acredita integridad de esa
ejecución, **no una hipótesis económica ni datos research-ready**. Estructura
raw, selección de contratos y calidad causal son revisiones distintas.

## Cómo revisar sin ejecutar research

Python 3.12 y [entorno del repo](ENVIRONMENT.md).

```bash
# JSON guardado con metadata y blob.source, sin ejecutar ni importar ese source:
python tools/audit_kaggle_notebook_source.py notebook-info.json

# Sobre un envelope externo ya preparado, nunca sobre ticks:
python -m edgelab.edge_brain.result_lineage result-evidence.json
```

El primer comando devuelve **hints estáticos** y SHA del source; exit 0 sólo
significa que pudo inspeccionarlo. No publica source privado ni URLs firmadas.
El segundo devuelve `REQUIRES_REVIEW` (exit 2) o
`METADATA_COMPLETE_UNADJUDICATED` (exit 0). **Ambos mantienen
`research_authorized=false` y `bias_adjudicated=false`.**

## Contrato de evidencia para futuras corridas

`edgelab.edge_brain.result_lineage.require_complete_result_envelope` comprueba
consistencia de declaraciones, antes de reutilizar un resultado. Es **opt-in**:
no está insertado automáticamente en los kernels legacy ni reemplaza
`research_access`, la revisión independiente o los gates de promoción.

Envelope `schema=edgelab_result_evidence_v1`:

- `run_id`, `instrument`, `contracts`: identidad y contratos consumidos.
- `execution`: `output_run_id`, `notebook_version` entero positivo,
  `source_sha256`, `code_bundle_sha256`, `runtime_sha256`, `seed_policy`
  (`stable_explicit_v1` con `seed` entero no negativo, o `no_randomness`).
- `campaign`: `spec_sha256`, `authorization_sha256`, `data_start`, `data_end`,
  `holdout_start` original (fechas ISO; fin anterior al holdout).
- `inputs`: lista no vacía de `{dataset_version: owner/slug/version,
  file, sha256}` **consumidos**, sin inferirlos de attachments.
- `resolver_sha256`; `quality_review_refs`: SHA por `calendar`, `coverage`,
  `liquidity`, `clock`, `selection`, `source`.
- `transformations`: lista explícita de `{name, evidence_sha256}`, o `[]`
  si no hubo ninguna; evidencia debe explicar filtros/sentinelas/warmup y
  observaciones excluidas, no sólo repetir “PASS”.
- `outputs`: lista no vacía de `{file, sha256}`.
- `unresolved_issues`: lista explícita, incluso vacía.

Referencias con formato SHA **no se autentican ni se verifican contra bytes**
en este checker. La revisión independiente debe obtener artefactos, medir
hashes, verificar autoridad y vincular run/version/outputs. El checker no
certifica que las declaraciones sean ciertas ni que cubran todo el universo.
La cuarentena conocida se aplica al par exacto versión/archivo consumido;
una declaración PASS no la borra y MNQ no se convierte en NQ.

## Pendientes y orden de trabajo

1. Obtener provenance/output-version de cada corrida histórica; adjuntos y
   código actual no alcanzan. Los kernels no revisados siguen **no revisados**.
2. Recuperar manifiestos originales y code bundles, sin correr nuevas hipótesis.
3. Resolver calidad/continuidad/selección sólo para fuentes realmente consumidas;
   reparar ES upstream cuando estén los originales solicitados.
4. Anexar revisiones por artefacto y propagar únicamente dependencias comprobadas.
5. Integrar el envelope en el runner futuro y exigir gates independientes;
   no afirmar que las rutas legacy ya están protegidas.