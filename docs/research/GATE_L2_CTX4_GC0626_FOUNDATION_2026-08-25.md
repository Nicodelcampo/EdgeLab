# GATE L2 CTX-4 — fundación causal para GC 06-26

- **Fecha:** 2026-08-25
- **Rama de trabajo:** `work/futures-l2-context-foundation-20260825`
- **Base observada:** `44baf8f11ede62cda6deff60337df1b3aae7e962`
- **Estado:** `IMPLEMENTED_SYNTHETICALLY_TESTED / REAL_13_SESSION_EXTRACTION_PENDING`
- **Alcance:** target-free; no outcomes, retornos, P&L, MAE/MFE ni selección de parámetros por resultado.

## Dictamen de diseño

Se construyó la instancia concreta de la cadena:

```text
L1/L2 mezclado por source_row
  → libro causal + features de minuto publicadas al cierre
  → HMM3 forward-only (calm / normal / volatile)
  → sticky + overlay de estrés de flujo (toxic)
  → adapter point-in-time en t0
  → G-operable vs G-stress
  → diagnósticos target-free
  → borrador CTX-3, todavía cerrado a outcomes
```

Los cuatro estados son **climas**, no cuatro estrategias. El indicador permanece
congelado: EdgeLab etiqueta contexto offline y después, sólo bajo preregistro, pregunta si
el estimando de la familia cambia entre celdas.

## Componentes implementados

| Ruta | Función |
|---|---|
| `edgelab/context/l2_gate.py` | reconstrucción de libro, features, overlay tóxico, sticky, adapter y reporte target-free |
| `edgelab/context/hmm3.py` | HMM Gaussiano diagonal de tres estados, checkpoint sellado e inferencia forward-only |
| `tools/build_l2_gate_contexts.py` | runner real sobre Parquets L1/L2 y manifests; outputs atómicos locales |
| `specs/gate_l2_context_v1.json` | contrato congelable de datos, features, modelo y split temporal |
| `tests/context/test_l2_gate.py` | intercalado, enum 0..8, libro, causalidad, identidad e invariancia de prefijo |
| `docs/research/H-GC-BT2A-CTX-3_PREREGISTRO.md` | trial condicionado, aún no congelado |

## C0 — linaje y reconstrucción

1. La única clave de orden es `source_row`, proveniente del CSV mixto original.
2. L1 y L2 se fusionan por esa clave; un empate en `ts_us` no pierde el orden.
3. Códigos L1:
   - `0=ASK`, `1=BID`, `2=LAST` entran a quotes/trades;
   - `3=OPENING`, `4=HIGH`, `5=DAILY_VOLUME`, `6=LOW`, `7=SETTLEMENT`,
     `8=OPEN_INTEREST` quedan sólo en diagnóstico.
4. Códigos L2: lados `0=ASK`, `1=BID`; operaciones `0=ADD`, `1=UPDATE`, `2=REMOVE`.
5. El libro valida nivel, orden de precios, locked/crossed book y bootstrap. Una falla no
   produce una feature aparentemente válida: el libro se invalida hasta resincronizar.
6. `GC 06-26.Last.parquet` queda fuera por contrato: no tiene `source_row` y el reloj
   absoluto L2 sigue no resuelto.

## C1 — features disponibles antes del evento

El minuto `[t,t+1)` se publica en `t+1`; se exige:

```text
data_window_end_us <= feature_available_at_us
available_source_row < event_source_row
```

Features principales:

- volatilidad realizada rolling `rv_ticks_15m`;
- tasa de eventos;
- spread en ticks;
- OFI BBO normalizado y su magnitud;
- efficiency ratio de 10 minutos;
- profundidad top-5 por lado, total log e imbalance;
- adds, updates, removes, depleción y replenishment proxy;
- volumen agresor buy/sell clasificado contra BBO vigente y tick rule causal;
- locked/crossed book y cobertura de clasificación.

La fase horaria no se llama Asia/RTH mientras el reloj absoluto siga sin resolver. Se
conserva sólo `wall_clock_minute_of_day_unresolved`.

## Los cuatro climas

### Base HMM3

El HMM usa seis features target-free y se identifica por checkpoint completo: config,
normalizador train-only, pesos, matriz de entrenamiento, sesiones y commit. Los estados se
ordenan por RV:

- `calm`;
- `normal`;
- `volatile`.

La inferencia es `p(S_t | X_0:t)`, nunca posterior suavizado. El cambio de estado base
requiere tres minutos de confirmación y posterior mínimo 0,45.

### Overlay `toxic`

La idea legacy hablaba de VPIN. Esta versión **no reintroduce un VPIN falso**. El overlay
usa información que el bundle sí soporta:

- `abs_ofi_normalized`;
- `abs_tape_imbalance`;
- `spread_ticks_close`;
- `l2_remove_rate`;
- `depth_depletion_ratio`.

Cada componente se escala con mediana/IQR del train; el score es el promedio de los tres
shocks positivos mayores. Entrada: q90 train-only + dos minutos de confirmación. Salida:
q75 + tres minutos. El nombre formal es
`l2_flow_toxicity_overlay_not_vpin`.

Si en el futuro se desea VPIN, debe ser otra versión: buckets de volumen congelados,
clasificador de trades auditado y prueba incremental target-free contra los componentes de
volatilidad/volumen. No se promociona por nombre.

### Celdas

```text
G-operable = calm + normal
G-stress   = volatile + toxic
```

