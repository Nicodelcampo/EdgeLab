# Tanda 5: T+Z+R a tamaño mínimo, veto de noche para PREAPERTURA-ES y filtro Franklin de T en forward (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de calcular. Pedido de Nico: «dale con todo». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Nada mira el holdout para elegir; lo nuevo se decide en forward desde
2026-11-14 (o desde el primer día con la herramienta lista, declarado en el forward).

## T5a. T+Z+R a tamaño mínimo junto a la cartera (descriptivo; elige qué seguir)
- Tamaño: **1 MNQ por regla** (T, Z y R; Z y R con el stop de catástrofe 0,5 × ATR20). Es el menor posible: a 200 USD Z y R ya estaban en 1 MNQ
  y T en 3; la quema de la tanda 4 (34 %) venía de ahí.
- Mismo cálculo que C2 (`tools/cartera_tanda4.py`, ventana 2025-08-05 → 2026-09-29, prop 50K, media contraída y media 0) para v2 + TZR mín,
  v3 + TZR mín y v2 + T mín sola.
- Regla de uso declarada: una versión con TZR entra al forward como paralela si su quema (media contraída) ≤ 10 % **y** su probabilidad de
  pasar ≥ la de la cartera sola. Si no, nada cambia.

## T5b. PREAPERTURA-ES sin operar con noche movida (sólo forward)
- Hipótesis (salió de la tanda 4, dirección opuesta a la pre-registrada): PREAPERTURA-ES rinde menos con noche ALTA (tercil superior del rango
  18:00 → 09:30 relativo contra los 250 previos, causal). Como el holdout de PREAPERTURA-ES ya se vio, **sólo el forward decide**: se siguen las
  operaciones de PREAPERTURA-ES con y sin veto, con e-proceso sobre «R sin veto − R con veto» por sesión (cotas −6/+6 R). Contador: 1.

## T5c. Filtro Franklin de T (forward)
- El filtro que pasó en `reels_20261116/RESULTADO.md` (T sólo si su lado coincide con el sesgo NY vs Londres y VWAP en el minuto de entrada) se
  sigue en el forward de T+Z+R como versión paralela «T filtrado»: e-proceso propio, mismas cotas que T. Contador: 1 (ya contado en FRANKLIN 7).

## No se hace (con motivo)
- **TORI con salida al cierre**: el motor de TORI no tiene objetivo «cierre» (sus ejecuciones son SWING/MID/CORTO × 2 stops). Agregarlo cambia
  los índices de la ejecución congelada y exige re-correr ticks de futuros en Kaggle; TORI no está en la cartera. Queda propuesto.

## Justificación económica / cómo podría refutarse
T5a: con el tamaño mínimo, la descorrelación (0,08) debería sumar sin llevar el drawdown fuera de la cuenta; se refuta si la quema sigue > 10 %.
T5b: la noche movida adelanta el movimiento que la ruptura de las 09:30 necesita; se refuta si el forward no muestra diferencia. T5c: igual que
en el resultado de reels.
