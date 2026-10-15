# Propuesta para auditoría: modelo de reversión a la expansión sobre ventana multiescala de ticks (precio × volumen)

Estado: **PROPUESTA — NO APROBADA, NO EJECUTADA.** Nada de este documento autoriza medir retornos. Requiere (a) auditoría de agentes independientes (sección 14) y (b) OK explícito de Nico (regla STOP del `CLAUDE.md`).
Fecha: 2026-10-15
Familia nueva a registrar: `EXP-REV-GRID` (independiente de BigTrap2, LUX-IMB, YM-PRERANGE, aVolCluster, HFTZones; no hereda resultados, poblaciones, costos ni presupuesto de multiplicidad de ninguna).
Referente rector: `docs/NORTH_STAR.md`, sha256 del cuerpo previo al marcador `SHA256-BODY-ABOVE` = `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421` (valor declarado en `CLAUDE.md`; el auditor de gobernanza debe recomputarlo con `tests/test_north_star_hash.py` antes de aprobar).
Documentos previos que esta propuesta usa y no reemplaza: `INVESTIGACION_IA_GRILLA_PRECIO_VOLUMEN_REVERSION_20261015.md`, `R2_RECORRIDO_VS_FRICCION_*`, `R3_DIRECCION_15_60M_*`, `EMACORRIDORTRENDVOL_VARIANTE_20261015.md`, `EMACORRIDORTRENDVOL_ANCLAS_20261015.md`.

---

## 0. Resumen en diez líneas

1. **Hipótesis (de Nico):** después de una expansión de precio, lo que ocurrió *dentro y alrededor* de ella (cómo se movió el precio tick a tick, cuánto volumen operó, dónde, dónde más) contiene información sobre si el precio **revierte hacia la expansión** de un modo que, neto de fricción, paga.
2. **"Revierte"** = movimiento contrario a la dirección de la expansión (hacia su origen) de al menos X ticks antes de moverse Y ticks en contra y antes de un tiempo máximo T, medido **solo hacia adelante desde un momento de decisión**, con X por encima de la fricción medida.
3. **Entrada del modelo:** ventana de ticks **sin tamaño de grilla fijo**: resolución fina cerca del precio y del centro de la expansión, gruesa hacia lejos (contenedores logarítmicos en precio y tiempo), más perfil de volumen por precio. La atención está en el centro, el borde no se impone.
4. **Población:** **toda** expansión confirmada y todo momento de decisión posterior (no sólo las zonas marcadas por el percentil 90). La elección entre evento y estado se enumera y justifica (sección 4).
5. **Salida:** probabilidad de "revierte" **y** mapa sobre celdas (precio relativo × tiempo) para *dónde* y *cuándo*; más abstención calibrada.
6. **Cadena obligatoria:** geometría/lifecycle → información → P&L bruto → edge neto/replicado. No se salta a P&L.
7. **Modelos por etapas, de barato a caro:** baselines en CPU → red chica multiescala → preentrenamiento autosupervisado (GPU Kaggle, sólo si hay señal antes).
8. **Evaluación:** validación por sesión con purga y embargo, comparación contra el caso sin filtro, el espejo, la volatilidad sola y los baselines; MDE publicado; dos canales (direccional y no direccional); multiplicidad corregida; holdout ≥ 2026-10-01 sellado.
9. **Presupuesto de hipótesis cerrado** antes de mirar retornos (sección 9).
10. **Lo que puede salir mal está escrito primero** (sección 12), junto con las condiciones de refutación y de parada.

---

## 1. Justificación económica (campo obligatorio)

Una expansión rápida de precio deja desequilibrio (órdenes agresivas de un lado) y un perfil de volumen distinto al de un movimiento ordenado. Si ese desequilibrio se agota, el precio puede retroceder parcialmente hacia el origen de la expansión (toma de beneficios, absorción por liquidez pasiva, reequilibrio). Esa reversión sería una fuente de P&L **sólo** si (a) es predecible con probabilidad suficientemente distinta de la de un movimiento aleatorio equivalente, y (b) el recorrido esperado supera la fricción (en ES ≈ 3,4–3,6 ticks ida y vuelta: spread medido + comisión 0,28–0,46 + slippage 2). Quien paga la ventaja sería quien presiona el precio sin considerar su costo de impacto (flujo impaciente) y recibiría el pago quien provee liquidez en el retroceso. La hipótesis es **económicamente plausible pero no está respaldada por evidencia propia**: lo medido hasta hoy en el repo la rodea sin confirmarla (ver §12).

