# Plan de integración de producto

## Objetivo

Una base explícita, módulos entendibles y un camino reproducible para humanos y agentes. Considerar futuros consumidores autónomos sin implementar ahora ccbus, servidor o su planeación local.

## Fase 1 — Navegación y límites (este cambio)

- README y entrada única; instrucciones de agentes breves.
- Registro legible por máquina, mapa de componentes y catálogo stdlib sin operaciones.
- Checks focales de estructura y rutas. Sin afirmar suite histórica verde.
- Inventario de ramas/PR con corte y procedencia. No archivar ni mergear por conteo.

## Fase 2 — Reconciliar base y entorno

Main `ab9a054` y foundation `617064e` tienen ocho y 1.711 commits exclusivos respectivamente. Mantener los avances de main y seleccionar infraestructura de foundation en lotes revisables. No adoptar uno de los árboles a ciegas.

Reproducir issue 37 en Python 3.12/Ubuntu; corregir rutas locales, datos faltantes y contratos Arrow sin skips globales. Acreditar instalación/imports fuera del repo y smoke sintético. Los checks del catálogo no sustituyen estos requisitos.

### Avance de entorno en esta base

Se agrega empaquetado de subpaquetes, lock CPU, configuración de rutas sin efectos de import, tests sintéticos y workflow CPU/wheel. La suite de main pasa antes de este lote (19 tests en Python 3.12), pero eso no prueba ni arregla la suite de foundation. La reconciliación sigue pendiente y no se abre ninguna reserva de datos.

### Primer port selectivo de foundation

Se recuperan configuración typed/precedencia y parser NT8, timezone e identidad de eventos con sus tests. Se incorporan pruebas sintéticas para los módulos que ya eran byte-idénticos: contratos/regímenes, continuo, memoria, controles y preflight. Se recuperan además typed_registry, schema_validator y retrieval, dependencias ausentes detectadas por tests de relaciones/consulta. Los 35 esquemas se empaquetan como recursos; esto no implementa el atlas ni SSRN. Los tests de historia real/anchors y los dos checks de oráculo real no se arrastran.

La [matriz de comparación](../config/module_reconciliation_20261009.json) describe los snapshots originales: 49 archivos edgelab idénticos, 16 diferentes, 98 sólo-foundation y 10 sólo-main; 28 archivos validation idénticos. Es comparación de blobs, no equivalencia semántica ni estado live.

## Fase 3 — Datos y ejecución

### Avance CPU aislado (2026-10-10)

Se integra el alcance acotado del aislamiento de PR 63: recortes por D0/D1, horizonte completo, presupuesto float64 y oráculo sintético. Se fortalece el batching público, split congelado en CLI, compatibilidad inverse/reverse y preservación de outputs. La route del runner queda CPU-only; upstream/features, data gate 65 y paridad GPU end-to-end siguen pendientes. No se mergea 64 ni se cierran 63/64 como totalmente resueltos.


Revisar PR 65 (gate no conectado a todos los consumidores), 63 (aislamiento de arrays y parity), y la infraestructura de 64 separada de campañas. Adaptar PR 68 a la base elegida, con preflight, shards por contrato, merge fijo y evidencia verificable. El título/body de 68 está desactualizado respecto de su evidencia final: reconciliarlo antes de usarlo como estado.

## Fase 4 — Memoria, bibliografía y Brain

Hipocampo durable ya está presente en main y foundation: no portar 56 otra vez sin diff semántico. PR 67 declara sustituir 52; revisar bootstrap y deuda de ledger/metadatos. Revisar raíz 57 y cadena 43/46/56/58 para elegir componentes, no hacer merge automático de toda la cadena.

## Fase 5 — Bridge, visor y módulos laterales

Separar infraestructura del visor PR 48 de bundles y campañas; conservar paridades específicas, marcas exploratorias y threads de revisión. Ubicar propfirm/context/GEX/regímenes como módulos con consumidores explícitos. Catalogar FP4 y learning-packet adapter antes de duplicarlos.

## Fase 6 — Histórico y estado

Sólo cerrar PR reemplazados tras equivalencia documentada. Conservar backup/preserve, auditorías congeladas, negativos e invalidaciones. PR cerrado/mergeado a una feature no demuestra integración de su HEAD actual en main.

## Criterios de aceptación por lote

Propósito/rutas claros; dependencias y permisos explícitos; tests focales y CI de integración reales; ejemplo sintético; evidencia conservada; sin lectura de reservas ni promoción automática. No confundir un PASS de navegación con producto listo para research autónomo.

## Fuentes del corte

- [Issue 37: CI](https://github.com/Nicodelcampo/EdgeLab/issues/37).
- [PR 67: reemplazo SSRN](https://github.com/Nicodelcampo/EdgeLab/pull/67).
- [PR 68: evidencia final](https://github.com/Nicodelcampo/EdgeLab/pull/68#issuecomment-6092785805).
- [Inventario de organización](../config/repository_inventory_20261009.json): 123 ramas, 27 PR; observación histórica, no estado live.
