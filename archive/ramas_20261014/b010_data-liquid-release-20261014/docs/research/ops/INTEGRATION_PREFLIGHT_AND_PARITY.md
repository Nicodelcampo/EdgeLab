# Integración de elegibilidad y primer candidato de optimización

Estado: **METADATA_ONLY + SYNTHETIC_PARITY_ONLY**. No ejecución autónoma de mercado ni cambio en la campaña activa.

## Adaptador de preflight canónico

`tools.research_ops.preflight.check_bundle` consume el contrato de `edgelab.data.research_data_gate.require_research_eligibility`, sin duplicar su lógica de calendario, contrato, liquidez ni challengers causales D-1. El formato es exactamente `research_gate_request_v1` con las ocho claves de request canónicas. No admite comandos, rutas de datos o campos de ejecución.

Además del pin de certificado, régimen y límites existentes, exige un SHA256 externo del archivo JSON completo. Lectura acotada a 1 MiB, archivo regular POSIX sin seguir el último symlink, apertura no bloqueante para rechazar FIFO, rechazo de claves repetidas y NaN/Infinity, control de cambios durante lectura. Los componentes padre del path y el filesystem pertenecen a una identidad confiable; no es un sandbox para paths hostiles. El resultado siempre mantiene `execution_allowed=False`, `authority_authenticated=False`, `promotion_allowed=False` y `market_data_read=False`.

El hash NO autentica autoridad ni crea permiso. Los pins reales deben venir de un registro aprobado independiente, nunca calcularse a partir de entradas arbitrarias para hacerlas pasar. El chequeo no produce un certificado; valida afirmaciones previamente revisadas. Un CLI exitoso no inicia la cola ni un subprocess.

```bash
python -m tools.research_ops.cli preflight-metadata APPROVED_METADATA.json --expected-sha256 EXTERNAL_APPROVED_SHA256
```

### Campaña MNQ exploratoria: límite importante

La campaña vigente tiene autorización exploratoria por contrato y riesgo de fuente declarado; **no tiene certificación del original**. Este preflight NO la convierte en `SANITIZED_VERIFIED` ni puede sustituir su autorización de alcance distinta. Un archivo `avzvol_exploratory_authorization_v1` es rechazado por este adaptador canónico; eso es incompatibilidad de alcance, no un hallazgo nuevo de error en el dataset.

El ejecutor exploratorio y su selección exacta deben integrarse mediante su adaptador específico, pins y revisión de riesgos, sin elevar el estatus científico ni habilitar reservas. Hasta implementarlo y revisarlo, Research Ops no adopta, relanza ni programa campañas reales. La corrida externa ya autorizada sigue intacta.

## Candidato de rendimiento: rango previo por sesión

El runner actual calcula en cada señal el máximo de highs menos mínimo de lows de las 256 barras previas, limitado al inicio de sesión y excluyendo la barra del trigger. El candidato de este hito demuestra esa semántica en enteros sintéticos mediante deques monotónicas; no procesa señales ni outcomes reales.

- Referencia: slices y max/min repetidos, aproximadamente O(n × ventana).
- Candidato: deques con máximo/mínimo deslizantes, aproximadamente O(n), con reset por sesión.
- Inputs explícitos alineados, enteros, sesiones monótonas; ventana 1–3000 y hasta 16.384 barras.
- Tests cubren límites de ventana, igualdad de precios, precios negativos, sesión nueva y exclusión de la barra actual; paridad aleatoria reproducible con seed fija y referencia independiente.
- Benchmark fijo de 4.096 barras, cuatro sesiones, ventana 256, tres repeticiones; conserva todos los tiempos, identidad de input y output. Los dos métodos incluyen validación de inputs.

```bash
python -m tools.research_ops.cli benchmark-synthetic
python -m unittest discover -s tests/research_ops -v
```

**No extrapolar los tiempos sintéticos a MNQ.** Python entero no equivale a NumPy/Numba en el motor; el host comparte CPU con la corrida. Este microbenchmark no demuestra aceleración de campaña, consumo total, paridad de filas o resultados económicos. El candidato no se instaló en el runner activo.

La integración debe medir primero el perfil real: precomputar rangos por sesión o reutilizarlos por barra sólo si el ahorro supera materialización/memoria, comparar contra la implementación real, conservar censuras y filas idénticas y tener fallback explícito. No abrir nuevos datos para medirlo.

## Evidencia y siguiente hito

`PHASE2_TEST_EVIDENCE.json` registra 77 tests focales en Python 3.12 y las mismas 77 pruebas en 3.13, además de 18 pruebas de navegación en 3.12. No son 154 pruebas científicas independientes. Fixtures de certificados son inventadas, exclusivamente para tests. No se modificaron controles canónicos ni la campaña activa.

Siguiente hito: revisión del adaptador exploratorio específico y su contrato de ejecución, con identidad del runner, pins de fuente/selección/código, checkpoint externo, presupuesto y verificación de particiones. Después, benchmark de paridad del motor completo en inputs ya aprobados. Aún quedan planner/LLM, revisión científica independiente, gasto API, alertas y despliegue continuo separados.
