# AVZVOL: cinta causal del detector y auditoría del límite O5

**Productor matemático implementado; censo de mercado todavía no ejecutado.**
Se reutilizaron los seis exports O5 ya expuestos sólo para QA de etiquetas,
no para nuevos contrastes ni para certificar las fuentes.

## 1. Productor sin estados finales ni loaders

API: `edgelab.kaggle.avzvol_detector_tape.replay_declared_detector`.
Se empaquetaron únicamente `DEFAULTS`, `_pct`, `_racimo` y `run` del notebook k1
recuperado, SHA256 `58e81f5cf440921a88f164ae3e974709f7296d130f22ecb9271c06fb369ad310`.
El fixture puro distribuido tiene SHA256
`93ef7966589c278c1880d3f89365f63de23484be9147cdba8aa4d19eafdd7b0a`.
Sin imports, bootstrap del notebook, loaders ni funciones de outcomes.
El hash se verifica ANTES de compilar la fuente; dos hooks AST registran snapshots
al crear la zona y cerrar el bloque, sin cambiar el flujo de detección.

El replay exige los parámetros completos del ZP2 histórico, sin cambiar `SPEC=25`
ni hacer clustering (`racimo_min=0`). No reconstruye todavía el roster de racimos.
El run legado conserva internamente su watching/invalidation; esos estados
mutables finales y membresías no salen de la cinta. Añadir/modificar precios de
sesiones futuras en los fixtures no reescribe las decisiones anteriores.

Cada bloque lleva muestra/calibración de sesiones previas, disponibilidad al ancla,
conteo de zonas, origen de sesión y snapshots. Con menos de tres niveles, la rama
histórica de threshold no se ejecutó: se conserva `threshold=null`, aunque se
registre separadamente el umbral matemático derivado del historial previo.
El [clasificador conservador](AVZVOL_ZONE_NEGATIVE_TAPE_20261010.md) mantiene UNKNOWN.
Las colas incompletas se declaran; no se rellenan con la siguiente sesión.

`first_bar_end_ns` y `block_end_ns` son timestamps de cierres de barra declarados,
NO duración completa desde el primer tick ni horizontes físicos O5 certificados.
El replay valida forma/CSR, límites, geometría, orden, no recurrencia de sesiones
etiquetadas y finitud; incluye STOP ante overflow de score. Todo sigue siendo
coherencia de declaraciones, no autenticidad ni paridad del builder con NT8.

### Reproducción offline sin fuente de mercado

Desde checkout instalado con dependencias CPU fijadas:

```bash
python -m tools.avzvol_detector_tape_smoke
```

El smoke tiene datos completamente inventados, sin opciones de paths de mercado.
La CI también lo ejecuta desde un wheel instalado FUERA del checkout. Importar
el módulo no abre datasets. Pasar arrays reales requiere lineage/campaña/gates
ANTES de construirlos; este helper no concede permisos ni reemplaza
`read_research_session`/`require_research_store`.

## 2. Riesgo nuevo en la verificación histórica de O5

En el source fijado, el range forward de 200 barras desde `te+1` incluye
`te+1 … te+200`. La condición de la línea 417 sólo verifica
`send[te+HPOST-1] == send[te]`, es decir `te+199`.
**Puede pasar esa condición con la última barra incluida (`te+200`) en otra sesión.**
Un test del guard histórico exacto lo demuestra con IDs de sesión inventados.
No afirma que haya ocurrido en una frecuencia determinada en mercado.

Una implementación futura debe verificar el último índice realmente incluido,
completitud de todas las ventanas y mismo-session del prewindow también, según
protocolo revisado. Corregir una condición no adjudica el calendario o el reloj.
El fixture del guard, SHA256
`2cb3bba9be80c306a4f4d349726694a34e9b57e3cd2359771a02f950639f4455`,
conserva la condición histórica para caracterización; NO parchea resultados.

## 3. Comprobación real acotada sobre exports existentes

[Registro agregado completo](../../config/research/avzvol_o5_boundary_export_audit_20261010.json).
Se validaron los seis footers, filas y hashes contra la auditoría fijada ANTES
de deserializar cualquier payload. Sólo `contract,cell,kind,session,t0,te,o5`.
No ticks, precios nuevos, endpoint nuevo, P&L ni holdout.

Regla de QA retrospectiva: formar un mapa EXACTO `t0 -> session` con las etiquetas
ya expuestas. Para cada fila con O5 finito buscar `te+200`; si hay una etiqueta
única comparar con la sesión del ancla. Buscar también `te+199` sólo si está
etiquetado exactamente. No interpolar barras no observadas ni seleccionar una
etiqueta favorable ante conflictos. Este lookup posterior NO sirve como feature
as-of, control causal o prueba independiente del reloj.

