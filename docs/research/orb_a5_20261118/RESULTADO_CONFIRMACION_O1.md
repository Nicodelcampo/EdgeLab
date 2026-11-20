# ORB-A5 O1 (ORB de 5 min): confirmación en el holdout A5 de NQ/ES/YM + MidCap y Russell completos (resultado, 2026-11-18)

Estado: RESULTADO — **NO_CONFIRMADA (SIN_POTENCIA al nivel reservado); económicamente no operable.**
- **Pre-registro:** `PREREGISTRO_CONFIRMACION_O1.md`.
- **Apertura y α:** registrados y commiteados antes de calcular desenlaces (`APERTURA_CONF_O1.json`; LORD++ nivel 0,0036, potencia 0,80).
- **Datos:** `CONFIRMACION_O1.json` (decisión y descriptivos) y `OPS_CONFIRMACION_O1.csv.gz` (operaciones).
- **Herramienta:** `tools/orb_confirmacion_o1.py`.
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5.

## Decisión pre-registrada (una vez)
- **Resultado:** n = 10.082 operaciones; **+0,073 R bruto** por operación (EE por sesión 0,031); **p = 0,0093** contra un nivel reservado
  de 0,0036. **No rechaza.**
- **Años positivos:** 60 % (justo en el umbral).
- **Terciles de volatilidad:** ninguno en contra (+0,073, +0,140 y +0,011).
- **Veredicto:** media > 0 sin llegar al nivel → **NO_CONFIRMADA (SIN_POTENCIA)**.
- **Potencia:** el MDE80 al nivel fue 0,078, contra +0,090 declarado. Lo observado (+0,073) queda justo por debajo.
- **Holdout:** el de la familia ORB_A5 quedó consumido. Lo mismo EMD y RTY para el linaje de ORB.

## Lo que dice más allá de la decisión
**El mecanismo bruto existe y es chico.**
- Es parejo entre fuentes: holdout A5 de NQ/ES/YM +0,072; índices nunca usados (EMD, RTY) +0,074.
- Es positivo en los cinco instrumentos: EMD +0,071, ES +0,029, NQ +0,085, RTY +0,081, YM +0,101.
- No hay evidencia de que sea selección: no se desinfla en los datos nuevos.

**Pero no paga.**

| Época | n | Bruto (R) | Neto mini | Neto micro | Operable (fricción ≤ 0,08 R): n, neto mini |
|---|---|---|---|---|---|
| 2006–11 | 2.489 | +0,079 | −0,316 | −0,388 | 37, +0,29 |
| 2012–19 | 3.972 | +0,104 | −0,169 | −0,216 | 308, +0,18 |
| 2020–25 | 3.621 | +0,035 | −0,058 | −0,068 | 2.299, −0,030 |

- **Neto negativo** en todos los instrumentos y épocas, con mini y con micro.
- **El subconjunto operable de 2020–25 da −0,03 R.** Es la única época con tamaño suficiente.
- **NQ 2020–25 en el holdout:** bruto −0,031 (n 303, EE 0,12), neto micro −0,098. El «+0,16 mini / +0,15 micro en NQ 2020–25» de
  DESC+REP **no se reproduce**: era selección o ruido de una sola sub-celda.
- **2024 y 2025:** −0,10 y −0,11 R bruto en el agregado.

## Consecuencias
- **ORB O1 no se opera ni va a las canastas de prop firm.** La línea «T + ORB5» de `SENALES_ESTABLES_LUCID_20261118.md` queda sin base:
  usaba el neto de DESC+REP en NQ 2020–25.
- **El efecto bruto de +0,07 R es real pero menor que la fricción** en todos los instrumentos donde el rango de 5 min es chico. Sólo
  un instrumento con fricción en R mucho menor podría aprovecharlo; ninguno de los medidos cumple en 2020–25.
- **Sin rescate:**
  - no se reinterpreta por instrumento ni por época para buscar el subgrupo que «sí»;
  - O4 y O6/O7 (nominadas en DESC, sin confirmar en REP) no heredan este holdout ni tienen otro.
- **Cómo podría revivir:** sólo como hipótesis NUEVA sobre datos que la familia no usó (por ejemplo, forward desde 2026-10-01 en el
  holdout terminal) y con una ejecución que baje la fricción en R (stop más grande frente al costo). Las dos cosas se pre-registran
  antes de mirar.

## Notas de medición
- Fricción con `edgelab/costos.py`. El costo de EMD es ESTIMADO, dentro del permiso K33 de este pre-registro. RTY y EMD no tienen micro
  en la tabla: su columna «micro» repite el mini.
- 7 de 10.089 operaciones contadas quedaron sin desenlace (riesgo inicial 0 o sin datos al cierre).
