# LUXIMB-A5: impulsos de LUX-IMB con zonas en el 25 % inicial, en M1 de NQ 2006–2022 con la partición A5 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «revisá si se podrían lanzar variantes de lux imb con impulso y zonas en el 25 %» y «sí, … corregí errores que surjan».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapas:** EF3 en DESC, EF4 en REP y EF5 en HOLDOUT.
- **Familia:** `LUXIMB_A5_ZONAS25`. Es la primera campaña con la partición HOLDOUT-A5.
- **Herramienta:** `tools/luximb_a5.py`.

Antecedentes: `tools/antecedentes.py "impulso LUX-IMB zonas atravesadas en el 25 % inicial fade hacia A visor"`.
- **F-LUXIMB-ZONAS-VS-CONTROL-B** (PISTA_VIVA): con ≥ 3 zonas, la expansión revierte mejor que sin zonas.
  - Visor − control: +0,04 a +0,17 R en el desarrollo (NQ y USATECH, 2025-08 → 2026-09).
  - En la confirmación congelada en USATECH 2023-01 → 2025-07 dio +0,056 R, NO_CONFIRMADA por potencia (MDE80 0,15).
  - El visor queda ≈ 0 neto en absoluto.
- **F-LUXIMB-HFT-ZONAS** (NO_REPETIR): zonas HFT en lugar de OG/VI. No se usan acá.
- **Tablas de desarrollo en ticks:** `luximb_hvn_20261111/tablas`.
- **Qué agrega esta campaña:** potencia. 17 años de M1 dan decenas de miles de marcas, contra 489 en el desarrollo.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v1 — §0–§5.
- §2: el linaje usó 2023-01 → 2026-09; se calibra M1 contra ticks antes de correr.
- §3: medido en R con el stop inicial (`k_` = 0,5/0,35/0,2 · D); K36 abajo; bruto y neto con fricción en R por época.
- §4: K38 no aplica (la regla es propia); la potencia está abajo.

Potencia previa: DEV_TICKS_z2_sl05_bruto.csv: 36.4 ops/mes, R/op +0.103, sd 1.43, n para decidir 1210, 33.2 meses → OK | lectura de N 4200 con la mitad del efecto: potencia 0.749 (NO se abre).
- **Lectura:** con la mitad del efecto de desarrollo (+0,05 R bruto, sd 1,43), el holdout de 2006–2022 (≈ 4.000–4.500 operaciones de la
  celda de ≥ 3 zonas, contadas sin retornos en Q1-2010) queda cerca del límite.
- **Regla declarada:** la potencia de cada celda nominada se recalcula con el N real del holdout. Ese N se cuenta en `EVENTOS.csv.gz`,
  sin desenlaces. Si no llega a 0,8, la apertura no se gasta (E8) y la celda queda SIN_POTENCIA.
- **Extensión posible:** ES/YM con la misma regla, como pre-registro aparte.
- **Neto, no es el estadístico de esta campaña:** la celda de stop 0,5 tarda 88 meses en forward (+0,063 R, K27).

## 1. Justificación económica
Un impulso amplio y rápido que atraviesa enteras zonas de desequilibrio recién nacidas (OG/VI) cerca de su origen consume liquidez de un
solo lado. Si el empuje fue flujo urgente y no información, el precio vuelve hacia A. Las zonas en el 25 % inicial marcan ese consumo
temprano. Sin la condición de zonas (control) no debería haber reversión.

## 2. Espacio de eventos y población (regla de población)
**Espacio:** impulsos del detector D3_20 (≥ 3·ATR14 en ≤ 20 velas, eficiencia ≥ 0,3). Para cada uno, la PRIMERA vela M1 en que cumple a la vez:
- amplitud ≥ percentil 60 causal de los tramos confirmados;
- rapidez ≥ mínimo causal;
- la condición de zonas.

**Definiciones de zonas** (`LG.ZON`):
- z0, sin condición: es el control;
- z1: ≥ 1 zona en el 25 % inicial;
- z2: ≥ 3 zonas (el visor);
- z3: ≥ 5 zonas.

En z1–z3 se exige además que ≥ 50 % de las zonas atravesadas caigan en esa franja.

**Alternativas no elegidas:** creación de zona, toque, estado continuo, franja del 50 %, detectores D2/D4/D3_40 y la entrada EXT.
- Quedan fuera para mantener la familia chica (21 pruebas).
- La hipótesis previa es la del 25 % con fade a mercado.

**K36, parámetros en puntos fijos:**
- El piso de amplitud de 60 pts del visor se retira, porque en 2010 deja 3 marcas por año. Queda sólo el percentil causal, sin escala.
- El detector de zonas OG/VI no tiene piso de ancho.
- Los únicos pisos en ticks del detector son de 2 ticks (despreciables).
- La calibración usa la definición con piso, igual a las tablas de ticks.

## 3. Ejecución y medición
**Ejecución:** fade hacia A a mercado en el primer tick de la vela k+1, con objetivo 1,0·D y D = |entrada − A|. El stop sale a mercado al
tick que lo cruza, con el salto (`luximb_hvn._e0_nb`). La tenencia máxima es de 240 velas, o hasta el fin de sesión o un hueco de 30 min.

**Stops:** 0,5·D, 0,35·D y 0,2·D, tres ejecuciones sin parcial ni BE.

**Unidad:** R bruto = resultado / stop inicial. El neto resta la fricción canónica de NQ (`embudo_runners.friccion`, 1,5455 pts) /
riesgo en puntos.

**Subconjunto operable declarado:** fricción en R ≤ 0,08.

