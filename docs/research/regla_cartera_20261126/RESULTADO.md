# REGLA-CARTERA: la regla fija de suma decorrelacionada supera a la cartera actual fuera de tiempo, con un cuarto de la caída (resultado, 2026-11-26)

Estado: RESULTADO — pre-registrado (`PREREGISTRO.md`), 1 lectura contada.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `RESULTADO.json`, `VALIDACION_*.csv.gz`, `TODA_*.csv.gz` y `CURVAS_REGLA_CARTERA.png`. Herramienta `tools/regla_cartera.py`.
- **Unidad:** USD con 1 micro (riesgo parejo = 1 / sd mensual, peso medio 1).

Episodios: caída máxima y peor mes de cada cartera, en las tablas.

## Validación fuera de tiempo (selección 2019-07 → 2023-06, evaluación 2023-07 → 2026-09, 39 meses)

| Universo | Cartera | USD/mes | Sharpe | % meses + | Caída máx. | Peor mes |
|---|---|---|---|---|---|---|
| **Intradía** | Regla (riesgo parejo) | +863 | **2,01** | **64 %** | **−3.702** | −2.081 |
| | Regla (1 micro cada una) | +1.017 | 1,81 | 69 % | −4.939 | −2.829 |
| | INTRADIA8 actual | +1.423 | 1,46 | 56 % | −13.964 | −4.242 |
| **Mixto** | Regla (riesgo parejo) | +1.075 | **2,31** | **69 %** | **−4.041** | −2.030 |
| | Regla (1 micro cada una) | +1.289 | 2,20 | 69 % | −5.206 | −2.545 |
| | INTRADIA8 + INTERDIA3 actual | +2.322 | 1,90 | 67 % | −15.311 | −5.061 |

**Elegidas con 2019-07 → 2023-06:**
- Intradía: T, ES5N NQ, Z, V, F, C y N.
- Mixto: las mismas más C2_VZ NQ.

**Lectura:**
- **Pasa el criterio pre-registrado:** fuera de tiempo, la cartera de la regla no tiene menos Sharpe ni menos % de meses positivos que la
  actual; tiene más.
- **La caída máxima es un cuarto** de la actual en Intradía y Mixto.
- **El USD/mes es menor** porque la regla pone menos estrategias y menos riesgo. A igual riesgo hay que escalar la regla ≈ 1,6–2× en micros,
  y aun así la caída queda ≈ −6.000 a −8.000 contra −14.000 a −15.000.
- **La diferencia de Sharpe** (≈ 0,4–0,55) está en el borde de lo que 39 meses distinguen del ruido. La caída y el % de meses son la
  señal más clara.

## Regla aplicada a toda la ventana (2019-07 → 2026-09, descriptiva: elegida sobre datos vistos)
- **Intradía:** T, Z, F, V, RQ5 NQ, N y C, cada una con 1 micro. Sharpe 2,16, caída −5.895, +1.141 USD/mes. INTRADIA8: 1,67, −13.964,
  +1.362.
- **Mixto:** T, Z ×2, C2_VZ NQ, F ×2, V, RQ5 NQ, SOM NQ, N, O y C. Sharpe 2,36, caída −8.432, +1.877 USD/mes. Actual: 1,87, −15.311,
  +1.935.
- **Dejan afuera:** R (correlación 0,50 con T), Franklin y ES5N (se pisan con RQ5) y RQ5 ES.
  - Las de la mañana quedan representadas por una sola, RQ5 NQ, en vez de tres.
  - Por eso la caída de 2026 pesa mucho menos.

## Límites
- **Holdout:** las series incluyen meses HOLDOUT de A5 ya vistos por otras campañas; la validación es fuera de tiempo, no un holdout
  sellado.
- **O:** no opera desde 2025-10 por su techo de margen; para usarla hay que operarla con tamaño fijo.
- **F, C y N:** en la lectura A5 no se confirman por sí solas (SIN_NOMINAR / NO_CONCLUYENTE). Entran por estabilidad y baja correlación,
  que es la tesis de la decisión, no por ventaja confirmada.
- **Confirmación:** la definitiva es el forward de la cartera de la regla.
