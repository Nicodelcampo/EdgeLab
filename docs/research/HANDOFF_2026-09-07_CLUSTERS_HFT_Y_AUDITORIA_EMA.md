# Handoff 2026-09-07 — clusters HFT (NQ) y auditoría del hallazgo EMA (GC)

> Escrito para continuar **sin acceso a la conversación que lo produjo**.
> Rama: `foundation/f0b-compatibility-probe`.
> Se lee junto a `docs/research/HANDOFF_2026-08-21_ESTADO_COMPLETO.md` y `PENDIENTE.md`.

---

## 1. Línea nueva y viva: magnetismo de clusters HFT sobre NQ

**Hipótesis de Nico:** las aglomeraciones (clusters) de zonas con actividad HFT atraen
al precio.

**Estado:** plan de medición recibido, implementación **no empezada**. Ningún dato
medido todavía. Nada que interpretar aún.

### 1.1 Qué hay ya, y dónde

| Artefacto | Ruta | Qué es |
| :-- | :-- | :-- |
| Prompt de deep research | `docs/research/PROMPT_DEEP_RESEARCH_HFT_CLUSTER_MAGNETISMO.md` | Autocontenido. Describe el objeto y los tres defectos del instrumento. |
| **Resultado del deep research** | `docs/research/deep_research/DEEP_RESEARCH_HFT_CLUSTER_MAGNETISMO_2026-09-07.md` | **La pieza central.** Embudo de 7 escalones con estimand, población, nulo, refutación y MDE por escalón. |

### 1.2 El objeto: qué construye `HFTZonesNQPureV4.cs` hoy

El indicador vive en
`C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTZonesNQPureV4.cs`
(1.375 líneas; **no está versionado en el repo salvo la copia clonada en
`nt8/CleanImpulses.cs`**). Cambió el 2026-09-07 09:09 para agregar clusters.

Zonas HFT: ráfagas sobre subserie de 1 tick, con compuertas de pasos, velocidad
(`MaxAvgMs`), duración (`MaxTotalMs`), tasa de volumen (`MinVolumeRate`), volumen total
(`MinTotalVolume`) y retroceso. Nacen en una barra y ocupan `[Lower, Upper]`.

Clusters, en `DetectarSolapamientoCluster()`, disparado **sólo al nacer una zona**:

1. Candidatas: hasta 150 zonas hacia atrás con `VisualEndBar > nuevaZona.StartBar`.
2. Histograma de densidad **por tick de precio**; cada zona suma 1 en cada tick que cubre.
3. Ticks con densidad ≥ `MinOverlapRectangulos` (4) → agrupados en segmentos contiguos
   con tolerancia de 1 tick de hueco.
4. POC = tick de máxima confluencia, desempate por volumen acumulado.
5. Si solapa en precio con un cluster activo, **fusiona in-place**: `Lower = min`,
   `Upper = max`, `ZoneCount = max(anterior, nuevo)`, `EndBar` extendido.

### 1.3 Los tres defectos del instrumento (verificados en código, no supuestos)

Gobiernan todo el diseño de la medición.

- **D1 — la vigencia es un parámetro cosmético.** Una zona participa del histograma
  mientras `VisualEndBar = CurrentBars[0] + ExtensionDibujo` (600 barras) no expiró.
  Un parámetro de presentación decide membresía, ancho y vida del cluster.
- **D2 — el cluster no decae y se reescribe hacia atrás.** `ZoneCount` es marca de agua
  que nunca baja; la geometría fusionada es la unión histórica. **El objeto que existe
  al final del gráfico no es el que existía en el instante t.**
- **D3 — se dibuja 600 barras hacia el futuro** (`endAgo = -ExtensionDibujo`). La
  atracción siempre *parece* real en pantalla. Toda la proyección a la derecha del
  nacimiento es no-información en tiempo real.

### 1.4 Lo que el deep research concluye, resumido

- La literatura **no respalda** un imán genérico. El único efecto de atracción robusto
  y replicado es el *pinning* de opciones (Ni, Pearson & Poteshman, JFE 2005; Golez &
  Jackwerth, JFE 2012), que es **mecánico, de canal identificado (delta-hedging) y
  chico** — y hay evidencia moderna, en working paper sin revisión por pares, de que se
  degradó o se invirtió hacia amplificación entre 2016 y 2025.
- El magnetismo de POC/HVN del perfil de volumen **no tiene respaldo revisado por
  pares**. La citada "regla del 80%" es del Value Area, no del POC, y viene de
  literatura práctica sin control.
