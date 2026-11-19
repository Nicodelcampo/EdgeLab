# MEJORA-SF-CONF: confirmar «Franklin en días volátiles» en YM, EMD y RTY (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr.
- **Origen:** `RESULTADO.md` de MEJORA-SF §3 vía (a). Pedido de Nico: «no olvides ninguno de los frentes … sé riguroso en los controles y que
  pasen por toda la cadena, sin falsos positivos».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF4** (confirmación en una muestra donde el contraste nunca se miró). **Familia:** `FRANKLIN`.
- **Herramienta:** `tools/mejora_sf.py conf` (mismas definiciones M3/M6 que DESC; `exigir_contada` al inicio).

Antecedentes: MEJORA-SF DESC (Franklin·M3 +0,172, p 0,017; Franklin·M6 +0,211, p 0,009 en NQ+ES), F-FRANKLIN-OTROS-INDICES (bruto de Franklin
en YM/EMD/RTY/GC ya mirado; el contraste por volatilidad NO).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K33 costo estimado de EMD declarado acá, K48, K49, K51).

Potencia previa: se calcula en la corrida ANTES de leer desenlaces de la muestra de confirmación, con la mitad del contraste de DESC como
efecto, la sd por día de DESC y el número de sesiones con operación de Franklin en YM+EMD+RTY (2006 → 2025-07, todos los bloques A5 salvo
HOLDOUT y EMBARGO), al nivel LORD++ de `FRANKLIN`. Si no llega a 0,8 la prueba no se lee y queda `SIN_POTENCIA_PREVIA`.

## Justificación económica
- Franklin es un sesgo direccional decidido a las 10:00 NY; en días volátiles el desplazamiento del día es mayor frente a la fricción fija y,
  con VIX alto, la cobertura de gamma corta empuja a favor del movimiento (Baltussen et al. 2021). Si el efecto es de mecanismo y no de
  selección en NQ+ES, debe aparecer en otros índices de renta variable de EE. UU.

## Prueba
- Muestra: operaciones de Franklin (`1000|rango|ninguno`) en **YM, EMD y RTY**, bloques A5 DESC y REP, hasta 2025-07-31. GC queda fuera (el VIX
  es de renta variable; mezclarlo cambiaría el mecanismo).
- **Costos:** canónicos; el spread de EMD es **estimado** (2 ticks, `costos_canonicos.json`): se declara acá y se reporta además sin EMD.
- Dos contrastes unilaterales (dentro − fuera, R neto, bootstrap por sesión): M3 (ATR20 en el tercio superior de 250 sesiones previas) y M6
  (percentil 252 del VIX al cierre previo ≥ 66,7). Se prueban con `LibroLord().probar("FRANKLIN", …)`.
- **Confirmada** si LORD rechaza y el R neto dentro es > 0. **Cómo podría refutarse:** contraste ≤ 0 o sin rechazo con potencia ≥ 0,8.
- **Contador:** 2 pruebas en `FRANKLIN`.
