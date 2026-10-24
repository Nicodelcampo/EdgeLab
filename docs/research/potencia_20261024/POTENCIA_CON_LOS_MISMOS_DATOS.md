# Más potencia con las mismas operaciones y los mismos datos (U1 y LUX-IMB), 2026-10-24

Estado: VIGENTE. Pedido de Nico: «fijate de qué manera podemos tener más potencia, con las mismas operaciones y los mismos datos».
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`

## Lo que sí da potencia (medido)
### 1. Nulo geométrico (ruina del jugador) por operación
Si una operación termina en TP o en SL, bajo un paseo aleatorio sin deriva la probabilidad de tocar el TP primero es
`dist_SL / (dist_TP + dist_SL)`. Esto da un nulo **exacto**, sin estimar la varianza del P&L.
- **LUX-IMB (regla del visor, TP 1,0·D y SL 0,2·D → p0 = 1/6):**
  - 104 TP en 495 operaciones resueltas, tasa 0,210.
  - z = **2,59** (p = 0,007), contra t ≈ 1,8 de la prueba sobre P&L.
  - La prueba quita el ruido del tamaño de D: es como tener unas 2 veces más operaciones.
  - Se calculó sobre conteos ya publicados en `RECALCULO_CANONICO_RELEASE_20261024.json`, antes de registrarla. Quedó registrada después como 1 prueba (`luximb/nulo_geometrico`).
- **U1 (desarrollo, T3 con tope 3×, sólo las operaciones que terminan en TP o SL):**
  - P1: z = 2,26 (t empírico 3,63).
  - P2: z = 2,44 (t empírico 3,56).
  - El efecto sobrevive al nulo exacto, así que no es un artefacto de la geometría. Aquí no suma potencia: la varianza empírica ya es menor que la del nulo.

**Límite:** esto mide *información*, no *rentabilidad*.
- Con costos, el umbral de LUX es una tasa de ≈ 0,179 (D medio ≈ 108 pts, fricción 1,5455).
- La tasa observada (0,210) supera ese umbral con z ≈ 1,8, igual que la prueba de P&L.
- El cuello de botella económico es el margen fino, no el método: hacen falta unas 930 operaciones.

### 2. Prueba económica eficiente para el holdout (pre-registrable)
Usar como estadístico `Σ (gana_i − p*_i)`, con `p*_i = (0,2·D_i + c) / (1,2·D_i)`: el umbral de rentabilidad de cada operación.
- Es exacto bajo la geometría fija.
- Evita la varianza de D_i.
- Requiere D por operación: hay que relanzar el recálculo con salida por operación, sin holdout.

### 3. Seguimiento secuencial (e-procesos)
`edgelab/funnel/secuencial.py` ya existe. Permite mirar cada semana sin pagar multiplicidad. Hay que usarlo con el estadístico 2.

### 4. Número efectivo de pruebas (Li-Ji)
Las 47 pruebas de LUX y los ~19 M del linaje de U1 son variantes muy correlacionadas. Cobrar el número bruto subestima el DSR.
El arreglo está en curso (rama `claude/embudo-falsos-negativos`).

## Lo que no da potencia o ya se probó
- **Régimen de rango para U1:** refutado (`u1/RESULTADO_REGIMEN_RANGO_U1.json`). En rango alto la media es −8,1 y en bajo +10,9. Por pre-registro, no se prueba otra variable sobre esos datos.
- **Ejecutar la misma señal en MNQ o en el CFD:** son los mismos eventos y no aportan información independiente.
- **Normalizar por R:** baja la potencia de U1, porque el efecto está en las operaciones de geometría ancha.

## Cómo acercarse a confirmar sin holdout
- **U1:**
  - La evidencia nueva solo puede salir de sesiones no usadas, desde el 2026-10-23.
  - Lo que sí se puede hacer ya es fijar el estadístico más potente (nulo geométrico más económico) y el seguimiento secuencial.
  - Las sesiones nuevas de Dukascopy se pueden bajar solas: el descargador ya está arreglado.
- **LUX-IMB:**
  - Igual que U1: desde el 2026-10-22, con el estadístico 2.
  - Además, la grilla masiva de variantes está en preparación (rama `claude/luximb-grilla-masiva`). Una variante con más margen por operación es la única forma de bajar las 930 operaciones necesarias.
