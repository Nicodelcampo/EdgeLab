# Auditoría del informe k32 — "replicación pre-registrada" de RRE en ES abr–sep 2026 y IA de aprendizaje continuo

Estado: PROVISIONAL (un solo auditor: gonzasib-claude; sin acceso al kernel ni a los JSON)
Fecha: 2026-10-16
Familia / módulo: EXP-CORRIDOR (RRE sobre EmaCorridorTrend, `P_REENTRY_F1A_P1/P2`) · módulo `autopilot`
North Star: `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421` (el informe cita el mismo hash que el registro de la familia)
Procedencia: informe `informe_replicacion_preregistrada_y_aprendizaje_continuo_k32_20261016.md`, enviado por Nico por Chaski el 2026-10-16 (copia íntegra: `INFORME_EXTERNO_K32_REPLICACION_RRE_20261016.md`). Kernel Kaggle 138964727 v1 y JSON en Drive **no verificados** desde este repo: esta máquina no tiene credenciales de Kaggle y los enlaces del informe están envueltos en `google.com/search`.

## Veredicto

**Se acepta la refutación; no se aceptan tres de sus afirmaciones.** A la escala probada (micro-zonas de 16 ticks, reversión al cierre de barras de 100 ticks, 3 a 5 operaciones por sesión, fills pasivos) la familia pierde después de fricción en todo lo que el informe llama fuera de muestra. Eso coincide con lo que el registro de la familia ya tenía (`HA` neto −2,01 ticks). Lo que no se sostiene es la etiqueta de "replicación pre-registrada", el adjetivo "contundente" para la IA continua y la "ley estructural" de los pilares.

| Partición (informe §3.2) | Mejor variante (H3) | z | Lectura |
|---|---|---|---|
| Assessment, 32 sesiones (feb–mar 2026) | +2,01 / +1,36 ticks/op | +0,63 / +0,61 | no significativo |
| Abr–sep 2026, 121 sesiones | −2,52 / −2,54 ticks/op | −1,83 / −2,31 | pierde |
| Total "OOS", 153 sesiones | −1,30 / −1,60 ticks/op | −0,97 / −1,58 | pierde; DSR 0,0003 / 0,0000 |

## Hallazgos

1. **Abr–sep 2026 no es muestra virgen.** El registro de la familia (`CORREDOR_EMA_MEDIDO_Y_NO_MEDIDO.md`, 2026-10-15, NO MEDIDO) dice que las 299 sesiones, incluida la ventana abr–sep, se inspeccionaron para diseñar (HOLDOUT-A3 reglas 1 y 4), y que la replicación de ES "no está disponible para esta familia". El informe llama a esas 121 sesiones "vírgenes" y "pre-registradas" sin citar un manifiesto committeado antes de tocarlas. Consecuencia: todas las particiones "OOS" del informe son, a lo sumo, desarrollo; nada en k32 cuenta como réplica. No cambia el veredicto (pierde igual), pero sí invalida la lectura positiva de los pilares.
2. **"H3 supera de forma contundente" no está demostrado.** Las dos cifras positivas son 32 sesiones con z = 0,63 y 0,61; un Sharpe de +1,76 con z < 1 es ruido con signo. En abr–sep H3 sigue negativa. Lo que sí muestra el informe es una mejora **relativa** frente al modelo congelado (H2) con PBO 0,26 entre 8 variantes, y menor drawdown. Mejora relativa no es edge: la media neta tiene que superar la fricción sola. Detalle que conviene mirar: en el único tramo positivo H3 operó más que H2 (n 145 vs 123); el controlador adaptativo aflojó el umbral justo ahí.
3. **"Jerarquía de pilares = ley estructural" es una sobreinterpretación.** El orden de 5 pilares se repitió (bajo un nulo uniforme e independencia, p ≈ 1/120), pero (a) por el punto 1 las muestras no son independientes, y (b) las magnitudes se encogieron 4 veces o cambiaron de signo: REJ_3 de +3,20 a +0,84 ticks brutos, REJ_2 de +1,03 a −0,22. Es regresión a la media de libro. Vale como prior para diseñar features (REJ_4 y REJ_5 son protectores en ambas eras), no como hallazgo.
4. **El paso 2 del roadmap repite el error que el informe critica.** La "compuerta de abstención de régimen" (expectativa rodante de 15 sesiones < 0 → no operar) se diseñó después de ver la pérdida de abr–sep. Es exactamente la compuerta post-hoc del punto 3 del propio informe. Es una hipótesis nueva: se pre-registra y se mide en datos que no la motivaron.
5. **El paso 1 del roadmap es coherente con la regla de fricción del repo.** Movimiento esperado ≥ 3 × fricción por viaje (ES 3,55 ticks → ≥ 10,7 ticks brutos por operación). La familia tenía edge bruto de +0,20 a +0,85 ticks/op: ratio < 0,25. El chequeo mecánico de `edgelab/autopilot/promocion.py` la habría rechazado si `mov_esperado_ticks` se declara como lo que la operación captura tras el fill, no como la amplitud nominal de la zona (16 ticks). Esa aclaración quedó en `edgelab/autopilot/friccion.py`.
6. **Lo que sí se rescata como método.** (a) Replay tick a tick con máquina de estados causal para fills pasivos: midió +0,64 ticks/op de optimismo en el modelo anterior, coherente con LES-BAR-FILL-OPTIMISM; (b) reportar IS / VAL / OOS por separado y nunca un "All"; (c) DSR y PBO acumulados por familia. M = 36 se declara, no se deriva: tiene que salir del ledger de pruebas del agente.
7. **No verificado y por qué.** Kernel 138964727 (sin credenciales en esta máquina), JSON de resultados (enlaces inaccesibles), conteo M = 36, y si el indicador `EmaCorridorTrend` se parametrizó mirando abr–sep (si fue así, el punto 1 es aún más fuerte).

## Qué se integró al sistema (mismo commit)

- `config/autopilot/herramientas.json`: técnicas `replay_causal_fills_pasivos` y `aprendizaje_continuo_con_embargo`; regla común ampliada: "virgen" se verifica contra el registro de la familia, y un gate diseñado tras ver la pérdida es prueba nueva.
- `edgelab/autopilot/contexto.py`: prioridad fija nueva en todos los ciclos (fills causales, réplica declarada, gate post-hoc).
- `edgelab/autopilot/friccion.py`: `mov_esperado_ticks` es movimiento capturado tras el fill, no amplitud nominal.
- `deploy/debian/autopilot.example.json`: "RRE reversión micro-zonas 16 ticks al cierre de barras 100T ES" en `familias_retiradas`; el filtro de novedad la bloquea.
- `CORREDOR_EMA_MEDIDO_Y_NO_MEDIDO.md`: sección "Informes externos (no verificados en el repo)" con k32.

## Qué queda abierto

- Si Nico quiere seguir el paso 1 (H ≥ 32–48 ticks, 0,3–0,8 op/sesión, L2), la familia nueva necesita su propio manifiesto y una ventana que el registro declare sin usar. Con abr–sep quemado, en ES no queda ventana antes del holdout: la confirmación tendría que ser en NQ/YM (sellados) o esperar datos nuevos.
- Verificar el kernel y los JSON desde SV1 cuando tenga credenciales, y asentar el recibo agregado junto a esta auditoría.
