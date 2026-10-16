# Definición inicial — estudio CORREDOR × zonas HFT (ES, barras de 100 ticks)

Estado: BORRADOR — definición inicial para que Nico y Gemini la diseñen en detalle y la corran; no autoriza ninguna medición sobre retornos ni precios futuros
Fecha: 2026-10-16
Familia / módulo: EXP-CORREDOR-HFT (confluencia; debe registrarse como familia nueva con ledger propio antes de medir)
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)
Decisiones de Nico (2026-10-16): se usa el detector HFT `HFTZonesESPureV2` tal cual (paridad supuesta ≈ 99 %; respaldada por oráculo del archivo con hash `dc114e6d…`, medida en ES 03-26); el indicador de impulsos depende de las barras, así que **todo se mide en barras de 100 ticks** (100T); zonas absorb no se usan.

## 1. Pregunta
Si en el **50 % inicial de un impulso** del indicador del corredor hay **al menos una zona HFT activa** (creada antes o dentro de esa ventana, mientras siga vigente), ¿cambia la probabilidad de que el precio (a) **llegue** a esa zona y (b) la **atraviese en dirección contraria a la de la zona**? ¿Y qué tiene que haber hecho el precio (virginidad de la zona, tiempo desde su creación, volumen operado desde su creación, alejamiento en ticks) para que esa probabilidad supere al azar, si lo supera?

## 2. Definiciones (todas causales)
- **Barras:** 100T estrictas por sesión (`trade_date` constante; mismo constructor que Pasada 2). El corredor corre sobre esas barras.
- **Impulso:** zona del detector del corredor con `DET_NT8` (ATR = SMA(Rango)), preset **1** como primario y preset 2 como sensibilidad (declarar el presupuesto). Se toma el estado conocido en cada instante: el origen se reubica y la zona se confirma ≥ 65 barras después, por lo que **la extensión final del impulso no se conoce en tiempo real**.
- **50 % inicial (definición primaria, causal):** con `origin_bar` y `conf_bar` (barra de confirmación), la ventana inicial es `W = [origin_bar, origin_bar + floor(0.5·(conf_bar − origin_bar))]`. **El instante de decisión es `conf_bar`.** Alternativas declaradas (sensibilidad): (B) 50 % de la extensión final `origin..end_bar` (**retrospectiva, no operable**; sólo descriptiva); (C) primeras *k* barras fijas desde el origen.
- **Zona HFT activa:** la que registra el detector en el logger/oráculo con `available_at = end_ts` del barrido (el `start_ts` es retroactivo y **no** se usa). Es activa en la barra *b* si `available_at ≤ b` y `b ≤ creación + E`, con **E = 600 barras de 100T** (fija, primaria). Extensión **dinámica** (alternativas a barrer, declarar cada una): hasta la primera mitigación (precio cruza la zona completa) o hasta el *k*-ésimo toque; fijas adicionales 300 y 1200 barras.
- **Presencia (corregida por Nico, 2026-10-16):** el impulso "tiene HFT" si el precio **tocó al menos una vez un rectángulo HFT** dentro de W: en alguna barra de W cuyo rango [mínimo, máximo] intersecta el rectángulo **mientras éste estaba activo** (`available_at ≤ b ≤ creación + E`). **Vale igual si el precio termina W dentro de la zona**, y vale aunque el rectángulo haya dejado de dibujarse después. Mera coexistencia en el tiempo, sin toque, **no** cuenta (se reporta aparte como `hft_activa_sin_toque`). Alternativas declaradas: toque medido a nivel de tick en vez de barra de 100T; presencia más estricta (el precio está dentro de la zona al cierre de W).
- **La extensión E sólo decide cuándo un rectángulo cuenta para la presencia.** Para los **desenlaces** la zona sigue siendo un nivel de referencia hasta el horizonte *H* aunque ya no se dibuje (primario); sensibilidad: contar sólo mientras esté activa.
- **Zona de referencia:** la **más cercana al precio de decisión** entre las activas (primaria); alternativas: la más grande, la más antigua. La dirección propia de la zona HFT es la del barrido que la generó.
- **Desenlaces (primer paso desde `conf_bar`, horizontes *H* ∈ {150, 300, 600} barras 100T, a declarar):**
  - **E1 = llega:** el precio toca el borde cercano de la zona de referencia antes de *H* (la zona no necesita seguir dibujada; ver arriba). Si el precio ya está dentro de la zona al decidir (`inside_at_conf`), E1 se da por cumplida en el instante 0 y se analiza aparte.
  - **E2 = atraviesa en contra:** tras llegar, recorre todo el ancho de la zona en dirección **opuesta** a la de la zona antes de *H* y antes de volver a salir por el borde de entrada.
  - Censura por fin de sesión explícita (no se cuenta como "no ocurrió"); empates en el mismo tick = ambiguos.
