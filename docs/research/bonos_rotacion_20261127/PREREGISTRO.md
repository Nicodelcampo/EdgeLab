# BONOS-ROTACION: la versión swing de la técnica de la charla, con bonos propios y comisión cero (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — antes de calcular cualquier exceso. Se miró la foto de spreads de data912 (sin retornos). BONOS-RATIOS ya había
medido la reversión, sin P&L, en DESC y REP: es un antecedente declarado.

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2.** **Familia:** `RATIOS_BONOS_AR`, la misma que BONOS-RATIOS.
- **Pruebas:** 6.
  - Primaria: canasta de los 4 pares con ventana de 15 ruedas.
  - Secundarias: cada par con 15 ruedas (4) y la canasta con 7 ruedas (1).
- Pedido de Nico: releer la charla, aplicar sus técnicas concretas y las condiciones del broker (VetaFLAT: comisión cero y más cupo), y
  volver a probar si hay ventaja explotable.

Cambio respecto a falla previa:
- BONOS-RATIOS midió si el ratio revierte, pero no una regla operable.
- La charla agrega tres cosas:
  - el operador hace sobre todo **swing de 2–3 días** con el promedio de 7/15 días, buscando 0,7–1 %;
  - rota **en tandas, nunca todo**: 50/50 en el promedio, 80/20 en los extremos y siempre un 20–25 % remanente;
  - opera **con bonos propios y comisión cero** (plan flat), así que el costo es sólo el spread y los derechos.
- Esa regla, congelada, es la que se mide acá.
- La versión intradía (velas de 5 s a 30 min) **no se puede medir**: no hay intradía histórico disponible desde el entorno (el endpoint
  de Open BYMA Data no fue autorizado).

Antecedentes:
- `bonos_ratios_20261127/RESULTADO.md`: revierte en 3/4 pares; no lo hace desde la salida del cepo;
- `biblioteca_ideas_20261028/RATIOS_BONOS_LUCIONI_20261126_TRANSCRIPCION.md` y `…_RESUMEN.md`;
- `RATIOS_BONOS_FUENTES_DE_DATOS_20261127.md`.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7:
- K32: todo por EdgeLab;
- K34: costos estimados y declarados;
- K36: se decide al cierre de t y se ejecuta al cierre de t+1;
- A5: DESC y REP; HOLDOUT sellado (la familia conserva su única apertura).

Potencia previa:
- La reversión medida en DESC da desvíos típicos de 1,6–2,3 % con pendiente de −0,15 a −0,25 por cada 5 ruedas.
- Con rotación de ±0,3 del capital, el exceso bruto esperado es del orden de 0,05–0,15 % por mes, antes de costos.
- Con ≈ 20 meses DESC por par, la t esperada es ≤ 1,5 si no hay ventaja grande: **potencia baja (≈ 0,3–0,5)**, declarada.

Diagnóstico de mecanismo: sin grilla. Los valores (ventana de 15 y 7 ruedas, 80/20, z = 2) vienen de la charla, no se buscaron. Se publican:
- costo ×0,5 y ×2;
- el bruto sin costos;
- la rotación media diaria;
- el capital mínimo para pagar el abono.

## Costos y condiciones del broker (VetaFLAT, vetacap.com.ar/personas, consultado el 2026-11-27)
- **Comisión y aranceles de mercado:** 0 %. Igual se cobran los derechos de BYMA de 0,01 % por lado, peor caso.
- **Spread:** foto de data912 del 2026-11-27 a las 19:07 de Buenos Aires, después del cierre. Es una cota alta:

  | Bono | Spread |
  |---|---|
  | AL30 | 0,085 % |
  | GD30 | 0,223 % |
  | AL35 | 0,527 % |
  | GD35 | 0,506 % |
  | AE38 | 0,324 % |
  | GD38 | 0,743 % |
  | AL41 | 0,292 % |
  | GD41 | 0,791 % |

  El costo por unidad rotada es la mitad de cada spread más los derechos.
- **Abono:** PRO $85.000, ADVANCE $160.000 y ELITE $285.000 por mes, más IVA.
- **Cupo de saldos y bonos de aire:** 175 %, 250 % y 400 % de la cartera.
- **Bonos de aire:** se reciben a 24 h y se recompran al día siguiente en contado inmediato. Sirven para cortos de un día, no para el swing
  de 2–3 días. Por eso la regla usa bonos propios.

## Lectura (decidida antes)
- **Primaria:** canasta de 4 pares con 15 ruedas y costo ×1, exceso mensual contra 50/50 en DESC.
  - CONFIRMA si t ≥ 1,645, y se replica una vez en REP (t ≥ 1,645).
  - NO_CONCLUYENTE si la media es > 0.
  - EN_CONTRA si la media es ≤ 0.
- **Secundarias:** cada par con BH q 0,10 en DESC.
- **Económico (descriptivo):** capital mínimo para cubrir el abono = abono / (exceso mensual × cupo).

## Justificación económica
La prima de ley NY entre bonos del mismo flujo se desarbitra por flujos puntuales y vuelve a su media en 1–4 semanas
(`bonos_ratios_20261127`). Rotar hacia el bono relativamente barato, sin quedar nunca afuera del par, captura esa vuelta sin exponerse
al riesgo país. Con comisión cero, el costo es sólo el spread.

## Cómo podría refutarse
- Exceso ≤ 0 después de costos en DESC, o que no replica en REP.
- Exceso positivo pero menor que el abono para un capital razonable.
- Que el bruto sea positivo y el neto no: en ese caso es el spread, no la señal, lo que decide.
- En todos los casos, la técnica no es explotable en su versión swing con estos datos; la intradía queda sin medir.
