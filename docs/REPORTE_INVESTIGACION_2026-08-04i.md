# Reporte de investigación (9) — contrato de decongestión de primeros toques

Se cerró antes de outcomes el grado de libertad que impedía integrar la nueva
población al censo.

La separación de 120 minutos se conserva como restricción existente, pero se
mueve explícitamente al instante operativo correcto: `first_touch_ms`. Se aplica
por sesión CT y reinicia en cada frontera de sesión.

Los empates son esperables porque BigTrap2 marca lifecycle al cierre de barra.
Se congeló FIFO (`created_ms` más antiguo, luego `zone_id`) para no privilegiar
un side ni mirar resultados.

`first_touch_decongestion.py` implementa el contrato y devuelve eventos
conservados, rechazos, resumen por sesión y metadata outcome-free. Falla cerrado
ante identidades duplicadas, timestamps inválidos y fechas de sesión inválidas.

Siguiente integración: ejecutar `extract_first_touch_events` y luego
`decongest_first_touch_events` dentro del censo completo, condicionado a los
gates de integridad y cobertura.

**Aporte al referente:** el proceso de eventos quedó definido en el instante de
entrada real, con frontera y desempate reproducibles, antes de observar tasas o
outcomes.
