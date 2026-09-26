# Solicitud de Deep Research: datos L2 (libro de órdenes) al servicio de un edge neto, robusto y operable

**Para:** un agente de investigación en modo *deep research*.
**De:** EdgeLab. El resultado lo va a usar otro agente de código para **implementar**: construir mecanismos, entrenar modelos y validarlos.
**Fecha:** 2026-09-23. North Star sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.
**Idioma de la respuesta:** español, con los títulos de papers y los nombres técnicos en su idioma original.

---

## 0. Qué te pido en una frase

Hacé una investigación **exhaustiva y verificable** de todo lo que la literatura académica, la práctica profesional y las herramientas existentes dicen sobre usar datos de **Level 2 / libro de órdenes** en **futuros CME**, para **encontrar, validar y ejecutar edges netos de costos**. Entregala como un **manual de implementación**: qué medir, qué modelos entrenar, cómo entrenarlos, cómo validarlos sin engañarse y cómo ejecutarlos con latencia de trader minorista. No me alcanza un resumen de literatura: necesito recetas.

---

## 1. El objetivo rector (no negociable)

> EL OBJETIVO FINAL DEL PROYECTO ES ENCONTRAR EDGES VÁLIDOS Y APLICABLES EN EL MERCADO A TRAVÉS DE ALGORITMOS QUE, A TRAVÉS DE LA RENTABILIDAD, PERMITAN OBTENER GANANCIAS EN LAS CUENTAS DE TRADING DONDE SE APLICAN.

Jerarquía para priorizar todo lo que encuentres:
1. Expectativa económica **neta** (después de comisión, spread y slippage).
2. Validez fuera de muestra (holdout sellado, sin data snooping).
3. Robustez estadística (MCPT, PBO, DSR/SPA, walk-forward, sensibilidad).
4. Ejecutabilidad real (feed en vivo, fills realistas, latencia, reglas completas de entrada/salida/sizing/kill switch).
5. Control de riesgo.
6. Paridad, determinismo, trazabilidad y visor, solo **como medios** para lo anterior.

Consecuencia práctica: una técnica que predice muy bien el próximo cambio del mid-price a 10 ms, pero que no se puede explotar con nuestra latencia y nuestros costos, **vale poco para nosotros**, aunque sea el estado del arte académico. Evaluá todo con ese filtro, y decilo explícitamente cuando algo no pasa el filtro.

---

## 2. Contexto real del proyecto (restricciones que tenés que respetar)

### 2.1 Datos L2 que tenemos
- **Fuente:** NinjaTrader 8 (8.1.8.2) Market Replay (`.nrd`), exportado con `MarketReplay.DumpMarketDepth` (la misma llamada que usa NRDToCSV) y convertido a parquet.
- **Tipo:** **MBP-10** (Market By Price, 10 niveles por lado). **No es MBO:** no hay ID de orden ni prioridad en cola. Cada evento es insertar, cambiar o borrar un nivel (lado, posición 0..9, precio, tamaño). Además hay L1 (bid, ask, last) intercalado.
- **Orden y tiempo:**
  - `source_row` es el orden de línea del archivo de NT8, **no** una secuencia del exchange.
  - El tiempo es reloj de pared de la PC de NT8 (medimos que es hora argentina, UTC-3, para GC, ES y 6E).
  - La fracción de segundo viene en ticks de 100 ns.
  - No hay timestamps del exchange ni de *matching engine*.
- **Peculiaridades medidas:**
  - Al abrir la sesión hay una ráfaga de ADDs que reconstruye el libro (bootstrap).
  - Aparecen DELETE del nivel 10 cuando el lado tiene menos niveles (1 de cada ~3,8 M eventos).
  - Algunos días vienen defectuosos del servidor: "Success" pero sin L2; un archivo que se superpone ~13 h con el día siguiente (11/08/2026, en dos instrumentos).
  - La reconstrucción del libro coincide con L1 en ≥99,7 %.
- **Agresor:** NT8 **no** expone el lado agresor. Lo inferimos con regla de cotización más tick-test (heurística no validada). Sale ~50/50, con <0,03 % neutral.
- **Ventana:** NT8 solo sirve los **últimos ~90 días** (lo medimos). Lo que no se baja a tiempo se pierde.
- **Volumen disponible:**
  - **Antes del holdout** (se puede usar para descubrir):
    - GC: ~30 días de calendario (mayo–junio de 2026) en dos contratos a la vez (06-26 y 08-26, período de roll).
    - 6E: unos pocos días de fines de junio.
    - ES: 11 sesiones, todavía en cuarentena administrativa.
  - **Del holdout** (solo visor e integridad): julio–septiembre en GC y 6E, en crecimiento.
  - Desde enero de 2027 se acumula L2 nuevo cada mes.
  - Escala: una sesión de GC tiene ~4–7 M eventos L2; en parquet pesa ~20–30 MB por sesión.
