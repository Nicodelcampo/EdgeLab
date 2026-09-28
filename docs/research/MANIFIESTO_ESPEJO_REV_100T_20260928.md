# Manifiesto ESPEJO-REV-100T: ¿después de completar el espejo, el precio se da vuelta hacia B? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** OK de Nico (28/09, «ejecutá»). Código `tools/espejo_rev_100t.py`. Kaggle, datos Lucid.
**Origen:** observación visual de Nico en GC 04-26 feb-2026 (12 espejos seguidos, 11 vuelven hacia B). Medido en el mes
completo: 19/39 llegan 0,5 W hacia B antes que 0,5 W más allá de A (≈ azar). Pista independiente: CONT-TPSL ES 25t N4
dio R bruto negativo en las 30 celdas de continuación (equivale a reversión positiva en bruto).
**Febrero 2026 de GC queda excluido** (es el mes que Nico miró para formular la idea).

## Hipótesis y refutación
- **A (cruce, idea de Nico):** una vez que el precio empieza a cruzar el rango de vuelta (primer cierre del lado de B tras
  la completación), llega al x ∈ {25, 50, 75, 100 %} del camino hacia B antes de un extremo nuevo más allá de A, más que
  el azar; y el efecto depende de cuánto se alejó más allá de A antes de empezar a cruzar (overshoot O, terciles).
- **B (TP/SL de reversión):** límite en A a favor de B (se llena si la vela pasó A ≥ 1 tick); alguna combinación TP/SL
  tiene exceso bruto sobre el nulo (aunque no pague costos: se prueba después a mayor escala).
- **Refutación:** ninguna celda supera el máximo estadístico del instrumento; o el efecto es el mismo con cualquier filtro
  (sería genérico de rupturas, no del espejo).
- **Aviso de Nico (efectos que se anulan):** se publican ambos canales (llega / falla) y la distribución por overshoot.

## Diseño
- Configuraciones: GC W ≥ 100 t / 30 velas; ES, NQ, YM niveles 3–5 del visor (17/20, 13/25, 9/30). Velas 100t.
- Filtros: todos; «no lista» + ineficiente (configuración de la captura de Nico).
- Nulo: `simulate_null` desde el cierre del evento, ternas 25t estrictamente anteriores, 300 trayectorias.
- Multiplicidad: máximo estadístico por instrumento sobre todas las celdas (A: x × overshoot × filtro × config;
  B: 15 celdas × filtro × config), bootstrap por sesión recentrado. Landscape completo publicado.
- Tope de cómputo: 8.000 eventos por configuración (orden cronológico; se declara si se alcanza).
- Descubrimiento ≤ 2026-03-31. Confirmación única abr–jun 2026 (Lucid) sólo de lo que sobreviva. Holdout oct+.