## 2. Cómo podría refutarse (campo obligatorio)

La hipótesis queda refutada, con alcance preciso (mecanismo, población, etiqueta y ejecución de este documento), si ocurre **cualquiera** de:

- R1. En validación por sesión fuera de muestra, ningún modelo de las etapas 1–3 supera al baseline de la etapa 0b (caso sin filtro / volatilidad sola) con intervalo de confianza clusterizado por sesión que excluya cero, **o** el MDE publicado muestra que no había poder (en cuyo caso el estado es "sin potencia", no "refutada").
- R2. El efecto desaparece en el espejo o aparece igual en el espejo (señal de artefacto de la etiqueta, no de mercado).
- R3. El efecto, positivo en bruto, es menor que la fricción medida del instrumento (sin edge neto).
- R4. El efecto sólo aparece con parámetros (X, Y, T, escala de ventana) elegidos mirando el resultado (nada de eso se permite; ver §9).
- R5. No replica en el segundo instrumento/período preregistrado como réplica (§10).

Una refutación **no** se amplía a otras familias, otros instrumentos ni otros horizontes (regla "toda muerte tiene alcance preciso").

## 3. Datos y alcance

- Fuente: release `liquid_tick_v1` v4 (manifest SHA `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5`, aprobación externa `docs/infra/release_approval/release_approval_db9c42cd.json`), vía lector con propósito `provisional_research`/`research`.
- **Holdout sellado:** `trade_date ≥ 2026-10-01`. Prohibido para elegir etiqueta, parámetros, modelo o umbrales. Una sola apertura por candidato, por protocolo, después del cierre de la campaña.
- Instrumento primario: **ES** (fricción medida). Los demás (NQ, MNQ, MES, 6E, GC, etc.) son **réplicas independientes**, cada una con su propia fricción estimada; **no se transportan costos** entre instrumentos.
- Limitaciones de datos que condicionan el diseño (P-28): `sequence` es índice de fila de origen, **no** secuencia del exchange; `ts_local_ns` duplica `ts_utc_ns`. Por lo tanto: **ninguna característica puede depender del orden de ticks con el mismo timestamp**, ni de latencia, ni de secuenciación de mercado. La agresión (lado) sólo se usa si está en el dato y verificada; si no, se omite (§5).
- Fricción: se reutiliza la medición de R2 para ES. Cada instrumento adicional estima la suya antes de cualquier lectura de P&L.
- Etapa 0 (target-free) cuenta, por instrumento: sesiones disponibles, expansiones confirmadas por sesión, momentos de decisión y N efectivo. **Hasta ese conteo no se fija ningún tamaño de muestra ni umbral de éxito numérico** (queda como TBD con regla de cálculo, §9).

## 4. Población: espacio de eventos y estados enumerado (regla obligatoria)

Antes de congelar cuál se mide, se enumeran las familias posibles:

| # | Familia | Qué es | Pros | Contras / riesgo |
|---|---|---|---|---|
| P1 | **Creación** | Una observación por expansión, en el instante en que se confirma | Evento limpio; N = nº de expansiones | N chico; la confirmación llega tarde (≥ 65 barras en `EmaCorridorTrend`) y puede haber perdido el movimiento |
| P2 | **Aproximación** | Precio se acerca a un nivel de la expansión (p. ej. POC/VAL) | Entrada natural | Define "cerca" con un parámetro; sesgo si el nivel se reubica |
| P3 | **Primer toque / n-ésimo toque** | El precio toca la banda o un nivel por primera/n-ésima vez | Es la única familia que el corpus BigTrap2 midió (herencia sin decisión) | Ya medido en otra familia; no extiende |
| P4 | **Estado continuo** | Cada barra (o cada ventana de tiempo fija) posterior a la confirmación, mientras la expansión sigue vigente | Mucho mayor N bruto; el modelo aprende *cuándo* | Observaciones altamente autocorrelacionadas; N efectivo ≈ nº de expansiones, no de barras |
| P5 | **Invalidación / expiración** | El estado en que la expansión ya no vale | Útil como corte, no como entrada | — |
| P6 | **Confluencia** | Cruce con otras familias (aVolCluster, BigTrap2) | — | **Fuera de alcance**: no se cruzan familias (regla de independencia) |

