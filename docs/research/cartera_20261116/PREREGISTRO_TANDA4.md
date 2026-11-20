# Tanda 4: conexiones para subir rentabilidad y bajar riesgo de quema (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de calcular. Pedido de Nico: «sí» a las conexiones 1, 2, 5 (baratas) y 3, 4 (mayor potencial).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Herramienta: `tools/cartera_tanda4.py`. Nada mira el holdout
para elegir; **noviembre ya no es limpio para lo que se elija acá** (se vio por regla), así que toda versión nueva se decide en el forward desde
2026-11-14.

## C1. Re-elegibilidad con el filtro de fricción (M1 confirmado)
- Se repite la regla de selección §5 de `PREREGISTRO.md` **aplicando antes M1 a todas las reglas** (se saltean las operaciones con fricción canónica /
  riesgo > 0,08). E2 pasa a medirse sobre las operaciones que quedan. Mismos E1, E3–E6, mismo orden por R contraído, ≤ 2 por familia, correlación ≤ 0,5,
  máx. 10. Sesiones ≤ 2026-10-30.
- Resultado: **cartera v3** (si cambia respecto de la v2). Aviso declarado: la idea de reincorporar TORI-NQ-R y PREAPERTURA-ES se propuso sabiendo
  que PREAPERTURA-ES ganó en noviembre; por eso v3 sólo se decide en forward. Contador: 1.

## C2. Cartera conjunta (v2 o v3) + canasta T+Z+R
- T, Z y R en MNQ: micros fijos por regla con el riesgo mediano de desarrollo (T: |entrada − stop|; Z y R: el stop de catástrofe 0,5 × ATR20 de la tanda
  2) a ≈ 200 USD; Z y R con stop de catástrofe. Ventana común 2025-08-05 → 2026-09-29 (desarrollo de la cartera).
- Medidas: correlación diaria entre la cartera y T+Z+R; t diario, drawdown y probabilidad de pasar / quemar la evaluación 50K
  (`estimar_propfirm.sim`, media de desarrollo contraída y media 0) de: v2, v2 + TZR, v3, v3 + TZR. Descriptivo: elige qué seguir en forward.

## C5. Freno diario de cartera
- Regla declarada: si el P&L del día de la cartera llega a **−500 USD** (2,5 × 200), no se toman más operaciones ese día. Se evalúa en la
  simulación de prop (con y sin freno) para cada versión de C2. Descriptivo; si baja la quema sin bajar la probabilidad de pasar, se agrega al forward.

## C4. Noche movida como contexto (la pista de ASIA) para PREAPERTURA-NQ, PREAPERTURA-ES, T y Z
- Noche = tercil del rango 18:00 → 09:30 relativo, contra sus 250 previos (causal; misma definición que ASIA). H: R (o neto) con noche ALTA > resto.
- Descubrimiento/confirmación: T y Z — A 2020–2023, B 2024 → 2026-09; PREAPERTURA — DESC → REP. Pasa si la dirección se repite en B/REP con p < 0,10
  (bootstrap por sesión) y BH sobre las 4. Contador: 4.

## C3. Ruptura de PREAPERTURA a través de un cluster HFT grande (próxima vuelta)
- Necesita las tablas de clusters del E0-b (`hft_clusters_u1_20261110`) cruzadas con las rupturas de PREAPERTURA (Kaggle). Se pre-registra en
  detalle antes de lanzarse; acá sólo queda declarada.

## Justificación económica / cómo podría refutarse
C1: el filtro de fricción quita las operaciones que sólo pagan costos; reglas buenas en bruto pasan a ser elegibles. C2/C5: mecanismos
descorrelacionados y un freno diario reducen la quema más que lo que bajan la media. C4: la noche movida marca días con información. Refutación:
v3 = v2, la combinación no mejora la quema, el freno no ayuda, la noche no ordena fuera de la muestra de descubrimiento.
