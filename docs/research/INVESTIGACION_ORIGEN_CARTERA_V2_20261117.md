# De dónde salieron las 8 reglas de la cartera v2 y por qué no aparecieron más (investigación, 2026-11-17)

Estado: VIGENTE — pedido de Nico: «las estrategias de la cartera v2 aparecieron todas en un período muy corto, encontradas por Claude, y
luego no se encontraron más; investigá qué pasó para replicarlo y seguir encontrando». Descriptivo (no mide P&L nuevo). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Fuentes: historial de git, `docs/research/*/embudo/*/estado.json`
(229 campañas), `docs/research/cartera_20261116/PREREGISTRO.md`, `HOLDOUT_VENTANAS.jsonl`, `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`.

## 1. Línea de tiempo
| Regla de la v2 | Campaña (primer estado) | Origen |
|---|---|---|
| U1-ORO-GRILLA | `u1_oro_20261025` (25-oct) | grilla U1 sobre zonas, señal en CFD |
| U1-RACIMOS-GRILLA-NQ, U1-ZONAS-BT2-ES, U1-ZONAS-BT2-NQ | `u1_zonas_20261025` (26-oct) | grilla U1 sobre racimos y zonas BigTrap2 |
| PREAPERTURA-NQ | `paquete_20261031` (31-oct) | paquete de ideas de sesión |
| CVGAP-ES-C, CVGAP-CFD-ES-C | `relanzamiento_causal_20261102` (2-nov) | re-lanzamiento con código causal corregido |
| CONF-CVR-CFD-NQ-R | `relanzamiento_R_20261102` (2-nov) | re-lanzamiento medido en R |

**Las 229 campañas del embudo se crearon entre el 25-oct y el 9-nov, y después no se lanzó ninguna más.** Por semana: 9 (25-oct), 59
(26-oct → 1-nov; 31 con pistas vivas), **158** (2 → 7-nov; 72 con pistas vivas), 3 (9-nov), 0 desde entonces. Los picos de commits
coinciden: 26-oct, 2/3-nov y 7/8-nov.

## 2. Qué era «la máquina» de esas dos semanas
1. **Volumen**: sesiones de Claude lanzando campañas en lote con el embudo automático (`edgelab/research/embudo.py`, Kaggle), muchas
   variantes de cada idea en futuros y en CFD como señal (familias U1, CVGAP, CONF, TORI, EXPZ, DRC…).
2. **Embudo de dos etapas**: descubrimiento (ago-25 → mar-26) con nominación FDR → pistas → réplica no mirada (abr → sep-26) → canasta.
3. **Puerta a la cartera**: el 26–27-oct se aprobaron las actas de holdout por canasta de pistas y de régimen (`holdout_canasta`,
   `canasta_regimen`); el universo de la cartera fueron **las 27 reglas con acta vigente** desde el 1-oct, y la selección fija (R > 0 en
   descubrimiento Y réplica, fricción ≤ 0,08 R, sin las 5 mejores > 0, ≥ 55 % meses positivos, octubre no en contra, ≤ 2 por familia,
   correlación ≤ 0,5) dejó 8. El holdout (oct + nov) fue a favor sin ser concluyente (v2: t 1,8 en 31 sesiones).

## 3. Por qué se cortó (cinco causas, con evidencia)
1. **Se dejó de usar la máquina.** Ninguna campaña del embudo después del 9-nov. Desde el 10-nov el trabajo pasó a banco de eventos
   (10-nov), cadena de tablas E0 → una hipótesis → P&L (11-nov) y, del 15 al 17-nov, estrategias de afuera (reels, FundedSync, QuantLab, SQX).
2. **Una guarda nueva frenó las grillas grandes**: K4 (10-nov) — KILL a toda grilla con retornos de más de 500 celdas sin un E0 que la
   reduzca, tras la lección `F-SELECCION-EN-GRILLAS-GRANDES` (lo elegido así cae a ≈ 0 en réplica). Las U1 eran justamente grillas.
