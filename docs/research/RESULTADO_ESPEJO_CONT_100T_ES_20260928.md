# ESPEJO-CONT-100T-FILTROS — ES (Lucid) — resultado (2026-09-28)

Kaggle `edgelab-espejo-cont100t-es-20260928` (código con el nulo corregido: arranca en el cierre de la vela de entrada).
Artefactos `artifacts/espejo/cont100t_kaggle/ES/out/`. 213 sesiones de descubrimiento.

**Veredicto: 0 de 1.035 celdas sobreviven el máximo estadístico (t crítico 4,05; p global 0,079).**

| Nivel | Trades (candidatos) | R bruto medio (todos, 15 celdas) | Exceso medio sobre el nulo |
|---|---|---|---|
| 1 | 602 | −0,042 W | +0,017 |
| 2 | 2.301 | −0,061 | +0,001 |
| 3 | 6.716 | −0,064 | +0,001 |
| 4 | 8.000 (17.125) | −0,081 | −0,006 |
| 5 | 8.000 (41.659) | −0,105 | −0,008 |

## Lectura
- **Con el nulo corregido el exceso es ≈ 0 en todos los niveles.** El R bruto negativo no es información del espejo: es la
  mecánica de la entrada. El toque de A es por mecha y la vela suele cerrar de vuelta; entrar con stop en A + 1 tick
  arranca en desventaja respecto del precio real, y el nulo que arranca en ese cierre reproduce la pérdida.
- **Corrige la lectura de CONT-TPSL ES 25t** («continuación pierde ⇒ reversión gana»): con el nulo viejo el exceso salía
  −0,06 a −0,13 y lo atribuí a reversión; es geometría de entrada, no una tendencia a volver hacia B. Una entrada de
  reversión (límite en A) tiene la imagen especular de esa ventaja sólo si se llena, y los llenados en el toque sufren
  selección adversa: se mide aparte en ESPEJO-REV, sin darla por buena.
- Filtros (VWAP, EMA 20/50/200, S2v2, «no lista», ineficiente): ninguna combinación sobrevive. Los R brutos positivos
  (35/1.035) están en celdas chicas (n 69–385) y no pasan la corrección.
