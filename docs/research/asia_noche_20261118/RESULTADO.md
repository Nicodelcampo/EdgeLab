# ASIA-NQ y la «noche movida»: veredicto (2026-11-18)

Estado: RESULTADO — **la «noche movida» de ASIA queda cerrada. Era en su mayor parte una fuga de dato futuro. Lo que queda causal es
chico e inestable (NO_CONFIRMADA por la regla pre-registrada) y no hace rentable a la regla: ASIA pierde en bruto en 20 años y cinco
índices, en todos los estados de la noche.**
- **Pre-registro:** `PREREGISTRO.md` (commiteado y contado antes de correr).
- **Datos:** `RESULTADO.json` (decisión), `DEV.json` (desarrollo), `BRUTO_NETO.json`, `SENSIBILIDAD_RIESGO_NULO.json`, y las corridas
  en `docs/research/papel_m1_20261115/resultados/FUTM1NT8_*`.
- **Herramienta:** `tools/asia_noche.py`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 1. Primero se arregló la medición (no el motor)
- **El motor M1 estaba bien.** ASIA en futuros M1 de NT8 contra ticks reales de NQ (ago-2025 → sep-2026):
  - operación por operación, 1.804 en común con la mediana de la diferencia en 0;
  - por sesión, +5,32 contra +5,20 (corr 0,985).
- **K47:** el «M1 duplica a los ticks» de las validaciones anteriores era una comparación entre agregaciones distintas (media de las
  celdas que operan contra la suma / número de celdas de la ficha).
- **K48, la fuga:** la variable `noche` es el rango 18:00→09:00 de la misma sesión en la que ASIA opera. El 100 % de sus entradas
  ocurre en esa franja.
- **Ranking:** el de `papel_regimen` perdía medio año de estados tras cada feriado. Corregido.

## 2. Prueba única en datos nunca mirados
**Datos:** NQ, ES y YM 2006–2011; EMD 2006 → 2025-07; RTY 2017 → 2025-07. Son 9.261 sesiones por instrumento.

| | Noche baja | Media | Alta | Alta − baja (EE) | p |
|---|---|---|---|---|---|
| **Noche anterior (causal, la prueba)** | −0,154 | −0,145 | −0,120 | **+0,035** (0,0125) | 0,0027 |
| Noche de la misma sesión (no causal, descriptivo) | −0,220 | −0,140 | −0,067 | +0,153 (0,0123) | < 0,0001 |

R neto de la canasta por sesión (suma de R / 20 celdas).

- **LORD++:** nivel 0,0109; rechaza.
- **Años:** 7 de 20 con la diferencia positiva (pre-registrado: ≥ 60 %).
- **Veredicto pre-registrado:** **NO_CONFIRMADA**. Hay efecto estadístico pero no es estable entre años. REFUTADA tampoco aplica:
  la cota superior (+0,055) pasa el mínimo útil de 0,04.
- **La fuga medida en los mismos datos limpios:** +0,153 con la misma noche contra +0,035 con la anterior. **Cerca del 80 % de la
  «noche movida» era dato futuro.**
- **Por instrumento** (alta − baja con la noche anterior): NQ +0,099, ES +0,087, YM +0,059, RTY +0,040, EMD +0,005. Descriptivo: 27
  de 44 instrumento-años positivos.

## 3. Económico: la regla pierde en todos los estados
- **Con noche anterior alta:** −0,120 R por sesión (p 1,0). **Operando siempre:** −0,161.
- **Por operación, bruto (antes de costos) y neto:**

| | NQ | ES | YM | EMD | RTY |
|---|---|---|---|---|---|
| R bruto/op | −0,107 | −0,107 | −0,111 | −0,055 | −0,019 |
| R neto/op | −0,777 | −0,612 | −0,574 | −0,294 | −0,170 |
| Fricción en R (mediana) | 0,52 | 0,44 | 0,36 | 0,16 | 0,13 |

- **No es fricción:** el bruto ya es negativo en los cinco índices.
- **Lo que queda:** el +0,19 R por operación de ago-2025 → sep-2026 (desarrollo, donde se eligieron sus 20 celdas) no tiene respaldo
  en 20 años de historia limpia.

## 4. Veredicto y consecuencias
- **F-ASIA-NQ-NOCHE-MOVIDA → NO_REPETIR.** La pista nació de la fuga. La versión causal es chica, inestable y no rescata a la regla.
- **ASIA-NQ-CANASTA** (papel):
  - en historia limpia pierde en bruto en cinco índices, y ningún estado de la noche la vuelve positiva;
  - no se le da tamaño;
  - la recomendación es sacarla en la próxima versión de la cartera (pre-registro nuevo).
  - Por el principio de «edges actuales» el pasado solo no la da de baja: si sigue en papel, lo decide el forward, sin filtro de noche.
- **No se repite:** ningún filtro «de noche» (ni de contexto diario) para reglas nocturnas sin verificar a qué hora se conoce (K48).

## 5. Integridad
- **Riesgo nulo:** 47 de 65.469 operaciones (0,07 %) tienen riesgo inicial indefinido (stop en el precio de entrada; sólo pagan
  fricción). La canasta en R de la prueba dejó afuera esas sesiones enteras, unas 40 de 9.261.
- **Sensibilidad** (excluye sólo esas operaciones, como el estándar `k > 0` del motor): +0,036 (p 0,002), 10 de 20 años, −0,161 R
  siempre. Mismo veredicto. `asia_noche._canasta_R` quedó corregida para filtrar por operación.
- **Costos:** de `costos.py`; EMD con costo estimado dentro del permiso K33 de este pre-registro.
- **Datos:** copia verificada de `tools/datos.py`; nada posterior al 2025-07-31.