De 544.531 filas totales, 539.759 tienen O5 finito. En 19.466 filas el último índice tiene una etiqueta observada coincidente; 520.293 no tienen anotación exacta. Cobertura del extremo: 3.61% de las filas O5 finitas. No se observaron contradicciones exactas ni anchors con etiquetas ambiguas.

**UNKNOWN aquí significa que falta esa anotación de barra en el export de eventos,
no que se haya demostrado un hueco en los ticks ni una contaminación de O5.**
Cero contradicciones observadas no elimina el riesgo del guard: no hay mapa completo
bar/session, timestamp de cada extremo ni inicio del prewindow en esos exports.
Los 4.772 O5 faltantes no se atribuyen al desfase; los 4.485 con salida conservan
motivo desconocido. No imputación, filtro correctivo ni reescritura de O5.

| Contrato | Filas O5 finitas | Extremo anotado, misma etiqueta | Extremo sin anotación | Contradicciones exactas |
|---|---:|---:|---:|---:|
| `MNQ_09-25` | 55.852 | 2.584 | 53.268 | 0 |
| `MNQ_12-25` | 106.064 | 3.481 | 102.583 | 0 |
| `MNQ_03-26` | 93.201 | 2.592 | 90.609 | 0 |
| `MNQ_06-26` | 102.857 | 2.742 | 100.115 | 0 |
| `MNQ_09-26` | 147.329 | 6.334 | 140.995 | 0 |
| `MNQ_12-26` | 34.456 | 1.733 | 32.723 | 0 |

Grano: filas evento×celda, NO racimos independientes. Los anchors pueden repetirse
por celda/pseudo; sus etiquetas sirven para lookup, no suman evidencia independiente.
Las categorías y totales se verificaron por dos caminos: groupby/map de pandas y
sets/Counter de Python. Las posibles filas testigo quedan privadas, no se publican
calendarios ni datos raw. Los resultados descriptivos anteriores se preservan con
esta nueva advertencia, no se convierten en réplica corregida ni certificada.

### Reproducir la auditoría de exports

```bash
python tools/audit_avzvol_o5_boundary_exports.py \
  --audit-reference docs/infra/AVZVOL_AUDIT_20261010.json \
  --audit-reference-sha256 AUDIT_SHA256 \
  --inventory exports-locales.json \
  --out-dir CARPETA_NUEVA \
  --allow-exposed-output-audit
```

`AUDIT_SHA256` es el valor fijado en el registro agregado; inventario contiene
exactamente los seis paths locales. No acepta sustituir los pins por latest,
no sobreescribe la salida ni recalcula valores O5.

## 4. Estado y ruta restante, sin confundir software con ciencia

- P1: hashes/estructura y esta QA interna avanzaron; reloj, calendario, continuidad,
  quotes/agresor, selección líquida D-1, warmup y consumo histórico siguen abiertos.
- P2: productor/clasificador de cinta implementados y tests; NO censo real ni
  enumeración de consolidaciones aprobada. `negative_classification_asof_rule`,
  `control_census_selection_rule` y `cross_session_cluster_policy` siguen null.
- P3: desfase histórico documentado; completitud/censura/horizontes físicos siguen
  pendientes. No escoger horizontes mirando el resultado ni usar duraciones
  previas como proxy de la duración real de O5.
- D: no hay nueva confirmación independiente; exposición existente se conserva.
- P4: outcomes económicos siguen prohibidos.

Orden operativo: acreditar las fuentes/sesiones y el warmup necesarios con el
[gate existente](../../edgelab/kaggle/research_access.py); producir la cinta;
congelar la enumeración/as-of y política de sesiones; publicar todos los UNKNOWN
/no soportados; revisar balance y benchmark del propio censo; sólo después
contrastes nuevos no económicos. Evidencia upstream ausente no se puede fabricar
con un token, hash o test. Los listados MCP consultados mantienen catalog v15,
canonical v1 y reexport v2; no prueban por sí solos completitud ni calidad.

## Validación

659 tests +25 subtests; 18 navegación. El wheel incluye el fixture fijado y el smoke
se verificó fuera del checkout. El replay, guard histórico y lookup se prueban con
datos inventados, además de la QA interna de exports declarada arriba. Software
PASS no cierra los bloqueos científicos ni modifica originales.
