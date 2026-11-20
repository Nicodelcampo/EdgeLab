# T (FtmEngine): ¿el cambio de 2020 es de todo el mercado? Confirmación en MidCap y Russell (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — commiteado antes de mirar T en EMD y RTY. Las operaciones ya se generaron ayer con la corrida de FundedSync sobre
esos índices (`FS_OPS_EMD/RTY.csv.gz`), pero T no se analizó ni se imprimió nunca: sólo se contaron operaciones por módulo. Pedido de
Nico: «indagá más en T, pasó de estar en una cartera a no estar sin tanto motivo». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4.

Antecedentes: exploratorio de hoy, sobre datos ya vistos de NQ/ES/YM, medido en R = neto / riesgo propio de T:
- El tope de 100 puntos del stop de T no se activaba antes de 2018 en NQ y recorta el 25–72 % de las operaciones desde 2020. Pero no es la
  explicación: en NQ 2020–2025, T rinde lo mismo con y sin tope (bruto +0,175 y +0,178 R).
- Bruto en R:
  - NQ: +0,036 (2008–2019) → +0,18 (2020–2025);
  - ES: +0,015 → +0,10;
  - YM: ≈ 0 → +0,11.
- El salto aparece en los tres índices a la vez.
- La conclusión de ayer, «T sin señal antes de 2020», salió de medir en ATR. En R, la señal previa en NQ es chica pero existe: se corrige.

Potencia previa: `holdout_ventanas.plan_potencia` con efecto = mitad del bruto 2020–2025 de T en NQ/ES/YM (≈ +0,13 R), sd 1,2, N ≈ 2.500
(EMD + RTY, 2020–2025): potencia 0.856, n para decidir 2.108.

## Hipótesis
Desde 2020 cambió algo de todo el mercado de índices de EE. UU. que favorece la ruptura del rango de apertura filtrada de T. Candidatos
(no se prueban acá): el auge minorista de 2020 y las opciones de vencimiento diario desde 2022.

## Prueba (una)
- **Qué se prueba:** T (lógica de fábrica, riesgo propio en R), en EMD + RTY, sesiones 2020-01-01 → 2025-07-31, BRUTO por operación.
- **Veredictos:**
  - **A_FAVOR** (el cambio de 2020 es de mercado) si IC90 inferior > 0 y ≥ 60 % de años positivos;
  - **EN_CONTRA** si media ≤ 0 con potencia ≥ 0,8;
  - si no, NO_CONCLUYENTE.
- **Descriptivo:**
  - EMD 2012–2019 (antes del cambio) y el neto con costos (EMD estimado, K33);
  - T por año 2016–2025 en NQ, ES, YM, EMD y RTY, para ver cuándo empieza el cambio.

## Consecuencias declaradas
- **A_FAVOR:** T vuelve a ser un pilar con el estatus de «ventaja de régimen post-2020 confirmada en índices no usados». Las carteras B y B'
  siguen en paralelo y el tamaño lo decide el forward.
- **EN_CONTRA:** el salto es propio de NQ, ES y YM, o de cómo se eligió T, y T queda frágil.

## Contador y refutación
- **Contador:** 1 prueba, familia `M1LARGO_EXTERNAS_20261117`.
- **Justificación económica:** la ruptura del rango de apertura gana cuando el día continúa la dirección de la primera media hora. Si
  desde 2020 los flujos que empujan el día en una dirección son más fuertes (coberturas de opciones de vencimiento diario, flujo minorista
  concentrado en la apertura), el efecto tiene que verse en todos los índices.
- **Cómo podría refutarse:** media ≤ 0 en EMD + RTY 2020–2025 con potencia.
