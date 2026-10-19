# Evaluación del auditor: `V3VolumeHeatmapExt` / `V2GapsHeatmap` — 2026-08-14

**Contexto**: Nico recibió de otra IA un análisis entusiasta de estos dos indicadores (HVN como "anclas/imanes", LVN como "autopistas", "ecuación física del mercado") y preguntó si conviene y si es cierto. Leí ambos `.cs`. Este documento es el veredicto; referenciado desde `HANDOFF_AUDITORIA_2026-08-14.md` §6.

## 1. Lo que el código ES (leído, no el marketing)

- **`V3VolumeHeatmapExt.cs`** (570 líneas): heatmap 2D volumen-a-precio por barra (subserie tick:1, bins por precio) con "extensión inteligente": si una celda cruza `HighVolThresholdPct`, el nivel **se congela `ExtensionBarsHigh` barras** para leerse como banda persistente de S/R. Es un **renderer sobre la ventana VISIBLE** (el propio comentario: "empezamos el cálculo desde atrás" para retener volumen previo a la ventana en pantalla), SharpDX, buffers de render. **Sin log de eventos, sin ciclo de vida de zonas, sin export.**
- **`V2GapsHeatmap.cs`** (1.040 líneas): densidad de gaps solapados (anclados barra+precio, extendidos `ExtensionBars`) + detector de "patinaje" (ZigZag de umbral adaptativo + percentiles rodantes de velocidad/rango/fricción). Procesa solo en cierre de barra (línea 224: "sin repintado"). **24 parámetros.** Tampoco tiene log de eventos.

## 2. ¿Es cierto? — Los claims son hipótesis, y uno es parcialmente un artefacto

- **"HVN = imanes/anclas", "LVN = autopistas", "ecuación física"**: hipótesis de microestructura, no hechos. En ESTE proyecto la familia "imán" ya acumula evidencia previa **negativa**: aVol en ES = ABSTAIN / sin imán; 6E baseline con signo invertido; F2.7/F2.8 = no-magnet; PreRange 72,38 % = tautología (p=0,103). La barra de evidencia para esos claims es alta y hoy nadie la pasó. La "ecuación" es una metáfora sin estimand hasta que se pre-registre.
- **El punto más fino**: la *persistencia* que se ve en el heatmap de volumen es **parcialmente manufacturada por la regla de congelado** — una celda que cruzó el umbral queda pintada caliente `ExtensionBarsHigh` barras haga lo que haga el mercado. Si se mide "half-life" o "defensa del nivel" sobre la serie congelada, la medición queda contaminada por la regla de display: hay que medir las marcas crudas, no la extensión retenida.
- Las 3 propuestas de medición recibidas (first-touch rejection rate, half-life decay, breakout acceptance) **tienen la forma correcta** y mapean a maquinaria que el proyecto ya tiene (estimand de primer pasaje F2.7, ciclo de vida de zonas, atlas nulo). Pero pasan por los mismos gates de siempre: pre-registro, nulo browniano (que históricamente mata 54–76 % de este tipo de claims acá), MDE publicado.

## 3. ¿Conviene incorporarlos? — Overlap con familias existentes (F9 sigue pausada)

- `V2GapsHeatmap` ≈ **Gaps2** (ya existe, con paridad hecha) + el detector de patinaje.
- `V3VolumeHeatmapExt` ≈ **aVolClusterPOI / aVolCellPOI2 / VolTicksPOC2** (masa de volumen a precio; paridad de las dos últimas pendiente) + el render de persistencia congelada.
- La pregunta disciplinada antes de incorporar nada: **¿qué agregan sobre esas familias más allá de la visualización?** Si la respuesta es "el detector de patinaje" o "las bandas congeladas", eso se testea como VARIANTE de un kernel existente, no como familia nueva. F9 (indicadores nuevos) sigue pausada hasta cerrar la paridad de los cuatro pendientes.

## 4. Riesgos concretos para paridad (qué habría que modificar — Nico ya lo anticipó)

1. **No hay log de eventos** → agregar export sellado (`LogEventAt` con `s.Time` inmutable, meta line, un archivo por resolución por corrida, sin append). Sin eso no hay oráculo y no hay paridad posible.
2. **El cómputo depende de la ventana VISIBLE** (renderer) → para paridad debe ser data-driven: la ventana de pantalla no es reproducible en Python.
3. **Pin de parámetros + warmup/estado por sesión declarados** (24 params en V2: el conjunto exacto entra al meta).
4. **El "patinaje" usa percentiles rodantes auto-adaptativos**: declarar la ventana del percentil (si usa historia completa acumulada hay look-ahead visual — mismo motivo por el que `TopPercentFilter`/`AutoScale` están PROHIBIDOS en el PARAM_SPEC de BigTrap2).

## 5. El camino si se deciden incorporar (la autopista ya está pavimentada hoy)

1. `.cs` con log sellado → oráculo CSV con identidad.
2. Réplica sandbox (probada hoy de punta a punta: datos certificados + harness + comparación 1:1).
3. Paridad ≥ umbral contra el oráculo.
4. **Recién ahí** diseño de medición pre-registrado. Nunca medir sobre una simulación no-paritaria — si el indicador dibuja 1 tick arriba o se congela distinto, el edge medido no existe en vivo.

---

Aporte al referente: la pregunta de Nico era la correcta (paridad primero) y la respuesta del proyecto es la de siempre — se mide, no se argumenta. Estos dos indicadores entran, si entran, por la misma puerta que todo lo demás: oráculo sellado, paridad verificada, estimand pre-registrado.
