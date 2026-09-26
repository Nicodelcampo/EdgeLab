# aVolCellPOI2 — medición de paridad (2026-08-01)

**Regla 98.** Este archivo existe porque tres números venían circulando en hilos
de chat sin respaldo en ningún archivo del repo. Se los buscó por todo el árbol
y por todo el historial de git y **no existen**. Acá quedan los números
**medidos**, con su procedencia, para que la próxima discusión parta de algo
citable.

## Procedencia

| qué | valor |
|---|---|
| reporte | `runs/gates/aVolCellPOI2_v21/parity_report.json` |
| config_id | `2079d03008f00937` (`aVolCellPOI2_4bc766b4c2`) |
| oráculo | `oracles/aVolCellPOI2_6E_0926_v21.csv` |
| sha256 oráculo | `5c85155e102eca877132be69a5033c5c4321b777db8eacc733a0f8bbb3285a2c` |
| eventos Python | `runs/gates/aVolCellPOI2_v21/aVolCellPOI2_4bc766b4c2_events_py.csv` |
| ventana | `2026-07-13T22:00:00Z → 2026-07-16T21:00:00Z` |
| ventana en tz del chart (UTC−3) | `2026-07-13T19:00 → 2026-07-16T18:00` |
| gate | **FAIL** |

Control de reproducción: recortando ambos lados a la ventana se obtienen
**146** zonas Python y **144** NT8, idénticos a `py_zones`/`nt8_zones` del
reporte. Toda la tabla siguiente está medida sobre esa misma población.

## Números medidos

### Apareo

| métrica | valor |
|---|---|
| zonas Python | 146 |
| zonas NT8 | 144 |
| pares formados por el matcher voraz | 120 (= 108 `MATCHED` + 12 `GEOMETRY_DIFF`) |
| `MISSING_IN_NT8` | 26 |
| `MISSING_IN_PYTHON` | 24 |
| `TIMESTAMP_DIFF` / `FEATURE_DIFF` / `MATURITY_TAIL` | 5 / 6 / 4 |
| **pares por clave exacta** `(bar_close_time, lower_tick, upper_tick)` | **111** |
| huérfanas bajo clave exacta | 68 (35 Python + 33 NT8) |

La clave exacta forma **menos** pares que el matcher (111 vs 120), no más: es
más estricta. Los 12 `GEOMETRY_DIFF` y 5 `TIMESTAMP_DIFF` que el matcher aparea
por proximidad, la clave los rechaza. Eso es lo correcto, pero significa que
**la clave no reduce las huérfanas: las aumenta de 50 a 68.**

### Geometrías duplicadas (dentro de la ventana)

| lado | zonas | geometrías distintas | geometrías duplicadas | zonas en geometría duplicada |
|---|---|---|---|---|
| Python | 146 | 111 | 25 | 60 |
| NT8 | 144 | 107 | 32 | 69 |

## Los tres números huérfanos — veredicto

| número que circulaba | veredicto |
|---|---|
| "35 geometrías duplicadas entre las 169 zonas" | **NO REPRODUCIBLE.** No hay ninguna población de 169 zonas en este gate (146 / 144). Los conteos de duplicadas medidos son 25 (Python) y 32 (NT8). Se retira del expediente. |
| "un matcher óptimo global coincide con el greedy en sólo 68 de 120 pares" | **NO REPRODUCIBLE como está enunciado.** El `120` sí existe (`matched_pairs`). El `68` no se pudo reproducir: no hay implementación de matcher óptimo global en el repo con la cual medirlo. Coincidencia notable: 68 es exactamente el número de huérfanas bajo clave exacta — posible confusión de dos magnitudes distintas, pero **no lo afirmo**, no tengo con qué verificarlo. Se retira hasta que exista el matcher óptimo y se pueda medir. |
| "NT8 312" | **NO DETERMINABLE.** No hay ninguna magnitud 312 en este reporte ni en el oráculo. Sin saber qué medía, no se puede ni reproducir ni refutar. Se retira. |

## Hallazgo principal: el desacuerdo de sesión no viaja por el bucket

Sobre las **111 zonas emparejadas por clave exacta** — misma barra, misma
geometría, o sea la misma zona sin ambigüedad de apareo:

| campo | acuerdo Python ↔ NT8 |
|---|---|
| `bucket` | **111/111 idéntico (100%)** |
| `session_index` | **0/111 idéntico** — NT8 = Python **+2**, constante |
| `session_count` (sesiones en el perfil) | 75/111 idéntico (deltas −3, −2, −1, 0) |
| `sample_count` (observaciones del perfil) | **0/111 idéntico** |
| `threshold` (cuantil de detección) | 16/111 idéntico — **95 difieren** |

**Esto refuta la cadena causal que se venía conjeturando.** La hipótesis era:
desacuerdo de calendario → ancla de sesión contaminada → **bucket** corrido →
otra celda anómala → otras zonas. Pero el `bucket` es **exactamente idéntico en
las 111**. La cadena se corta en el eslabón del medio.

`bucket` (SessionRelative) se calcula como
`(anchor_ns − session_begin_ns) / bucket_minutes`: depende de **dónde empieza**
la sesión, no de **cuántas van**. Los dos lados coinciden en dónde empieza. Lo
que difiere es el **conteo** de sesiones transcurridas (+2, constante).

La cadena real es:

```
desacuerdo de calendario (feriado del 3 de julio, warm-up)
    -> distinto NÚMERO de sesiones transcurridas  (+2, medido)
    -> distinta composición del deque de lookback_sessions=20
    -> distinto sample_count en el perfil          (111/111 difieren)
    -> distinto threshold del cuantil              (95/111 difieren)
    -> distinta decisión de anomalía
    -> distintas zonas creadas
```

Nótese que `sample_count` difiere en el **100%** de los casos, incluso en las
75 zonas donde `session_count` coincide: mismo número de sesiones, pero
**sesiones distintas** (corridas 2 lugares), así que distintas observaciones.

### Consecuencia práctica

Tocar `sessions.session_begin_ns` (el ancla) **no cambiaría nada**: ya
coinciden. Lo que hay que reconciliar es la **enumeración** de sesiones — qué
sesiones existen, o sea el calendario de feriados de `sessions.py` contra el
`SessionIterator` de NT8 — porque eso es lo que determina qué entra en la
ventana de 20 sesiones del perfil.

### Y confirma que son dos defectos apilados

De las 68 huérfanas bajo clave exacta:

- **22** (10 Python + 12 NT8) tienen su geometría presente del otro lado **en
  otro instante** — compatible con detección desplazada.
- **46** (25 Python + 21 NT8) tienen una geometría que **no aparece nunca** del
  otro lado — divergencia de detección pura.

La clave de zona resuelve el apareo. **No resuelve esto.** Arreglar sólo la
clave produciría exactamente el error que se quería evitar: creer que el
problema está cerrado cuando el kernel sigue divergiendo.
