# Detector de estados (consolidación / expansión) + coeficiente de desplazamiento — segunda lectura del CerebroSSRN — 2026-10-06

Pedido de Nico, foco único. Soporte/resistencia queda **fuera** por decisión de Nico.
Corpus `E:\$ACerebroSSRN` (401 papers), búsqueda por palabras clave sobre 24.340 pasajes y 771 hallazgos.
Todo es `LITERATURE_CLAIM_UNVERIFIED`.

## Qué sabemos ahora y no sabíamos en la primera lectura
1. Después de una zona aVolClusterPOI, la ventana recorre 5–8 % más **con barras de tamaño normal**. Es
   desplazamiento, no agitación (VOL-2 B).
2. Ese desplazamiento **no tiene sesgo de lado** a 10/50 barras (SR-DIR D1): es "se mueve", no "hacia dónde".
3. Después viene **compresión** (VOL-1/2: `y_rv` < 0 a H50/H200).
4. La forma ráfaga→decaimiento coincide con los procesos de Hawkes, pero la zona agrega información **más allá** del
   volumen y la intensidad (A2).

Conclusión de diseño: la herramienta tiene que separar **dos ejes que hoy se confunden**:
- **Amplitud**: cuánto se mueve el precio por unidad de tiempo o de barra.
- **Eficiencia**: cuánto de ese movimiento es neto, recorrido recto, y cuánto es ida y vuelta.

"Expansión" con eficiencia alta es desplazamiento (tendencia corta). "Expansión" con eficiencia baja es agitación.

## Qué aporta el corpus
| tema | papers | lo útil |
|---|---|---|
| Ratio de varianzas (Lo–MacKinlay) | [6] revisión de métodos, [111] *Efficient or Not? Price Measures*, [280] | Medida estándar de "random walk vs persistencia" a varias escalas: VR(q) > 1 es persistencia, < 1 es reversión. Es la base formal del coeficiente de desplazamiento. |
| Hurst / memoria larga | [18] y [19] (guías de Quantitative Portfolio / Volatility Trading, con capítulos de Hurst y R/S), [289] | La memoria larga **casi no se ve en retornos con signo y sí en |retornos|** ([19]). Para estados conviene medir persistencia sobre amplitud, no sobre dirección, y coincide con nuestro hallazgo 2. |
| Estimadores de volatilidad por rango | [18] Parkinson, Garman–Klass, Rogers–Satchell, Yang–Zhang; [60]; [372] | Amplitud con OHLC de barra, más eficiente que con cierres. Con barras de ticks el tiempo es variable: normalizar por duración. |
| Régimen por desviación del VWAP | [372] *VWAP-Based Regime Classification* | Desvío del VWAP normalizado por volatilidad → régimen tendencia (±1) o reversión. Candidato simple y causal. Paper flojo, sin OOS. |
| HMM / Markov switching | [66] HMM asimétrico de OFI (régimen de "acumulación agresiva" de unos 4,3 min), [48] HMM de 3 estados, [21], [322] | Estados latentes con duración. Aviso: los HMM sobre retornos dan regímenes de unos 2,5 min, muy ruidosos ([66]). Más robusto sobre features de amplitud y eficiencia que sobre retornos. |
| Tendencia vs rango (ADX) | [238] *ADX-conditioned VWAP*, [22] (ADX para suspender entradas en oro) | ADX como "fuerza direccional": heurística, sin validación seria en el corpus. Sirve sólo como baseline. |
| Contracción → ruptura | [289] (Bollinger squeeze / contracción de volatilidad) | La consolidación precede movimientos grandes **en cualquier dirección**. Coincide con nuestro patrón, pero en el corpus es sólo afirmación de manual. |
| Pulsos y dislocación | [233] *Microstructural Pulse Dislocation* | Los eventos informativos producen pulsos direccionales con expansión de rango y colapso de profundidad, y lo propone tratar como **régimen propio**. A 1 s, en FX; anecdótico (6 eventos). |
| Corridas estratégicas HFT | [166] | Muchos mensajes con bajo contenido informativo: la actividad alta no implica desplazamiento. Apoya separar amplitud de eficiencia. |
| Cambio estructural / CUSUM | [6], [57], [54] | Detectar **el momento** del cambio de estado (evento) además del estado (continuo). |

Lo que **no** está en el corpus: el *efficiency ratio* de Kaufman (sólo una mención irrelevante) y el "cambio
direccional / tiempo intrínseco" (Glattfelder/Olsen, ausente). Son de la literatura práctica, y se usan igual porque
son simples y causales.

## Diseño propuesto (target-free; nada se elige mirando retornos futuros)
Calculado en cada barra t, causal, sobre ventanas N ∈ {10, 50, 200} barras (las mismas escalas que AVCL):
1. **Amplitud A_N**: rango de la ventana en ticks / mediana móvil del mismo rango a la misma hora, en 20 sesiones. Hay
   una variante por duración, ticks por minuto, porque las barras de 50t tienen tiempo variable.
2. **Coeficiente de desplazamiento E_N** (eficiencia) = |close_t − close_{t−N}| / Σ|Δclose| ∈ [0, 1].
   Variante robusta: rango de la ventana / Σ rangos de barra. Esta variante es la que reveló el hallazgo de VOL-2.
3. **Ratio de varianzas VR_N(q)** como versión con nulo conocido de E_N: bajo random walk se sabe su distribución, lo
   que da un umbral **sin calibrar con resultados**.
4. **Estado**, una grilla 2×2 sobre percentiles móviles causales:
   - consolidación = A baja y E baja;
   - agitación = A alta y E baja;
   - desplazamiento = A alta y E alta;
   - deriva lenta = A baja y E alta.

   Umbrales en terciles móviles, fijados de antemano. Opcional: HMM de 3 estados sobre (A, E) para comparar.
5. **Eventos de cambio de estado** (CUSUM sobre A y E) además del estado continuo, para cumplir la regla "separar
   evento de estado".

## Primera validación (target-free, antes de usarlo como contexto)
- Estabilidad: duración media de cada estado, matriz de transición, sensibilidad a N y a los umbrales.
- Paridad Python ↔ NT8 si va al chart, y capa en el visor.
- Recién después, como **contexto pre-registrado** de AVCL: ¿la expansión post-zona cambia según el estado previo? Por
  ejemplo, una zona creada en consolidación contra una creada en agitación.

## Cómo podría refutarse
- Estados inestables (duración de 1–2 barras) o que dependen fuerte de N y de los umbrales.
- Que E_N no se distinga de su nulo de random walk en ninguna escala: en ese caso no hay "desplazamiento" medible
  en estas barras.

## Siguiente paso concreto
Implementar `edgelab/regimes/state.py` (A, E, VR, estado 2×2, CUSUM) sobre el cache de barras de AVCL (MNQ, 6
contratos). Reportar la estabilidad y el mapa de estados: target-free, y en minutos con el cache.