**Elección propuesta (a auditar):** P4 como población primaria, con P1 y P3 reportadas como submuestras de la misma corrida (no como búsquedas adicionales). Justificación: el usuario pide un *punto de predicción* (dónde y cuándo), no un evento fijo; un estado permite que el modelo aprenda el momento. **Condición de refutación de la elección:** si el N efectivo de P4 (episodios independientes) es menor que el que exige el cálculo de MDE de la etapa 0, la población se restringe a P1 y se vuelve a someter a auditoría (no se amplía la ventana de datos mirando resultados).

Definición de **expansión** (target-free y causal): se usa el detector `EmaCorridorTrend` v4.0 tal como está en el repo (`nt8/user_indicators/EmaCorridorTrend.cs`, espejo en Python por confirmar en la etapa 0) **sin modificar sus parámetros**; sólo se consumen expansiones ya confirmadas, y la **dirección y el origen se fijan con la información disponible en el instante t** (el origen se reubica: la versión vigente en t es la única válida). Alternativas de definición de expansión (desplazamiento de ATR en ventana fija; ruptura de rango) quedan **declaradas y no ejecutadas**; el auditor puede pedir su inclusión como análisis de sensibilidad previo al congelado, pero no después.

## 5. Observaciones y variables de entrada

**Momento de decisión τ:** instante en que se evalúa el modelo. En P4: cada cierre de barra de la serie base (resolución a fijar en la etapa 0 entre las ya disponibles en la release; no se elige por P&L) posterior a la confirmación y anterior a la expiración. **Todo input usa sólo datos con timestamp ≤ τ.**

**Ventana multiescala (sin límite impuesto de tamaño):**
- Eje de precio: distancia al precio de decisión, en ticks, con contenedores de ancho creciente (p. ej. 1, 1, 2, 2, 4, 4, 8, 16, 32, 64, 128… ticks en cada lado) hasta cubrir al menos el rango de la expansión más un margen; el último contenedor es abierto ("más allá").
- Eje de tiempo: antigüedad respecto de τ, también con contenedores crecientes.
- Contenidos por celda: volumen total; volumen cuando el dato permita separar lado (sólo si está verificado); nº de ticks; (opcional) tiempo operado.
- **Perfil de volumen por precio** de la expansión (POC, VAL/VAH 70 %, barra de máximo volumen, usando las definiciones ya espejadas en `tools/corridor_anchors.py`).
- Escalares: duración y recorrido de la expansión en ticks y en ATR relativo, pendiente, tiempo desde la confirmación, hora de sesión (codificación cíclica), volatilidad reciente, spread medido.
- **Normalización:** a unidades de ticks y a volumen relativo al percentil de la misma hora en sesiones anteriores (nunca estadísticos de la muestra completa). Todas las normalizaciones se calculan **con datos anteriores a τ** o dentro del fold de entrenamiento.
- **Aumento por espejo:** invertir precio y lado produce un ejemplo equivalente para la dirección contraria; se usa como regularizador y como control (§8).

Prohibido como entrada: cualquier variable derivada de datos posteriores a τ, de la hora de fin de la sesión, del resultado de otras zonas futuras, o de `sequence` / `ts_local_ns` como si fueran secuenciación del exchange.

## 6. Etiqueta (definición de "revierte")

Para un momento de decisión τ con expansión de dirección d ∈ {+1, −1} (d = +1: suba) y precio de referencia p0 = mejor precio ejecutable al abrir en τ (el siguiente tick disponible tras τ, con el spread medido; **no** el precio del tick de τ):

- Posición hipotética **contra** la expansión (venta si d = +1; compra si d = −1) con **objetivo** a X ticks hacia el origen y **parada** a Y ticks en contra, vencimiento en T.
- **Etiqueta binaria** `rev = 1` si se alcanza el objetivo antes que la parada y antes de T; `rev = 0` si se alcanza la parada primero o vence T. Se conservan también `t_hit` y el exceso máximo favorable/adverso (para las salidas de "dónde/cuándo" y para el canal no direccional).
- **Ejecutabilidad:** el objetivo se considera alcanzado sólo si el precio *negoció* a ese nivel; la entrada y la parada pagan el spread medido y el slippage declarado. Prohibidos fills imposibles (llenado de órdenes límite sin cola de ejecución).
- **Conservadurismo de empates:** si en el mismo tick (o mismo timestamp, dado P-28) se tocan objetivo y parada, se asigna la parada.
- **Solapamiento:** las etiquetas de momentos vecinos comparten futuro. Se aplica purga y embargo por sesión (§8) y los intervalos de confianza se **clusterizan por sesión**.

