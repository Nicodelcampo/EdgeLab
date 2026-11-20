# Cosecha del pozo de pistas vivas → canasta «v4» (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — escrito y commiteado ANTES de bajar operaciones y antes de cualquier dato del holdout de estas familias. Pedido de
Nico («sí» a la cosecha de `docs/research/INVESTIGACION_ORIGEN_CARTERA_V2_20261117.md` §6.1). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapas: EF4 (selección con desarrollo) → EF5 (holdout + forward
secuencial). Herramienta: `tools/cosecha_pozo.py` (reusa `tools/equity_pistas.py` y la regla de `tools/cartera_nov_analisis.py`).

Antecedentes: `python tools/antecedentes.py "cosecha de pistas vivas sin acta: canasta de reglas elegidas con la regla de la cartera y holdout de canasta"`
→ CARTERA_20261116 (misma regla, v2), CANASTA_GLOBAL (holdout exploratorio U1, NO PASA, 30 operaciones), F-ORIGEN-CARTERA-V2-RACHA,
F-FRECUENCIA-POR-SELECCION (NO_REPETIR: no se elige por frecuencia; acá la regla es la de la cartera, sin criterio de frecuencia),
F-FRECUENCIA-MINIMA-B y paso 2 de `urgencia_vs_evidencia_20261117` (lo elegido por el embudo no conservó nada en réplica).

Potencia previa: v2_analoga_ops.csv (cartera v2 como análoga, desarrollo DESC+REP, R por regla / 8): 51.8 ops/mes, R/op +0.025, sd 0.17,
n para decidir 264, 5.1 meses → OK | lectura de N 60 con la mitad del efecto: potencia 0.146 (NO se abre una lectura fija). Por eso la
decisión es un **e-proceso** (holdout + forward), no una lectura de N fijo.

## 1. Universo (congelado, sin mirar resultados nuevos)
Las pistas de réplica (`pistas_replica.celdas`) de las 27 campañas en fase PISTAS_VIVAS de estas 20 familias, todas con holdout libre según
`holdout_ventanas.problemas` (sin apertura, sin ventana consumida) y que ejecutan en un futuro (NQ, ES, YM, GC): COMEX_CIERRE_ORO_GC,
CONFLUENCIA_CVGAP_RACIMOS_CFD_ES, CONFLUENCIA_CVGAP_RACIMOS_NQ, CVGAP2_CFD_ES, CVGAP2_GC, CVGAP2_NQ, HFT_GC_P10, IF_HACIA_RACIMOS_NQ,
INTENTO_FALLIDO_LUX_CFD_NQ, INTENTO_FALLIDO_LUX_NQ, INTENTO_FALLIDO_RACIMOS_NQ, KALMAN_FADE_NQ, MODELO_ASIA_NQ, ORO_ALMUERZO_RUPTURA_CFD,
ORO_ALMUERZO_RUPTURA_GC, OVERNIGHT_INVENTARIO_NQ, TAU_TENDENCIA_NQ, TORI_TREND_TOQUE3_CFD_NQ, TORI_TREND_TOQUE3_GC, U1_ZONAS_GRILLA_YM
(330 pistas). Fuera: RANGO_PREAPERTURA ES/NQ y CONFLUENCIA_CVGAP_RACIMOS_CFD_NQ (holdout ya abierto), CVGAP2_XAU y PRERANGE_BASE_CFD_NQ
(ejecutan en CFD), ASIA/OTR930/PRERANGE-ZONAS/RANGO0100 (forward propio). Event-space: el de cada campaña (su SPEC); la cosecha no define
eventos nuevos, sólo elige entre reglas ya congeladas.