## 4. Partición A5 y ventana
**Ventana:** NQ M1 de NT8 (`M1NT8:`), 2006-01-06 → 2022-12-30.
- 2023-01 → 2026-09 queda fuera: lo usó el linaje (H-ZONAS en USATECH 2023-01 → 2025-07 y el desarrollo en ticks 2025-08 → 2026-09).
- **Riesgo declarado:** familias hermanas miraron otros objetos LUX-IMB en años de la ventana, sin propagar al linaje por la regla de
  herencia:
  - LUXIMB_AMARILLA, la caja amarilla en M1 de Dukascopy 2012–2023;
  - INTENTO_FALLIDO_LUX_NQ, aproximación fallida, «atrás» 2006–2022.
- **Sensibilidad:** todo se reporta también en 2006–2011, años que ninguna familia LUX-IMB miró con impulsos.

**Partición:**
- Los eventos (sin retornos) se calculan de corrido en toda la ventana.
- Los desenlaces se calculan sólo en sesiones DESC y REP (`holdout.a5_bloque`).
- HOLDOUT y EMBARGO quedan sin desenlace hasta la apertura.
- Las operaciones son intradía y no cruzan bloques.

## 5. Fases y decisión
0. **Calibración (K30)**, sobre el desarrollo ya mirado (2025-08 → 2026-09).
   - Se corre la misma tabla en M1 de NT8 y se compara por sesión con las tablas de ticks de LUXIMB-HVN.
   - Criterio de `atras_m1.calibrar`: ≥ 30 sesiones comunes, mismo signo, diferencia ≤ 1 EE y correlación > 0,5.
   - Una celda que no calibra no se nomina. Se commitea `CALIBRACION.json` antes de correr.
1. **DESC:** 21 pruebas sobre R bruto con error estándar agrupado por sesión, p unilateral.
   - 12 absolutas: z0–z3 × 3 stops.
   - 9 contrastes zonas − control: bootstrap por sesión, porque comparten impulsos.
   - BH q 0,10.
   - **Nominada si:** BH + media > 0 + ≥ 60 % de años DESC positivos (las absolutas) + calibra.
2. **REP:** las nominadas, con un paso del libro LORD++ (`LUXIMB_A5_ZONAS25::REP_20261118`). Se commitea `DESC.json` antes.
3. **HOLDOUT:** una apertura de la familia, con todos los meses HOLDOUT de 2006–2022 a la vez.
   - **Requisitos para abrir:**
     - sólo las confirmadas en REP, a N fijo;
     - plan de potencia ≥ 0,8 con la mitad del efecto de DESC;
     - `registrar_apertura` y la reserva LORD hechas antes.
   - **Confirma si se cumplen las tres:**
     - p ≤ nivel reservado y media bruta > 0;
     - ≥ 60 % de años positivos;
     - ningún tercil de volatilidad en contra significativo.
   - **Lectura económica:** R neto del subconjunto operable (fricción ≤ 0,08 R) en el holdout.
   - Si es > 0 con el IC90 por sesión, va a papel/forward al tamaño mínimo. El terminal (A4) vigila.

## 6. Cómo podría refutarse
- **Mecanismo refutado:** ningún contraste zonas − control nominado con potencia en DESC, o en contra en REP.
- **Regla refutada (en bruto):** la celda absoluta ≤ 0 en el holdout con potencia.
- **No operable:** el neto operable ≤ 0, aunque el bruto confirme.

## 7. Contador y linaje
- **Contador:** 21 pruebas, `tools/registro_global.py preregistrado LUXIMB-A5 LUXIMB_A5_ZONAS25 21 docs/research/luximb_a5_20261118/PREREGISTRO.md`.
- **Linaje:** padres LUXIMB_HVN, LUXIMB_GRILLA y LUXIMB_FADE_VISOR (`LINAJES.jsonl`).
- **Integración en el embudo:** pendiente. Esta campaña aplica A5 con `holdout.a5_bloque` desde la herramienta, y la integración general
  queda como tarea aparte.

## Enmienda 1 (2026-11-18, antes de cualquier desenlace de 2006–2022): modelo de stop en M1
- **Qué pasó:** la fase 0 falló en las 12 celdas (`CALIBRACION_v0.json`).
  - La correlación por sesión fue alta (0,71–0,96), pero M1 resultó sistemáticamente más negativo. En el control con stop 0,2·D, M1 da
    −10 R por sesión contra +0,15 en ticks.
- **Causa raíz** (medida en ago–oct 2025):
  - Los stops saltan con la misma frecuencia en M1 y en ticks (82 %).
  - La pérdida media en M1 es −1,53 R contra −1,01 R en ticks, con un mínimo de −7,8 R.
  - `_e0_nb` sale al precio del tick que cruza el stop, y con pseudo-ticks de M1 (apertura, extremos, cierre) ese tick es el extremo de
    la vela.
  - El motor común (`areas_expansion.simular_cierre_linea`, error 27) usa la misma convención. Con stops anchos no se nota; con stops de
    0,2–0,5·D sí.
- **Corrección** (modelo de llenado, no tolerancia; con datos reales no cambia nada): con `ctx["m1_sintetico"]`, un stop cruzado por un
  pseudo-tick que no es apertura sale en el nivel del stop, y uno cruzado en la apertura (hueco) sale al precio de la apertura.
  - Test: `tests/research/test_luximb_hvn.py::test_e0_m1_stop_en_su_nivel_salvo_hueco_en_la_apertura`.
- **Qué no cambia:** criterios de calibración, celdas, ventanas y decisión.
- **Si la recalibración vuelve a fallar:** la familia no se corre en M1 y queda para ticks.