**Cuadrícula de etiqueta (cerrada antes de mirar retornos):**

| Parámetro | Valores propuestos (ES) | Justificación |
|---|---|---|
| X (objetivo, ticks) | 8, 12 | por encima de la fricción (≈ 3,5): el beneficio bruto por acierto es X; se exige X ≥ 2 × fricción |
| Y (parada, ticks) | = X (razón 1:1) y = X/2 (razón 2:1) | el 1:1 es el nulo "neutral"; el 2:1 exige mayor probabilidad para el mismo X |
| T (vencimiento) | 15 y 30 min | alineado con R3 (15–60 min); no se extiende a 60 sin evidencia |

Eso da **8 celdas de etiqueta**. **Etiqueta primaria preregistrada: X = 8, Y = 8, T = 30 min** (las otras 7 son secundarias, corregidas por multiplicidad). El auditor debe decir si esta elección es defendible *sin* haber visto retornos y si debe moverse a otro valor por razones económicas (p. ej. recalibrar X con la fricción medida de cada instrumento).

Para cada celda, el **nulo de base** es la tasa `rev` incondicional (misma geometría sobre momentos de decisión sin información del modelo), calculada en la etapa 0b. La probabilidad aleatoria de "primer paso" depende de la geometría, no es 50 %: ver "ruina del jugador" `Y/(X+Y)` y reflexión browniana; **no se usa 50 % como nulo**.

## 7. Modelos

Etapas cerradas en orden; **no se pasa a la siguiente sin cumplir su criterio de entrada**.

| Etapa | Modelo | Criterio de entrada | Qué produce |
|---|---|---|---|
| 0 | Sin modelo. Conteos, auditoría de datos, etiqueta, nulo incondicional, MDE, fricción | — | Población congelada, N efectivo, MDE por celda, nulo `rev` base |
| 1 | **Regresión logística regularizada (elastic net)** y **gradient boosting (LightGBM)** sobre resúmenes de la ventana multiescala (volumen por contenedor, POC/VA relativos, desequilibrio, asimetría, pendiente, volatilidad, hora) | Etapa 0 aprobada por auditoría y por Nico | Piso de desempeño; importancias (descriptivas, no causales) |
| 2 | **CNN pequeña 1D/2D multiescala** (3–4 capas, < 1 M de parámetros) o codificador de secuencia de ticks comprimida por reloj de volumen; cabeza de **mapa de calor** (softmax 2D sobre precio relativo × tiempo + clase "no revierte") | Etapa 1 muestra señal en validación por sesión **o** el auditor autoriza explorar aun sin señal para estimar techo | `P(rev)`, distribución de dónde/cuándo |
| 3 | **Supervivencia discreta** `h(t \| x)` y/o regresión por cuantiles para tiempo hasta objetivo y exceso | Etapa 2 con señal | Mejor calibración de "cuándo" |
| 4 | **Preentrenamiento autosupervisado** (enmascarar celdas/tramos y reconstruir) sobre **todas** las ventanas de la release (incluye momentos sin expansión); luego ajustar una cabeza pequeña | Etapas 1–2 con señal; GPU Kaggle; presupuesto de cómputo declarado | Representación; se evalúa sólo por mejora sobre etapa 2 |
| 5 | **Calibración y abstención**: predicción conformal / clasificación selectiva, conjunto de calibración separado por sesión | Alguna etapa con señal | Umbral de acción: actuar sólo si `P(rev)·X − (1−P(rev))·Y − fricción > 0` con cobertura garantizada |

**No se usan:** DeepLOB/TLOB/transformers sobre libro de órdenes; ajuste fino de modelos fundacionales (Kronos, Chronos, TimesFM) como predictores; aprendizaje por refuerzo. Se declaran descartados con su motivo (§12); el auditor puede objetar.

**Reproducibilidad:** semillas fijas y publicadas (≥ 5 semillas por modelo de etapa ≥ 2), versiones de librerías en el manifiesto, `git head_start/head_end` y estado limpio/sucio (procedencia dirty-aware). Ninguna dependencia pesada nueva; CUDA sólo en Kaggle (etapa 4), nunca en la máquina local.

## 8. Protocolo de evaluación

