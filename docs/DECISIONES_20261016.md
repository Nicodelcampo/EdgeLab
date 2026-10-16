# Decisiones de Nico — 2026-10-16

Estado: VIGENTE
Fecha: 2026-10-16
Fuente: sala de Chaski, mensajes de Nico a gonzasib-claude del 2026-10-16. Asentadas el mismo día (protocolo de documentación §5).

1. **Orquestación: Python orquesta, los LLM son roles.** Pregunta de Nico (un agente avanzado orquestando todo vs. varios de capacidad media en bucle). Recomendación aceptada ("sí"): el que orquesta es código, no un LLM; los modelos se reparten por juicio requerido. Implementado en `edgelab/autopilot/roles.py`.
2. **La mejora es un imperativo global:** infraestructura de agentes, módulos individuales y eficiencia; sistema que se repara y mejora a sí mismo. Registro de mejoras con separación automático / sólo humano: `edgelab/autopilot/mejora.py`.
3. **La promoción humana no es necesaria.** Decisión textual: "la idea del sistema es que la promoción humana no sea necesaria". Implementado como promoción automática con perímetro en código (`edgelab/autopilot/promocion.py`) bajo la enmienda `docs/incidents/AMENDMENT_AUTONOMIA-A1_2026-10-16_PROPUESTA.md`.
4. **Fricción como criterio implícito de los agentes:** elegir escenarios macro donde la fricción es baja y no correr análisis donde la fricción probablemente gana. `edgelab/autopilot/friccion.py` (regla 3× por viaje).
5. **Herramientas y aprendizaje recursivo** (informe RRE-AI del 2026-10-15): los agentes del servidor deben conocer y crear herramientas, aplicarlas a los descubrimientos, y usar ingeniería predictiva e inversa. Catálogo: `config/autopilot/herramientas.json`; lentes `ingenieria_inversa` y `meta_etiquetado` en `edgelab/autopilot/contexto.py`.
6. **Foco inmediato:** lo que falta para que la infraestructura esté lista en el servidor (SV1). Kit: `deploy/debian/`.
7. **"firmo, apruebo y mergea"** (sobre la enmienda AUTONOMIA-A1 y el PR #121). Qué se hizo con eso:
   - La firma queda asentada acá y en el encabezado de la enmienda. **El texto todavía no está en `docs/NORTH_STAR.md`**: por la condición (d) de la propia enmienda el agente no puede modificar ese documento ni su hash; ese commit tiene que ser de Nico (o una instrucción explícita suya de que lo haga el agente, que quedaría registrada). Hasta entonces `auto_promocion` sigue en `false`.
   - El PR #121 se mergea a `foundation/f0b-compatibility-probe` una vez verde el CI (los tres tests rojos eran de higiene documental: registro de módulos, índice de docs y fecha de `docs/CURRENT.md`).
8. **Auditar el informe k32 e integrarlo como aprendizaje** del sistema: `docs/research/AUDITORIA_K32_REPLICACION_RRE_20261016.md`.