- **Otros datos:** ticks de operaciones (sin libro) de 11 instrumentos, de agosto de 2025 a junio de 2026 (GC, ES, NQ, YM, MES, MNQ, 6E, 6B, 6J, ZB, MBT), ~1.000 M de ticks. Tienen precio, bid, ask, volumen y agresor.

### 2.2 Qué ya existe y qué ya se probó (no lo repitas como novedad; sí criticalo)
- **Visor tipo Bookmap:** mapa de calor del libro a 1 s y burbujas de trades por agresor en celdas de 1 s. Velas de 5 s, 15 s, 30 s y 1 min salidas del mismo feed.
- **Detectores heurísticos no validados:**
  - **Iceberg:** nivel consumido y repuesto ≥3 veces.
  - **Spoofing:** orden grande (p95) que vive <5 s y se ejecuta <20 %.
  - **Absorción:** flujo agresivo p99 en 10 s que no atraviesa el precio.
- **Indicadores propios sobre ticks:**
  - **BigTrap2:** zonas de traders atrapados por desequilibrios apilados en el footprint. **Refutado** como soporte/resistencia (~96 % de ruptura) y **refutado como imán**. Lo único que sobrevivió: "una vela extrema marca una carrera asimétrica", que no es exclusivo del indicador.
  - **BigTrap2Absorption:** flujo sobre desplazamiento. En la familia HP-008 (absorción + reversión a EMA) quedó **falsado** incondicionalmente. Sobrevivió un subconjunto post hoc (días rotacionales), sospechoso de *forking paths*.
  - **HFTZones:** sobre ES, cinco mediciones, ninguna positiva, **sin potencia** en 2 de 3 terciles (el límite es N).
  - **HP-007, "corredores de vacío":** efecto microestructural certificado **como fenómeno, no como edge**.
  - **aVolClusterPOI:** familia viva sin nulo propio.
- **Infraestructura estadística:**
  - MCPT, PBO, DSR (dos métodos versionados), SPA.
  - `PrimaryCI`: bootstrap estacionario agrupado por sesión, con criterio `lower > 0`.
  - Gates G0–G5 de "edge válido y aplicable".
  - Registro inmutable de hipótesis, contraejemplos y lecciones (Edge Brain) con techo de promoción: nada se autopromueve.

### 2.3 Cómputo y ejecución
- **Cómputo:**
  - PC Windows con CPU, **sin CUDA local**.
  - Servidor Debian con Celeron N4020 (2 núcleos, 7,6 GB de RAM), siempre encendido.
  - Kaggle para kernels. Verificá qué GPU y qué cuota gratuita ofrece hoy y si alcanza para entrenar.
  - Stack: Python 3.12, duckdb, polars, pyarrow, numpy y pandas. Sin dependencias pesadas nuevas salvo que la justifiques contra lo que aporta.
- **Ejecución:**
  - NT8 con un broker de futuros minorista, o una **prop firm**. Latencia de trader minorista: estimá el orden de magnitud realista de ida y vuelta.
  - Las órdenes son de mercado o límite. No hay colocación, co-location, *feed* directo del exchange ni prioridad de cola conocida.
- **Costos:** comisión más spread más slippage, **por instrumento**. Hoy son supuestos, no medidos. Una de las cosas que el L2 debería darnos es justamente **medirlos**.

### 2.4 Reglas metodológicas que tu propuesta tiene que respetar
- **Holdout sellado del 2026-07-01 al 2026-12-31.** No se usa para diseñar, elegir parámetros, horizontes, costos ni candidatos. Se abre una sola vez por candidato, según protocolo. Tus recetas de *train/validation/test* tienen que funcionar **sin** tocarlo.
- **Pre-registro obligatorio** antes de cualquier búsqueda sobre retornos: hipótesis, justificación económica, **cómo podría refutarse**, espacio de búsqueda, N efectivo de hipótesis y MDE.
- **Poblaciones:** antes de congelar una población hay que enumerar el espacio completo de eventos y estados: creación, aproximación, primer toque, toque n-ésimo, invalidación, expiración, confluencia y estado continuo. **Separar evento de estado:** un estado vale en cada barra y suele tener más potencia.
- **Orden de la cadena:** geometría/lifecycle (target-free) → información condicional → P&L bruto → edge neto/replicado. No saltar pasos.
- **Todo nulo publica su MDE**, y todo efecto se mide en **dos canales**: el direccional, el no direccional (volatilidad, magnitud) y la distribución completa.
- **No transportar** costos, resultados ni presupuesto de multiplicidad entre instrumentos ni entre familias.
- Si un render elimina zonas mitigadas, lo que se ve en pantalla no es evidencia (sesgo de supervivencia). Hace falta un censo *as-of*.

