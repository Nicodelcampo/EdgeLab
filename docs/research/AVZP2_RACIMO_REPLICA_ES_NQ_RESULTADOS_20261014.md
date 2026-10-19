# AVZP2-RACIMO-REPLICA — resultados — 2026-10-14

Manifiesto (escrito antes de abrir datos): `AVZP2_RACIMO_REPLICA_ES_NQ_MANIFIESTO_20261014.md` (commit d80a947d). NORTH_STAR `ed4293b5…a5f8`.
Datos: release `liquid_tick_v1` (CANDIDATE_NOT_RESEARCH_APPROVED), ES y NQ, 5 contratos cada uno (09-25 → 09-26; 12-26 sin sesiones evaluables), barras 25t,
parámetros de la config de Nico. Etapa 1: `tools/avzp2_racimo_replica_stage1.py`; etapa 2: `tools/avzp2_racimo_replica_stage2.py`.
Salidas completas: `avzp2_replica_20261014/` (`salida_ES.txt`, `salida_NQ.txt`, JSON). **Información, no P&L.**
Procedencia: el árbol de research estaba limpio al correr; semillas por `crc32`. Holdout no leído (la release lo excluye).

> **ESTADO: PROVISIONAL.** Todo lo de esta acta se calculó sobre la release `liquid_tick_v1` v3, que está marcada
> `CANDIDATE_NOT_RESEARCH_APPROVED` (política de liquidez, licencia y calendario sin aprobar). La auditoría independiente del
> 2026-10-14 (`docs/infra/LIQUID_RELEASE_INDEPENDENT_AUDIT_20261014.md`) halló defectos de código en el productor de la release;
> medidos, no cambian ninguna sesión ni contrato seleccionados (ver `docs/infra/LIQUID_RELEASE_AUDIT_RESPONSE_20261014.md`),
> pero hasta que la release se apruebe para research estos resultados se conservan como **provisionales** y no se promueven.
> Control a favor: MNQ sobre la release saneada reproduce sus resultados originales (calculados sobre datos sin sanear).

## Veredicto por criterio pre-registrado
| | ES | NQ |
|---|---|---|
| racimos (celda 4/1000/30 … 6/1000/45) | 4.471 – 7.862 | 115 – 1.478 |
| **O5 compresión** (criterio: ≥5 de 7 celdas con β<0 y Holm ≤0,05) | **7/7 → REPLICA** | 4 de 5 evaluables con Holm ≤ 0,05 (no evaluables por n < 150: 6/500/30 n=48 y 6/1000/30 n=115; 5/1000/30 Holm 0,059) → **NO cumple el criterio (≥5 de 7)** |
| **O1 continuación a favor de tendencia, con control** (criterio: ≥4 de 6) | **6/6 → REPLICA** | 4 de 5 evaluables con Holm ≤ 0,05 (4/1000/30: +1,9 pp, Holm 0,27, no significativa) → cumple (≥4 de 6), justo en el umbral |

## ES (potencia alta; MDE O1 ≈ 1,4–2,0 pp)
- **O5:** β −6,1 a −8,0 % de rango (config de Nico 6/500/30: −6,1 %; celdas largas −6,7 a −8,0 %). Misma magnitud que en MNQ (−4 a −10 %).
- **O1 controlado (FE de magnitud de tendencia y momentum):** +4,6 a +6,9 pp en las 6 celdas (MNQ: +4 a +8,5 pp). Sin control: +8,4 a +11,8 pp.
  El control recorta a ≈ la mitad: **la mitad del efecto crudo es momentum**, como se vio en MNQ; el resto es del racimo.
- Todas con Holm < 0,0001 salvo indicación; MDE publicados en el JSON.

## NQ (potencia baja)
- O5: en las 5 celdas evaluables β = −4,9 a −8,8 % (4 con Holm ≤ 0,05; 5/1000/30 con Holm 0,059). La config de Nico (6/500/30) tiene sólo 48 racimos (β +4,2 %, MDE 21 %): **no informa**.
- O1 controlado: +1,9 pp (4/1000/30, n.s.), +5,6 (4/1000/45), +7,2 (5/1000/30), +7,3 (5/1000/45), +7,0 (6/1000/45); 4 con Holm ≤ 0,05. Cumple el umbral de 4 sin margen.
- NQ tiene 3–5× menos racimos que ES porque la misma altura en ticks cubre menos precio relativo: la misma definición en ticks no es la misma geometría.
  **NQ no refuta nada: la falla formal de O5 es de potencia (n 48–1.478).** Tampoco replica con holgura: es consistente en signo, no concluyente.

