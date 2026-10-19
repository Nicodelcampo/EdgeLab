# VTD-DIR — qué predice el LADO del tramo largo después de una marca VolTicksDef — propuesta iterada — 2026-10-06

**Estado: PROPUESTA, pendiente de OK de Nico. No se corrió nada.**
Contexto: la asimetría de la excursión es universal (`EXPLO_ASIMETRIA_EXCURSION_20261006.md`). VTD anticipa
**movimientos más grandes** (único sello que sobrevivió a AVCL-PRE). Lo que falta para un RR capturable es **el lado**.

## 1. Lo que dice el corpus SSRN (segunda consulta, por palabras clave; autoridad: literatura no verificada)
| línea | papers | qué aporta | peso |
|---|---|---|---|
| Momentum de series de tiempo en futuros | [18] (Moskowitz et al. citado: continuación a varias frecuencias, Sharpe > 1,2) | La dirección reciente tiende a continuar. Horizontes de días a meses; intradía es menos claro. | medio |
| Momentum intradía en oro | [22] *Regime-Filtered Intraday Gold (VWAP + EMA)* | "El oro tiende a seguir en la dirección establecida". Usa EMA + VWAP + filtro de régimen. Relevante para MGC. | bajo (sin OOS serio) |
| VWAP como sesgo de dirección | [374] *VWAP Trend Trading* (Zarattini: lado del VWAP en QQQ, ORB), [372] régimen por desvío del VWAP | El lado del VWAP de sesión como filtro de tendencia intradía. | bajo–medio |
| Extremos de la sesión previa + ADX + VWAP | [238] | En extremos de sesión con desvío grande del VWAP, **reversión** (agotamiento). Es lo contrario de tu "pero no tanto". | bajo |
| **Desbalance de órdenes → dirección y ASIMETRÍA** | [195] (el desbalance de market orders predice retornos intradía), **[246] (el desbalance de MO es el factor nº 1 de la *skewness* de retornos)**, [206] (rob. alta) | Es lo más cercano a tu hipótesis: el desbalance comprador/vendedor no sólo predice el signo, **predice la asimetría**. Tenemos el agresor por tick. | **medio–alto** |
| Régimen tendencia/rango | [289] (la tendencia gana en mercados con tendencia y pierde en reversión), [92] (el momentum sufre en giros bruscos), [122] (HMM de 2 estados reduce el DD 30 %, rob. alta), [304] (persistencia de regímenes) | **El mismo predictor cambia de signo según el régimen.** Por eso tu filtro rango/expansión es clave. | medio |
| Advertencia | [210] (rob. alta) | Una regla de medias móviles con Sharpe 1,9 in-sample **fracasó** fuera de muestra (−0,13) y una de reversión se dio vuelta. Las reglas MA son frágiles al régimen y a la selección. | alto |
| Antecedente propio | `mgc_ema_20261002` | Señal de dirección con EMA 200/500/2000 en MGC (p 0,02–0,04 en una celda) que **no sobrevivió** a elegir la mejor de 21 (p_max 0,10). | alto |

Conclusión del corpus: hay **otras maneras de filtrar la dirección**, además de la EMA, con igual o más respaldo: el
**desbalance de órdenes** (la más alineada con la asimetría), el **VWAP de sesión**, el **momentum reciente** y la
**posición respecto de los extremos de la sesión**. Y todas dependen del **régimen**.

## 2. Iteración sobre la propuesta anterior (correcciones)
1. **No medir dirección contra el rango previo** (la lección de AVCL-PRE). Resultado sin escala y sin ventana pasada:
   `asim_H = (U − D) / (U + D)` ∈ [−1, 1], con U y D = excursiones desde el close de la marca en [b+1, b+H]. El
   predictor acierta si `signo(pred) × asim_H > 0`. También `P(cociente ≥ 3 a favor del predictor)`, que es el "RR 3".
2. **Dos preguntas separadas:**
   - (a) **¿el predictor acierta el lado en las marcas VTD?** Es lo operable.
   - (b) **¿acierta MÁS en las marcas que en barras al azar?** Mide si VTD aporta al lado o sólo al tamaño.

   Aunque (b) sea ≈ 0, si (a) > 0 hay valor: VTD aporta el tamaño del tramo y el predictor, el lado.
3. **EMA sobre barras de tick = horizonte variable en tiempo.** Se fija de antemano una EMA por **cantidad de barras**
   de 150t y otra **por tiempo** (minutos), y se reportan las dos.
4. **"Pero no tanto"** se fija antes de mirar: distancia al EMA menor a 1 ATR(14) de la serie. "Lejos" (> 2 ATR) se
   prueba aparte, como hipótesis de **agotamiento** ([238]), con el signo opuesto. No se barre el umbral.
5. **El régimen no puede ser un filtro sin validar.** Etapa 0 (target-free) construye el detector de estados (diseño
   corregido en `AVCL_ITERACION2_...` §1: amplitud y eficiencia contra nulo de random walk). Recién validado, entra como
   **moderador pre-registrado**.
