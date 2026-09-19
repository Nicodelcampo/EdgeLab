# Auditoría de Semántica de Medición — Edge Discovery Factory

> **Fecha:** 2026-09-19  
> **Rama:** `audit/edge-discovery-factory-foundation-20260919`  
> **Referente:** `docs/research/EDGE_DISCOVERY_FACTORY_SPEC.md`  
> **Principio Canónico:** Si el código midió un proxy diferente de lo que decía medir el informe, se clasifica como `MEASUREMENT_SEMANTICS_FAILURE`.

---

## 1. GAP-01: Fills Sintéticos por Latencia Fija vs Fill Ejecutable Real

- **INTENDED_MEASUREMENT:** El timestamp del primer tick observable del mercado en el cual una orden de entrada podría ejecutarse causalmente tras la disponibilidad de la señal (`executable_fill_ts > signal_available_ts`).
- **ACTUAL_IMPLEMENTED_MEASUREMENT:** Un timestamp sintético derivado mediante una constante aritmética fija:
  $$\text{executable\_fill\_ts} = \text{signal\_available\_ts} + 250{,}000{,}000\text{ ns}$$
- **SEMANTIC_GAP:** Se sustituyó la observación del mercado por una constante arbitraria de 250 ms. En instrumentos de baja liquidez o fuera de RTH, 250 ms puede no contener ningún trade. En instrumentos de alta frecuencia (NQ/ES en RTH), 250 ms representa cientos de ticks transcurridos.
- **AFFECTED_CLAIMS:**
  - `3.328.710 zonas causales con fill ejecutable`: **RECHAZADO**. Las zonas tienen timing causal de disponibilidad, pero no poseen fill observado.
  - `100% disponibilidad causal verificada`: **CORREGIDO**. Causalidad de señal sí; fill ejecutable no.
- **PREVENTION_RULE:** Prohibido fabricar timestamps de ejecución mediante offsets fijos. En datasets puramente target-free sin cálculo de ejecución, el campo debe ser `null` con estado `NO_EXECUTABLE_FILL_AVAILABLE`. Si se requiere fill, debe obtenerse mediante búsqueda del primer tick real con `ts > signal_available_ts`.
- **REQUIRED_REGRESSION_TEST:** `test_no_synthetic_fill_in_target_free_records` en `tests/test_edge_factory_audit_comprehensive.py`.

---

## 2. GAP-02: Escala de Precios Aproximada vs Especificaciones Canónicas de CME

- **INTENDED_MEASUREMENT:** Espesor de zonas y distancias geométricas normalizadas exactamente en ticks nativos del contrato (`height_ticks = (top - bottom) / tick_size`).
- **ACTUAL_IMPLEMENTED_MEASUREMENT:** Una regla heurística binaria simplificada:
  ```python
  tick_size = 0.25 if ("ES" in inst or "NQ" in inst) else 0.0001
  ```
- **SEMANTIC_GAP:** Esta regla heurística produce distorsiones masivas en 8 de los 11 instrumentos:
  - `YM` (Dow): tick real es `1.0`. Se dividió por `0.0001` (error de factor $10{,}000\times$).
  - `ZB` (Bonos 30Y): tick real es `0.03125` ($1/32$). Se dividió por `0.0001` (error de factor $312.5\times$).
  - `GC` (Oro): tick real es `0.10`. Se dividió por `0.0001` (error de factor $1{,}000\times$).
  - `MBT` (Micro Bitcoin): tick real es `5.0`. Se dividió por `0.0001` (error de factor $50{,}000\times$).
  - `6E` (Euro FX): tick real es `0.00005`. Se dividió por `0.0001` (error de factor $0.5\times$).
  - `6J` (Yen): tick real es `0.0000005`. Se dividió por `0.0001` (error de factor $0.005\times$).
- **AFFECTED_CLAIMS:** Todas las distribuciones de percentiles de `height_ticks` en el censo nocturno para activos distintos de ES y NQ quedaron completamente invalidadas por distorsión de escala.
- **PREVENTION_RULE:** Ningún cálculo geométrico en ticks puede usar condicionales ad-hoc. Debe invocar obligatoriamente el registro centralizado `edgelab.edge_factory.instrument_spec.get_instrument_spec()`.
- **REQUIRED_REGRESSION_TEST:** `test_canonical_instrument_specs_all_11_assets` y `test_price_to_ticks_conversion`.

---

## 3. GAP-03: Emparejamiento Consecutivo de Zonas vs Corredores Reales de Densidad

- **INTENDED_MEASUREMENT:** Estructuras de canal o corredores de baja densidad entre murallas activas de liquidez, calculados a partir de un perfil continuo de densidad as-of (KDE) y persistencia causal.
- **ACTUAL_IMPLEMENTED_MEASUREMENT:** Emparejamiento mecánico trivial de zonas consecutivas en el tiempo:
  $$\text{Corredor}_i = (\text{zona}_i, \text{zona}_{i+1}) \quad \text{con } \text{density\_score} = 0.5$$
