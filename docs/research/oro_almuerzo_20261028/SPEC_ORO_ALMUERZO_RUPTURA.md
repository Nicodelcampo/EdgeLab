# Especificación Pre-Registrada — Familia `ORO-ALMUERZO-RUPTURA` (`Estrategia del Oro de la Hora de Comer`)

## 1. Motivación e Hipótesis Microestructural
Esta familia traduce y expande al marco de grilla masiva de EdgeLab (`grilla_generica.py`, **1.259.712 celdas por canal**) la estrategia del oro (`XAUUSD` / `GC`) basada en la acumulación matutina europea (`08:00` a `14:00` hora de España `Europe/Madrid`) y la ruptura a la «hora de comer» (`14:00` Madrid, coincidente con la apertura de la mañana estadounidense `08:00 ET`), integrando los aprendizajes empíricos de `ORO-0530-RUPTURA` y `U1-ORO`.

### Hipótesis Física
1. **Rango Matutino Europeo (`08:00–14:00 Europe/Madrid`) y Sesgo respecto a `Open_08`**:
   Entre las `08:00` y las `14:00` hora de España (`CET/CEST`), el oro define su caja de liquidez matutina `[lo_man, hi_man]` de altura `H_man = hi_man - lo_man`. Cuando el precio marca cierres horarios por debajo del precio de apertura de las `08:00` (`Open_08`) sin destruir la estructura alcista mayor («mañana bajista de absorción») y posteriormente a partir de las `14:00` rompe el máximo de la mañana (`hi_man`), se desencadena un desplazamiento direccional impulsado por la entrada de flujo de Nueva York hasta las `18:00` hora de España (`240` minutos).
2. **Contraste con `ORO-0530-RUPTURA` y `U1-ORO`**:
   En `ORO-0530-RUPTURA` se observó que las órdenes stop puras en el borde sufren whipsaws en horizontes cortos (`15–30 min`), pero mejoran en horizontes largos con filtros de confirmación o retesteo, mientras que `U1-ORO` demostró la importancia de condicionar por la `escala_mensual` causal de volatilidad del oro y por los vacíos de liquidez (`ZONAS-GAPS`). Por ello, esta grilla parametriza simultáneamente la regla literal del video y sus variantes estructurales.

## 2. Espacio de Parámetros (`VARIABLES` — 9 Perillas + `EJECUCIONES` = 1.259.712 Celdas por Canal)

| # | Perilla (`Variable`) | Columna | Modo | Niveles | Definición Exacta |
|---|---|---|---|---|---|
| 0 | `ventana_manana` | `v_man` | `grupo` | 3 | `0`: `08:00–14:00 Europe/Madrid` (literal video, DST-aware) · `1`: `08:00–13:30 Europe/Madrid` (pre-macro EE.UU.) · `2`: `07:00–13:00 UTC`. |
| 1 | `gatillo_entrada` | `gat` | `grupo` | 3 | `0`: `RUPTURA_STOP` (`Buy Stop` en `hi_man` / `Sell Stop` en `lo_man`, literal video) · `1`: `CIERRE_CONFIRMA` (cierre fuera por $\ge 0.06 H_{man}$) · `2`: `RETEST_O_TRAMPA_U1` (excursión $\ge 0.10 H_{man}$ y regreso al borde). |
| 2 | `condicion_sesgo` | `sesgo_cond` | `eq_any` | 3 (+1) | `0`: algún cierre H1 opuesto a `Open_08` (literal video) · `1`: cierre de las `14:00` opuesto a `Open_08` · `2`: mañana a favor · `3`: cualquiera. |
| 3 | `simetria_lado` | `lado_sim` | `eq_any` | 2 (+1) | `0`: `SOLO_LONG` (ruptura de `hi_man`, literal video) · `1`: `SOLO_SHORT` (ruptura de `lo_man`) · `2`: `AMBOS_SIMETRICO` (cualquiera). |
| 4 | `escala_mensual` | `esc_mes` | `ge` | 3 | Escala causal de los últimos 20 días previos (`u1_oro`): `0`: todas · `1`: $\ge 0.65$ · `2`: $\ge 1.05$. |
| 5 | `gap_iman` | `g_iman` | `eq_any` | 3 (+1) | Puntaje continuo `ZONAS-GAPS` de gaps vivos creados durante la mañana (`cortes = (0.05, 1.00)`). |
| 6 | `compresion_manana` | `tam_man` | `extremos` | 3 | Terciles causales de `H_man / ATR14` (`0`: mañana comprimida T1 · `1`: mañana expandida T3 · `2`: cualquiera). |
| 7 | `posicion_open08` | `pos_op08` | `extremos` | 3 | Terciles causales de la posición relativa de `Open_08` dentro de `[lo_man, hi_man]`. |
| 8 | `vwap_al` | `vwap_al` | `eq_any` | 2 (+1) | `0`: contra `VWAP` · `1`: a favor del `VWAP` de la sesión · `2`: cualquiera. |
| 9 | `ejecución` | — | `grupo` | 36 | `2` modos (`RUPTURA`, `FADEO_U1`) $\times$ `2` entradas (`CIERRE`, `SIG`) $\times$ `3` objetivos (`TIEMPO_18H` = salida horaria 240 min / `18:00` Madrid con techo `3.0 H`, `TP_100H`, `TP_150H`) $\times$ `3` stops (`S_OPEN08` = `0.35 H`, `S_MID50` = `0.60 H`, `S_OPUESTO` = `1.00 H`). |

## 3. Campañas y División por Cuentas de Kaggle
- **`ORO-ALM-CFD`** (`sensor: DK:XAUUSD`, `ejecucion: GC`, `cuenta_kaggle: nicobuttaro`, `desc: [20250805, 20260331]`, `oos: [20260401, 20260930]`).
- **`ORO-ALM-GC`** (`sensor: GC`, `ejecucion: GC`, `cuenta_kaggle: nicolasbuttaro`, `desc: [20250805, 20260331]`, `oos: [20260401, 20260930]`).