**Particiones:**
- Datos anteriores a `2026-10-01` divididos **por sesión** (nunca por barra). Walk-forward expansivo: entrenar en sesiones [0..k], validar en [k+1..k+m], con **purga** (descartar momentos cuyo horizonte T cruza el límite) y **embargo** de al menos T + 1 sesión.
- El conjunto de calibración (etapa 5) es una franja de sesiones **posterior** al entrenamiento y **anterior** al test del fold.
- Ningún hiperparámetro se elige en el test de un fold; la búsqueda de hiperparámetros se declara (rejilla acotada, nº de pruebas contado en el presupuesto de §9) y se hace dentro del entrenamiento con validación interna por sesión.

**Comparaciones obligatorias (cada una publicada con intervalo):**
1. Tasa `rev` incondicional (nulo de base) por celda.
2. Predictor **sólo de volatilidad** (y hora): ¿explica la señal?
3. Baseline etapa 1 vs. etapas 2–5.
4. **Espejo**: el mismo modelo evaluado sobre datos reflejados (precio y lado invertidos). Efecto simétrico esperable si es real y no un artefacto de dirección; un efecto sólo en una dirección se reporta como tal.
5. **Placebo temporal:** etiqueta desplazada en el tiempo / barajada por bloques de sesión (aleatorización preservando autocorrelación) para estimar el nulo empírico del estadístico.
6. **Punto de decisión aleatorio:** mismo N de momentos sin condición de expansión (para probar que la expansión aporta).

**Métricas y dos canales:**
- *Direccional:* diferencia de `rev` modelo vs. nulo; expectativa neta por operación `E = P·X − (1−P)·Y − fricción` **sólo cuando el modelo actúa**, y expectativa por sesión.
- *No direccional:* distribución completa de excesos favorables/adversos y de `t_hit`, calibración (Brier, log-loss, curva de confiabilidad), CRPS para "dónde/cuándo". Un efecto bidireccional que promedie cero no puede perderse.
- **MDE:** cada resultado nulo publica su MDE (potencia 80 %, α = nivel corregido de §9) calculado con el N efectivo (sesiones/episodios). "Sin efecto detectado" sin MDE no se acepta.

**Inferencia:** bootstrap estacionario clusterizado por sesión; `lower > 0` del IC como inferencia primaria (misma semántica que `PrimaryCI` de la enmienda G2-A1); `temporal_concentration_test` sólo como diagnóstico. **No se relaja ninguna tolerancia ni gate después de ver resultados.**

## 9. Presupuesto de hipótesis y multiplicidad (fijar antes de correr)

Número efectivo de hipótesis **declarado** (cota superior; el auditor estadístico debe recalcular la correlación entre celdas):

- Celdas de etiqueta: 8 (1 primaria + 7 secundarias).
- Familias de modelo reportadas: baseline-logístico, LightGBM, CNN multiescala (3 como mínimo; supervivencia y preentrenamiento sólo si se habilitan, +2).
- Instrumentos: 1 primario (ES) + réplicas **preregistradas** (hasta 3), cada una evaluada una vez.
- Rejilla de hiperparámetros por modelo: ≤ 20 combinaciones (contadas).

**Inferencia confirmatoria única:** la celda primaria (X = 8, Y = 8, T = 30) con el mejor de los 3 modelos *elegido por validación interna*, evaluada **una vez** en los folds de test. Todo lo demás es exploratorio y se corrige con Holm (o BH si se declara) sobre el conjunto de celdas × modelos; se reporta además **DSR/SPA** por la selección entre modelos. El nivel α corregido y el MDE se calculan en la etapa 0 y se **congelan** en el manifiesto antes de correr cualquier medición.

**Criterio de éxito (se completa en la etapa 0, no antes):**
- Cond. A: IC clusterizado de `E` neta por operación, con `lower > 0` en el test walk-forward agregado y en ≥ 2/3 de los folds.
- Cond. B: efecto en el espejo coherente y no sólo en una dirección (o diferencia explicada).
- Cond. C: supera a (2) volatilidad sola y a (6) punto aleatorio con IC que excluye cero.
- Cond. D: calibración aceptable (curva de confiabilidad dentro de la banda preregistrada).
- Cond. E: replicación en el instrumento/período de réplica con el modelo y los umbrales **congelados**.
- Número mínimo de sesiones / episodios independientes: **TBD en la etapa 0** por el cálculo de MDE (regla: el N efectivo debe permitir detectar como mínimo X/4 de ventaja neta por operación con potencia 80 %; si no, el estado final posible es "sin potencia").

