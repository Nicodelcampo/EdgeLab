# Pre-registro (BORRADOR): ESPEJO-PICOS — el espejo clasificado por qué picos tomó la ida (07/11/2026)

Estado: BORRADOR — no lanzar hasta observar el barrido sin condicionales (`espejo_macro_10t_20261107/`, pedido de Nico). Se cierra en
un commit propio, con el hash del referente, antes de lanzar.

## Hipótesis (Nico)

Si el primer impulso existió para tomar picos de liquidez, cuando los tomó el motivo desapareció. Entonces la vuelta completa el espejo
(llega a A) o va más allá.

**Cómo podría refutarse:**
- los espejos con picos tomados no llegan a A ni lo pasan más seguido que los que no tomaron ninguno, a igual ancho, duración y
  horario; o
- la diferencia no se ve en R neto.

## Definición (`edgelab/research/espejo_picos.py`, tests en `tests/research/test_espejo_picos.py`)

- **Detector:** el mismo del padre ESPEJO-MACRO-10T (causal, umbrales laxos). El módulo padre no se toca.
- **Pico:** pivote del lado del impulso de w velas de 10 ticks, confirmado antes de A y vivo (sin romper) hasta A. Los picos vivos
  forman una escalera, como en `tools/peaks_rule.py`.
- **Tipo** (perilla, decisión de Nico: los dos):
  - **cualquiera:** todo pico vivo en las 2000 velas previas a A;
  - **consecutivo:** sólo los de series de 3 o más con separación ≤ 60 velas (w = 3) o ≤ 200 velas (w = 10).
- **Escala del pivote:** w = 3 o w = 10.
- **Qué tomó la ida:**
  - cantidad de picos tomados: 0, 1–2, 3+ o cualquiera;
  - posición media dentro del impulso: inicio, medio o final;
  - sobrepaso del último pico tomado: ≤ 0,10 W, ≤ 0,25 W o más;
  - si quedaron picos vivos más allá del extremo.
- **Fijo como en el padre:** fracción de entrada, ancho en viajes de fricción y RTH.
- **Ejecuciones (8):** stop en B (1 tick o 10 % de W) × objetivo A, 1,25 W, 1,5 W (más allá de A, la hipótesis) o 2R.
- **Tamaño:** 259.200 celdas por canal.

## Orden de medición

1. **Información, sin P&L:** probabilidad de llegar a A y de pasarlo (1,25 W y 1,5 W) por clase, contra el control emparejado. El
   control son los espejos sin picos tomados con el mismo ancho, duración y horario.
2. **Embudo en R:** con linaje hijo de ESPEJO_MACRO_10T_{NQ,ES,YM,GC}, que hereda su multiplicidad.

## Después (fase 2)

La misma estructura de «qué tomó la ida» con:
- niveles de sesión (máximos y mínimos del día previo, overnight, OR30, VWAP);
- gaps;
- volumen de la ida y clímax en B;
- OG/VI de LuxAlgo, zonas HFT, aVolZone y BigTrap2.
