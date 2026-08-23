# `modules/` — código externo en evaluación

Directorio para módulos que **entraron al repo para ser auditados**, no para ser usados.

Regla: nada en `modules/` se importa desde `edgelab/`, se llama desde `tools/`, ni participa de
ninguna corrida formal de paridad, censo o trial. Está fuera del paquete importable a propósito.

Cada módulo lleva un `ESTADO.md` en su raíz que declara, como mínimo:

- qué está validado y **sobre qué datos** (real vs sintético)
- los defectos encontrados en la lectura de ingreso, **documentados y no parcheados**
- las restricciones de orden respecto de estudios pre-registrados vigentes
- qué haría falta para que deje de ser cimiento

| módulo | qué es | estado |
|---|---|---|
| `gate/` | etiquetador de contexto de micro-régimen en `t0` | **`CIMIENTO_SIN_VALIDAR`** — ver `gate/ESTADO.md` |