6. **Multiplicidad chica y fijada:** pocos predictores, cada uno con razón económica; nada de grillas de parámetros.

## 3. Diseño propuesto
**Etapa 0 — detector de régimen (target-free, sin mirar resultados direccionales).**
- E_N (eficiencia = |Δ neto| / Σ|Δ|, con corrección de rebote) y A_N (amplitud por tiempo), con N = 50 y 200 barras de
  150t, contra un nulo de random walk con incrementos permutados dentro de la sesión.
- 3 estados: **rango** (E bajo), **tendencia/expansión** (E alto y A alta) y **neutro**, con umbrales en percentiles
  del NULO, no de la serie.
- Validación: duración de estados contra nulo, transiciones y estabilidad entre contratos.

**Etapa 1 — predictores del lado en las marcas VTD 150t (MNQ, 6 contratos; MGC como réplica descriptiva).**
Todos se calculan **al cierre de la barra marcada**:
| # | predictor | signo | razón |
|---|---|---|---|
| P1 | **EMA (Nico)**: lado del close respecto de la EMA 200 barras, sólo si \|dist\| < 1 ATR | a favor | pullback dentro de la tendencia |
| P2 | **VWAP de sesión**: lado del close respecto del VWAP | a favor | [374], [372], [22] |
| P3 | **Desbalance de órdenes**: (compra − venta agresora) / volumen en las 20 barras previas | a favor | [195], [246]: predice signo **y skew** |
| P4 | **Vela marcada**: signo de close − open y posición del close en el rango de la barra | a favor | lado que dejaron los lotes grandes |
| P5 | **Momentum reciente**: signo del retorno de las 50 barras previas | a favor | [18] |
| P6 | **Extremos de sesión**: cerca (< 0,5 ATR) del máximo/mínimo de la sesión | **en contra** | [238] (agotamiento) |

**Pruebas formales:**
- P1–P6 × H ∈ {10, 50} sobre la media de `signo × asim_H` en RTH: **12 pruebas, Holm**. Estimador con FE
  (contrato × franja) y SE por sesión.
- Más (b): P1–P6 en marcas contra barras al azar, H = 10: **6 pruebas**.
- Total: **18, Holm**.

**Descriptivos y moderación por régimen:** cada predictor dentro de cada estado de la Etapa 0. Hipótesis
pre-registrada, a partir del corpus: P1/P2/P5 aciertan en **expansión** y fallan o se invierten en **rango**, y P6 al
revés. Si la Etapa 0 valida el detector, la interacción con el régimen pasa a formal **en una corrida siguiente**, con
datos o contratos que no se usaron aquí.

## Justificación económica
- VTD ya da un tramo más grande (unos 52 contra 24 ticks en MNQ 50t H10).
- Si un predictor acierta el lado aunque sea en un 55 %, con el stop del lado corto y una asimetría típica ≥ 3:1 el
  pago esperado puede superar el costo.
- Esto **no** es todavía una prueba de P&L: antes de cualquier backtest hay STOP y manifiesto aparte.

## Cómo podría refutarse
Si todos los predictores dan `signo × asim` ≈ 0 en las marcas (MDE publicado), el lado no es predecible con
información pública de precio/volumen en este horizonte, y VTD queda sólo como sello de volatilidad.

## Lo que necesito de Nico
- OK al diseño.
- Confirmar la EMA: ¿200 barras de 150t está bien, o preferís otro período? ¿Y por tiempo, por ejemplo 60 minutos?
- ¿El umbral "no tanto" = 1 ATR te representa?

## Enmienda 1 (2026-10-06, decisión de Nico: "que se prueben distintas", sin fijar período ni umbral de la EMA)
- **Grilla EMA (P1):**
  - período en barras de 150t ∈ {20, 50, 100, 200, 500};
  - período por tiempo ∈ {15, 30, 60, 120, 240} min;
  - condición de distancia ∈ {< 0,5 ATR, < 1 ATR, < 2 ATR, sin límite}, más "lejos > 2 ATR" con signo **contrario**
    (agotamiento);
  - H ∈ {10, 50}.
  - Total: 10 × 5 × 2 = **100 celdas**.
- **Control de selección:**
  1. **Descubrimiento:** contratos MNQ 09-25, 12-25 y 03-26. Cada celda contra el **máximo de las 100** bajo dirección
     sorteada por sesión (max-T, 2.000 sorteos).
  2. **Confirmación:** las celdas que pasen (p_maxT ≤ 0,05) se prueban **una sola vez** en 06-26, 09-26 y 12-26, sin
     cambios, con Holm sobre las que pasaron.
  3. **Meseta:** se publica el mapa completo. Una celda aislada sin vecinos positivos no se promueve aunque pase.
- P2–P6 conservan su definición fija, con el mismo esquema de descubrimiento y confirmación (Holm sobre 5 × 2).
- **El orden no cambia:** primero la Etapa 0 (detector de régimen, target-free).
