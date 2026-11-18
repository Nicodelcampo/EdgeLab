# ORB-A5: ocho variantes de Opening Range Breakout en M1 de NQ, ES y YM 2006–2025, con la partición A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «quiero que midas variantes de ORB; diseñalas vos en base a los datos que ya hay en EdgeLab y también con research
  en Internet».
- **Diseño:** `DISENO.md`, misma carpeta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT. **Familia:** `ORB_A5` (nueva).
- **Herramientas:**
  - `edgelab/research/orb_a5.py` (contrato de `tablas`; preflight OK);
  - el motor único, con la salida por vela por fila (`("PRECIOS", obj, stop, fin)`, test y calibración del motor nuevos);
  - `tools/a5_campana.py` con `CAMPANA.json`.

Antecedentes: `tools/antecedentes.py "initial balance primera hora rango apertura NY ..."` y la búsqueda de ORB del `DISENO.md` §1.
- **F-ORB-EMA20-NQ-STOP-OPUESTO (NO_REPETIR):** no hay variante con retroceso a la EMA ni stop elegido por P&L.
- **OTR930:** negativa 2012–2025.
- **T:** ORB 15 + KNN, pista NQ.
- **ORB0100:** EN_CONTRA.
- **Literatura** (`DISENO.md` §2): Zarattini-Aziz 2023/2024, Zarattini-Aziz-Barbon 2024, Gao-Han-Li-Zhou 2018, Crabel 1990,
  Holmberg et al. 2013.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v2 — §0–§5.
- §2: A5; calibración contra ticks; K40.
- §3: R; K36 (rangos y ATR relativos; los parámetros publicados se usan tal cual, sin ajuste); bruto y neto por época.
- §4: K38 (reglas de terceros probadas en instrumentos y años que sus autores no usaron: QQQ/SPY → futuros NQ/ES/YM 2006–2025).

Potencia previa: plan de `holdout_ventanas.plan_potencia` (sin desarrollo; efectos declarados de 0,10 R; N del holdout contado sin retornos en NQ 2021, ≈ 250 operaciones por año e índice en O1/O2/O6):
- **Con la mitad del efecto:**

  | Variante | Potencia | N necesario |
  |---|---|---|
  | O1 (sd 2,5) | 0,33 | 15.457 |
  | O2 (sd 1,8) | 0,53 | 8.013 |
  | O6 | 0,43 | — |
  | O7 | 0,30 | — |
  | O8 | 0,64 | — |
  | contrastes | ≈ 0,3 | — |

- **Lectura:** el holdout A5 de tres índices sólo confirma efectos de ≥ ~0,2 R (o ≥ 0,15 en O8). Lo que DESC muestre por debajo queda
  SIN_POTENCIA para la apertura y su camino es el forward (E8).

## 1. Justificación económica
- **O1/O2:** el rango de apertura concentra la información de la noche y la subasta de apertura. Romperlo con participación anormal
  (O5), con contracción previa (O3) o a favor del gap (O4) indica desequilibrio que continúa.
- **O6:** el rebalanceo del cierre y la información lenta prolongan el movimiento de la primera media hora (Gao et al.).
- **O7:** salir de la banda de ruido diaria es salir del equilibrio (Zarattini-Aziz-Barbon).
- **O8:** la ruptura que vuelve adentro atrapa a los que la siguieron.

## 2. Espacio de eventos y población
**Espacio:** rango de apertura de 5, 15, 30 o 60 min (el de 60 min está en IB-MADONNA). Sobre él:
- ruptura por cierre, por toque o por orden;
- retroceso, ruptura fallida y aceptación;
- estado;
- momentum de la primera media hora;
- banda de ruido.

**Elegidas:** las 8 del `DISENO.md` §3, con sus parámetros de la fuente.

**Fuera:** rango de 60 min (en IB), retroceso a la EMA (NO_REPETIR) y entrada por orden (selección adversa).

**Población:** sesiones RTH (9:30–16:00 NY) de NQ, ES y YM, M1 de NT8, 2006-01-06 → 2025-07-31.

## 3. Ejecución y medición
- **Entrada:** a mercado en la vela siguiente a la decisión.
- **Stop:** el de cada variante.
- **Salida:** objetivo 10R (O1) o el cierre RTH. La salida es la vela k + los minutos hasta las 15:59 (causal; con minutos faltantes
  puede terminar unos minutos después).
- **O7:** stop fijo en el VWAP o la banda (sin el stop dinámico del paper: el motor no lo tiene; se declara).
- **Unidad:** R bruto y neto con la fricción canónica; subconjunto operable con fricción ≤ 0,08 R.

## 4. Partición A5 y fases
Las mismas que IB-MADONNA y ESCALONADAS-M1:
0. calibración contra ticks (2025-08 → 2026-03);
1. DESC con 11 pruebas (8 absolutas + 3 contrastes: O3, O4 y O5 contra su complemento), BH q 0,10;
2. REP con LORD++;
3. HOLDOUT con apertura única, compuerta económica y potencia ≥ 0,8.

**Sensibilidad:** 2006–2011 por separado (`limpios`).

## 5. Cómo podría refutarse
- **Regla:** bruto ≤ 0 con potencia en DESC/REP/HOLDOUT.
- **Filtro:** su contraste ≤ 0.
- **Literatura:** si O1 y O7 (las reglas publicadas) dan ≤ 0 en futuros 2006–2025, su resultado no transfiere de ETF a futuros, o no
  sobrevive fuera de su muestra.

## 6. Contador y linaje
- **Contador:** 11 pruebas.
  `tools/registro_global.py preregistrado ORB-A5 ORB_A5 11 docs/research/orb_a5_20261118/PREREGISTRO.md`.
- **Linaje:** familia nueva diseñada desde la literatura (padres: ninguno). T, OTR930 y ORB-EMA20 miraron NQ 2012–2025 con otras reglas
  de apertura: sensibilidad 2006–2011.