## Enmienda 1: MNQ canónico y MES (misma corrida, mismo criterio; manifiesto enmendado antes de correr)
| | racimos (celdas largas) | O5 compresión | O1 con control |
|---|---|---|---|
| **MNQ canónico** | 1.140 – 9.056 | **7/7**, −5,9 a −8,2 % (Holm ≤ 0,0012) | **6/6**, +4,6 a +7,9 pp (Holm ≤ 0,0004) |
| MES (mismo subyacente que ES, no cuenta como independiente) | 3.560 – 5.805 | 7/7, −3,9 a −5,6 % | 6/6, +6,1 a +8,8 pp |
- **Control de integridad de datos:** los resultados originales de MNQ (compresión −4 a −10 %, O1 +4 a +8,5 pp) se obtuvieron con exports sin sanear. **Sobreviven sobre la release saneada, con las mismas magnitudes.** Los hallazgos no eran un artefacto de duplicados de huso ni de contratos mezclados.
- La config de Nico (6/500/30) en MNQ canónico queda con 346 racimos (antes 454, por las 20 sesiones de warm-up por contrato) y compresión −7,3 % (Holm 0,0012).
- Con esto, **tres instrumentos con potencia (MNQ, ES, MES; ES y MES comparten subyacente)** replican compresión y continuación; NQ queda sin potencia por geometría de barra.

## Qué cambia
1. **La compresión y la continuación a favor de la tendencia previa dejan de ser una rareza de MNQ**: replican en un segundo instrumento (ES) con potencia, y van en el mismo signo en un tercero (NQ).
2. **La lectura "pausa con inventario" gana evidencia independiente** (otro instrumento, otro año de datos canónicos). Sigue sin ser un edge: nada de esto tiene P&L.
3. Orden de magnitud del activo económico potencial: la continuación controlada ≈ +5–7 pp sobre un 63–80 % base; el recorrido posterior es pequeño por la compresión
   (excursión mediana ≈ 0,25 alturas en MNQ). Si ese recorrido paga los costos de ES es lo que **hay que medir con costos propios** (ver siguiente paso).

## Descriptivo del recorrido en ES (sin P&L; sólo salidas reales con te ≥ 0)
Excursión máxima favorable (MFE) después de la salida, en ticks, antes de volver a cerrar dentro del racimo (celdas 6/1000/30, 6/1000/45, 4/1000/30):
- **A favor de la tendencia previa** (≈ 78–81 % de las salidas): p25 = 1, **mediana = 3**, p75 = 5–6, p90 = 14–15 ticks.
- En contra de la tendencia (≈ 19–22 %): mediana 4, p75 5–6 ticks.
- La MFE es un techo no capturable: un target fijo realiza menos. **Con fricción de ES (≥ 1 tick de spread al entrar a mercado + comisión ≈ 0,3–0,4 tick + slippage en stops) la mediana de MFE casi se agota en costos.**
  Prior honesto: el efecto es real en probabilidad pero **chico en recorrido**; que sea económicamente neto es improbable con entrada a mercado y es una pregunta abierta con entrada pasiva.

## Por qué NQ tiene tan pocos racimos: la barra de 25 operaciones no es la misma barra (medido, sin desenlaces)
Rango mediano de una barra de 25 operaciones (contrato 06-26, release canónica, ≈250–400 mil barras): **ES 1 tick (media 1,66); NQ 11 ticks (media 12,6)**.
Una franja de 30 ticks son ~30 barras de rango en ES y ~3 en NQ: **la definición "en ticks" y la barra "25t" no transportan geometría entre instrumentos**
(el factor para equiparar sería ≈ 7–11×, es decir alturas de 200–330 ticks en NQ, lo que ya es otra hipótesis). Por eso la falla formal de NQ es de geometría/potencia y no un contraejemplo.
Normalizar por conteo es inviable: el rango escala ≈ √n, así que igualar el rango de ES en NQ pediría < 1 operación por barra. Una réplica en NQ requiere **barras de rango constante o de tiempo** (no existen aún en `edgelab.bridge.bars` para este indicador). NO MEDIDO; campaña aparte con su propio manifiesto. El parámetro `AVCL_SPEC` del stage1 queda disponible para ese trabajo.

## Límites declarados
- La release sólo tiene el contrato líder: las primeras 20 sesiones de cada contrato se excluyen (warm-up del umbral de zonas). ES: 193 sesiones evaluables.
- Alturas en ticks, sin reescalar por volatilidad; no se probó (NO MEDIDO).
- `sequence` de la release es índice de fila (P-28); el footprint usa bid/ask del tick.
- Los pseudo-racimos apareados por ocupación previa; sin control por hora de sesión más fino que 30 min ni por evento macro (NO MEDIDO).
- Sin ledger de pruebas adicional: 13 pruebas por instrumento, Holm por instrumento, todas publicadas.

## Siguiente paso (requiere STOP y OK de Nico antes de correr)
Manifiesto de P&L bruto→neto de la regla (a): salida de un racimo largo (≥1.000 velas, 30–45 ticks) a favor de la tendencia de 500 velas, sobre **ES**
(potencia suficiente), con costos propios de ES (spread medido en la release + comisión + slippage), objetivos cortos, simulación tick a tick, sin mirar el holdout.
Ver `AVZP2_PNL_MANIFIESTO_PROPUESTO_20261014.md`.
