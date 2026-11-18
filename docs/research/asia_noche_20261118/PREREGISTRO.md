# ASIA-NQ y la «noche movida», versión causal: prueba única en datos no mirados (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea y se cuenta antes de correr un solo desenlace en los datos no mirados.
- **Pedido de Nico:** «indagá en noche movida Asia […] seguro podés arreglar el motor y llegar a un veredicto, sin dejarlo en
  seguimiento».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. **Etapa EF4** (confirmación de una pista
  con regla congelada). **Familia:** `ASIA_NOCHE_PREVIA` (linaje: `ASIA_BOS_GAPS_NQ`).
- **Herramienta:** `tools/asia_noche.py` (reutiliza `papel_regimen.variables`, `papel_m1.local`, `cartera.papel.canasta_por_sesion`
  y `a5.diferencia`).

Antecedentes: `python tools/antecedentes.py "ASIA noche movida …" --familia ASIA_BOS_GAPS_NQ`.
- **Datos mirados por el linaje:** DESC/REP ago-2025 → sep-2026; holdout desde oct-2026 consumido. El largo v1 de papel M1 miró ASIA
  en NQ, S&P y Dow desde 2012 (CFD).
- **F-RUPTURA-VIVE-DEL-DIA-DE-TENDENCIA:** la noche no anticipa los días de tendencia en otras reglas de ruptura.
- **Lo que se descubrió hoy** (`docs/research/papel_m1_20261115/VALIDACION.md`, v2 corregida):
  1. **El motor M1 no era el problema.** ASIA en futuros M1 de NT8 coincide con ticks reales operación por operación (1.804 en
     común, mediana de la diferencia 0) y por sesión (+5,32 contra +5,20, corr 0,985).
  2. **El «M1 duplica a los ticks» era un error de agregación de la validación** (K47): media de las celdas que operan contra la
     suma / número de celdas de la ficha.
  3. **La variable `noche` NO es causal para ASIA.** Es el rango 18:00→09:00 NY de la misma sesión, y el 100 % de las entradas de
     ASIA ocurre dentro de esa noche (K48).
  4. **En desarrollo** (ticks reales, `DEV.json`, después de arreglar el ranking con huecos): noche de la misma sesión alta − baja
     +0,194 R por sesión (p 0,001); noche ANTERIOR (causal) +0,080 (p 0,086). La mayor parte del patrón venía del dato futuro.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6.
- §2: datos con `tools/datos.py`; M1 calibrado contra ticks (K30); K40.
- §3: R con el riesgo inicial; canasta con la función de la ficha; costos de `costos.py` (EMD estimado dentro del permiso K33 de
  este pre-registro).
- §4: potencia al nivel LORD++; árbol de confirmación.
- §6: K45–K48.

Potencia previa: `holdout_ventanas.plan_potencia("fijo", 0,04, 0,373·√2, n=2.500, alfa=0,0109)` → potencia 0,93 (n necesarias
1.709 sesiones por tercil).
- **Efecto:** la mitad del contraste causal de desarrollo (+0,080 → 0,04 R por sesión).
- **Desvío:** el de la canasta en R por sesión en desarrollo (0,373).
- **N esperado:** ≈ 2.500–2.900 sesiones por tercil en los datos no mirados.

## 1. Justificación económica
- **El mecanismo:** una noche anterior con rango grande indica volatilidad y flujo internacional activo. Si persiste, la caja
  asiática siguiente debería romper con más continuación.
- **Lo que no vale:** el rango de la misma noche no sirve como filtro. Se conoce recién a las 09:00, cuando ASIA ya operó, y en
  parte lo forma la propia ruptura que la regla aprovecha.

## 2. Datos (nunca mirados para ASIA ni para la noche)
- **NQ, ES y YM:** 2006-01 → 2011-12. El largo v1 empezó en 2012. El ranking de 250 sesiones deja 2006 como calentamiento.
- **EMD (MidCap):** 2006-01 → 2025-07. **RTY (Russell):** 2017-07 → 2025-07. Nunca se midió ASIA en ellos.
- **Fuente:** M1 real de futuros de NT8 (`M1NT8:`), copia local verificada (`tools/datos.py`); lector `bloques_m1nt8` (corta en la
  frontera). Ningún dato posterior al 2025-07-31.
- **Regla:** ASIA-NQ-CANASTA congelada (mismas 20 celdas, cortes y tope), con el motor único y la ejecución en el mismo instrumento.

## 3. Variable y prueba (una sola vez)
- **`noche_previa`:** tercil del rango 18:00→09:00 NY relativo al cierre de la sesión anterior, contra los 250 rangos previos con
  dato (`papel_regimen.variables`), desplazado una sesión. Se conoce a las 09:00 de la sesión d−1.
- **Valor por sesión e instrumento:** R neto de la canasta = Σ (neto / riesgo inicial) / 20 celdas (`canasta_por_sesion`).
- **Estadístico primario:** media en `noche_previa` alta (tercil 2) − media en baja (tercil 0), juntando los cinco instrumentos.
  Bootstrap agrupado por fecha (`a5.diferencia`), p unilateral.
- **α:** el nivel LORD++ de la familia, reservado al correr (`LibroLord().reservar`, ≈ 0,0109).

**Veredicto:**
- **CONFIRMADA:** p ≤ nivel, diferencia > 0 y ≥ 60 % de los años con la diferencia positiva.
- **REFUTADA:** diferencia ≤ 0, o cota superior unilateral al 95 % (diferencia + 1,645·EE) < 0,04 R: el efecto, si existe, es
  menor que el útil.
- **NO_CONFIRMADA:** cualquier otro caso. Con la potencia declarada no debería pasar.

**Económico** (decide si se opera, no el mecanismo):
- R neto en `noche_previa` alta > 0 con p ≤ 0,05.
- Se reporta por instrumento y el R de operar siempre.

**Descriptivo** (no decide): el mismo contraste con la noche de la misma sesión (no causal), para medir el tamaño de la fuga.

## 4. Cómo podría refutarse
- **Diferencia ≤ 0 o menor que 0,04 R con potencia:** la noche movida de ASIA era sólo la fuga de la misma noche.
- **Confirma pero el neto en noche alta no es > 0:** el filtro ordena, pero no hace rentable a la regla.

## 5. Contador y linaje
- **Contador:** 1 prueba.
  `tools/registro_global.py preregistrado ASIA-NOCHE-PREVIA ASIA_NOCHE_PREVIA 1 docs/research/asia_noche_20261118/PREREGISTRO.md`.
- **Linaje:** `ASIA_NOCHE_PREVIA` ← `ASIA_BOS_GAPS_NQ` (`LINAJES.jsonl`).
