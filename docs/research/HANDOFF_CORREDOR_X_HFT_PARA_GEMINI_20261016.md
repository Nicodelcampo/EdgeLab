# Handoff para Gemini — estudio CORREDOR × zonas HFT (ES, 100T): descripción de la corrida y pedido de la parte ML/IA

Estado: VIGENTE (instrucciones de trabajo; la corrida de desenlaces NO está autorizada todavía: requiere manifiesto congelado + OK de Nico)
Fecha: 2026-10-16
Familia / módulo: EXP-CORREDOR-HFT (confluencia; registrar como familia nueva)
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)
Autor del handoff: Claude (con pocos créditos; Gemini continúa). Revisión de Nico pendiente.

## 1. Qué se quiere medir (formulación final de Nico)
Apuntar a la **inversión de un impulso** del indicador del corredor (`EmaCorridorTrend`) con **zonas HFT en su inicio**. Mapa de franjas:
- **A dónde:** las zonas HFT del **inicio** del impulso (su primera mitad).
- **Por dónde:** la **segunda mitad** del impulso, que debe estar **libre** de zonas HFT (camino de la inversión).
- **Desde dónde:** el extremo del impulso donde empieza la inversión; **no necesita zonas**.
Preguntas: (a) ¿cambia la probabilidad de que el precio **llegue** a esas zonas (E1) y de que las **atraviese en dirección contraria a la de la zona** (E2)? (b) ¿qué tiene que haber hecho el precio para que esa probabilidad le gane al azar (virginidad de la zona, edad, volumen desde su creación, alejamiento en ticks)? Se pidió también la variante "al menos 2 zonas tocadas en la primera mitad".

## 2. Decisiones de Nico vigentes
- Detector HFT: **`HFTZonesESPureV2Flat`** (el `HFTZonesESPureV2` del gráfico conserva el error `isDown-first`: NO se usa). Paridad NT8→Python ≈ 99 % medida en ES 03-26 (9.481/9.486 zonas; oráculo `runs/oraculo_espurev2flat_ES_snapshot.sqlite`: 6.685 Absorb, 2.800 Predator, 1 Ultra). **Zonas absorb no se usan.** Parámetros por defecto del `.cs`.
- Todo en **barras de 100 ticks** (el corredor depende de la barra). Corredor = `DET_NT8` (ATR = SMA(Rango)), preset 1 primario, preset 2 sensibilidad.
- "Zona HFT presente" = el precio **tocó** el rectángulo en la ventana (aunque termine dentro de la zona o el dibujo haya expirado). Extensión fija primaria **600 barras de 100T**; alternativas 300, 1200 y dinámicas (hasta mitigar / hasta el 1.er toque).
- Panel de modelos decidido para el programa de IA: baselines → CNN chica → DeepLOB-style → Transformer chico → fundacional congelado → RL al final; **para este estudio, el ML es tabular** (ver §6).

## 3. Definiciones causales (borrador a congelar; detalle en `DEFINICION_INICIAL_CORREDOR_X_HFT_20261016.md`)
- **Barras:** 100T estrictas por sesión (`trade_date` constante), mismo constructor de Pasada 2.
- **Instante de decisión (nuevo): `cls_b`, el cierre de la zona del corredor** (la tendencia se rompe). En ese instante ya se conocen `origin_bar` y `end_bar` (extremo), así que **las mitades se miden sobre `origin..end_bar` sin mirar el futuro**: 1.ª mitad = `[origin, origin + floor((end − origin)/2)]`, 2.ª mitad = el resto hasta `end_bar`. (Sensibilidad: mitades por `conf_bar`, confirmación ≥ 65 barras.)
- **Zona HFT:** del port Python de `Flat`; **disponible desde `end_ts` del barrido** (el `start_ts` es retroactivo y no se usa); creación = primera barra con cierre ≥ `end_ts`; activa en la barra *b* si *b* > creación y *b* ≤ creación + E (fija) o hasta mitigación/1.er toque (dinámica). **Tocada** = el rango [mín, máx] de la barra intersecta la zona.
- **Presencia (objetivo):** ≥ *k* zonas distintas tocadas en la 1.ª mitad (k = 1 primario, k = 2 secundario) **y ninguna tocada en la 2.ª mitad**. "Ninguna **activa**" en la 2.ª mitad es casi imposible (28 impulsos) y no se usa.
- **Control:** impulsos con **0 zonas tocadas en ambas mitades**; controles alternativos (todos < k; exactamente 1) y **pseudo-zonas** del mismo ancho y distancia sin zona HFT.
- **Desenlaces (a medir desde `cls_b`, sin implementar todavía):** E1 = el precio llega al borde cercano de la zona de referencia antes de *H*; E2 = tras llegar, recorre todo el ancho **contra la dirección propia de la zona** antes de salir por el borde de entrada. *H* ∈ {150, 300, 600} barras 100T (a declarar). Censura por fin de sesión explícita; empates = ambiguos. Zona de referencia primaria: la más cercana al precio de decisión entre las tocadas en la 1.ª mitad (alternativas: más grande, más antigua).