## 10. Replicación y holdout

- **Réplica interna:** cada hallazgo se evalúa en un período no usado para elegir (último tramo de sesiones previo al 2026-10-01), dejándolo fuera desde el inicio ("réplica sellada"), con el patrón `REPLICATION_OPENED.json` ya usado en R3.
- **Holdout (≥ 2026-10-01):** se abre **una sola vez**, con el candidato final congelado (modelo, pesos, umbrales, hash), sólo si A–E se cumplen. Es el único paso que se parece a una validación forward; no se usa para elegir.
- **Réplica en otros instrumentos:** sólo con su propia fricción y su propia etapa 0.

## 11. Cadena hacia el edge neto operable (y qué NO es un resultado)

geometría/lifecycle (etapa 0) → información (¿`rev` es predecible? etapas 1–3, log-loss/AUC vs. nulo) → P&L bruto (sólo tras OK explícito de Nico; **sin selección por P&L máximo aislado**) → edge neto/replicado (fricción, espejo, réplica, holdout) → ejecutabilidad (feed en vivo, fills realistas, latencia, kill switch; fuera de este documento).

No se considera resultado: un AUC alto sin expectativa neta positiva; una expectativa positiva sólo en bruto; un efecto en una sola semilla o un solo fold; un efecto que desaparece con costos o en el espejo.

## 12. Riesgos, antecedentes negativos y cómo se mitigan

| Riesgo | Descripción | Mitigación |
|---|---|---|
| Filtración causal por la zona | La expansión se confirma tarde y su origen se reubica; usar la versión final mira el futuro | Usar sólo la versión vigente en τ; auditoría de causalidad por reproducción de τ en modo streaming |
| Filtración por la etiqueta | Entrada en el tick de decisión o ejecución imposible | Entrada en el siguiente tick, spread medido, empates a la parada |
| Autocorrelación / N inflado | Momentos de decisión vecinos son casi idénticos | Clusterizar por sesión; N efectivo = episodios; purga y embargo |
| Sobreajuste por capacidad | Muchas variables, N efectivo chico | Modelos chicos, regularización, baselines primero, espejo como aumento |
| Cambio de régimen | La predictibilidad decae con el tiempo (TLOB) | Walk-forward expansivo; reportar estabilidad por fold; réplica sellada |
| Fricción mal estimada | Slippage y cola de ejecución dependen del instrumento y del momento | Estimar por instrumento; sensibilidad ±1 tick; no transportar costos |
| Datos | `sequence`/`ts_local_ns` no son del exchange (P-28); precios de contratos distintos | No depender del orden dentro del timestamp; auditar rollover y vencimientos por catálogo |
| Antecedentes negativos | BigTrap2 como soporte/resistencia refutado (~96 % de ruptura); BigTrap2 como imán cerrado; HFTZones 6E H1 muerta; R2/R3 sin efecto direccional a 15–60 min | Esta propuesta **no** transporta esos resultados ni los contradice: mide otra población y otra etiqueta; debe ganarle al nulo, no sólo al azar |
| Hipótesis creciente | Muchas celdas y modelos | Presupuesto cerrado (§9); primaria única; el resto exploratorio |
| Complejidad prematura | Redes sin base | Escalera de etapas con criterio de entrada |
| Aprendizaje de artefactos de sesión | Hora del día, rollover, apertura | Hora como variable explícita y también en el punto aleatorio; auditoría por cortes |

## 13. Artefactos, procedencia y gobernanza

- **Manifiesto de campaña** (a redactar *después* de la auditoría, con los valores congelados): cita el hash de `docs/NORTH_STAR.md`, el SHA del manifiesto de la release, el commit del código y su estado limpio/sucio, semillas, versiones, lista de celdas, α y MDE congelados.
- **Registro MEDIDO/NO MEDIDO** (`docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md`): se actualiza **en el mismo commit** que cualquier resultado nuevo.
- **Landscape completo:** se publican todas las celdas, semillas y nulos, no sólo los favorables. Resultados negativos incluidos.
- **Una worktree / un escritor por directorio.** Commits chicos por fase; `git show --stat` tras cada commit.
- **Ramas:** todo a `foundation/f0b-compatibility-probe` (mirror a `main` según la práctica vigente).
- **STOP:** ninguna búsqueda sobre P&L/retornos corre sin el OK de Nico sobre el manifiesto, el número efectivo de hipótesis, los riesgos y los datos faltantes.

