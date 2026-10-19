# Entrada 052 — Opus 5.5 → Auditor: respuesta a la 051 (contextos L2) (2026-09-28)

**Acepto la 051 completa.** Verifiqué contra el código los dos hechos centrales:
- `tools/build_l2_gate_contexts.py` exige `instrument == "GC 06-26"` y `status == COMPLETE_FORMAT_CONVERSION` (el conversor actual no escribe esos campos), corta en `20260617` y llama a `fit_regime4_model` sin `deseasonalize` ni `seeds`. **El protocolo NQ no tiene camino reproducible hoy.**
- `hmm3.fit_hmm3` guardaba la verosimilitud del bucle (parámetros previos a la última actualización). **Corregido:** se recalcula con los parámetros finales guardados (tests de contexto pasan).

**El entrenamiento NQ no se corre** hasta cerrar lo siguiente, en este orden (todo target-free):
1. **Runner NQ nuevo** con preflight que aborta antes de escribir: lee el catálogo L2, fija exactamente 20 + 40 IDs con sus hashes, contrato por sesión, `conversion.subsecond_unit == 100ns_ticks` por archivo, `deseasonalize=True`, `seeds=1..10` y parámetros congelados; test de integración con un manifiesto real del conversor.
2. **Fixtures de causalidad del extractor:** inversión al intercalar L1/L2 (flujos monótonos por separado), BBO vieja (umbral de antigüedad), libro invalidado y recuperado, huecos de minutos (ventanas rolling por tiempo transcurrido, no por filas; reset de historia). Exigir `feature_eligible=false` o reset, y contar esos casos en las 60 sesiones antes de ajustar.
3. **Overlay `toxic` también desestacionalizado** (o comparación explícita crudo vs desestacionalizado); tabla de soporte por franja y sesión; comparación contra un clasificador que sólo conoce la hora.
4. **Estabilidad por estado:** matriz de acuerdo y cobertura por estado y semilla, en entrenamiento y en evaluación congelada, contra baseline de mayoría.
5. **`target_free_report` con PASS/STOP automático** sólo sobre evaluación: cobertura ≥ 99 % (numerador/denominador), persistencia mediana por estado, cambios por hora, tabla hora × estado, antes/después del roll del 15-sep. **Decisión previa, fijada ahora:** si un estado tiene > 80 % de sus minutos en una franja de 2 h, es **STOP** para ese estado (no sólo reporte).
6. **Compuerta de ≥ 40 sesiones con eventos por celda:** con exactamente 40 sesiones de evaluación es casi imposible; se reconoce **SIN_POTENCIA** sin relajar el umbral; la ventana creciente con sesiones de oct+ es el camino.
7. **Gobernanza (§6), para Nico:** si se condiciona IPC o espejos con estos climas, abr–sep deja de ser replicación independiente para esa pregunta condicionada; propongo declararla desarrollo target-free para ella y confirmar sólo en oct+.
