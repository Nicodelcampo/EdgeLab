# FILTRO-PICOS: esperar picos (o un barrido) antes de entrar, como capa sobre gatillos de otras reglas — NQ/ES/YM M1 2006–2022, partición A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Idea y parámetros: Nico.** «Sí, lanzá el filtro de picos con esos parámetros» (espera de 15/60 velas, 1–2 picos, vuelta de 0,25·D,
  cancelación a 1·D).
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT. **Familia:** `FILTRO_PICOS_A5`.
- **Herramientas:**
  - `edgelab/research/filtro_picos.py` (contrato de `tablas`; preflight OK; causalidad en datos reales con 80 disparos y 40 cortes
    arbitrarios);
  - `tools/a5_campana.py` (calibración y corrida);
  - `tools/filtro_picos_a5.py` (análisis pareado).

Antecedentes: búsqueda en FACTORES (2026-11-18).
- **A favor:** la entrada en la vuelta fue lo mejor de la exploración de LUXIMB-HVN (EXT, +0,16 a +0,22 R neto contra ≈ 0 de la
  inmediata; elegida en una búsqueda grande, nunca confirmada). En la caja amarilla, la única forma que aparece en los 4 cortes es
  «entrar después de la vuelta» (F-AMARILLA-DESPUES).
- **En contra:**
  - F-SELECCION-EN-GRILLAS-GRANDES y F-AJUSTE-FINO-NO-PAGA (SOM: entrar 25 min más tarde mata el efecto);
  - F-SELECCION-ADVERSA-PASIVA (sólo entrada a mercado al confirmar);
  - F-STOP-GRANDE (el stop detrás del barrido achica el riesgo y sube la fricción en R).
- **ESCALONADAS-M1** (la escalera como señal) quedó refutada. Esto es otra hipótesis: los picos como condición de ENTRADA de otra regla.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v2 — §0–§5.
- §1: espacio de eventos (abajo).
- §2: A5; calibración contra ticks; K40.
- §3: R; K36 (todo en D0 = riesgo original del gatillo); bruto y neto; tasa de entrada.
- §4: BH y potencia abajo.

Potencia previa: plan de `holdout_ventanas.plan_potencia` (efecto declarado de 0,05 R de diferencia pareada, sd 1,2, la mitad en la lectura):
- **LUX** (≈ 12.000 gatillos en el holdout): 0,74.
- **IBV3** (≈ 1.300): 0,19.
- **AZAR** (≈ 2.000): 0,24.
- **Lectura:** sólo LUX tiene potencia razonable para efectos chicos. En las demás bases el holdout sólo confirma efectos ≥ ~0,15 R.

## 1. Justificación económica
- **Picos sin romperse:** si después del gatillo se forman picos en contra que el precio no logra extender, hay absorción en contra del
  movimiento adverso.
- **Barrido (B):** cuando el precio barre esos picos, ejecuta los stops que había detrás, y la vuelta posterior confirma que ese flujo se
  agotó.
- **Lo que gana entrar después:** mejor precio y un stop estructural.
- **Lo que pierde:** las operaciones que van directo al objetivo.

## 2. Espacio de eventos y diseño
**Gatillos (bases)**, cada uno con su stop y objetivo originales:
- **LUX:** impulso LUX-IMB con ≥ 1 zona en el 25 % inicial; fade hacia A, stop 0,5·D.
- **IBV0:** Madonna.
- **IBV3:** aceptación → continuación.
- **ESC:** escalera; stop 4·rg, objetivo 8·rg.
- **AZAR:** gatillo al azar por hash del minuto; stop 2·rango medio, objetivo 4·rango medio. Es el NULO: la capa no debería crear ventaja
  sobre gatillos sin señal.

**Capa:**
- **A «picos»:** ≥ n pivotes blandos en contra (pivote de 1 vela); se confirma cuando el cierre vuelve 0,25·D0 a favor desde el último.
- **B «barrido»:** igual, pero primero el precio tiene que superar el último pivote; la vuelta se mide desde el extremo del barrido.
- **Espera:** 15 o 60 velas M1. **Picos mínimos:** n ∈ {1, 2}.
- **No entra si:** se toca el objetivo original, el precio se aleja 1·D0 en contra o vence la espera.
- **Placebo PL15/PL60:** entra a las espera/4 velas con las mismas cancelaciones y sin condición de picos.
- **Entrada:** a mercado en la vela siguiente a la confirmación.
- **Stops:** el ORIGINAL es el primario; el que va detrás del pico o del barrido (−0,1·D0) es descriptivo.

**Fuera:** picos estrictos (escalonadas PLANAS), entrada límite en el pico y escala de segundos (M1 no la ve).

## 3. Medición y prueba
**Valor por gatillo** (pareado): el R de la configuración si entró, 0 si no entró. Siempre con el tamaño de 1 R de su propio riesgo, la
convención de una prop firm.

**Pruebas:** 80 = 5 bases × 8 configuraciones × 2 contrastes:
- configuración − entrada inmediata (INM);
- configuración − placebo de la misma espera.

**Estadístico:** diferencia bruta con EE por sesión, p unilateral, BH q 0,10.

**Nominada si:** BH + diferencia > 0 + ≥ 60 % de años positivos + calibran las dos celdas del contraste.

**Se reporta además:** diferencia neta (fricción canónica por instrumento), tasa de entrada, R de las que entran y diferencia con el stop
detrás del barrido.

**Control de artefacto:** si en AZAR alguna configuración da diferencia positiva significativa contra INM, la capa crea «ventaja» de la
nada (artefacto del simulador o de la selección). Sus nominaciones en las otras bases quedan en duda.

## 4. Partición A5, ventana y fases
- **Ventana:** 2006-01-06 → 2022-12-30, la de LUX, cuyo linaje usó 2023+; la misma para todas las bases.
- **Pasos:** calibración contra ticks (2025-08 → 2026-03, Kaggle), DESC y REP con LORD++.
- **Holdout:** apertura única con compuerta económica y potencia ≥ 0,8.
- **Linaje:** abrir el holdout de esta familia consume también el de las bases (LUXIMB_A5_ZONAS25, IB_MADONNA_A5, ESCALONADAS_M1_A5), hoy
  sellados.

## 5. Cómo podría refutarse
- **Ninguna configuración supera a INM ni al placebo con potencia:** esperar picos no agrega a la entrada.
- **Las que superan a INM no superan al placebo:** lo que ayuda es esperar (o cancelar cuando el precio se va), no los picos.
- **AZAR da positivo:** artefacto.
- **El neto no acompaña** (por ejemplo, por el stop más chico).

## 6. Contador y linaje
- **Contador:** 80 pruebas.
  `tools/registro_global.py preregistrado FILTRO-PICOS FILTRO_PICOS_A5 80 docs/research/filtro_picos_20261118/PREREGISTRO.md`.
- **Linaje:** padres LUXIMB_A5_ZONAS25, IB_MADONNA_A5, ESCALONADAS_M1_A5 y LUXIMB_HVN (la entrada en la vuelta, EXT).