- **Nulo ("azar"):** (1) impulsos **sin** zona HFT activa en W, emparejados por hora, volatilidad (ATR/precio), distancia y ancho; (2) **pseudo-zonas** del mismo ancho y distancia colocadas en niveles sin zona HFT, con el mismo desenlace. La distribución de primer paso de la caminata aleatoria sin deriva es sólo referencia, no benchmark.

## 3. Indicadores (variables) de la corrida
| Grupo | Variable | Definición |
|---|---|---|
| Presencia | `n_hft_tocadas_W`, `hft_tocada_W` | número de rectángulos HFT activos tocados por el precio en W; indicador binario (primario) |
| Presencia | `hft_activa_sin_toque`, `n_hft_activas_W` | coexistencia sin toque (control/estrato) y número de zonas activas en W |
| Toque | `inside_at_endW`, `n_touches_W`, `penetration_ticks`, `t_first_touch_rel` | si W termina dentro de la zona, cuántos toques, cuánto penetró y en qué fracción de W ocurrió el primero |
| Zona | `age_bars` | barras desde `available_at` hasta `conf_bar` |
| Zona | `vol_since_creation` | volumen operado (ticks de la serie de 1 tick) desde `available_at` hasta `conf_bar` |
| Zona | `virgin_pre_W` / `n_touches_pre_W` | si el precio había tocado la zona **antes** de W (desde su creación); número de toques previos |
| Zona | `width_ticks`, `dir_zone` | ancho y dirección propia de la zona HFT |
| Relación | `dist_ticks` | distancia del precio de decisión al borde cercano de la zona |
| Relación | `ahead` / `aligned` | si la zona está delante o detrás del precio respecto a la dirección contraria al impulso; si su dirección coincide con la del impulso |
| Impulso | `imp_dir`, `imp_len`, `slope`, `score` | del detector del corredor, al instante `conf_bar` |
| Contexto | `hora_ct`, `atr_ticks`, `rango_sesion` | hora de Chicago real (no UTC fija), volatilidad, rango de la sesión hasta `conf_bar` |
| Desenlace | `E1`, `E2`, `t_E1`, `t_E2`, `censurado` | primer paso, tiempos y censura |

## 4. Diseño de análisis (a detallar por Nico y Gemini)
1. **Censo sin retornos (primer paso):** impulsos por sesión, prevalencia de `hft_en_W` por extensión (600 fija; 300/1200; dinámicas), tamaño del grupo control y distribución de edad/distancia/volumen. Define el N efectivo y el MDE.
2. **Probabilidades:** P(E1) y P(E2 | E1) con y sin zona; diferencia pareada por sesión; IC clusterizado por sesión; MDE publicado. Espejo sólo como robustez.
3. **Qué hizo el precio:** superficie monótona P(E1 o E2 | edad, volumen, distancia, virginidad) (modelo logístico/ elastic net con restricciones; sin árboles profundos), con rejilla **chica y declarada** y corrección por multiplicidad (Holm); selección dentro de validación por sesiones; nulo del pipeline (desplazamiento circular) si se prueban varias herramientas.
4. **Dos canales:** direccional y no direccional (distribución completa de excursiones, no sólo el primer paso).
5. **Economía:** fuera de esta fase (probabilidades primero; fricción de ES 3,546 ticks después).

## 5. Reglas y advertencias
- **STOP:** antes de ejecutar, manifiesto con número efectivo de hipótesis y tu OK; esta definición es un borrador.
- **Familia nueva:** cruce corredor × HFT = confluencia → registrar, no heredar resultados ni presupuesto de ninguna de las dos.
- **Datos/particiones:** ES descubrimiento 2025-07-18 → 2026-03-31 para diseño; abril–septiembre **ya expuesto** para el corredor (HOLDOUT-A3 reglas 1 y 4); holdout ≥ 2026-10-01 sellado. El oráculo HFT de ES 03-26 cubre 22-dic-2025 a 19-mar-2026 (62 sesiones); para otras fechas la fuente es el port de Python con los parámetros por defecto del `.cs`.
- **Paridad:** supuesta ≈ 99 % (9.481/9.486 en ES 03-26; no medida en 06-26 ni 09-26). Si el censo usa esos contratos, comparar el oráculo existente contra el Python; no hace falta exportar de NT8.
- **Causalidad:** `available_at`, no `start_ts`; el corredor sólo con lo conocido en `conf_bar`; sin cajas finales; probar prefijos vs streaming.
- **Pendientes de decisión (Nico/Gemini):** operacionalización del 50 % (A/B/C), medición del toque (barra 100T vs tick; wick vs cierre), zona de referencia (más cercana/más grande/más antigua), horizontes *H*, extensión dinámica concreta, rejilla de parámetros y su presupuesto.

*Aporte al referente:* deja definido, con tiempos causales y un nulo explícito, el estudio que mide si las zonas HFT presentes en el arranque de un impulso cambian la probabilidad de que el precio llegue o atraviese la zona, antes de gastar presupuesto de hipótesis.
