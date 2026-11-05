# Pre-registro: piso de riesgo frente a la fricción en las 11 reglas (04/11/2026)

Estado: PRE-REGISTRO (commiteado antes de calcular). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF3** (filtro
común sobre reglas ya elegidas). Pedido de Nico (04/11), a partir de `REVISION_ATLAS_CONTEXTO_FRICCION_20261104.md`.

## Hipótesis

La fricción es fija en puntos por instrumento (costos canónicos). En R pesa `f_R = fricción / riesgo`, que se conoce al entrar. Las
operaciones con stop chico frente a la fricción pierden en R por construcción. **No operar cuando `f_R > u`** debería subir el R
medio de la cartera sin cambiar ninguna señal.

**Justificación económica:** la fricción es un costo seguro; si la ventaja esperada por operación es de unas décimas de R, un costo de
0,09R se come la mayor parte.

**Cómo podría refutarse:** en DESC ningún umbral sube el R medio, o el umbral elegido en DESC no lo sube en la réplica, o mejora menos
de 7 de las 11 reglas en la réplica.

## Datos (ya existentes, sin corrida nueva)

- **8 reglas:** `programa_r_20261103/trayectorias/*__{desc,rep}.json`, con `riesgo` y `R_regla` reales.
- **U1-CRUZADO:** `canasta_7_20261030/desarrollo_en_r/`, con neto en puntos y `R = neto / riesgo`.
- **TORI-NQ-R y CONF-CVR-CFD-NQ-R:** `nominacion_forzada_R_20261103/desarrollo/`, con neto ya en R.
- **Fricción:** `embudo_runners.friccion` del instrumento de ejecución (NQ 1,5455 pts; ES 0,8877 pts).
- **Tramos:** DESC (ago 2025 – mar 2026) y réplica (abr – sep 2026). Octubre no se usa.

## Grilla y decisión (3 pruebas)

- Umbrales: `u ∈ {0,10; 0,075; 0,05}`. Equivalen a un piso de riesgo de 15,5 / 20,6 / 30,9 pts en NQ y de 8,9 / 11,8 / 17,8 pts en ES.
- **Elección:** sólo con DESC, el umbral con mayor R medio de la cartera (todas las operaciones juntas).
- **Confirmación en la réplica**, con ese mismo umbral y sin volver a elegir. Tienen que cumplirse las dos:
  1. el R medio de la cartera sube;
  2. ninguna regla empeora en más de 7 de las 11: al menos 7 mejoran o quedan igual.
- **Se reportan las 3** en los dos tramos, junto con el bruto (`R + f_R`) y la fracción de operaciones descartadas.

## Advertencias declaradas

- **Las 11 reglas se eligieron mirando la réplica.** La confirmación en la réplica es más débil que en datos nuevos. La validación limpia es
  desde noviembre de 2026, hacia adelante.
- **Ya miré el agregado de la fricción por tercil del stop en 8 reglas** (revisión del 04/11) antes de escribir esto. No miré ningún
  umbral.

Contador global: `programa_r/piso_riesgo/20261104`, 3 pruebas, familia `PISO_RIESGO_FRICCION`.