- **El nulo correcto es una fórmula cerrada:** bajo caminante sin deriva,
  `P(tocar a distancia d en horizonte t) = 2·(1 − Φ(d/(σ√t)))`. Como decrece
  estrictamente en `d`, los niveles cercanos se tocan más **por construcción**. Medir
  toques sin descontar `d` es medir geometría, no imán. **Con σ no constante hay que
  usar volatilidad realizada integrada o reloj de varianza**, o un cluster nacido en
  régimen de alta σ "atraerá" sólo por eso.
- **Precedente que más importa:** De Ceuster, Dhaene & Schatteman (*Journal of
  Empirical Finance*, 1998). Las "barreras psicológicas" en números redondos daban
  positivo hasta que se reemplazó el benchmark uniforme por permutaciones cíclicas; con
  el nulo correcto el efecto desapareció. Es la misma forma de falla que mató al 6E.
- **Cuello de botella declarado:** sin **censo as-of** y sin **doble registro
  vivo/reconstruido**, los escalones 1 a 5 **no son medibles de forma creíble**.

Conjeturas que el propio autor marca como suyas y **no** como literatura: la
formulación del sesgo de proximidad como artefacto de atracción, y el espejo geométrico
exacto como placebo (los análogos publicados son los niveles arbitrarios de Osler
2000/2003 y las permutaciones de De Ceuster 1998).

### 1.5 El embudo, en una línea por escalón

| # | Escalón | Unidad | Mata el escalón si… |
| :-- | :-- | :-- | :-- |
| 0 | Auditoría de repintado + censo as-of *(prerrequisito físico)* | evento | el repintado supera la tolerancia fijada de antemano |
| 1 | Proximidad: toque real vs nulo browniano **y** vs placebo emparejado | evento | el IC bootstrap del contraste cruza cero |
| 2 | Ciclo de vida con riesgos competitivos (CIF Fine-Gray) | evento | la CIF del cluster no supera la del placebo |
| 3 | Barrido de vigencia (50–1200 barras, y vigencia por invalidación) | evento | el signo o el tamaño cambian con el parámetro |
| 4 | Dinámica de la distancia precio–POC | **estado** | el drift hacia el cluster ≈ hacia el placebo ≈ reversión genérica |
| 5 | Condicionamiento por intensidad (Hawkes) + objeto hold-out | evento | el efecto desaparece al condicionar por intensidad |
| 6 | Clustering de POC en el eje precio (Ripley 1-D vs CSR) | evento | no excede el clustering de la rejilla de ticks / redondos |

Cada escalón mide **canal direccional Y no direccional**. Kaplan-Meier está prohibido
para incidencia acumulada acá: con riesgos competitivos sobreestima; va CIF.

### 1.6 Trabajo en vuelo cuando se cortó la sesión

Se lanzó un workflow de 5 lectores en paralelo para mapear el repo antes de diseñar los
módulos. **No terminó**; sólo hay eventos `started` en el journal.