## 4. Qué se hizo (todo sin retornos ni desenlaces)
Censo en Kaggle: kernel `nicolasbuttaro/edgelab-corredor-hft-census-v1` (CPU, ~6 min; release `nicolasbuttaro/edgelab-liquid-ticks-20261014` v4; ES descubrimiento 2025-07-18 → 2026-03-31, **178 sesiones**). Código: `tools/corridor_hft_census/` (`census_addon.py`, `build_census_script.py`) + `tools/corridor_pass2/` (Pasada 2 sha256 `10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec`, `DET_NT8`, loader y barras) + `edgelab/bridge/kernels/hftzones_es_pure_v2_flat.py` (port HFT). Salidas: `corredor_hft_census_20261016/` (impulsos por fila con conteos de zonas tocadas/activas en las dos mitades por extensión).
Resultados clave:
- Zonas HFT sin absorb: **7.841** (44,1 por sesión) ≈ oráculo sin absorb (2.801/62 = 45,2): **densidad verificada**.
- Preset 1: **5.312** impulsos (30 por sesión). Con fija 600, ≥ 1 zona tocada en cualquier ventana de la 1.ª mitad por `conf_bar`: 54,5 % (2.897 vs control 2.415).
- **Definición por extensión (`cls_b`):** ≥ 1 tocada en la 1.ª y ninguna tocada en la 2.ª: **1.270** impulsos (control 0-0: **1.952**; 173 sesiones; MDE80 ≈ 5,7 pp con efecto de diseño 2 **supuesto**). **≥ 2 y 2.ª libre: 599** (MDE ≈ 7,4 pp). Por `conf_bar`: ≥ 2 y 0 en la 2.ª = 443.
- Preset 2 (fija 600): ≥ 1 y libre 1.567 (control 2.818); ≥ 2 y libre 683.
Documentos: `CENSO_CORREDOR_X_HFT_RESULTADOS_20261016.md`, `DEFINICION_INICIAL_CORREDOR_X_HFT_20261016.md`.

## 5. Contexto que condiciona (no transportar como evidencia)
- El **corredor solo no tiene efecto neto en ES** (`HA` bruto +1,5 / neto −2,0 ticks; nulo del pipeline p = 0,239): en este estudio es una **capa a evaluar**, no una premisa. Ver `CORREDOR_EMA_MEDIDO_Y_NO_MEDIDO.md`.
- ES de abril a septiembre está **expuesto** por la línea del corredor; holdout **≥ 2026-10-01 sellado**; diseño en descubrimiento. Las 299 sesiones de ES no son réplica limpia.
- Resolución de etiquetas: a 100T y barreras de zona los timeouts dominan (55–61 % en el corredor); aquí los desenlaces son de **llegada/atravesamiento**, no P&L: la economía (fricción de ES 3,546 ticks) queda para una fase posterior.
- Cualquier cruce entre familias exige **registrar la familia nueva** con ledger propio; no heredar presupuesto de multiplicidad.

