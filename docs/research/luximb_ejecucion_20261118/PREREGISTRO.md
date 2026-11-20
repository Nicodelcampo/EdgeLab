# LUXIMB-EJECUCION: rediseño de la ejecución del fade de impulsos LUX-IMB (stop amplio, objetivo, BE, parcial y rescate de Nico) en NQ M1 2006–2022, partición A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea, se cuenta y se commitea el registro antes de calibrar y correr.
- **Pedido de Nico** (punto 2): «para rediseñar la ejecución sería bueno probar un mecanismo de: al precio adentrarse x en el stop,
  se espera a que vuelva a x de la entrada y se cierra. Y todo lo que propongas vos también probalo».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC y EF5 en el holdout A5. **Familia:** `LUXIMB_EJECUCION_A5` (hija de `LUXIMB_A5_ZONAS25`).
- **Herramientas:**
  - módulo `edgelab/research/luximb_ejecucion.py` (contrato de `tablas`, preflight OK);
  - motor único con la ejecución nueva `RESCATE` (tests y calibración del motor sin optimismo);
  - `tools/a5_campana.py` (calibración, corrida, DESC).

Antecedentes: `docs/research/luximb_a5_20261118/RESULTADO.md` y F-LUXIMB-A5-REVERSION-BRUTA-B.
- **Lo medido:** el fade hacia A después de un impulso fuerte revierte en bruto en NQ 2006–2022. DESC dio +0,02 a +0,11 R en 21/21
  celdas y REP confirmó `z0|sl0.2` (+0,053) y `z1|sl0.35` (+0,076) con LORD++.
- **Por qué no se operó:** la fricción en R (0,1–2,2 R con stops de 0,2–0,5·D) supera al bruto. REFUTADA_ECONOMICA; el holdout A5
  quedó sellado para el linaje.
- **Lo que dice el factor:** «sólo un hijo con stop amplio (fricción ≤ 0,08 R) abre el holdout».
- **Palancas aplicables:** F-STOP-GRANDE-FRENTE-A-FRICCION, F-SALIDA-TECNICA-REGALA-LA-GANANCIA y F-AJUSTE-FINO-NO-PAGA (meseta: se
  publica la grilla entera).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6.
- §2: A5; M1 de futuros (`tools/datos.py`); calibración contra ticks; K40.
- §3: R con el riesgo inicial; bruto y neto con mini y micro; fricción por época.
- §4: BH; potencia al nivel LORD (K42); árbol de confirmación.
- §6: K45–K48.

Potencia previa:
- **Holdout A5 de NQ 2006–2022** (meses HOLDOUT del linaje, sellados): ≈ 42.800 marcas z0 y ≈ 8.500 z1 (CORRIDA de LUXIMB-A5).
- **El plan de potencia de la apertura** se calcula con `holdout_ventanas.plan_potencia` al nivel LORD reservado (K42), con efecto = la
  mitad del R neto en DESC de cada celda congelada y su desvío. Se abre sólo si da ≥ 0,8.
- **DESC tiene ≈ 106.000 marcas z0** (con superposición; EE agrupado por sesión). Alcanza para ver diferencias de 0,02 R.

## 1. Justificación económica
- **La señal:** la reversión de un impulso fuerte hacia su origen es real pero chica (≈ 0,05 R con stop corto).
- **La fricción:** es fija en puntos, así que con stops cortos pesa más que la señal.
- **El rediseño:**
  - un stop más amplio baja la fricción en R, y si la reversión es un fenómeno de distancia (no de timing fino), el bruto por R no
    debería caer proporcionalmente;
  - el rescate de Nico corta la cola de pérdidas cuando la operación se fue en contra y vuelve: convierte parte de los stops en salidas
    cerca de la entrada, sin achicar el stop;
  - el BE, el parcial y el objetivo más allá de A son alternativas clásicas del mismo problema.

## 2. Espacio de eventos y ejecuciones
**Eventos:** los de LUXIMB-A5 (D3_20, amplitud ≥ p60 causal sin piso). Definiciones:
- **`z0`:** control, toda marca;
- **`z1`:** ≥ 1 zona OG/VI en el 25 % inicial.

**22 ejecuciones del motor único** (D = distancia a A desde la entrada):
- **MERCADO** stop 0,5 / 1 / 1,5 / 2·D, objetivo A;
- **objetivo 1,5·D** con stop 1 y 2·D;
- **BE a 0,5·D** con stop 1 y 2·D;
- **parcial del 50 % a 0,5·D** con stop 1 y 2·D;
- **RESCATE** stop 1 / 1,5 / 2·D, objetivo A, d ∈ {0,5; 0,75}, x ∈ {0; 0,25}. Interpretación de la frase de Nico: «adentrarse x en el
  stop» = ir d del riesgo hacia el stop; «vuelva a x de la entrada» = volver a −x del riesgo desde la entrada (x = 0: la entrada).

**Pruebas:** 44 = 2 definiciones × 22 ejecuciones.

## 3. Datos y fases
- **NQ M1 de futuros 2006-01-06 → 2022-12-30**, con la partición A5. 2023+ lo miró el linaje.
- **Fase 0, calibración:** M1 contra ticks reales en 2025-08 → 2026-03 (desarrollo ya mirado), con el criterio único
  `a5.calibrar_por_sesion`, commiteada antes de correr.
- **DESC (meses DESC):**
  - nominada = BH q 0,10 sobre el bruto, media > 0, ≥ 60 % de años positivos y calibra (`a5.nominar`);
  - **compuerta económica:** R NETO (fricción canónica de NQ) > 0 en DESC.
- **REP** (meses REP, ya consumidos por la familia madre con otras ejecuciones): sólo chequeo de signo del neto, sin α.
- **Holdout A5:**
  - hasta 3 celdas congeladas: las de mayor cota inferior del IC90 del neto en DESC entre las que pasan DESC y el signo en REP;
  - una apertura, con el plan de potencia al nivel LORD (≥ 0,8);
  - confirmada = p ≤ nivel (neto > 0), ≥ 60 % de años positivos y neto con micro > 0.

**Se publica la grilla entera** (las 44) y, como descriptivo, rescate − mercado con el mismo stop.

## 4. Cómo podría refutarse
- **Ninguna ejecución tiene neto > 0 en DESC:** la reversión no sobrevive a la fricción con ninguna ejecución razonable. La familia
  se cierra en lo económico.
- **El bruto por R cae al ensanchar el stop tanto como baja la fricción:** la reversión es de timing fino, no de distancia.
- **El rescate no mejora al mercado con el mismo stop:** la cola recuperable es chica o el rescate corta ganadoras.
- **El holdout no confirma:** lo de DESC era selección.

## 5. Contador y linaje
- **Contador:** 44 pruebas.
  `tools/registro_global.py preregistrado LUXIMB-EJECUCION LUXIMB_EJECUCION_A5 44 docs/research/luximb_ejecucion_20261118/PREREGISTRO.md`,
  y el commit del registro antes de correr.
- **Linaje:** `LUXIMB_EJECUCION_A5` ← `LUXIMB_A5_ZONAS25`. Su holdout A5 es el del linaje: una sola apertura.