- Script: `C:\Users\Usuario\.claude\projects\E--EdgeLab\58e6fec8-c9ac-4ffd-80e4-99949f8e65cd\workflows\scripts\plan-hft-cluster-funnel-wf_084ca78b-748.js`
- Transcripts: `…\subagents\workflows\wf_084ca78b-748\` (los `agent-*.jsonl` sirven aunque el resume no funcione: el resume es sólo dentro de la misma sesión).

Las cinco áreas que mapeaba, por si hay que rehacerlo: anatomía del indicador NT8;
infraestructura de paridad del repo; primitivas del bridge Python; toolkit estadístico
existente; precedente 6E y artefactos de gobernanza obligatorios.

### 1.7 Próximo paso concreto

Nico pidió, textual: *«tiene que ser una medición en embudo y modular, es decir, las
partes independientemente aportan valor, y a su vez los módulos base de investigación
sirven para los siguientes»*, y avisó que está dispuesto a **modificar el indicador si
eso hace la paridad más fácil**.

Orden acordado: **paridad primero, medición después.** Y una advertencia ya formulada
que conviene no perder: por D2 la paridad de clusters contra el estado final es
probablemente imposible — el objeto muta. Lo más probable es que el indicador deba
**emitir el censo as-of** (una fila por cluster cada vez que cambia, con su estado en
ese instante) y que la paridad se valide contra ese log de eventos, no contra lo
dibujado.

Tensión de diseño pendiente de resolver: el escalón 0 es prerrequisito de todo, pero un
módulo cuyo único valor es habilitar al siguiente viola el criterio de modularidad de
Nico. Su valor propio, si lo tiene, es que **la auditoría de repintado es un resultado
en sí misma**: dice si el indicador que se ve en pantalla es el que existía en tiempo
real.

---

## 2. Cerrado en esta sesión: auditoría del hallazgo EMA sobre BigTrap GC

**Acta:** `docs/audits/AUDITORIA_HALLAZGO_EMA_BIGTRAP_GC_2026-09-06.md`.
**Auditado:** commit `e50bbf3`, rama `work/bt2a-gate2-p2a-freeze-20260826` (trabajo de
otro agente, en `D:\EdgeLab`).
**Datos crudos de la re-corrida:** `docs/audits/ema_gc_2026-09-06/*.json`.

Verificado y correcto: el holdout `GC 08-26` está intacto (el runner carga cuatro
contratos y 08-26 no aparece en el código), y la simulación es causal.

Cinco defectos, todos con número:

1. **El efecto grande es del período, no del filtro.** El control **sin filtro** da
   −$962 in-sample y **+$30.230 out-of-sample**. Todas las configuraciones se dan
   vuelta entre períodos.
2. **El out-of-sample ya se había gastado.** `INFORME_OPTIMIZACION_EJECUCION_GC.md`
   titula «Top 5 Configuraciones **Validadas Out-of-Sample**» — la resolución de barra y
   el par SL/TP se eligieron mirando `04-26`/`06-26`, los mismos contratos que después
   se reportan como fuera de muestra. **Oro ya no tiene un OOS fuera del holdout.**
3. **La falsación de la hipótesis tendencial usa la muestra de test.** El acta cita
   `TREND_EMA_200` a 150 ticks con −$50.008 OOS; esa misma celda da **+$24.688 IS**. A
   150 ticks el contraste se da vuelta en 14 de 20 celdas.
4. **Faltaba el costo de entrada.** Se cobraba comisión y 1 tick en el stop, pero la
   entrada se llenaba gratis al cierre de barra.
5. **88 celdas, no 5**, sin corrección por multiplicidad, sin IC, sin bootstrap, sin
   MCPT. Con ~11% de win rate los $21.000 los producen unos 30 trades.

**Re-corrida cobrando el tick de entrada (ejecutada).** Parche verificado primero: con
`ENTRY_SLIP_TICKS=0` reproduce el JSON original en **440 campos, 0 diferencias**.

| | celdas | positivas IS | positivas OOS | contraste `REV−TRD` estable |
| :-- | --: | --: | --: | --: |
| 25 ticks | 44 | **4** | 33 | **18 / 20** |
| 150 ticks | 44 | **0** | 18 | 3 / 20 |

`REVERT_EMA_200` a 25 ticks pasa de +$8.476 a **+$646 en 783 trades** (+$0,83 por
trade). A 150 ticks el control pasa de +$42.652 a −$8.478 OOS.

**Veredicto.** Muere la rentabilidad absoluta. Sobrevive, y sin tamaño confiable, una
regularidad condicional: a 25 ticks las entradas tomadas **contra** la EMA rinden más
por trade que las tomadas a favor, con el mismo signo en los dos períodos.
**Ojo:** el tick de entrada **no podía tocar** ese contraste — un costo constante por
trade se resta de los dos lados y se cancela en la diferencia. No leerlo como
confirmación.

**Reproducción:** worktree `E:/EdgeLab_worktrees/ema-audit-20260906` en `e50bbf3`, con
`tools/optimize_bigtrap_gc_ema.py` parcheado con la variable de entorno
`ENTRY_SLIP_TICKS`. `psutil` no está en el `.venv` y se neutralizó (sólo imprimía RAM).

**Antes de optimizar nada de esto:** bootstrap clusterizado por sesión sobre el
contraste, congelar una configuración por argumento y no por ranking, y conseguir OOS
nuevo con contratos de Oro anteriores a `GC 12-25`. El holdout `GC 08-26` se abre una
sola vez, al final.

---

## 3. Otras cosas de esta sesión

**`nt8/CleanImpulses.cs`** — clon literal de `HFTZonesNQPureV4` con la detección
intacta, más una función agregada: marca impulsos limpios. Los tramos los delimitan los
**nacimientos de zona**; entre dos nacimientos se mide la **altura** (máximo alto −
mínimo bajo) y se marca si supera `MinLegTicks` (6). La forma del impulso no interviene.

Historia útil para no repetirla: un port a mano de la detección compiló, corrió y dio
**cero zonas** donde el original daba muchas. Por eso ahora es un clon y no un port. Y
la regla estuvo mal aplicada tres veces por composición de filtros: percentil antes del
filtro de vacío (vacía la población por construcción), y unidad de análisis equivocada
(pivotes de 3 barras parten una escalera y dejan pasar picos de 2 barras).

**Pendiente sin validar:** Nico no confirmó todavía que lo que marca coincida con lo
que él llama un impulso.

---

## Aporte al referente

Deja asentado el plan de medición del único objeto vivo (clusters HFT), con su nulo
cerrado y su cuello de botella identificado antes de gastar una sola medición; y cierra
la línea EMA-GC en el tamaño que realmente tiene, evitando que se optimice sobre una
expectativa que dependía de que la entrada fuera gratis.
