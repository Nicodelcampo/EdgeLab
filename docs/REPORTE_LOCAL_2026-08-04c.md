# Reporte local (3) — 2026-08-04 · captura P2 auditada y un veredicto inalcanzable

> Ejecutado en la computadora operativa. Continúa `REPORTE_LOCAL_2026-08-04b.md`.
> Referente: `docs/NORTH_STAR.md`.

## 1 · Captura P2 — la deuda de schema está cerrada

El probe recompilado (`2f300f7`, ver reporte 1 §3.2) produjo una captura nueva.
Comparación medida contra P1, con el mismo auditor:

| | P1 (build viejo) | **P2 (probe v2.1)** |
|---|---|---|
| `schema` | `event_capture_raw_v2` | **`event_capture_raw_v2_1`** |
| `schema_ok` | **`False`** | **`True`** |
| `schema_errors` | `140 valores centinela extremos` | **`[]`** |
| `sentinel_values` | **140** | **0** |
| `transport_ok` | `True` | `True` |
| `transport_errors` | — | `[]` |
| filas | 1.685 | 2.505 |
| warnings | 3 | 2 |
| exit code del CLI | 1 | **0** |

Transporte, en detalle: `callbacks_seen = rows_written = n_rows = 2505`,
`dropped_at_queue = 0`, `writer_errors = 0`, `capture_utc_regressions = 0`. Sin
pérdida entre callback y disco.

Procedencia, que era el objetivo del schema v2.1: los tres campos que en P1 no
existían ahora están declarados y ninguno quedó como placeholder —
`provider_label = NinjaTrader Simulated Data Feed`,
`account_environment_label = simulation`,
`source_timezone_label = America/Argentina/Buenos_Aires`. El warning de P1
*"schema v2 legado: provider/account/timezone no separados"* **desapareció**.

Composición de la captura: `Ask` 1321, `Bid` 1031, `Last` 112, `DailyVolume` 41.

## 2 · DEFECTO — el veredicto `PASS` es inalcanzable por construcción

A pesar de todo lo anterior, el veredicto de P2 es **idéntico** al de P1:
`TRANSPORT_PASS_WITH_SCHEMA_DEBT`.

La causa está en `edgelab/data/capture_tsv.py:80-85`:

```python
@property
def verdict(self) -> str:
    if not self.transport_ok:
        return "TRANSPORT_FAIL"
    if not self.schema_ok or self.warnings:     # <-- `or self.warnings`
        return "TRANSPORT_PASS_WITH_SCHEMA_DEBT"
    return "PASS"
```

Cualquier warning fuerza la etiqueta de **deuda de schema**, aunque
`schema_ok is True` y `schema_errors` esté vacío — que es exactamente el estado
de P2.

Y uno de los dos warnings restantes es **permanente por construcción**:

```
capture_tsv.py:290-294   emite el warning si
                         source_sequence != "NOT_EXPOSED_BY_THIS_NT8_CALLBACK"
CaptureEventProbeV2.cs:132  escribe SIEMPRE ese literal exacto
```

El callback de NT8 no expone una secuencia de origen; el probe lo declara con
honestidad y el auditor lo registra como límite de observabilidad. **Correcto de
ambos lados.** Pero como el warning nunca puede faltar, `PASS` **no es
alcanzable** para este instrumento en ninguna captura, presente o futura.

### 2.1 Por qué importa

El veredicto es la línea que alguien lee cuando decide si una captura sirve como
evidencia. Hoy dice `TRANSPORT_PASS_WITH_SCHEMA_DEBT` tanto para P1 —que tenía
140 centinelas y `schema_ok=False`— como para P2, que no tiene ninguno. **La
etiqueta no distingue una deuda real de un límite declarado del feed**, y el
exit code (1 contra 0) sí los distingue: los dos canales del mismo auditor
discrepan.

El riesgo concreto es la lectura inversa a la de INC-007: allá se promovía con
gates que decían PASS sin serlo; acá se puede descartar evidencia válida porque
la etiqueta dice deuda cuando no la hay.

### 2.2 Arreglo propuesto — NO implementado