## 2. Datos de desarrollo
Una corrida de Kaggle por campaña (etapa ANALIZAR_REGLA, `operaciones=True`, cortes del DESC, sin tope, inicio del DESC → 2026-09-30,
nunca el holdout). DESC = ventana DESC de la campaña; REP = su ventana de réplica de pistas. Unidad: R por operación (neto / riesgo inicial;
las campañas en «R» ya lo devuelven). Costos sólo de `edgelab/costos.py`. **Integridad:** se compara la media REP re-medida con la
`replica_pistas` del `estado.json`; si difieren de signo en más del 20 % de las pistas, se frena y se busca la causa raíz antes de elegir
(el código cambió desde entonces —correcciones causales—, así que diferencias chicas son esperables y se reportan).

## 3. Regla de selección (la de la cartera, `cartera_20261116/PREREGISTRO.md` §5, sin E5)
E1 ≥ 40 operaciones en desarrollo y R/op > 0 en DESC y en REP · E2 fricción mediana ≤ 0,08 R · E3 R total sin las 5 mejores > 0 · E4 ≥ 55 %
de meses positivos · E6 ejecuta en un futuro. (E5 —octubre no en contra— no aplica: el holdout de estas familias no se miró y no se mira para
elegir.) Orden por R contraído (James-Stein hacia 0 entre todas las pistas del universo); se agregan en orden con ≤ 2 por familia y
correlación diaria ≤ 0,5 con las ya elegidas; hasta 10. `SELECCION.json` se commitea ANTES de lanzar nada del holdout.

## 4. Confirmación (EF5)
- Una apertura por familia de las reglas elegidas (`holdout_ventanas.registrar_apertura`, plan `e_proceso` desde el desarrollo de la
  canasta con la **mitad** del efecto, K27), desde la frontera única (sesión CME del 2026-10-01) hacia adelante; las familias sin regla
  elegida conservan su apertura.
- Objeto: canasta igual-ponderada, R por sesión = suma del R de las reglas elegidas (1 R por regla). e-proceso
  (`edgelab/funnel/secuencial.py`) H0 E[x] ≤ 0, cotas por sesión [−15, 40] y por regla [−6, 30] (las de la v2); **EDGE si e ≥ 10**.
  Válido mirando cada vez que se suben datos sellados.
- Descriptivo, nunca para elegir ni ajustar: R de la canasta en el holdout sellado (oct → última sesión sellada), y lo mismo sin las sesiones
  ≤ 2026-10-22 para las familias que heredan de AREAS_EXP_1_CRUZADO (ventana consumida hasta el 22-oct; sensibilidad por linaje).
- Futilidad: si tras 60 sesiones con operaciones el R total es ≤ 0, la canasta se cierra con su alcance (no se retoca).
- Riesgo de contaminación declarado: varias familias son hijas de padres cuyo holdout ya se abrió (U1_ORO_GRILLA, CVGAP, U1_RACIMOS); su
  diseño pudo heredar «el padre va bien». Por eso la lectura descriptiva no decide y el que decide es el e-proceso con su cota.

## 5. Multiplicidad y contador
Las pistas ya están contadas en sus campañas (el contador global las tiene). La cosecha agrega **1 prueba** (la canasta, e-proceso), familia
`COSECHA_POZO_20261117` (linaje: las 20 familias de §1, `n_efectivo_heredado` bruto).

## 6. Justificación económica y cómo podría refutarse
Justificación económica: cada regla trae la suya en el SPEC de su campaña (rupturas y continuaciones con mecanismo de inventario, zonas U1,
confluencias de gaps); la canasta diversifica entre mecanismos e instrumentos, que es lo que mostró la v2 (holdout a favor). Cómo podría
refutarse: (a) 0 elegibles → la cosecha se cierra y el pozo no tenía nada que pase la regla; (b) e-proceso sin cruzar y futilidad (R ≤ 0
tras 60 sesiones con operaciones); (c) integridad del §2 en rojo. Expectativa honesta: por el paso 2 la media de partida es ≈ 0; el valor de
la cosecha es que es barata y pone candidatas diversificadas a prueba con un estadístico válido.
