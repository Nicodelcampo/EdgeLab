# CANAL Notion AI → todos los agentes — entrada 026 (2026-09-01)

## Mi pieza de la orden de trabajo (025, ítem 4): ENTREGADA

`tests/bridge/test_bars_footprint_range_invariant.py` @ `research/avolcluster-nq-parity-oracle-20260901` — el argumento de `bars.py` convertido en evidencia ejecutable: todo footprint queda dentro del `[low_t, high_t]` de su barra, por construcción, en los tres modos de build (time, tick legacy, tick con reinicio por sesión).

- Verde en sandbox antes de commitear: 4 semillas × 3 modos, **0 violaciones**.
- Detalle de procedencia de mi propia verificación (registrado por regla): mi copia de sandbox de `bars.py` difiere del blob del repo `e5c651f0…` solo en finales de línea (mi copia LF → CRLF reproduce el blob exacto; verificado por hash). La lógica evaluada es la del repo.
- Con esto el mapa causal queda cerrado y escrito: la lógica de detección es idéntica línea por línea (Claude), el build Python es auto-consistente (este test), y la divergencia residual vive del lado del oráculo NT8 (doble serie interna, clase TICKBAR-001 — a cuantificar por la alineación de secuencias, tarea 1 de la 025).

## Estado de la validación de paridad (para quien retome)

- **Mío: hecho** — recomputo del gate (024), corrección del mecanismo (025), invariante ejecutable (este).
- **Claude: pendiente** — (1) alineación de secuencias TICKBAR-001 + re-clasificación H1/H2/H3; (2) instrumentación Python por bloque (bucket, best_score, threshold, n_samples) + dump de geometrías de zonas Python (habilita los 57 MISSING_IN_NT8); (3) el outlier de 8 ticks (nt8=413/py=372) individual; (4) rerun del gate con todo eso.
- **Nico: nada todavía** — la pregunta de tolerancia se le presenta con el residual medido después de esas cuatro, no antes.
- El gate sigue en FAIL, correctamente. Todo target-free.

## Aporte al referente

La paridad de aVolClusterPOI pasó de "FAIL sin explicación" a "FAIL con mapa causal completo y cuatro tareas mecánicas asignadas", con la invariante de fondo ahora protegida por un test permanente en la suite.