- **SEMANTIC_GAP:** Esto no mide canales de liquidez ni vacíos espaciales. Produce exactamente $N - 1$ pseudo-corredores por sesión, explicando por qué se reportaron $3{,}325{,}972$ corredores frente a $3{,}328{,}710$ zonas (diferencia de sólo $2{,}738$, correspondiente al número de sesiones con al menos 2 zonas).
- **AFFECTED_CLAIMS:**
  - `3.325.972 corredores`: **RECHAZADO FORMALMENTE**.
  - `Espesor mediano de corredores`: **INVALIDADO**.
  - Hipótesis de traversing de corredores: **BLOQUEADAS**.
- **PREVENTION_RULE:** El feature store validado no puede publicar corredores hasta que el motor canónico de densidad KDE del visor sea portado offline y certificado. Mientras tanto, debe clasificarse como `BLOCKED_PENDING_CANONICAL_CORRIDOR_ENGINE`.
- **REQUIRED_REGRESSION_TEST:** `test_corridor_pseudo_pairing_detection`.

---

## 4. GAP-04: Contradicción Narrativa de Simetría BULL/BEAR

- **INTENDED_MEASUREMENT:** Reportar de forma veraz y exacta la proporción empírica observada de zonas alcistas y bajistas en la población.
- **ACTUAL_IMPLEMENTED_MEASUREMENT:** Los datos medidos registraron inequívocamente:
  - `BULL`: $663{,}094$ zonas ($19.92\%$)
  - `BEAR`: $2{,}665{,}616$ zonas ($80.08\%$)
- **SEMANTIC_GAP:** En la prosa del informe maestro y en el markdown del censo se afirmó:
  > *"BULL 49.9% vs BEAR 50.1% — Simetría casi perfecta"*
  
  Existe una discrepancia de más de 30 puntos porcentuales entre la medición real ($80/20$) y la narrativa textual ($50/50$). La asimetría real refleja la microestructura de absorción en los mercados de futuros durante el período estudiado, mientras que el texto introdujo un sesgo de confirmación infundado.
- **AFFECTED_CLAIMS:**
  - `Simetría casi perfecta 49.9% / 50.1%`: **RECHAZADO**.
  - `0 anomalías críticas`: **RECHAZADO**.
- **PREVENTION_RULE:** Todo texto de reporte debe ser generado directamente a partir de variables evaluadas en el código, prohibiendo terminantemente números hardcodeados en plantillas de texto.
- **REQUIRED_REGRESSION_TEST:** `test_contradiction_detection_side_ratio`.

---

## 5. GAP-05: Biblioteca de Plantillas vs Hipótesis Descubiertas Autónomamente

- **INTENDED_MEASUREMENT:** Backlog autónomo de hipótesis analíticas generadas creativamente por inferencia de datos.
- **ACTUAL_IMPLEMENTED_MEASUREMENT:** Expansión cartesiana de una biblioteca predeterminada:
  $$20\text{ familias pre-fijadas} \times 4\text{ universos de activos} = 80\text{ registros}$$
- **SEMANTIC_GAP:** Las hipótesis no fueron descubiertas por un agente autónomo ni deducidas de anomalías del censo; fueron instanciadas desde plantillas conceptuales pre-escritas. Además, las etiquetas de `expected_information_gain` fueron asignadas por heurística estática (`HIGH`, `TRANSFORMATIVE`) sin base empírica.
- **AFFECTED_CLAIMS:**
  - `80 hipótesis autónomamente descubiertas`: **RECLASIFICADO** a `SEEDED_HYPOTHESIS_TEMPLATE_LIBRARY`.
  - `Ranking target-free verificado`: **CORREGIDO** a `AUTHOR_PRIOR_INFORMATION_GAIN`.
- **PREVENTION_RULE:** Separar estrictamente hipótesis generadas por templates de aquellas derivadas por inducción algorítmica.

---

## 6. GAP-06: Scaffold de Orquestador vs Sistema Operativo

- **INTENDED_MEASUREMENT:** Infraestructura operativa para ejecutar experimentos, invocar herramientas, monitorear recursos y recuperarse de fallos.
- **ACTUAL_IMPLEMENTED_MEASUREMENT:** Una clase de recorrido topológico de grafos en memoria que simula la ejecución cambiando estados internos de cadenas (`node.status = "COMPLETED"`).
- **SEMANTIC_GAP:** No ejecuta procesos del sistema operativo, no gestiona timeouts reales, no controla memoria de subprocesos ni valida artefactos generados.
- **AFFECTED_CLAIMS:**
  - `Orquestador operativo completo`: **RECLASIFICADO** a `ORCHESTRATOR_SCAFFOLD_ONLY`.
- **PREVENTION_RULE:** No declarar como "operativo" ningún componente que no haya sido validado mediante tests de integración con procesos reales.