No se incorpora lógica “SoloRTH” ni filtros dentro del `.cs`.

## Split temporal congelado

- Train hasta `20260617`: 8 sesiones (`09–12`, `14–17`).
- Evaluación target-free: `20260619`, `20260621–24`.
- `20260618`: prohibida.

El checkpoint no ve las cinco sesiones de evaluación. Etiquetas de train pueden usarse
para diagnóstico del ajuste, no para el trial condicionado.

## Bundle recibido y alcance de la evidencia

La auditoría de identidad ya cerró por hashes/manifests:

```text
BUNDLE_INTEGRITY=PASS
sessions=13
source_rows=69,229,635
l2_rows=51,828,327
l1_rows=17,401,308
```

Eso prueba identidad/cobertura de conversión, no que el extractor nuevo ya haya recorrido
los 69,2 M eventos. En este commit:

```text
REAL_13_SESSION_EXTRACTION=NOT_COMPLETED
REAL_MODEL_ID=NOT_MATERIALIZED
REAL_STATE_DISTRIBUTION=NOT_MEASURED
CORR_CONTEXT_VS_ZONE_WIDTH=NOT_MEASURED_EVENT_INPUT_ABSENT
```

La corrida formal debe hacerse con PyArrow del lockfile y árbol limpio. Los Parquets y
labels quedan local-only; al repo sólo vuelve el manifest/reporte target-free.

## Tests ejecutados

El candidato local previo al push pasó:

```text
python -m unittest discover -s tests -t . -p 'test_*.py' -v
Ran 4 tests in 0.098s — OK
python -m py_compile edgelab/context/*.py tools/build_l2_gate_contexts.py tests/context/test_l2_gate.py
PASS
```

El código fue publicado en `a9f85db83455d7b85257f3dc4c49e2fedda26550` con 5 archivos y 1.153 adiciones. La corrida real del bundle y el CI remoto siguen siendo compuertas separadas; no se infiere verde remoto desde la prueba local.

Cubren:

- intercalado L1/L2 por `source_row` con timestamps empatados;
- MarketDataType completo `0..8`;
- ADD/UPDATE/REMOVE, replenishment e invalidación fail-closed;
- trade buy/sell contra quote vigente;
- publicación causal al cierre del minuto;
- modelo hash-qualified;
- inferencia de prefijo invariante;
- vocabulario de cuatro estados;
- as-of estricto: igualdad de `source_row` no es pasado.

Identidad remota del commit de implementación:

```text
commit a9f85db83455d7b85257f3dc4c49e2fedda26550
edgelab/context/__init__.py        12 líneas
edgelab/context/hmm3.py           292 líneas
edgelab/context/l2_gate.py        626 líneas
tests/context/test_l2_gate.py      95 líneas
tools/build_l2_gate_contexts.py   128 líneas
```

## Corrida formal

```powershell
.venv\Scripts\python tools\build_l2_gate_contexts.py `
  --l2-dir E:\DatosNT8\replay.csv\GC JUN26\parquet_out\l2_depth `
  --l1-dir E:\DatosNT8\replay.csv\GC JUN26\parquet_out\l1_quotes `
  --manifests-dir E:\DatosNT8\replay.csv\GC JUN26\parquet_out\manifests `
  --out-dir E:\DatosNT8\replay.csv\GC JUN26\gate_ctx4
```

El runner verifica hashes y bytes, excluye `20260618`, conserva el split, sella el modelo,
publica features/labels/reporte/manifest y aborta si HEAD o árbol cambian.

## CTX-3 y límite de potencia

El preregistro queda en `DRAFT_TARGET_FREE_NOT_FROZEN`. Exige cobertura ≥99 %, baja corr
con ancho, model_id real y ≥40 sesiones por celda. El evaluation split actual tiene cinco
sesiones: sirve para causalidad e invariancia técnica, **no alcanza para abrir outcomes**.
Hay que ganar sesiones antes de CTX-3.

## Pendientes explícitos

1. Ejecutar los 13 Parquets con el entorno canónico y versionar sólo manifest/reporte.
2. Auditar conteos L1 `0..8` reales y cobertura de clasificación de LAST.
3. Resolver cualquier book invalid/crossed antes de ampliar tolerancias.
4. Corregir en el conversor la metadata `side_codes` (hoy enumera sólo 0/1/2/5) y registrar
   unidad subsecond/blob; no reconvertir si no cambia el payload.
5. Conectar eventos BigTrap/HFT sólo si comparten `source_row`; medir corr con ancho.
6. Aumentar sesiones hasta el piso del preregistro.
7. No portar el Transformer sintético legacy como modelo formal. Cualquier Transformer
   futuro usa este mismo contrato, train anterior e inferencia causal.

## Estado científico obligatorio

```text
CAMPAIGN_OUTCOMES_OPENED=false
PREEXISTING_OUTCOME_EXPOSURE=YES
TEMPORAL_HOLDOUT_TOUCHED_TARGET_FREE=YES
EDGE_DECLARED=false
GC_06_26_NON_FRONT_MONTH_DIAGNOSTIC=true
BUNDLE_INTEGRITY=PASS
```

## Aporte al referente

La intuición “L2 → clima → señal condicional” quedó convertida en código causal, identidad
de modelo, tests negativos y un trial con compuertas. Reduce el riesgo de inventar un
rescate post hoc; el próximo cuello es ejecutar el bundle y ganar sesiones, no agregar
más modelos.
