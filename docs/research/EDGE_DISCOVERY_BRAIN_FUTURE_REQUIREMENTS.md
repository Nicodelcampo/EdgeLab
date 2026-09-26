# Requisitos Futuros de Arquitectura: Cerebro de Descubrimientos (Edge Discovery Brain)

> **Documento de Diseño Preclínico — No Operativo**  
> **Fecha:** 2026-09-19  
> **Referencia:** Issue #42 y Auditoría Nocturna 2026-09-19  
> **Estado:** `ARCHITECTURAL_REQUIREMENTS_LOCKED` (Sin implementación activa)  

---

## 1. Visión y Principio Rector

El futuro Cerebro de Descubrimientos de EdgeLab no debe limitarse a almacenar hipótesis y resultados de PnL. Su función primordial es actuar como un **epistemólogo metodológico**, acumulando conocimientos sobre:

1. Qué supuestos de medición son válidos y en qué condiciones se quiebran.
2. Qué relaciones semánticas entre datos de microestructura representan verdaderos eventos físicos vs artefactos numéricos.
3. Qué errores metodológicos fueron descubiertos en el pasado para impedir su reaparición sistemática.

### Principio Obligatorio de Cascada de Invalidación

> **"Si se descubre que un experimento o extractor no midió lo que afirmaba medir, todos los resultados, hipótesis dependientes y afirmaciones que descansen sobre esa premisa deben transicionar automáticamente a `STALE_BY_DEPENDENCY`, `REQUIRES_REAUDIT` o `INVALIDATED_BY_MEASUREMENT_ERROR`."**

---

## 2. Modelo de Datos Canónico de Aprendizajes Metodológicos

Cada lección o corrección metodológica registrada por el sistema futuro deberá adherir a la siguiente estructura formal:

```json
{
  "learning_id": "METH-20260919-001",
  "topic": "Causal Zone Fill Measurement",
  "intended_measurement": "Observed market trade execution timestamp strictly posterior to signal availability",
  "actual_measurement": "Synthetic fixed 250ms latency constant added to available_ns",
  "semantic_gap": "Conflated synthetic assumption with empirical market fill observation",
  "error_discovered": "MEASUREMENT_SEMANTICS_FAILURE in build_edge_factory_target_free_store.py",
  "why_it_failed": "Attempted to provide an execution timestamp without streaming tick data",
  "affected_experiments": [
    "EXP-TARGET-FREE-STORE-V1",
    "EXP-HYPOTHESIS-BACKLOG-V1"
  ],
  "affected_dependent_claims": [
    "CLAIM-3.3M-ZONES-WITH-EXECUTABLE-FILL",
    "CLAIM-OVERNIGHT-FOUNDATION-COMPLETE"
  ],
  "prevention_rule": "Pure target-free datasets must record NO_EXECUTABLE_FILL_AVAILABLE unless actual tick sequence is evaluated",
  "required_invariant": "executable_fill_ts is None OR executable_fill_ts in tick_stream",
  "required_test": "tests/test_edge_factory_audit_comprehensive.py::test_no_synthetic_fill_in_target_free_records",
  "valid_scope": "All instruments and bar types",
  "known_exceptions": []
}
```

---

## 3. Catálogo de Campos Obligatorios del Registro Metodológico

1. **`INTENDED_MEASUREMENT`**: La definición conceptual exacta de lo que la investigación pretende cuantificar.
2. **`ACTUAL_MEASUREMENT`**: La implementación de código exacta que efectivamente se ejecutó.
3. **`SEMANTIC_GAP`**: La discrepancia formal entre la intención teórica y el cálculo empírico.
4. **`ERROR_DISCOVERED`**: Clasificación taxonómica del fallo (`MEASUREMENT_SEMANTICS_FAILURE`, `SCALE_DISTORTION`, `DATA_SNOOPING`, `ARTEFACT_COUPLING`).
5. **`WHY_IT_FAILED`**: Diagnóstico de causa raíz (código, suposiciones implícitas, falta de datos).
6. **`AFFECTED_EXPERIMENTS`**: Lista exhaustiva de identificadores de experimentos comprometidos.
7. **`AFFECTED_DEPENDENT_CLAIMS`**: Afirmaciones científicas o reportes invalidados por el fallo.
8. **`PREVENTION_RULE`**: Regla de guardrail inmutable que bloquea la repetición del error.
9. **`REQUIRED_INVARIANT`**: Afirmación matemática o lógica que el validador debe asegurar en runtime.
10. **`REQUIRED_TEST`**: Referencia al test unitario o de integración que previene regresiones.
11. **`VALID_SCOPE`**: Límites de aplicabilidad (activos, regímenes de volatilidad, timeframes).
12. **`KNOWN_EXCEPTIONS`**: Casos de borde explícitamente permitidos (si existen).

---

## 4. Ejemplos Paradigmáticos a Incorporar al Cerebro Futuro

### Ejemplo A: Madurez Temporal de Eventos de Retroceso
- *Intención:* Medir la tasa de retroceso posterior al rompimiento de un nivel.
- *Fallo Descubierto:* Medir en la barra inmediata siguiente cuando la microestructura requiere $K$ barras para definir un swing local.
- *Regla:* "Se deben esperar $X$ barras antes de medir un retroceso porque antes de ese punto el evento de swing aún no está definido geométricamente."

### Ejemplo B: Escala Multiactivo Invariante
- *Intención:* Normalizar espesores de zonas para comparar microestructuras entre activos.
- *Fallo Descubierto:* Dividir por constantes fijas (`0.0001`) asumiendo granularidad FX para contratos de Bonos (`ZB`), Oro (`GC`), Micro Bitcoin (`MBT`) o Dow (`YM`).
- *Regla:* "Toda geometría normalizada en ticks debe resolver dinámicamente el `tick_size` desde `instrument_spec`."

### Ejemplo C: Desacoplamiento de Corredores de Vacío vs Pares de Zonas
- *Intención:* Detectar vacíos de liquidez entre barreras institucionales.
- *Fallo Descubierto:* Emparejar zonas contiguas consecutivas en el log sin evaluar la distancia espacial ni la densidad KDE.
- *Regla:* "Un corredor de vacío solo existe si el perfil de densidad continuo as-of cae por debajo del umbral de régimen a lo largo de un span mínimo de precio."