## 6. Lo que se le pide a Gemini
**A. Refinar y completar el diseño (antes de correr):**
1. Cerrar las decisiones abiertas: medición del toque (barra 100T vs tick; mecha vs cierre), zona de referencia, horizontes *H*, extensión dinámica concreta, rejilla de parámetros (edad, volumen desde la creación, virginidad, distancia, ancho, `ahead`/`aligned`), qué control es primario.
2. Escribir el **manifiesto congelado** con número efectivo de hipótesis, MDE por parámetro, criterio de éxito/refutación y el **alcance preciso** de una muerte; citar el hash de `NORTH_STAR.md`.
3. Implementar el **motor de desenlaces causal desde `cls_b`** (E1/E2, censura, empates) y sus pruebas (prefijos vs streaming; cambiar datos posteriores a `cls_b` no cambia ninguna entrada; `available_at` de las zonas).

**B. Parte ML/IA (después de la estadística descriptiva; escalera con compuertas):**
1. **Descriptiva:** P(E1) y P(E2 | E1) por presencia y por cantidad de zonas (0, 1, 2, ≥ 3), con nulo emparejado (hora, volatilidad, distancia, ancho) y pseudo-zonas; IC clusterizado por sesión.
2. **Modelo simple:** regresión logística/elastic net con **4 variables preregistradas** (edad, volumen desde la creación, virginidad, distancia) + baseline continuo (hora, volatilidad, trayectoria).
3. **Franjas como variables** en LightGBM con restricciones monótonas justificadas económicamente y `interaction_constraints`: densidad/ancho/edad/virginidad de zonas **por franja** (inicio = a dónde; camino = por dónde; extremo = desde dónde), selección de zona dentro de la validación; **ablación re-entrenada** contra el baseline (¿aportan las franjas sobre hora/volatilidad/trayectoria?). Reutilizar `tools/corridor_pass2/dev_filters_analysis.py` (validación anidada por sesión con purga/embargo + **nulo del pipeline** por desplazamiento circular) y `tools/grid_support_pilot/`.
4. **Sólo si el paso 3 muestra información incremental calibrada:** modelos más grandes (CNN chica sobre tiles, riesgos competitivos en tiempo discreto) como ablaciones, con presupuesto declarado y ≥ 5 semillas. Sin FiLM/SE/Hawkes/etc. hasta tener esa base (ver `PAUTAS_PARA_GEMINI_CONTINUACION_EXP_REV_GRID_20261015.md`).
5. Reportar probabilidades (log-loss/Brier/calibración) y utilidad incremental contra el baseline fuerte; no confundir significación con relevancia; no leer "sin significación" como refutación (equivalencia vs un margen declarado).

**C. Lanzar:** sólo cuando el manifiesto esté congelado y Nico dé el OK explícito (regla STOP). Lanzar como kernel privado en Kaggle (CPU), con recibos y hashes; no abrir NQ/YM ni el holdout; no integrar al repo sin OK.

## 7. Reglas obligatorias
STOP antes de cualquier búsqueda sobre retornos/desenlaces; holdout intacto; diseño sólo en descubrimiento; **registrar cada variante intentada** (no sólo las ganadoras); dos canales (direccional y no direccional) y MDE en todo nulo; espejo = robustez, no nulo; no usar `start_ts` de las zonas; detector HFT = `Flat`; sin zonas absorb; un solo escritor por directorio; sin tokens ni URLs firmadas en los documentos.

## 8. Dónde está todo
Carpeta `corredor_hft_handoff_20261016/` en `resultados_claude_local` y `patches_for_review` (este documento, definición inicial, censo y sus CSV/JSON, scripts del censo y del piloto de soporte); repo `E:\EdgeLab-port` (rama `foundation/f0b-compatibility-probe`, espejo `main`). Kernels de Kaggle: `edgelab-corredor-hft-census-v1`, `edgelab-es-corridor-dev-events-v1` (tabla del corredor), `edgelab-grid-support-pilot-v1`. Puente Drive↔Kaggle: `tools/kaggle_drive_bridge.py` (activo mientras la PC y la sesión de Claude estén abiertas).

## 9. Cómo reportar
Por cada punto: acuerdo / desacuerdo / no verificable con evidencia; por cada componente de ML: qué agrega al presupuesto de hipótesis, prueba técnica, ablación y qué lo refutaría.

*Aporte al referente:* entrega a Gemini el estudio de inversión de impulsos con zonas HFT completamente definido y censado, con la parte de ML escalonada y con compuertas, para que lo termine de refinar y lo lance sin gastar presupuesto de hipótesis ni abrir datos reservados.
