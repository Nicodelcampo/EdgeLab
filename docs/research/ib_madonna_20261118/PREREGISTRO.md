# IB-MADONNA: Initial Balance + «Madonna» refinada y 10 variantes, en M1 de NQ, ES y YM 2006–2025, con la partición A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** el diseño en `DISENO.md`, misma carpeta, con la idea principal refinada y 10 variantes de lógica distinta.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT. **Familia:** `IB_MADONNA_A5` (nueva, sin linaje).
- **Herramientas:** `edgelab/research/ib_madonna.py` (contrato de `tablas`; preflight OK) y `tools/a5_campana.py` con `CAMPANA.json`.

Antecedentes: `tools/antecedentes.py "initial balance primera hora rango apertura NY fade bordes objetivo mitad primer toque"`.
- **Vinculados, todos con estado NO_REPETIR o EN_CONTRA:** F-OP1-FADE-NIVEL-LIMPIO, F-ORB-EMA20-NQ-STOP-OPUESTO y ORB0100.
- **T (ORB 15 min + KNN):** pista NQ.
- **Palancas:** F-STOP-GRANDE-FRENTE-A-FRICCION y F-SELECCION-ADVERSA-PASIVA.
- **Nada medido sobre el IB de 60 min ni sobre la Madonna.** El diseño descarta la grilla de 62 parámetros de las fuentes, los filtros
  en puntos y la entrada límite (`DISENO.md` §1).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v2 — §0–§5.
- §1: población y espacio de eventos (abajo).
- §2: A5; calibración contra ticks (K30); K40 en el motor.
- §3: R; K36 (todo en fracciones del IB o del rango); bruto y neto con fricción en R por época.
- §4: potencia abajo; K38: es una regla de un tercero, por eso se prueba en tres índices y 20 años que el autor no pudo usar para
  ajustar.

Potencia previa: plan de `holdout_ventanas.plan_potencia` (sin operaciones de desarrollo; efectos declarados; N contado sin retornos en NQ ene–jun 2022, ≈ 100 Madonnas por año e índice):
- **V0, tres índices (≈ 1.450 en el holdout):**
  - efecto 0,10 R (sd 1,2): potencia 0,48;
  - efecto 0,20 R: 0,94.
- **V3** (≈ 2.000, efecto 0,10, sd 1,5): 0,44.
- **Filtros** (diferencia, ≈ 700): 0,27.
- **Lectura:** el holdout sólo puede confirmar efectos de ≥ ~0,15–0,2 R. Si DESC muestra efectos menores, la familia queda SIN_POTENCIA
  y su camino es el forward (el terminal), no la apertura (E8).

## 1. Justificación económica (general; la de cada variante está en `DISENO.md` §3)
- El IB es el rango donde los participantes de corto plazo establecieron valor en la primera hora.
- En un día de equilibrio, el primer rechazo de un borde (los compradores no aceptan precios más altos) devuelve el precio hacia el
  valor (la mitad).
- En un día de desequilibrio, la aceptación afuera señala que los de largo plazo empujan, y la ruptura continúa.
- Las variantes separan esos dos tipos de días con información conocida en el momento:
  - apertura dentro/fuera del rango previo;
  - IB ancho/angosto;
  - Open-Drive;
  - gap;
  - volumen;
  - impulso.

## 2. Espacio de eventos y población
**Espacio:** con respecto a un borde del IB, después de las 10:30:
- primer toque con rechazo (Madonna);
- primer toque con aceptación;
- ruptura fallida;
- doble prueba;
- aceptación sostenida (dos cierres afuera);
- toque n-ésimo;
- estado (adentro/afuera del IB);
- extensión de rango.

**Elegidas:** Madonna (V0 y sus filtros V1, V2, V5–V9), aceptación (V3), ruptura fallida (V4) y doble prueba (V10).

**Fuera:** toque n-ésimo (salvo V10), estado y extensión como objetivo de grilla.

**Población:** sesiones RTH de NQ, ES y YM (9:30–16:00 NY, M1 de NT8), con ≥ 50 velas en el IB, 2006-01-06 → 2025-07-31.

## 3. Ejecución y medición (motor único, ejecución `PRECIOS`)
- **Entrada:** a mercado en el primer tick de la vela M1 siguiente al cierre de la vela de decisión de 5 min.
- **Stop y objetivo:** los precios de cada variante (`DISENO.md`). Tenencia de 240 velas o fin de sesión.
- **Unidad:** R bruto; neto con la fricción canónica de cada índice.
- **Subconjunto operable declarado:** fricción ≤ 0,08 R.
- **MNQ/MES/MYM:** mismo precio; el neto con su fricción se reporta como descriptivo.

## 4. Partición A5 y fases (igual que ESCALONADAS-M1)
0. **Calibración** contra ticks en 2025-08-05 → 2026-03-31 (Kaggle) con `a5.calibrar_por_sesion`. Una celda que no calibra no se nomina.
1. **DESC:** 16 pruebas (11 variantes, cada una con su ejecución, más 5 contrastes filtro − complemento: V1, V2, V6, V7, V9). R bruto,
   EE por sesión, BH q 0,10. **Nominada:** BH + media > 0 + ≥ 60 % de años positivos (absolutas) + calibra.
2. **REP:** un paso de LORD++.
3. **HOLDOUT:** apertura única, sólo con las confirmadas. Exige compuerta económica (neto operable) y potencia ≥ 0,8 con el N real.
   **Confirma si:** p ≤ nivel, media > 0, ≥ 60 % de años positivos y ningún tercil de volatilidad en contra.

## 5. Cómo podría refutarse
- **La Madonna:** V0 ≤ 0 en bruto con potencia. Si además V0 no supera a la aceptación ni al toque sin rechazo, el «rechazo» no aporta,
  igual que F-OP1.
- **Cada filtro:** su contraste ≤ 0.
- **La economía:** el neto operable ≤ 0.

## 6. Contador y linaje
- **Contador:** 16 pruebas.
  `tools/registro_global.py preregistrado IB-MADONNA IB_MADONNA_A5 16 docs/research/ib_madonna_20261118/PREREGISTRO.md`.
- **Linaje:** familia nueva. V8 usa marcas de LUX-IMB como condición (padre declarado: LUXIMB_A5_ZONAS25, cuyo holdout sigue sellado; V8
  no lo abre).
