# REGIMEN-FORWARD: canasta T+R y SOM/Franklin como regímenes, con vigilancia secuencial en forward (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de mirar cualquier dato forward con estas reglas.
- **Pedido de Nico:** «¿Querés que pre-registre la canasta T+R con vigilancia y, en paralelo, los puntos 1 y 2 para SOM y Franklin? La
  respuesta es sí». El punto 1 (curva bruto–stop) ya se hizo (stop no es palanca); este documento es el punto 2 y la canasta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF5 (forward).** **Familias:** `FUNDEDSYNC` (canasta T+R), `SOM`, `FRANKLIN`. Enmienda la cartera B (`fundedsyncstack_20261115/
  PREREGISTRO_CARTERA_B.md`): sale Z (INTERMEDIO, pico del vendedor) y R pasa a stop de catástrofe 0,25 × ATR20 (NETO-PISTAS). La cartera B
  original sigue registrándose igual (no se reescribe su historia).
- **Herramienta:** `tools/regimen_forward.py` (lee los forwards que ya producen `fundedsync_cadena.py`, `som_seguimiento.py` y
  `franklin_seguimiento.py`; `edgelab/funnel/secuencial.py::EProceso`). Se llama al final de `tools/seguimiento_forward.py`.

Antecedentes: T-REGIMEN (REGIMEN_ROBUSTO; VIGILANCIA.md), NETO-PISTAS (R REGIMEN_ROBUSTO en R con 0,25 × ATR20), REGIMEN-SOM-FRANKLIN (señales
robustas; SOM con quiebre 2017-11 y neto +0,03; Franklin sin quiebre, +0,078 desde 2020), auditoría de Antigravity (piso de futilidad −4).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K27 potencia del forward, K42 alfa, K48, K49, K51).

Potencia previa: meses para decidir, con la media de desarrollo del régimen — canasta T+R ≈ 1,0 sesión con operación por día hábil a
+0,27 R/día (sd ≈ 1,6): e ≥ 20 en ≈ 4–8 meses; T sola (+0,15 R/op, sd 1,16, ≈ 19/mes) ≈ 10–15 meses; R sola (+0,45 R/op, ≈ 3/mes) ≈ 12–20 meses;
SOM NQ (+0,054, ≈ 17/mes) > 60 meses (no decide sola: sólo vigilancia); Franklin NQ+ES (+0,078, ≈ 17/mes) ≈ 30–40 meses.

## 0. Justificación económica
- T y R explotan el momentum intradía de NQ (ruptura del rango de apertura con capa de vecinos; fase del ATR en la primera hora), coherente
  con cobertura de gamma corta y flujo de opciones de corto plazo (Baltussen et al. 2021); su ventaja neta se mantiene en régimen desde
  2021 (T) y casi todos los años con salto desde 2020 (R). SOM y Franklin son señales de apertura con bruto estable cuyo neto vive en el
  régimen de fricción relativa baja (2017+ y 2020+). El forward es el único dato que nadie miró.

## 1. Reglas congeladas
- **T:** fábrica, NQ (en forward: USATECH sellado con costos de NQ), riesgo = clip(ORB15 × 1,25, 2, 100), R = neto / riesgo.
- **R:** fábrica, NQ, stop de catástrofe 0,25 × ATR20 de la sesión previa aplicado con el MAE: R = (resultado − fricción) / (0,25 · ATR20).
- **Canasta T+R:** suma diaria de R (1 unidad de riesgo por regla y operación).
- **SOM:** celda `sin_finde` (lo que produce `som_seguimiento.py`, NQ). **Franklin:** `1000|rango|ninguno` (lo que produce `franklin_seguimiento.py`).

## 2. Vigilancia (e-procesos válidos mirando cuando sea; datos desde la sesión del 2026-11-14)
| Serie | Edge (H0 E ≤ 0): EDGE si e ≥ 20 | Futilidad: SUSPENDER si e ≥ 10 con mu0 | Corte por drawdown (R) | Cotas [piso, techo] |
|---|---|---|---|---|
| T (por operación) | EProceso(0) | mu0 0,075 | −20 | [−4; +3,5] |
| R (por operación) | EProceso(0) | mu0 0,10 | −15 | [−2; +12] |
| Canasta T+R (por día) | EProceso(0) | mu0 0,13 | −26 | [−6; +16] |
| SOM NQ (por operación) | EProceso(0) | mu0 0,027 | −40 | [−4; +8] |
| Franklin (por operación) | EProceso(0) | mu0 0,04 | −44 | [−3; +18] |
- Cotas tomadas del rango de desarrollo con margen (T: −1,47/+2,99; R: −1,30/+9,07; canasta −2,46/+11,99 por día; SOM NQ −3,05/+5,91;
  Franklin −1,89/+14,04). Un valor fuera de cotas detiene esa serie con LIMITE_VIOLADO (no se recorta). Futilidad = la mitad del nivel del
  régimen en desarrollo; drawdown = ≈ 2 × el peor del régimen (T −9 → −20, R −7,4 → −15, canasta −12,8 → −26, SOM NQ −20 → −40, Franklin
  −21,9 → −44).
- **Decisión:** EDGE en la canasta T+R (e ≥ 20, α 0,05) con ≥ 30 operaciones → candidata a REAL con tamaño micro (decisión humana:
  CLAUDE.md, operar con dinero es sólo de Nico). SUSPENDER por futilidad o drawdown. Nada de esto cambia reglas, stops ni tamaño: un cambio
  es una versión nueva con su pre-registro.
- **Cómo podría refutarse:** futilidad o drawdown en la canasta antes de EDGE; para SOM/Franklin, futilidad (su régimen no se sostiene).
- **Contador:** 1 prueba en `FUNDEDSYNC` (canasta; T y R se reportan pero la decisión es la canasta), 1 en `SOM`, 1 en `FRANKLIN`.
