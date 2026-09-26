# Manifiesto IPC macro: la misma lógica sobre ES en velas de 500 ticks — BORRADOR 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** BORRADOR. Mira retornos: **STOP**. Corre sólo después de (1) validar el detector con marcas de Nico y (2) su OK explícito a este manifiesto.
**Familia:** IPC (`MANIFIESTO_IPC_IMAN_20260926.md`). La escala es un **eje nuevo de la misma familia**: mismo ledger (`ipc_20260926.jsonl`) y las celdas se suman al presupuesto de multiplicidad (BH sobre el total).

## Por qué
En 25t, R (retroceso medio entre picos) ronda 2–4 ticks y D = k·R, 8–16 ticks: el costo de ida y vuelta de ES se come una fracción grande del recorrido. A mayor escala, la misma fricción pesa menos. **Criterio pre-registrado:** la escala sirve si el costo propio de ES es ≤ 10 % de la mediana de D en las celdas medidas; si no, se reporta como no operable aunque haya información.
**La escala (500t) la eligió Nico antes de ver los resultados de B en 25t**, y antes de que exista cualquier resultado de A con el control C-SW.

## Decisiones
- **Velas:** 500 ticks = 20 velas de 25t agrupadas dentro de cada sesión (`tools/build_agg_tick_bundle.py`; idéntico al constructor nativo porque cada vela de 25t tiene 25 ticks y el constructor reinicia por sesión). ~1.700 velas por sesión en ES.
- **Sesión (decidió Claude a pedido de Nico):** **sesión CME completa (ETH)**, igual que en 25t, sin separar RTH. Motivos: mantiene la continuidad con lo ya medido, maximiza N (la potencia es el límite en macro) y la hora ya entra en el control (± 1 h). RTH/ETH queda como **no medido**, no como celda.
- **Horizonte:** hasta el fin de la sesión (la zona vence ahí). No se arrastran zonas entre sesiones.
- **Detector:** la misma regla (cada pico no supera al anterior). Escalón y retroceso en **ATR(14) de la vela de 500t** en lugar de ticks fijos; separación en velas. Los valores se ajustan con las marcas de Nico en 500t (enero, igual que en 25t) y se **congelan** antes de medir.
- **Validación del detector (target-free):** Nico marca 30–40 zonas en `ES_03-26_202601_500T`. Se exige precisión ≥ 65–70 % fuera de muestra (mismo criterio que 25t). Si no llega, no se mide: un nulo con mal detector no distingue «no hay imán» de «no se ven las zonas».

## Grilla (más chica que en 25t por potencia)
- nivel: **sólo último pico**;
- k: **2, 4**;
- virginidad: virgen / no virgen;
- detector: estándar / estricto;
- volumen: sólo «todos» (los terciles se agregan únicamente si cada celda tiene N ≥ 300 eventos, decidido antes de medir).

**8 celdas.** Controles C-SZ y C-SW como en 25t; pasa a B sólo si gana a los dos, con IC inferior > 0 y el mismo signo en las dos mitades. MDE publicado por celda.

## Embudo B (idéntico a 25t)
Entrada al confirmarse el alejamiento, TP en el nivel + 1 tick, SL a otros D, costos propios de ES y control de entrada al azar con las mismas salidas.

## Justificación económica y refutación
- **Justificación:** la misma que en 25t: stops acumulados detrás de una serie de picos que no se superan. En escala mayor la liquidez acumulada debería ser mayor y la fricción relativa menor.
- **Cómo podría refutarse:** la tasa de regreso no supera a C-SZ o a C-SW; o supera pero el costo es > 10 % de D; o B no le gana a la entrada al azar.
- **Alcance de una muerte:** sólo ES, 500t, este detector y esta población. No mata la escala 25t ni otras escalas.

## No medido
RTH vs ETH; otras escalas (2000t, tiempo); zonas que cruzan sesiones; otros activos.

## Validación del detector 500t (26/09, target-free)
- **Punto de partida** (sin ajustar con marcas): w 2, separación ≤ 30 velas, escalón ≤ 6 t, retroceso ≥ 6 t, ≥ 5 picos → 113 zonas en enero (~4,7 por sesión).
- **Juicios de Nico:** 103 zonas, 69 ✓ / 34 ✗ → **67 %** de precisión sin filtro (`viewer/nt8_bridge/labels/ES_03-26_202601_500T.json`).
- Los ✓ tienen más picos (mediana 7 vs 5), duran más (44 vs 26 velas) y son menos empinados (0,31 vs 0,48 t/vela).
- **Validación cruzada por mitades de enero** (umbral elegido en una mitad, medido en la otra, conservando ≥ 50 % de las zonas): las dos mitades eligen el **tope de pendiente ≤ 0,45 t/vela**. Fuera de muestra: **73 %** (A→B) y **86 %** (B→A).
- **Congelado:**
  - **estándar:** punto de partida + pendiente ≤ 0,45 t/vela (validado fuera de muestra, ≥ 70 %);
  - **estricto:** estándar + ≥ 6 picos (89 % en muestra, 45 zonas; **no validado** fuera de muestra, se reporta como tal).
- **Nota sobre el paso a ATR:** el borrador decía escalón/retroceso en ATR; se congela en **ticks fijos** porque es lo que Nico validó. ATR queda como no medido.
- **Potencia esperada:** ~3 zonas por sesión con el estándar → del orden de 500–600 zonas en las sesiones de exploración, y menos eventos por celda (sólo las que se alejan k·R). Riesgo alto de SIN_POTENCIA en k = 4 y en la variante estricta; se publica el MDE.

## Variantes de entrada (pedido de Nico, 26/09, antes de medir; reemplaza la grilla de 8 celdas)
Nico: la ventaja puede estar (a) en entradas **muy cercanas en el tiempo a la creación**, o (b) en entradas cuando el precio **primero se alejó de una zona virgen y después volvió**. Se miden las dos, además del alejamiento general.
- **E1 alejamiento** (el de 25t): evento = primer cierre a ≥ D = k·R del último pico, zona sin romper.
  - **Momento (eje nuevo):** edad = velas entre la creación y el evento. **temprano** = edad ≤ mediana, **tardío** = edad > mediana. La mediana se calcula por detector y k **sobre las edades, sin mirar resultados**, y se publica. Más «todos».
  - Celdas: detector (2) × virgen / no virgen (2) × k 2, 4 (2) × momento todos / temprano / tardío (3) = **24**.
- **E2 regreso** (sólo zonas vírgenes): después del alejamiento E1, la primera vela cuyo cierre vuelve a ≤ D/2 del último pico **sin haberlo tocado** (si lo toca antes, la zona deja de ser virgen y no hay evento). Resultado: toca el nivel antes de volver a alejarse a D. Controles con las mismas distancias desde el cierre del evento. Celdas: detector (2) × k (2) = **4**.
- **Total: 28 celdas.** BH q = 0,10 sobre las 28 (y se informa también dentro de la familia IPC completa). Sólo último pico.
- **C-SW en 500t:** el pivote reciente se busca en las últimas **100 velas** (≈ 1,5 h), no 300 (300 velas de 500t son media sesión). Decidido antes de medir.
- **Horizonte:** fin de sesión (las series son por sesión).
- Pasa a B: INFO+ contra C-SZ con FDR, mismo signo en las dos mitades, e IC inferior > 0 contra C-SW. Se publica la mediana de D (ticks) por celda para el criterio de fricción.