---

## 3. Preguntas de investigación (cubrilas todas; agregá las que falten)

### A. Fundamentos del dato
1. **MBP-10 contra MBO:** ¿qué se pierde exactamente sin ID de orden? ¿Qué inferencias de la literatura requieren MBO (posición en cola, cancelaciones de órdenes individuales, icebergs "reales") y cuáles se pueden aproximar con MBP? ¿Con qué error?
2. **CME MDP 3.0:**
   - Semántica real de los mensajes: *incremental refresh*, *implied* (¿GC o 6E tienen liquidez implícita de spreads?), tag de lado agresor, *match event indicator*, secuencias.
   - ¿Qué parte de eso sobrevive en el replay de NT8? ¿Cómo lo verificamos?
3. **Reconstrucción y validación del libro:** mejores prácticas, invariantes a chequear, tratamiento del bootstrap, libros cruzados, huecos y días defectuosos del proveedor.
4. **Alineación trades–libro y clasificación de agresor:**
   - Lee-Ready, EMO, CLNV, *bulk volume classification* y otros.
   - Precisión reportada en futuros.
   - ¿Qué error induce la clasificación heurística en features de flujo (OFI, delta)?
5. **Fuentes alternativas de L2/MBO con historia larga:** Databento (MBO de CME), CME DataMine, Rithmic, dxFeed, AlgoSeek, LOBSTER (acciones), Tardis (cripto), entre otras. Para cada una: costo, licencia (¿se puede publicar o derivar?), profundidad, precisión de timestamps y formato. **¿Cuál es la forma más barata de tener 1–3 años de MBO de GC/ES/NQ/6E?**
6. **El problema de los 90 días:** estrategias de acumulación, y si conviene migrar a otra fuente para research, dejando NT8 solo para ejecución.

### B. Microestructura: qué fenómenos hay en el libro y cuáles tienen evidencia de valor económico
Para cada uno: definición operativa, fórmula, evidencia empírica (en qué mercado, período y horizonte), evidencia de **decaimiento o crowding**, y **si sobrevive a costos y a latencia minorista**.
1. **Order Flow Imbalance** (Cont, Kukanov, Stoikov) y sus variantes multinivel e integradas.
2. **Queue imbalance y microprice** (Stoikov; Gould & Bonart), incluida la dependencia de *large-tick* contra *small-tick*.
3. **Impacto de precio:**
   - Kyle's lambda.
   - Ley de la raíz cuadrada.
   - Modelos de propagador (Bouchaud et al.).
   - Resiliencia del libro.
4. **Procesos de Hawkes y modelos *queue-reactive*** (Huang, Lehalle, Rosenbaum). Para qué sirven en simulación y en predicción.
5. **Selección adversa y toxicidad del flujo:** VPIN y sus **críticas**, *realized spread*, *markouts*.
6. **Cancelaciones, spoofing y layering:** literatura académica, casos CFTC/DOJ y métodos de detección. ¿Hay valor predictivo en detectarlos, o solo valor forense?
7. **Icebergs:** detección con MBP contra MBO, y valor informativo documentado.
8. **Absorción y agotamiento, "muros" de liquidez, vacíos o huecos de liquidez:** ¿qué dice la literatura académica? ¿Qué dicen los practicantes (footprint, Bookmap, order-flow trading)? **Separá claramente evidencia de folklore.**
9. **Estacionalidad intradía, eventos macro (datos, FOMC), rolls y aperturas/cierres:** cómo cambian las propiedades del libro.
10. **Relaciones entre activos:** lead-lag ES/NQ/YM, GC contra el dólar (6E) y spreads entre contratos. ¿Qué parte es explotable a latencia minorista?

