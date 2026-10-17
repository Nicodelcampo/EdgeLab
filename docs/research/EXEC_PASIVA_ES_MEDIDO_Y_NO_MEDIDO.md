# Familia EXEC-PASIVA-ES — registro MEDIDO / NO MEDIDO (2026-10-17)

Manifiesto: `F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md` (enmienda A1 incluida). Kernel `edgelab-f0-exec-pasiva-es-v1` v2. Resultados: `f0_results_20261017/EXP_F0_RUN2_A1_RESULTS.json`.
Referente rector: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## MEDIDO (ES, ticks L1, 178 sesiones de descubrimiento + 121 de confirmacion 2026-04-01..09-30; holdout >= 2026-10-01 intacto)
- Decisiones: cierre de cada barra 100T (3,73 M obs. lado-decision en descubrimiento). Orden pasiva al touch, sin recotizar, `tau` = 60 s, regla de fill conservadora `R_TT` (trade-through de 1 tick).
- **Veredicto primario: `PASIVO_NO_CONVIENE`.** `F` = 0,860 (confirmacion 0,862). `M_p | fill` = -0,68 ticks; `M_a` agresiva incondicional = -0,55 (= medio spread); **`A*` = -0,13 ticks** (IC unilateral 97,5 % [-0,147, -0,112]; confirmacion -0,12). Valor por intento sin edge: pasivo -0,59 vs agresivo -0,55.
- Con `R_TT` la seleccion adversa (-0,68 tras fill) se come el spread capturado. Simetria compra/venta OK (|dif| = 0,015 tick).
- Heterogeneidad (Holm sobre 3, `A*`, `R_TT`): a favor vs en contra de la barra previa: **en contra** +0,30 tick mejor (`A*` +0,02 vs -0,28), p ~ 0; spread 1 vs >= 2: spread >= 2 +0,83 mejor (+0,65 vs -0,18; solo 6 % de las decisiones); primera media hora vs resto: sin efecto (p = 0,47).
- Cierres de impulso del corredor (T2, n = 10.616): `A*` = -0,10 (IC [-0,22, +0,01]): no difiere de la poblacion general.
- **Cota optimista `R_TOUCH`:** `F` = 0,956 y `A*` = +0,69. La verdad esta entre ambas reglas y depende de la posicion en la cola, **que L1 no observa**.

## NO MEDIDO / limites
- **Posicion en cola y fills reales.** Cierra o abre la brecha entre -0,13 y +0,69. Requiere L2 (`edgelab-l2-es-20261015`, jul-sep 2026, `research_allowed = false`): Fase 0C no autorizada.
- Cotizacion vieja (L1 solo trae cotizacion en filas de trades). Costos de comisiones (se asumen los del modelo de k35, **sin verificar** que 1,546 ticks = 1 tick spread + ~0,55 comisiones).
- Salidas (TP pasivo vs stop de mercado), recotizacion/seguimiento, otros instrumentos, otros `tau`/`h` mas alla de la grilla publicada, edge direccional.
- Una corrida previa (version 1 del kernel) dio `PASIVO_RECUPERA` por un estimando pareado que equivale al spread por construccion; **anulada** (enmienda A1). La ventana de confirmacion se leyo en esa corrida.

## Lectura
Con fills conservadores, entrar pasivo en el touch no mejora a cruzar el spread (-0,13 tick), salvo en contextos poco frecuentes (spread >= 2) y, marginalmente, cuando la orden va en contra de la barra previa (~0). El pasivo solo gana si la regla optimista se acerca a la realidad.
