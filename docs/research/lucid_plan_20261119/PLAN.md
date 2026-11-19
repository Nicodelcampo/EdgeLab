# LUCID-PLAN: elegir el plan de LucidFlex que más dinero da y reproducirlo sobre el holdout ya abierto (plan, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de correr `tools/lucid_plan.py`. Descriptivo: no cuenta pruebas ni abre ventanas nuevas.
Pedido de Nico: «simulá bien para determinar qué es lo que más me conviene hacer para ganar la mayor cantidad de dinero posible. Luego
simulá esa estrategia como si la hubiera hecho en challenges a partir del holdout». North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: económica (EF4, sin prueba nueva).

Antecedentes: LUCID-GUIA (`../lucid_guia_20261119/`: piso y DLL modelados al cierre; con minis eso sobrestima), REGIMEN-FORWARD, holdout de
FUNDEDSYNC (`../fundedsyncstack_20261115/RESULTADO_HOLDOUT.md`, abierto el 2026-11-16).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K33 costos, K49 potencia, K55 diagnóstico).

Potencia previa: no aplica a la elección (no es una prueba). La reproducción en el holdout son 32 sesiones (2026-10-01 → 2026-11-13): una
sola trayectoria, sin potencia para confirmar nada; es una ilustración de cómo habría ido la cuenta, no evidencia de ventaja.

Diagnóstico de mecanismo: la grilla de planes no busca ventaja: todas las celdas operan las mismas reglas (T, R, Z-banda) y sólo cambian
tamaño, cuenta y reglas de la cuenta. El número de operaciones por celda es el mismo para cada canasta; lo que mueve el resultado es el
tamaño frente al piso. Se publica la grilla entera.

## Modelo (mejoras sobre LUCID-GUIA)
- **Mínimo intradía de cada día:** cada operación aporta su excursión adversa (MAE topeada por el stop, con la fricción entera) después del
  P&L ya realizado ese día (orden por hora de entrada).
- **Piso:** se rompe si el saldo + el mínimo del día lo toca.
- **DLL:** si el mínimo del día lo toca, el día cierra en −DLL.
- **Contratos fijos por regla:** micros, o minis si son múltiplos de 10.
- **Tope de Lucid:** se aplica a todas las reglas abiertas a la vez. Z-banda = s//9 micros por configuración.
- **Datos:** desarrollo 2020-01 → 2026-09.
- **Media:** contraída a la mitad por operación (lectura principal); se reportan también la de desarrollo y la cero.
- **Calendarios:** 24 meses, bootstrap por bloques de 5 sesiones. Límites del hogar: 10 evaluaciones, 5 fondeadas, 10 en total; cierre al
  pasar a live.

## Criterio (fijo)
1. **Etapa 1:** grilla completa con 3 evaluaciones a la vez:
   - tamaño 25K / 50K / 100K / 150K;
   - canasta T / T+R / T+R+ZB;
   - unidad s de 1 a 50 micros;
   - DLL sí / no;
   - consistencia 40 / 50 %;
   - retiro máximo / en cuanto se pueda.
2. **Etapa 2:** las 25 mejores por neto medio a 12 meses, con 1, 3, 5 y 10 evaluaciones a la vez y las tres medias.
3. **Elegido:** el máximo neto medio a 12 meses con la media contraída, entre los planes con P(neto 12 m > 0) ≥ 0,8 con esa media.
- **Justificación económica:** el dinero sale de la ventaja de la canasta apalancada en la asimetría de la cuenta; el tamaño frente al
  piso decide cuánto de cada una.
- **Cómo podría refutarse:** que el plan elegido pierda con la media cero tanto como gana con la contraída (dependería de la ventaja
  entera); en forward, que la canasta tenga media ≤ 0.

## Reproducción en el holdout
- **Datos:** sólo las operaciones ya publicadas de `FUNDEDSYNC_HOLDOUT_OPS.csv` (2026-10-01 → 2026-11-13).
- **Reglas:**
  - T es la misma regla;
  - R y Z van de fábrica, sin stop ni MAE: no son las reglas del plan, se reportan aparte;
  - la Z-banda no existe en el holdout (se usa Z de fábrica con el mismo tamaño).
- **Excursión adversa:** no está en esos archivos. Se dan dos casos: ganadoras con MAE 0 y ganadoras con MAE = su riesgo entero.
- **Calendario:** el plan elegido sin cambios, compra de evaluaciones desde el 2026-10-01 (una por día hasta el máximo del plan); bitácora
  por cuenta.
- **Lo que no es:** esos resultados se vieron el 2026-11-16 (T +14,2 pts en 26 operaciones; Z 7/7; R 5), así que no es un test ciego. No
  se usa para elegir ni para ajustar el plan.