### C. Modelos: qué entrenar y cómo (núcleo del pedido)
Necesito un **catálogo de modelos ordenado por aplicabilidad a nuestras restricciones**, desde el baseline más simple hasta el estado del arte. Como mínimo:
- Lineales y logísticos sobre features manuales (OFI, imbalance, microprice).
- *Gradient boosting* (LightGBM/XGBoost) sobre features manuales.
- Modelos de estado y de Hawkes.
- CNN/LSTM sobre el libro crudo: **DeepLOB** y variantes.
- Transformers para LOB: TransLOB, TLOB, HLOB y lo más reciente de 2024–2026.
- Modelos de espacio de estados (Mamba y similares), si hay evidencia.
- Preentrenamiento auto-supervisado o contrastivo sobre LOB.
- "Universalidad" y transferencia entre activos (Sirignano & Cont).
- Simuladores generativos del libro (ABIDES, GAN o difusión de LOB, benchmarks tipo LOB-Bench), para aumentar datos o para hacer backtests de ejecución.

Para **cada modelo**, en una tabla más una ficha:
1. **Representación de entrada:** niveles, normalización, ventana, reloj por eventos o por tiempo.
2. **Etiqueta:**
   - Cambio de mid a horizonte h, *triple barrier* o etiqueta de costo ("¿el movimiento supera spread+comisión?").
   - Clasificación o regresión.
   - **Trampas conocidas de etiquetado:** el suavizado de FI-2010 filtra información futura, y así otras.
3. **Horizonte de predicción** y por qué. **Cuantificá hasta qué horizonte la señal del libro sigue teniendo información** (curvas de decaimiento del poder predictivo), porque nuestra latencia nos saca de los horizontes más cortos.
4. **Datos necesarios** (cuántos eventos o sesiones para no sobreajustar) y cómputo (CPU contra GPU, tiempo estimado). ¿Es viable con ~30 días pre-holdout de GC? ¿Qué hacemos si no alcanza?
5. **Receta de entrenamiento paso a paso:**
   - Particionado temporal por sesiones con *purging* y *embargo*.
   - Normalización sin fuga (estadísticos solo del pasado).
   - Balanceo de clases, early stopping sobre sesiones de validación, semillas y varianza entre semillas.
   - Búsqueda de hiperparámetros **contabilizada** en la corrección por multiplicidad.
   - Calibración de probabilidades.
   - Ablaciones obligatorias: sin el libro (solo trades), placebo con libro barajado, libro con retraso igual a nuestra latencia.
6. **Evaluación económica, no F1:**
   - Cómo se traduce una predicción en una regla de trading completa (entrada, salida, sizing, kill switch).
   - Cómo se simulan fills realistas con MBP (ver D).
   - Qué métricas netas reportar.
7. **Evidencia de generalización:** resultados fuera de muestra y entre activos. **Qué dicen los benchmarks críticos** (p. ej. LOBCAST, Prata et al. 2023/2024) sobre cuánto de lo publicado se sostiene.
8. **Modos de falla conocidos** y cómo detectarlos.
9. **Veredicto de aplicabilidad a EdgeLab:** alta, media o baja, y por qué.

Cerrá esta sección con **un plan concreto**: los 3 a 5 modelos que entrenarías primero, en qué orden, con qué datos y qué resultado mataría cada uno.

### D. Ejecución y costos (convertir señal en P&L real)
1. **Simulación de fills sin MBO:**
   - Modelos de posición en cola para órdenes límite a partir de MBP (supuestos pesimistas contra optimistas).
   - Probabilidad de fill.
   - Selección adversa de los fills pasivos.
2. **Latencia:** cómo modelarla y cómo medir la nuestra. Cuánto *alpha* se pierde por milisegundo o segundo según la literatura.
3. **Medir costos reales con nuestro propio L2:** spread efectivo, profundidad, impacto por tamaño y slippage esperado para 1 a N contratos, por instrumento y por hora. Dame la receta.
4. **Órdenes de mercado contra límite** a distintos horizontes. ¿Dónde está el punto de equilibrio?
5. **Prop firms:** reglas típicas (drawdown trailing, límite diario, consistencia) y cómo afectan el sizing de una estrategia de microestructura. Solo mecánica; no pido asesoramiento financiero.
6. **Herramientas de backtest con libro:** `hftbacktest`, NautilusTrader y otras. Qué modela cada una: colas, latencias, MBP o MBO. Cuál encaja con Python 3.12, CPU y nuestro formato.

