# SOM y R (AtrPhase) en índices no mirados: MidCap (EMD) y Russell (RTY) sobre M1 real de futuros (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — commiteado antes de correr sobre EMD y RTY. Pedido de Nico: subió el M1 de RTY y MidCap para confirmar SOM y R
(«ya subí lo que me pediste»). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4
(confirmación en instrumentos no usados). Herramienta: `tools/m1_largo.py correr … som|fs EMD|RTY` y `analizar_indices`.

Antecedentes: m1_largo RESULTADO.md (SOM bruto +0,064 R y R AtrPhase +0,097 ATR en años limpios de NQ/ES/YM), som_transfer_20261117
(SOM en el CFD del Russell 2019-03 → 2026-09: no transfirió en neto, con fricción alta), F-FRICCION-RELATIVA-REGIMEN.

Potencia previa: plan de `holdout_ventanas.plan_potencia` con la mitad del bruto de los años limpios como efecto:
- SOM: efecto 0,032 R, sd 1,0, N ≈ 5.100 → potencia 0.739, n para decidir 6.038;
- R: efecto 0,048 ATR, sd 0,6, N ≈ 680 → potencia 0.67, n para decidir 967.

Las dos quedan por debajo de 0,8 con la mitad del efecto. Con el efecto entero de los años limpios superan 0,99 (SOM) y 0,95 (R). Es la
mejor potencia posible con estos datos. Un NO_CONCLUYENTE no refuta.

## 1. Datos y ventanas
- **EMD** (E-mini S&P MidCap 400): 2006-01-09 → 2025-07-31. Nunca usado por nadie.
- **RTY** (futuros CME desde 2017-07):
  - para R, 2017-07-10 → 2025-07-31 (no usado);
  - para SOM, sólo 2017-07-10 → 2019-02-28, porque `som_transfer_20261117` miró el Russell (CFD) desde 2019-03.
- **Costos:**
  - RTY: los canónicos.
  - EMD: spread ESTIMADO de 2 ticks y comisión estimada (`costos_canonicos.json`, sólo dentro de `costos.estimados_permitidos`, K33).
  - La prueba es en bruto, así que el costo estimado sólo afecta al neto descriptivo.

## 2. Pruebas (dos)
- **SOM** (sin_finde, R) y **R** AtrPhase (ATR20): BRUTO por operación, EMD y RTY juntos, en sus ventanas limpias.
- **Veredictos:**
  - **A_FAVOR** si IC90 inferior > 0 y ≥ 60 % de años positivos;
  - **EN_CONTRA** si media ≤ 0 con potencia ≥ 0,8 para la mitad del efecto de referencia;
  - si no, NO_CONCLUYENTE.
- **Descriptivo:** bruto y neto por índice y período (2006–2011, 2012–2019, 2020–2025).

## 3. Contador, justificación y refutación
- **Contador:** 2 pruebas, familia `M1LARGO_EXTERNAS_20261117`.
- **Justificación económica:**
  - SOM: el impulso de la apertura de NY es un flujo común a los índices de EE. UU.;
  - R: la fase de ATR describe la expansión del rango intradía, también común.
  - Si son mecanismos y no propiedades del Nasdaq, tienen que aparecer en el MidCap y en el Russell.
- **Cómo podría refutarse:** bruto ≤ 0 con potencia en EMD + RTY; o NO_CONCLUYENTE con media ≤ 0 (señal que no transfiere).
