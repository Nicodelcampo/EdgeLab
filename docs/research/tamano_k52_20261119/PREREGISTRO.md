# TAMANO-K52: esquemas de tamaño sin sesgo de nivel de precio para RQ5, RQ6, SOM y Franklin (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Origen:** auditoría de Antigravity (`AUDITORIA_ANTIGRAVITY_20261119.md`, K52: no sumar puntos crudos entre épocas) y FRICCION-RQ §3 /
  NETO-PISTAS §B (contrato fijo y ∝1/√riesgo sesgados hacia los años de precio alto). Pedido de Nico: «realizá todos … sin falsos positivos».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 elección en meses DESC de A5; EF4 confirmación en meses REP (este contraste nunca se miró en REP). **Familias:** `ROBOQUANT_A5`
  (RQ5, RQ6), `SOM`, `FRANKLIN`.
- **Herramienta:** `tools/tamano_k52.py` (operaciones ya calculadas: `friccion_rq_20261119/OPS.csv.gz` celda `esc1`, `m1_largo_20261117/SOM_OPS_*`
  `sin_finde` y `FRANKLIN_OPS_*`; ATR20 previo de `m1_largo.atr20`; `holdout.a5_bloque`; `a5.diferencia`; `a5.plan_lectura`-equivalente para
  contrastes con `holdout_ventanas.plan_potencia`; `libro_lord`). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: K52 (Antigravity), F-STOP-CORTO-ES-FRICCION (contrato fijo sube el t medio: palanca confirmada en otras reglas), NETO-PISTAS §B (S1/S2/S4
sin confirmación en EMD+RTY), F-VENTAJA-EN-PUNTOS-NO-ESCALA.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36, K49, K51, K52).

Potencia previa: SOM ≈ 8.000 operaciones en DESC y ≈ 2.300 en REP; Franklin ≈ 2.100 / 600; RQ5 ≈ 3.300 / 900 y RQ6 ≈ 3.900 / 1.100 (ES+NQ).
La potencia de REP se calcula en días con la mitad del contraste de DESC y el nivel LORD++ de cada familia antes de leer (K49).

## Justificación económica
- La ventaja de estas reglas es un monto casi fijo en puntos por operación y la fricción es fija en puntos: las operaciones de stop chico
  rinden lo mismo en puntos pero pagan más fricción en R. Igualar el riesgo (R constante) les da demasiado peso. Un tamaño que iguale la
  exposición a la volatilidad del día (contratos ∝ 1/ATR20) deja de sobrepesar los stops chicos sin depender del nivel de precio de la época.

## Esquemas (cerrados)
- **S0** riesgo constante (actual). **W1** exposición constante a la volatilidad: peso por operación ∝ riesgo / ATR20 (contratos ∝ 1/ATR20).
  **W2** intermedio: peso ∝ √(riesgo / ATR20). R del esquema = Σ peso·neto / Σ peso·riesgo (cociente de sumas, en R de riesgo medio).
- Instrumentos: RQ5 y RQ6 en ES+NQ (declarado: se eligieron ES+NQ después de ver que YM no paga en FRICCION-RQ); SOM en NQ+ES+YM; Franklin en
  NQ+ES.

## Decisión
- Por estrategia, en DESC: el mejor de {W1, W2} por R neto; contraste mejor − S0 con bootstrap por sesión. Se nomina si p < 0,05 unilateral
  en DESC (4 pruebas: una por estrategia; BH q 0,10 entre las 4).
- REP: la nominada se lee una vez con LORD++ de su familia sólo si la potencia en días ≥ 0,8. **Mejora confirmada** si rechaza y el R neto del
  esquema en REP es > 0.
- **Cómo podría refutarse:** ningún esquema mejora en DESC, o la mejora no se repite en REP con potencia.
- **Contador:** 1 prueba en `ROBOQUANT_A5` por regla (RQ5, RQ6 → 2), 1 en `SOM`, 1 en `FRANKLIN`.
