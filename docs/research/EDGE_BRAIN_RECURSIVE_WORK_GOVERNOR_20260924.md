# Edge Brain — gobernador de trabajo recursivo (propuesta de infraestructura)

**Estado:** prototipo determinista, pendiente de CI/revisión; no es un daemon.
**Objetivo:** hacer que cada ciclo 24/7 mejore la capacidad de ciclos futuros sin medir progreso por horas de CPU, tokens ni cantidad de tareas.

## Qué cambia

`edgelab/edge_brain/work_governor.py` implementa un planificador puro: recibe candidatos con referencia a evidencia, reutilización esperada, reducción de bloqueos/incertidumbre, costo finito, dependencias y fallos previos; emite `READY`, `WAIT_HUMAN`, `BLOCKED` o `PARKED`, con puntuación explicable. Reutilizar una mejora se pondera más que producir trabajo aislado. Errores repetidos o ciclos sin avance aparcan el candidato. El feedback calcula resultados reutilizables/verificados, supuestos falsados, bloqueos resueltos y rendimiento de aprendizaje por unidad consumida; si hay gasto y cero aprendizaje, recomienda `STOP_AND_DIAGNOSE`.

## Lo que deliberadamente NO hace

- No llama a Claude, no invoca procesos, no toca red, secretos, datos de mercado, ledger ni cuentas.
- No ejecuta research/outcomes/holdout, despliegue o trading en unattended mode.
- No convierte una propuesta de LLM en evidencia, no adjudica lessons y no promueve hipótesis.
- No afirma ni promete crecimiento exponencial. El score solo asigna un presupuesto pequeño a trabajo candidato; la curva se medirá con outputs reutilizables por unidad de recurso en ventanas consecutivas.

## Ciclo objetivo (a construir en fases, no activar automáticamente)

1. **Observar:** leer el estado del repo, tests, bloqueos e historial de episodios con hashes/identidad.
2. **Proponer:** modelo sugiere candidatos, cada uno ligado a una falla reproducible, P pendiente, prueba faltante o infraestructura compartida.
3. **Gobernar:** este planner filtra/ordena dentro de allowlist y presupuesto; cualquier acceso sensible queda en espera humana.
4. **Ejecutar:** futuro executor aislado, idempotente, con límite de tiempo/recursos, locks de escritor y outputs en cuarentena.
5. **Verificar:** CI y validadores independientes prueban resultado, procedencia, tests y no regresión. Fallar no equivale a aprender.
6. **Aprender:** el Brain registra una lección propuesta con causa raíz, referencia y test; aprobación separada para incorporarla como regla durable.
7. **Compounding:** solo tareas que dejen herramienta, test, mejor recuperación, dato indexado con derecho de uso, o hipótesis falsada y reutilizable alimentan los ciclos posteriores.

## Métricas para evaluar si el tiempo vale

- `verified_reusable_outputs / resource_units` (principal).
- Bloqueos reproducibles cerrados y lecciones con test de regresión.
- Hipótesis correctamente falsadas por costo, contabilizando sus límites de alcance.
- Horas/ciclos sin progreso, tiempo de rework, retries y fallos repetidos.
- Throughput aceptado por revisión/CI, no propuestas generadas.

No se llamará “exponencial” a una mejora por una gráfica ascendente corta. Primero se necesita una serie de mediciones comparable y normalizada por costo, sin cambios silenciosos de criterio, y demostrar que cada mejora reusable aumenta el rendimiento futuro en holdout técnico independiente. La ventaja compuesta puede ser superlineal solo si el rendimiento medido por unidad de recurso crece sin aumentar fallos, sesgo o deuda.

## Camino de entrega con gates

A. Mantener este módulo sin efectos secundarios y añadirlo a CI.  
B. Diseñar un lector read-only del Brain/estado de Git; cubrir errores de integridad con abstención.  
C. Añadir un executor de sandbox con límites, no con credenciales de mercado.  
D. Pilotear solo auditoría, tests e índices deterministas; comparar con baseline manual.  
E. Revisar métricas por un humano antes de aprobar tareas research. Cualquier análisis de retornos/P&L necesita preregistro, presupuesto y OK explícito por el NORTH_STAR.  
F. Solo tras evidencia mantenida de valor, decidir operación continua en Debian y política/cuota de Claude API. No habilitar auto-deploy ni trading.

**Aporte al referente:** prototipo de gobierno que intenta convertir recurrencia en trabajo acumulativo: prioriza reutilización, presupuesto finito, fallos/stagnation y medición del aprendizaje; no confunde autonomía con autoridad ni actividad con progreso.