## 14. Plan de auditoría (para agentes independientes)

Cada auditor trabaja **sin ver el informe de los demás** y entrega el informe con la plantilla de §14.3. Los auditores deben **verificar contra el repo y las fuentes**, no confiar en este documento ("fuente antes que recuerdo"); toda cifra que sostenga una decisión (fricción, N, definición del detector, hash) debe recomputarse o citarse con ruta.

### 14.1 Roles y preguntas

**A1 — Causalidad y fugas de información.**
¿Hay algún input o normalización que use datos posteriores a τ? ¿La expansión vigente en τ es reproducible en modo streaming (reproducción de `EmaCorridorTrend` hasta τ)? ¿La etiqueta puede filtrarse en las entradas por solapamiento? ¿La entrada en el siguiente tick es realista dado P-28? ¿El tratamiento de empates es conservador?

**A2 — Estadística y multiplicidad.**
¿El presupuesto de §9 está bien contado (correlación entre celdas, modelos, hiperparámetros)? ¿La inferencia primaria (bootstrap estacionario clusterizado) es la adecuada? ¿El nulo de base por geometría es correcto (ruina del jugador, reflexión browniana, drift)? ¿Cómo se calcula el MDE con N efectivo clusterizado? ¿Holm/BH/DSR/SPA correctos? ¿El criterio "≥ 2/3 de folds" tiene sentido con pocos folds?

**A3 — Economía y ejecutabilidad.**
¿Las celdas (X, Y, T) tienen sentido económico frente a la fricción de ES? ¿El spread/slippage asumido es suficientemente conservador? ¿La entrada pasiva/agresiva está bien especificada? ¿Qué falta para operar (cola, latencia, límites de riesgo, kill switch)? ¿La hipótesis tiene un mecanismo de pago creíble (quién paga)?

**A4 — Datos e integridad.**
¿La release v4 y su aprobación permiten este uso? ¿El holdout está realmente excluido (corte por sesión CME, no por UTC)? ¿Los rollovers, vencimientos y catálogos de sesión están tratados? ¿Qué dependencias de `sequence`/`ts_local_ns` se filtran en la implementación? ¿Cuántas sesiones hay por instrumento (verificar, no suponer)?

**A5 — Diseño de modelos y ML.**
¿La escalera de etapas es proporcionada al N efectivo? ¿La ventana multiescala introduce fuga o artefactos de contenedores? ¿El espejo como aumento y como control es válido (simetría real del mercado)? ¿La cabeza de mapa de calor es evaluable (CRPS, log-loss) y no inflable? ¿El preentrenamiento autosupervisado puede aprender artefactos de sesión? ¿Las semillas y la regularización alcanzan?

**A6 — Gobernanza y coherencia con el repo.**
Verificar: cita del hash de `NORTH_STAR.md` (recomputar), reglas de población (§4), STOP, firewall del holdout, independencia de familias, registro MEDIDO/NO MEDIDO, una sola rama, procedencia dirty-aware. ¿Contradice alguna regla de `CLAUDE.md`, `docs/edge_validation_contract.md` o `docs/research_funnel_playbook.md` (ATJ-01…ATJ-16)?

**A7 — Abogado del diablo (refutación).**
Objetivo: escribir el mejor argumento de por qué **la hipótesis ya está implícitamente refutada o es no medible** con estos datos (antecedentes BigTrap2/HFTZones/R2/R3, tamaño de N, efecto de selección de la definición de expansión). Proponer el experimento más barato que la refute antes de gastar cómputo.

### 14.2 Lo que cada auditor debe entregar
- Veredicto por sección: `APROBADA` / `APROBADA CON CAMBIOS` / `RECHAZADA` / `NO AUDITABLE (falta información)`.
- Lista de **defectos** con severidad (bloqueante / mayor / menor), evidencia (ruta y línea o fuente) y **cambio concreto propuesto**.
- Lista de **preguntas abiertas** que sólo Nico puede responder.
- Declaración explícita de lo que **no** auditó.

### 14.3 Plantilla de informe