Separar *deuda* de *límite declarado*. Dos formas, ambas mínimas:

**(a)** Distinguir los warnings por naturaleza: los que son deuda subsanable
(centinelas, schema legado) contra los que son límite estructural del feed
(`source_sequence` no expuesta). Sólo los primeros degradan el veredicto.

**(b)** Agregar un estado intermedio explícito, p. ej.
`PASS_WITH_DECLARED_LIMITS`, para `schema_ok and transport_ok` con warnings
únicamente estructurales.

No se implementa acá porque **cambia la semántica de un veredicto que otros
documentos citan** (`docs/bridge/capture_tsv_audit.md` §"Interpretación P1"
declara `TRANSPORT_PASS_WITH_SCHEMA_DEBT` como el resultado *esperado* de P1).
Tocarlo sin acordar la taxonomía dejaría esa documentación desalineada.

## 3 · Observación sobre el feed (no es defecto, es dato)

`source_time_regressions = 29` sobre 2.505 filas (máximo 50 ms): el timestamp de
origen **retrocede** 29 veces dentro de la captura. En P1 fueron 44 sobre 1.685.

No es un bug del probe —que registra lo que recibe, sin reordenar— sino una
propiedad del flujo de callbacks. Importa declararlo porque cualquier consumidor
que asuma monotonía en `source_time` va a estar asumiendo algo falso. El orden
que sí es monótono y verificado es `callback_seq` / `capture_seq`, que es
precisamente la razón por la que `EventIdentity v2` los separa.

Recordatorio de alcance: esta captura viene del **Simulated Data Feed** de
NinjaTrader (ticks sintéticos, `TicksPerSecond=2`), declarado en
`provider_label`. Sirve para validar identidad y procedencia de captura, que es
lo que el contrato pide; **no** es evidencia sobre microestructura de mercado
real.

## 4 · Canal de lectura del auditor — confirmado

Confirmo que puedo leer los cambios y el razonamiento de la sesión de
investigación **desde el repositorio**, sin intermediación:

- `git fetch` sobre `github/work/research-architecture-hardening` funciona; se
  vinieron sin problema `b574d6c` y `f4367a2` en cuanto se publicaron;
- los mensajes de commit y los documentos de `docs/` transportan el razonamiento
  completo (INC-007, la enmienda G2, las mediciones de paridad, el guard del
  censo) y se leen íntegros;
- el tip leído al momento de escribir esto es `f4367a2`.

Límite del canal, declarado: la página de Notion **no** es legible desde acá; su
contenido sólo llega cuando se exporta. Todo razonamiento que viva únicamente en
Notion es invisible para esta máquina — como pasó con `§13.25 "Deuda inmediata
descubierta"`, la sección donde el export se cortó y que contenía justo los dos
bloqueos que invalidaban mi lectura de G2.

## 5 · Estado y pendientes

Cerrado hoy:

- pytest canónico de los siete commits del stack G2 (586 passed);
- `.cs` no compilable (CRLF) → corregido, compilado y verificado por artefacto;
- deuda de schema de la captura → **cerrada y medida** (§1);
- frontera de estimando `p_global` / `theta_trade` → declarada (reporte 2 §3.1);
- riesgo del corte de holdout → **retractado**, ya lo cubre la puerta única.

Abierto, y quién lo debe resolver:

| pendiente | de quién |
|---|---|
| criterio #5 de §12 (DSR con dependencia): tres caminos enunciados, ninguno elegido | Nico |
| taxonomía de veredictos del auditor de captura (§2.2) | investigación |
| calendario CME versionado: dos feriados medidos, riesgo de romper HFTZones2 | investigación |
| censo de 200 sesiones | bloqueado por lo anterior |
| paridad de `aVolCellPOI2` | falta el oráculo en esta máquina |
| `LongPathsEnabled=1` | operador (admin + reinicio) |

**Aporte al referente:** la captura queda con procedencia completa y sin deuda
medible, y se documenta que el veredicto del auditor no puede expresar ese
estado — un instrumento que no puede reportar éxito es tan riesgoso como uno que
no puede reportar fallo.
