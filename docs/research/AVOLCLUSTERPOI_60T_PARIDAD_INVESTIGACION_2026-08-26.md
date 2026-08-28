# aVolClusterPOI 60t — investigación de paridad NT8↔Python: dos hipótesis refutadas, causa abierta

- **Fecha**: 2026-08-26 · **Estado**: `MEASURED_COMMITTED`, `PARITY_PARTIAL_UNEXPLAINED`
- **No es un PASS.** Este documento existe para que nadie declare paridad firmada sobre
  este resultado sin leer que la causa del faltante sigue sin identificarse.
- Oráculo: `E:\DatosNT8\avolcluster_gc0426_60t_oracle.csv` — GC 04-26, 60 ticks, exportado
  por NT8, 180 `ZONE_CREATED` (OFF_PRICE), ventana comparada 2026-01-30 → 2026-03-26.
- Commits: `919ff35` (ART→UTC + refutación de warmup), `bfddd16` (refutación de ancla de sesión).

---

## 1. Línea de tiempo de la investigación

| Paso | Quién | Resultado | Match rate |
|---|---|---|---:|
| Export inicial + comparación en frío | Antigravity | Python arranca `SessionProfile` en frío al inicio de la ventana | **126/180 = 70,0%** |
| Hipótesis A: warmup insuficiente | Antigravity propuso, Claude probó | — | (sin probar todavía) |
| **Bug real encontrado**: timestamps del oráculo en hora ART, no UTC | Claude | Sin corregir, el comparador daba 0% — no era el warmup, era el comparador | 0% (bug, descartado) |
| Hipótesis A probada con el bug corregido | Claude | 114 sesiones reales de calentamiento (cinta completa desde 2025-10-10) | **123/180 = 68,3%** — **IGUAL o PEOR** que sin warmup |
| **Hipótesis A: REFUTADA** | — | El calentamiento no explica el faltante | — |
| Hipótesis B: ancla del bucket horario (`sessionBegin`) | Antigravity, verificado contra `nt8/aVolClusterPOI.cs:295` | `sessionBegin = sessionIterator.ActualSessionBegin` (17:00 CT oficial), NO el primer trade — discrepancia real con el script anterior | (sin probar todavía) |
| Hipótesis B probada, con `edgelab.bridge.sessions.session_begin_ns()` (validada 7/7) | Claude | — | **123/180 = 68,3% — IDÉNTICO byte a byte** (mismo `n_matched`, mismo desglose por sesión) |
| **Hipótesis B: REFUTADA** | — | El ancla de sesión no mueve ni un solo match | — |

## 2. Lo que SÍ está confirmado

Sobre las **123 zonas que coinciden**: precio (`lower_tick`/`upper_tick`), volumen (`score`)
y timestamp de cierre son **idénticos al tick y al milisegundo** en el 100% de los casos
(`delta_seconds_mediana = 0.0`, `delta_seconds_max = 0.0`). El kernel Python replica el
mecanismo de detección real del `.cs` — esto no está en duda.

## 3. Lo que NO está explicado

**57 de 180 zonas del oráculo no tienen ninguna zona Python equivalente dentro de
±2 segundos, y viceversa para 39-40 de las zonas de Python.** El desglose sesión por
sesión (`docs/research/avolcluster_60t_paridad_warmup_gc0426.json#por_sesion`) no
muestra ningún patrón temporal: el acierto salta entre 0% y 100% a lo largo de las
43 sesiones sin tendencia — no es "las primeras sesiones peor" (warmup) ni concentrado
en sesiones específicas de forma obvia.

**Candidatos NO probados todavía**, en orden de sospecha:

1. **Interpolación del cuantil**: `EmpiricalQuantile` en el `.cs` vs `empirical_quantile`
   en Python — ambos dicen implementar "sin interpolación" pero un desacuerdo de un
   solo tick en el umbral, en un score que ronda ese umbral, decide pass/fail.
2. **Desempate en `median_upper`/mediana**: comportamiento distinto ante empates exactos
   entre `.cs` (`double`) y Python (`float`) — aritmética de punto flotante entre dos
   lenguajes nunca es garantía de bit-a-bit sin verificarlo.
3. **Diferencia real en los datos de origen**: el feed que alimentó al `.cs` en vivo/replay
   de NT8 podría no ser byte-idéntico a `GC 04-26.Last.txt` — ya documentado como patrón
   conocido en este proyecto (ES: 0,8% de diferencia en conteo de trades entre export de
   ticks y dump NRD).
4. **Qué cuenta como "sesión completa" para el FIFO de `lookback_sessions`**: si NT8
   descarta sesiones irregulares (fin de semana, feriados, sesiones truncadas) que este
   script cuenta igual, la composición del historial difiere sin que el ancla ni el
   warmup-en-cantidad tengan la culpa.

## 4. Decisión (Nico, 2026-08-26)

**No se sigue cavando ahora.** Las dos hipótesis más plausibles y más baratas de probar
ya se probaron y fallaron. La causa real requiere un diagnóstico quirúrgico (un bloque
específico, valores intermedios lado a lado NT8↔Python) que no vale la pena todavía
frente a la cola de trabajo pendiente — la meseta + placebo (`AVOLCLUSTERPOI_RESOLUCION_RESULTADO_2026-08-26.md`)
ya dan evidencia independiente de estructura real (55× sobre el placebo), así que el
68% de paridad no bloquea seguir explorando target-free.

**Lo que SÍ queda bloqueado**: declarar paridad firmada estilo `HFTZones2`/`VolTicksPOC2`
(PASS, 0 diffs) sobre `aVolClusterPOI` en 60 ticks. Ese estado no se alcanzó.

## 5. Cómo se refutaría este cierre

Si alguien retoma esto y encuentra la causa real con el diagnóstico quirúrgico de §3,
este documento se actualiza (no se reescribe silenciosamente) con la causa confirmada
y, si corresponde, se recorre la paridad de nuevo para intentar el PASS completo.

## Aporte al referente

Cero directo — esto es integridad de instrumento, no medición de edge. El aporte es
negativo y útil: dos explicaciones plausibles quedaron descartadas con evidencia, no
con intuición, así que nadie va a re-proponerlas creyendo que son la respuesta.
