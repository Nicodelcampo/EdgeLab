# Familia EXEC-PASIVA-ES — registro MEDIDO / NO MEDIDO (2026-10-17)

Manifiesto: `F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md` (enmienda A1 incluida). Kernel `edgelab-f0-exec-pasiva-es-v1` v2. Resultados: `f0_results_20261017/EXP_F0_RUN2_A1_RESULTS.json`.
Referente rector: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## MEDIDO (ES, ticks L1, 178 sesiones de descubrimiento + 121 de confirmacion 2026-04-01..09-30; holdout >= 2026-10-01 intacto)
- Decisiones: cierre de cada barra 100T (3,73 M obs. lado-decision en descubrimiento). Orden pasiva al touch, sin recotizar, `tau` = 60 s, regla de fill conservadora `R_TT` (trade-through de 1 tick).
- **Veredicto primario: `PASIVO_NO_CONVIENE`.** `F` = 0,860 (confirmacion 0,862). `M_p | fill` = -0,68 ticks; `M_a` agresiva incondicional = -0,55 (= medio spread); **`A*` = -0,13 ticks** (IC unilateral 97,5 % [-0,149, -0,110]; confirmacion -0,12 [-0,148, -0,092]; version con cluster por sesion, ver F0C abajo). Valor por intento sin edge: pasivo -0,59 vs agresivo -0,55.
- Con `R_TT` la seleccion adversa (-0,68 tras fill) se come el spread capturado. Simetria compra/venta OK (|dif| = 0,015 tick).
- Heterogeneidad (Holm sobre 3, `A*`, `R_TT`): a favor vs en contra de la barra previa: **en contra** +0,30 tick mejor (`A*` +0,02 vs -0,28), p ~ 0; spread 1 vs >= 2: spread >= 2 +0,83 mejor (+0,65 vs -0,18; solo 6 % de las decisiones); primera media hora vs resto: sin efecto (p = 0,47).
- Cierres de impulso del corredor (T2, n = 10.616): `A*` = -0,10 (IC [-0,22, +0,01]): no difiere de la poblacion general.
- **Cota optimista `R_TOUCH`:** `F` = 0,956 y `A*` = +0,69. La verdad esta entre ambas reglas y depende de la posicion en la cola, **que L1 no observa** (ver Fase 0C).

## NO MEDIDO / limites
- **Fills reales en el mercado.** La Fase 0C simula la cola con el feed de NT8 (ver abajo) pero las cancelaciones por delante son inobservables; el resultado real puede caer en cualquier punto del rango [-0,16, +0,63].
- Cotizacion vieja (L1 solo trae cotizacion en filas de trades). Costos de comisiones (se asumen los del modelo de k35, **sin verificar** que 1,546 ticks = 1 tick spread + ~0,55 comisiones).
- Salidas (TP pasivo vs stop de mercado), recotizacion/seguimiento, otros instrumentos, otros `tau`/`h` mas alla de la grilla publicada, edge direccional.
- Una corrida previa (version 1 del kernel) dio `PASIVO_RECUPERA` por un estimando pareado que equivale al spread por construccion; **anulada** (enmienda A1). La ventana de confirmacion se leyo en esa corrida.

## Lectura
Con fills conservadores, entrar pasivo en el touch no mejora a cruzar el spread (-0,13 tick), salvo en contextos poco frecuentes (spread >= 2) y, marginalmente, cuando la orden va en contra de la barra previa (~0). El pasivo solo gana si la regla optimista se acerca a la realidad.

## Fase 0C — cola real con el feed L1 de NT8 (2026-10-17; autorizada por Nico: levanta `research_allowed`, solo jul-sep)
Pre-registro: seccion 13 del manifiesto. Kernel `edgelab-f0c-exec-pasiva-es-l1cola-v1` v3 (commit `4356e22e`). Resultados: `f0_results_20261017/EXP_F0C_L1COLA_RESULTS.json`.
- Datos: 65 sesiones usables (2026-07-01..09-30; se descartaron 7 vacias y 13 con reloj corrido), un contrato por fecha, ES. Octubre (holdout de ticks) no se uso. Causalidad del fill: 300 casos, diferencia 0,0.
- **Veredicto primario (`Q_PRORATA`, tau 60 s, h 60 s): `PASIVO_RECUPERA_L2`.** `F` = 0,924; `M_p | fill` = -0,12; `M_a` incondicional = -0,51; **`A*` = +0,39 ticks** (IC unilateral 97,5 % [+0,378, +0,408]).
- **Modelo conservador `Q_NOCANCEL`** (no decide): `A*` = **+0,18** [+0,166, +0,203], por debajo del umbral +0,25. Chequeo `R_TT` sobre las mismas sesiones: `A*` = -0,16 (coherente con F0). Cota `R_TOUCH`: +0,63.
- Heterogeneidad (Holm sobre 2): en contra de los 100 prints previos `A*` = +0,50 vs a favor +0,27 (dif. +0,23, p ~ 0); spread 1: +0,38 vs spread >= 2: +0,86 (6 % de las decisiones).
- **Lectura honesta:** el IC es angosto por el tamano de muestra, pero **la incertidumbre dominante es del modelo de cola**, no estadistica: segun como se cancele la cola, la ventaja pasiva va de ~+0,18 a ~+0,63 ticks; solo el modelo central supera el umbral pre-registrado. Es un ahorro de costo de entrada, **no un edge**.
- **Correccion de proceso (A2):** en F0 y F0C cada sesion aportaba dos filas (compra y venta) tratadas como dos clusters. Se corrigio a un cluster por sesion y se relanzaron ambos kernels; los veredictos no cambiaron (F0 `PASIVO_NO_CONVIENE`, F0C `PASIVO_RECUPERA_L2`) y los SE crecieron ~10-25 %.
- **No medido:** cancelaciones reales por delante, tamanos mayores a 1 contrato, impacto de nuestra propia orden, latencia, salidas (TP pasivo / stop de mercado), costos de comisiones, otros horarios/estaciones fuera de jul-sep, otros instrumentos.

## Correccion (2026-10-17): el contraste S3 de F0 no era la apertura de las 09:30 ET
`outside_regular` es 0 durante toda la sesion Globex del release `edgelab-liquid-ticks-20261014` (diagnostico de `edgelab-orb-diag-rth-v1`). En F0 (ticks) el estrato `S3_open30` ("primera media hora de la sesion regular") correspondio a la primera media hora **desde las 18:00 ET (apertura Globex)** y `S3_rest` al resto de la sesion Globex.
El resultado de S3 (diferencia +0,06 tick, p = 0,47) **queda como "sin efecto en la apertura Globex"** y no dice nada de la apertura de Nueva York. Los estimandos primarios y los contrastes S1 y S2 no dependen de esa bandera. F0C (L2) no uso S3. Tampoco se uso la bandera RTH en k36/K37 para decidir nada, pero su `is_rth` tampoco es RTH.
