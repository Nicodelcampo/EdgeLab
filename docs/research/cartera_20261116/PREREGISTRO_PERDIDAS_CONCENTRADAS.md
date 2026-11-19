# Dónde se concentran las pérdidas: stop corto relativo (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado ANTES de calcular nada por distancia al stop en los conjuntos de confirmación. Pedido de Nico (2026-11-16):
«detectar dónde se concentran las pérdidas sin caer en sobreajuste»; iteración de la propuesta «piso de stop».
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3 (réplica dirigida) + EF5 (holdout).
Familia `PERDIDAS_STOP_CORTO` (hija de `CARTERA_20261116`). Herramienta: `tools/perdidas_concentradas.py`.

## De dónde salió la idea (y por qué esos datos ya no prueban nada)
En desarrollo (DESC + REP) de **4 reglas** — U1-CRUZADO, CVGAP-NQ, U1-ZONAS-NQ, U1-ZONAS-AVCL-NQ — se miró el R por tercil de riesgo inicial
(distancia entrada→stop). En 3 de las 4 el tercil de stop corto pierde (U1-CRUZADO −0,19 R, CVGAP-NQ +0,03 vs +0,12, AVCL-NQ −0,17) y en
U1-ZONAS-NQ pasa lo contrario. Esas 4 reglas son **generadoras**: no entran en ninguna confirmación.

## Mecanismo, justificación económica y cómo podría refutarse
Un stop corto respecto de lo habitual en la misma regla queda dentro del ruido del precio: la operación se cierra por ruido antes de que el
mecanismo actúe (gana seguido pero pierde en promedio), y además la fricción fija pesa más en R. Refutación: en los conjuntos de confirmación
el tercil bajo NO rinde menos que el resto (Δ ≥ 0), o la diferencia es sólo fricción (bruto igual) — en ese caso es la palanca conocida
«stop grande frente a la fricción», no un hallazgo nuevo.

## Definición (fija, sin búsqueda de umbrales)
- **Rango causal del stop:** para cada operación, en orden cronológico dentro de cada regla (DESC → REP → holdout), percentil de su riesgo
  inicial entre las **60 operaciones previas** de la misma regla (mínimo 20 previas; antes no se clasifica). Nada de futuro.
- **Bajo** = percentil < 1/3. Resto = las demás.
- R neto por operación (fricción canónica ya descontada). R bruto = R neto + fricción canónica / riesgo.

## Conjuntos de confirmación (no mirados por esta variable)
- **C1 (principal):** desarrollo DESC + REP de **todas las reglas del universo de `PREREGISTRO.md` menos las generadoras** (24 reglas: U1-CRUZADO no está en ese universo;
  datos de `canasta_7_20261030/desarrollo_en_r` y de `cartera_20261116/ops`).
- **C2:** holdout de noviembre (2 → 13) de las reglas con datos de noviembre (futuros NQ/ES/YM), generadoras incluidas (su noviembre no se miró).
- **C3 (secundario):** holdout octubre + noviembre, mismas reglas que C2 más las de octubre solamente.

## Hipótesis (k = 3; BH q 0,10 sobre las tres)
- **H1 (principal):** en C1, Δ = R(bajo) − R(resto) < 0. Estadístico: Δ estratificado por regla (media de las Δ por regla ponderada por
  n_bajo·n_resto/(n_bajo+n_resto)); p de una cola por bootstrap de sesiones (B = 10.000) sobre el conjunto entero; además, conteo de reglas con
  Δ < 0 (prueba de signo).
- **H2:** la diferencia existe también en BRUTO (Δ_bruto < 0 en C1): separa ruido de fricción.
- **H3:** saltear el tercil bajo mejora el R total de C1 (suma de R del tercil bajo < 0).
- **C2 y C3 dan dirección** (sin potencia previsible: ≈ 20–40 operaciones en el tercil bajo de noviembre).

## Lectura fijada antes
- **CONFIRMADA** si H1 nominada por BH **y** Δ < 0 en C2. Entonces el filtro «no operar con stop en el tercil bajo causal» pasa a papel como
  **variante** de cada regla (no cambia la cartera ya congelada) y se sigue con e-proceso.
- **SÓLO FRICCIÓN** si H1 sí y H2 no: se aplica como regla de diseño (piso de stop en R de fricción), no como señal.
- **REFUTADA** si Δ ≥ 0 en C1 con potencia (MDE80 ≤ 0,10 R).
- Por regla NO se eligen umbrales ni reglas: el filtro es el mismo para todas o para ninguna.

## Descriptivo (no decide, no se poda nada con esto)
Concentración de pérdidas por hora de entrada (NY: 9:30–10:30, 10:30–14:00, 14:00–16:15, resto) y por día de la semana, en C1. Toda
hipótesis que salga de ahí va a otro pre-registro con datos no mirados.

## Tamaño (palanca 1, descriptivo)
En C1 y C2: t por operación con riesgo fijo (R), contrato fijo (puntos) y tamaño ∝ 1/√riesgo. No cambia ninguna señal; informa la decisión
de cómo dimensionar.

Contador global: 3 pruebas (familia `PERDIDAS_STOP_CORTO`).