3. **El agente del Debian estaba en pausa**: al 11-nov, `PAUSE` llevaba ≈ 12 días (`AUTOMATIZACION_PROCESOS_20261111.md`). La racha la
   hicieron sesiones manuales; cuando cambió el foco, nadie siguió lanzando.
4. **La puerta quedó angosta**: de 108 campañas con pistas vivas, sólo 11 tienen acta de holdout propia; **97 nunca llegaron al acta**, así
   que nunca pudieron entrar a la cartera. Desde hoy, además, toda apertura exige un plan de potencia (K27).
5. **Las ventanas de datos ya estaban gastadas para esos linajes**: todo descubrió y replicó en los mismos dos semestres; una familia nueva
   en los mismos datos repite el mismo par de períodos (paso 2 de `urgencia_vs_evidencia_20261117`).

## 4. Lo que la racha encontró, leído con honestidad
- Medido sobre todo el embudo, **lo elegido en descubrimiento no conservó nada en su réplica** (−0,08 desvíos por operación, 37 %
  positivas; `urgencia_vs_evidencia_20261117/RESULTADO_PASO2.md`). Pasar descubrimiento y réplica es un filtro débil; lo que distingue a la
  v2 es haber pasado además el holdout de octubre–noviembre a favor (sin ser concluyente). La racha produjo **candidatas**, no edges.
- Lo replicable no es «la suerte de esa semana» sino el **proceso**: mucho volumen de ideas con mecanismo, dos etapas sin mirar, y una
  confirmación limpia (holdout de canasta o forward) antes de la cartera.

## 5. El pozo sin cosechar (contado sin medias nuevas)
De las 97 campañas con pistas vivas sin acta, excluidas las familias con su propia ventana forward (ASIA, OTR930, PRERANGE-ZONAS,
RANGO0100): **34 familias tienen pistas que ya pasan el primer filtro de la cartera** (R > 0 en descubrimiento y réplica, ≥ 40
operaciones; 53 campañas, 205 pistas) y **25 de esas familias nunca abrieron su holdout**: COMEX_CIERRE_ORO_GC,
CONFLUENCIA_CVGAP_RACIMOS (CFD_ES, CFD_NQ, NQ), CVGAP2 (CFD_ES, GC, NQ, XAU), HFT_GC_P10, IF_HACIA_RACIMOS_NQ, INTENTO_FALLIDO
(LUX_CFD_NQ, LUX_NQ, RACIMOS_NQ), KALMAN_FADE_NQ, MODELO_ASIA_NQ, ORO_ALMUERZO_RUPTURA (CFD, GC), OVERNIGHT_INVENTARIO_NQ,
PRERANGE_BASE_CFD_NQ, RANGO_PREAPERTURA (ES, NQ), TAU_TENDENCIA_NQ, TORI_TREND_TOQUE3 (CFD_NQ, GC), U1_ZONAS_GRILLA_YM.

## 6. Cómo replicarlo (en orden de rendimiento)
1. **Cosecha (rápido, mayor rendimiento)**: aplicar la MISMA regla de selección congelada de la cartera (§5 del pre-registro de
   `cartera_20261116`) a las pistas de esas 25 familias, sólo con desarrollo; con lo que quede, **una** acta de holdout de canasta con plan de
   potencia (`tools/holdout_canasta.py`, K27) sobre oct → la última sesión sellada, y forward. Si pasa, es la «v4»; si no, se cierra con su
   alcance. Pre-registro y conteo antes (K32).
2. **Reencender la máquina con lo aprendido**: tandas semanales de 20–30 campañas del embudo (no grillas de miles de celdas sin E0: K4),
   medidas en R, con fricción mínima, test de causalidad y generadores nuevos del banco de eventos; instrumentos y mecanismos que la racha no
   tocó (GC, YM, ES fuera de la apertura, horarios de Asia/Londres). Reanudar el agente del Debian (sacar `PAUSE`) lo decide Nico.
3. **Datos frescos para confirmar**: lo nuevo que sale de los mismos dos semestres repite el mismo par de períodos; la confirmación que vale
   es el forward. Subir los datos sellados con regularidad (semanal) acorta todo el ciclo.
