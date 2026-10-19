# Propuesta archivada: campaña multi-instrumento con Edge Brain (2026-09-23)

**Estado:** `ARCHIVADA` por decisión de Nico. No aprobada, no ejecutada. **No se corrió ninguna búsqueda sobre retornos.**
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Idea
Las mismas 5 familias con justificación económica (momentum, reversión a VWAP/EMA, ruptura del rango de apertura, cierre de gap nocturno y ruptura por ATR), corridas sobre GC, ES, NQ, YM y 6E. Se usa research-v2, solo la parte pre-holdout (< 2026-06-30T22:00Z), con barras de 5 minutos, 7 meses de descubrimiento y 4 de validación en cada instrumento.

- **Regla de supervivencia:** MCPT contra el máximo de toda la búsqueda con p < 0,05, IC neto de validación > 0 y réplica en al menos 2 instrumentos.
- **Costos:** supuestos por instrumento, sin transportarlos entre instrumentos.
- **Edge Brain:** registra todo. Techo de promoción `LESSON_CANDIDATE`, rige `NO_SELF_APPROVAL`, y la decisión final es de Nico.

## Por qué multi-instrumento y no más variantes
Más variantes suben la vara de corrección y bajan el ratio de sobrevivientes reales. Más datos, y sobre todo la réplica entre instrumentos, bajan el MDE.

## Ejecución prevista (servidor Debian, cuando haya acceso SSH)
- **Fase 0:** entorno Python 3.12 y paridad de máquina contra la PC, comparando hashes.
- **Fase 1:** copia solo pre-holdout, con verificación contra `recut_index.json`.
- **Fase 2:** pre-registro congelado y comiteado antes de correr.
- **Fase 3:** servicio `systemd` con unidades chicas reanudables y procedencia dirty-aware.
- **Fase 4:** veredicto con la regla escrita y el landscape completo, todo registrado en el Brain.

## Para retomarla
Paquete STOP con el manifiesto definitivo y OK explícito de Nico.

Hallazgo de contexto: el Edge Brain no genera estrategias. Es memoria, elegibilidad e invalidación. La generación de hipótesis sigue pendiente de las pruebas de contaminación (paso 6 de `EDGE_DISCOVERY_BRAIN_FOUNDATION_20260919.md`).
