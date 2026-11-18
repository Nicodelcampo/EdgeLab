# ORB-A5 O1 (ORB de 5 min): confirmación en el holdout A5 de NQ/ES/YM + MidCap y Russell completos, una sola lectura (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea, se registra la apertura y se reserva el α ANTES de calcular un solo desenlace.
- **Decisión de Nico:** «MidCap+Russell primero» y, con la potencia corregida al nivel LORD, «Juntar los dos».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. **Etapa EF5** (confirmación).
- **Familia:** `ORB_A5`. Es su única apertura del holdout A5.
- **Herramienta:** `tools/orb_confirmacion_o1.py`.

Antecedentes: `docs/research/orb_a5_20261118/RESULTADO.md`.
- **Regla:** O1, la de Zarattini y Aziz (2023).
- **DESC:** +0,118 R bruto (p 0,001, 85 % de años positivos). **REP:** +0,090 (p 0,10; sin potencia).
- **Por época:** bruto ≈ +0,1 en 2006–11, 2012–19 y 2020–25.
- **Neto:** positivo sólo en NQ 2020–25 (mini +0,16, micro +0,15 R). Antes de 2020 el rango de 5 min es chico frente a la fricción.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v2 — §0–§5.
- §2: el holdout A5 se abre una sola vez; EMD y RTY nunca se usaron para ORB; motor con K40 (calibración de ORB 9/11, O1 calibra con
  corr 1,00).
- §3: R bruto como prueba; neto con mini y micro (EMD con costo ESTIMADO dentro del permiso K33 de este pre-registro).
- §4: K38, la regla de un tercero en instrumentos que sus autores no usaron (QQQ → futuros).

Potencia previa: `holdout_ventanas.plan_potencia("fijo", 0,090, 2,56, n=10.089, alfa=0,0036)` → potencia 0,801 (n necesarias 10.073).
- **Efecto:** el de REP, que no se usó para elegir.
- **Desvío:** el de O1 en DESC+REP.
- **N:** contado sin desenlaces.
  - Holdout A5: NQ 1.150, ES 1.134, YM 1.159.
  - EMD 4.684 (2006-01-09 → 2025-07-31).
  - RTY 1.962 (2017-07-10 → 2025-07-31).
- **α:** el próximo nivel LORD++ de la familia (después de un REP sin confirmar).
- **Reserva:** `LibroLord().reservar("ORB_A5", "CONF_O1_20261118")` antes de correr.

## 1. Justificación económica
El rango de la primera vela de 5 minutos concentra la subasta de apertura. Su dirección refleja el desequilibrio de órdenes acumulado a la
noche y en la subasta, que tiende a continuar durante el día (Zarattini y Aziz 2023; momentum intradía, Gao et al. 2018). Si el mecanismo
es general, tiene que aparecer en meses e índices que no se usaron para verlo.

## 2. Regla (congelada, sin cambios)
- **Módulo y celda:** `edgelab/research/orb_a5.py`, definición O1, ejecución `("PRECIOS", "obj", "stop", "fin")`.
- **Señal:** dirección de la vela 9:30–9:35 NY. No se opera si |cierre − apertura| < 5 % de su rango.
- **Ejecución:** entrada a mercado en la vela siguiente; stop en el lado opuesto de la vela; objetivo 10R o cierre RTH.
- **Motor:** el único, con K40.
- **Mismo código que DESC/REP.** El lector M1 de NT8 sólo suma EMD y RTY.

## 3. Datos
- **NQ, ES, YM:** sólo las sesiones de los meses HOLDOUT de A5 (`a5_bloque == "HOLDOUT"`; el EMBARGO no entra), 2006-01-06 → 2025-07-31.
- **EMD:** todas las sesiones de 2006-01-09 → 2025-07-31. **RTY:** todas las de 2017-07-10 → 2025-07-31. Para el linaje de ORB quedan
  consumidas.
- **Holdout terminal (desde 2026-10-01):** intacto.

## 4. Prueba y decisión (una vez)
**Estadístico:** media de R bruto por operación, juntando los cinco instrumentos, con EE agrupado por sesión (una sesión de varios índices
es un cluster). P unilateral (H1: media > 0).

**CONFIRMADA si se cumplen las tres:**
- p ≤ nivel reservado (`LibroLord().resolver`) y media > 0;
- ≥ 60 % de los años con operaciones positivos;
- ningún tercil de volatilidad en contra significativo (tercil del ATR20 de la sesión RTH dentro de cada instrumento; «en contra» =
  media < 0 con p unilateral < 0,05).

**REFUTADA:** media ≤ 0 con la potencia declarada (MDE80 al nivel reservado ≈ 0,09).

**NO_CONFIRMADA (SIN_POTENCIA):** media > 0 sin llegar al nivel.

**Se reporta además:**
- por fuente (holdout A5 contra índices nuevos) y por instrumento;
- por época;
- neto con mini y micro;
- subconjunto operable (fricción ≤ 0,08 R).

**Lo económico no decide la confirmación del mecanismo; decide si se opera** (en papel/forward al tamaño mínimo; el dinero real lo decide
Nico).

## 5. Cómo podría refutarse
- **Media bruta ≤ 0 con potencia:** el ORB de 5 min no se sostiene fuera de los datos donde se vio. DESC+REP serían selección o
  particularidad de NQ/ES/YM.
- **Confirma en el holdout A5 pero no en EMD/RTY:** no transfiere.

## 6. Contador y registro
- **Contador:** 1 prueba.
  `tools/registro_global.py preregistrado ORB-A5-CONF-O1 ORB_A5 1 docs/research/orb_a5_20261118/PREREGISTRO_CONFIRMACION_O1.md`.
- **Apertura:** `holdout_ventanas.registrar_apertura("ORB_A5", "ORB_A5::CONF_O1_20261118", 20060106, 10089, plan=...)`, antes de correr.