### E. Validación estadística específica de alta frecuencia
1. **Dependencia serial y agrupamiento por sesión:** bootstrap por bloques, estacionario o por sesión. Cómo calcular potencia y **MDE** con autocorrelación.
2. **Multiplicidad cuando hay cientos de features y modelos:** White's Reality Check, Hansen SPA, Romano-Wolf, Harvey-Liu-Zhu (umbral t > 3), DSR y PBO (Bailey, López de Prado). Cómo **contar** hiperparámetros y arquitecturas como pruebas.
3. **Diseños de validación con pocos datos:** walk-forward por sesiones, *combinatorial purged CV*, réplica entre instrumentos como sustituto de más historia.
4. **Nulos adecuados para microestructura:** permutaciones que preserven la estructura (barajar dentro de la sesión, desplazamientos circulares, *surrogates* con la misma autocorrelación). Qué nulo usar para cada pregunta.
5. **Diagnóstico de fuga de información** (*look-ahead*) en features de libro, sobre todo con timestamps de reloj de pared y sin secuencia del exchange.

### F. Estado del arte y del mercado
1. ¿Qué dicen las revisiones recientes (2020–2026) sobre la rentabilidad **neta** de estrategias basadas en el libro para participantes **sin** ventaja de latencia?
2. ¿Qué parte del *alpha* de microestructura ya fue arbitrada? ¿Hay evidencia de decaimiento en futuros CME?
3. ¿Qué horizontes y qué tipo de señales quedan a nivel minorista? Por ejemplo, el libro como **filtro o contexto** de entradas a varios minutos, en lugar de predictor a milisegundos.
4. **Casos documentados** (académicos o de practicantes serios) de uso de L2 para mejorar ejecución o timing en estrategias de horizonte medio.

### G. Herramientas, datasets y código
- Datasets públicos para entrenar y comparar: FI-2010 (y sus problemas), LOBSTER, cripto (Binance/Tardis), muestras de Databento. Qué sirve para **preentrenar** y qué solo para comparar.
- Repositorios de referencia: DeepLOB, LOBCAST, TLOB, hftbacktest, reconstrucción de libros, simuladores. Estado de mantenimiento, licencia y calidad.
- Visualización tipo Bookmap y buenas prácticas de visualización de L2 que ayuden a **investigar**, no solo a mirar.

---

## 4. Formato de entrega (obligatorio)

1. **Resumen ejecutivo** (1 página): las 10 conclusiones que más cambian lo que EdgeLab debería hacer con L2, ordenadas por impacto en la jerarquía del §1.
2. **Una sección por bloque (A–G).** Para cada tema:
   - **Qué es** (definición operativa y fórmula).
   - **Evidencia:** papers con cita completa (autores, año, título, venue o arXiv, DOI o link), mercado, período, horizonte y tamaño del efecto.
   - **Fuerza de la evidencia:** revisado por pares / preprint / practicante / anecdótico.
   - **Aplicabilidad a nuestras restricciones** (MBP-10, sin agresor nativo, latencia minorista, CPU, pocas sesiones pre-holdout).
   - **Receta de implementación:** pasos, pseudocódigo o ecuaciones, parámetros iniciales y qué librería usar.
   - **Primer experimento target-free** (sin mirar retornos) y después el experimento económico, con su **hipótesis pre-registrable**, su **justificación económica** y **cómo podría refutarse**.
   - **Trampas conocidas.**
3. **Catálogo de modelos** (tabla del §3.C) más fichas de entrenamiento.
4. **Hoja de ruta priorizada:** fases con entregables, datos necesarios, costo de cómputo y **criterio de parada** de cada fase. Separá lo que se puede hacer **ya** con los datos pre-holdout de lo que requiere comprar datos o esperar a 2027.
5. **Lista de "no hacer"**, con la evidencia de por qué.
6. **Preguntas abiertas** que no pudiste resolver, y qué dato o experimento las resolvería.
7. **Bibliografía completa** al final, en formato consistente.

---

## 5. Reglas para vos (calidad de la investigación)

- **No inventes citas.** Si no pudiste verificar una fuente, marcala `[NO VERIFICADO]`. Preferí fuentes primarias (el paper) antes que resúmenes.
- **Distinguí evidencia de opinión.** El material de practicantes (blogs, cursos de order flow, marketing de plataformas) es admisible, pero va etiquetado como tal y nunca como prueba.
- **Buscá activamente la evidencia en contra** de cada técnica prometedora: réplicas fallidas, críticas y benchmarks que no reproducen. Un edge documentado sin réplica independiente vale poco.
- **Cuantificá siempre que puedas:** tamaños de efecto, horizontes, costos, cantidad de datos y tiempos de cómputo.
- **Todo número tiene contexto:** mercado, período, tick size y latencia supuesta.
- Si una pregunta mía está mal planteada o falta una pregunta más importante, **decilo y agregala**. Mis preguntas son un piso, no un techo: el criterio es el objetivo del §1.
- No des asesoramiento financiero personalizado. Esto es investigación metodológica.