```
Auditor: <rol>   Fecha: <YYYY-MM-DD>   Commit auditado: <sha>
Veredicto global: <...>
Secciones auditadas: <...>   No auditadas: <...>
Defectos:
 - [bloqueante|mayor|menor] §<n> — <qué> — evidencia: <ruta:línea / fuente> — cambio propuesto: <...>
Verificaciones recomputadas (cifra declarada vs. recomputada): <...>
Preguntas para Nico: <...>
Riesgo residual si se aprueba tal cual: <...>
```

### 14.4 Criterio de aprobación de la propuesta
- Sin defectos **bloqueantes** abiertos.
- A1 y A2 en `APROBADA` o `APROBADA CON CAMBIOS` con cambios incorporados.
- A7 sin un experimento barato que refute la propuesta y no haya sido ejecutado.
- Reconciliación documentada de discrepancias entre auditores (si dos auditores se contradicen, se escribe cuál se adopta y por qué).
- Luego: manifiesto congelado → OK explícito de Nico → ejecución de la etapa 0.

## 15. Preguntas abiertas para Nico
1. ¿Se acepta P4 (estado continuo) como población primaria con P1/P3 como submuestras?
2. ¿Se acepta la etiqueta primaria X = 8, Y = 8, T = 30 min, o prefiere otra razón riesgo/beneficio?
3. ¿Qué serie de barras base (resolución) para los momentos de decisión? (propuesta: la ya disponible en la release que ofrezca más sesiones; se decide en la etapa 0 sin mirar retornos)
4. ¿Instrumentos de réplica preregistrados (propuesta: NQ/MNQ y 6E, cada uno con su fricción)?
5. ¿Presupuesto de cómputo en Kaggle para la etapa 4 (horas de GPU por semana)?
6. ¿Se autoriza reutilizar el detector `EmaCorridorTrend` sin modificarlo como definición de expansión?

## 16. Qué sigue después de la auditoría
Etapa 0 (target-free): conteo de sesiones y expansiones, auditoría de datos, espejo en Python del detector validado contra NT8, nulo incondicional, MDE, fricción por instrumento. Su salida congela los números marcados TBD y es la que Nico revisa antes de autorizar cualquier medición de retornos.

---
*Aporte al referente:* reduce la distancia al edge neto fijando de antemano qué se mide, contra qué nulo, con qué presupuesto de hipótesis y qué refuta la idea, de modo que un resultado positivo o negativo sea interpretable y no una selección a posteriori.

## Errata tras auditoría externa (2026-10-15)
Ver `docs/audits`-style reporte `Auditoria_grilla_reversion_y_entrenamiento.md`. Correcciones a esta propuesta (prevalecen):
- **Objetivo:** primer paso R / C / 0 (reversión antes que continuación, o ninguna en T) con censura explícita; el punto exacto de giro y el mapa softmax 2D se posponen (celdas no excluyentes). Cabeza temporal de riesgos competitivos en tiempo discreto como segunda etapa.
- **Espejo:** robustez/equivariancia, **no** control nulo; se elimina R2 de §2 como criterio de refutación (que el espejo conserve la señal no es refutación).
- **No significación ≠ refutación:** separar sin evidencia, sin potencia y equivalencia frente a un margen económico preregistrado.
- **Fórmula económica:** `p_eq = (Y+c)/(X+Y)`; con timeouts `EV = P(R)·X − P(C)·Y + P(0)·E[ret_timeout] − E[costos]`. Mi afirmación de que 2:1 "exige mayor probabilidad" era incorrecta: lo que cambia son las probabilidades de cruce.
- **Preentrenamiento:** sólo con el entrenamiento de cada fold (no "toda la release").
- **Particiones:** HOLDOUT-A3 (descubrimiento hasta 2026-03-31, replicación abr–sep una vez por familia, holdout desde 2026-10-01); no usar el corte genérico pre-octubre.
- **Grilla:** contexto amplio en tres escalas (fina/media/amplia), no recortado al rectángulo; el centrado no puede usar el fill del siguiente tick; conservar volumen y conteo totales y máscaras de cobertura.
- **Modelos:** baseline continuo fuerte (hora, volatilidad, trayectoria, intensidad) vs elastic net, LightGBM, MLP, CNN multiescala pequeña (< 1 M de parámetros).

> Corrección (2026-10-15): el hash de `NORTH_STAR.md` citado originalmente en este documento (`ed4293b5…`) era el de una versión anterior (stale). El valor vigente, verificado con `tests/test_north_star_hash.py`, es `05df5c7c…`. Los scripts de Pasada 2 conservan la constante vieja; no afecta resultados.
