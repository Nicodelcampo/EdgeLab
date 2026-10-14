# GC: presión, avance y trayectorias — V2 sobre la release canónica — manifiesto — 2026-10-14

Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. Estado: **PRE-REGISTRADO, escrito antes de leer ninguna estadística de avance o presión sobre la release**.
Lo único que se corrió antes: un conteo de rendimiento (anclas y estados de ventana, sin ninguna medida de progreso ni presión) sobre una sola sesión (`trade_date 20260105`).
Autoriza la corrida: Nico (2026-10-14, "correrlo nuevamente"). **Información, no P&L.** Todo resultado es **PROVISIONAL** (release `CANDIDATE_NOT_RESEARCH_APPROVED`).

## 1. Qué es y qué corrige
Reproduce el atlas del agente de Notion (`docs/research/ops/GC_PRESSURE_PROGRESS_PROTOCOL.md`, rama `feat/research-ops-supervisor-mvp`, commit de cierre `5a2bce86`) con **su mismo motor de medición** (`phenomena.py`, copiado sin cambios y con su SHA registrado), y corrige la **capa de datos y de análisis**:
| # | Debilidad del original | Corrección |
|---|---|---|
| 1 | **Datos:** GC_12-26 (contrato diferido, 3–10 de agosto), 6 sesiones. Las 24 h de calendario UTC incluyen la pausa 16–17 CT. | **Release v4 de GC**: el contrato líder causal de cada sesión CME (17:00→16:00 CT), pausa excluida (`outside_regular == False`). 273 sesiones pre-holdout. |
| 2 | **Calibración** con un solo día (31-jul). | Calibración con las **primeras 60 sesiones**, congelada (con SHA) antes de medir el resto. |
| 3 | **Unidad estadística:** se cuentan ventanas (6.581 pares) de 6 sesiones; la independencia efectiva es ≈ 6. | La **sesión es el cluster**: todo intervalo es bootstrap por sesión; se publica el número de sesiones. |
| 4 | **Sin nulo.** "Avance previo → retroceso ≈ avance" no dice nada sin una referencia. | **Placebo de dirección** (permutar la dirección dentro de sesión × fase) y **independencia de marginales** para las tablas. |
| 5 | **Correlación presión–avance absoluto**: la presión (volumen del lado) y el avance absoluto crecen juntos por actividad. | Se reporta además la **correlación parcial** controlando el número de trades de la ventana actual. |
| 6 | "3 excepciones de signo en 24 celdas" sin incertidumbre. | Intervalos por sesión para cada correlación y celda; sin interpretar signos sueltos. |

## 2. Población, partición y separación evento/estado
- **Evento:** ancla = primer print de cada celda de reloj de 5 s; par de ventanas **20 s previos + 20 s actuales** (definiciones y estados `OBSERVABLE/GAP_UNKNOWN/QUOTE_UNKNOWN…` exactamente los del motor original; cobertura de signo ≥ 80 %; sin regla de tick ni "compra por defecto": los prints interiores quedan `UNKNOWN`).
- **Estado:** fase `RTH` (08:30–15:00 CT) / `OTHER`, y dirección del flujo previo (±1). Celdas fase × dirección (4).
- **Alternativas no medidas aquí (se declaran para que no sean herencia):** relojes por volumen o por número de trades en lugar de 5 s; ventanas de 5 s y 60 s (el motor las calcula pero el atlas usa 20 s); estado continuo barra a barra; otros instrumentos.
- **Partición por sesiones cronológicas** (273 sesiones de la v4): **calibración** = sesiones 1–60; **atlas de desarrollo** = 61–180; **SELLADAS** = 181–273 (**no se leen**; reservadas para cualquier evaluación posterior). Holdout (≥ 2026-10-01) no existe en la release.

## 3. Medidas y pruebas (pre-declaradas)
**Descriptivas (sin prueba):** las 20 celdas presión × avance y las 25 trayectorias prior × actual (conteos completos y de ventanas no solapadas ≥ 40 s por sesión); medias y cuantiles 10/25/50/75/90 de los 9 descriptores; tres correlaciones de Pearson (más la parcial por trades); desglose por fase y dirección. Calibración y bins idénticos al original (`pressure_bin_edges` 0,5/1/2 y `progress_bin_edges` −4/−2/2/4 ticks; `searchsorted_right`).
**Información (con prueba), ventanas no solapadas:**
- **P1 — persistencia del flujo en 20 s:** Δ = E[avance dirigido actual] − E[avance dirigido actual bajo placebo]. Primaria: todas las ventanas elegibles. Secundarias: RTH y OTHER por separado.
- **P2 — continuación tras avance previo:** sea d(G) = P(avance dirigido actual ≥ +2) − P(avance dirigido actual < −2) dentro del grupo G de ventanas. P2 = d(avance previo ≥ +4) − d(avance previo pequeño, es decir en [−2, +2)). Es un contraste **interno** (mismo atlas, mismo cluster por sesión): mide si haber avanzado en la ventana previa cambia la distribución de la actual respecto de no haberse movido. No se usa el placebo de dirección acá porque permutar la dirección también cambia qué ventanas pertenecen a cada grupo previo.
- **Número efectivo de pruebas = 4** (P1 primaria, P1 RTH, P1 OTHER, P2). **Holm** sobre las 4. IC 95 % por **bootstrap por sesión** (2.000 remuestreos, semilla `crc32`).
- **MDE:** se publica 2,8 × SE de cada prueba. Un resultado sin MDE no se interpreta como ausencia.
- **Placebo:** dentro de cada sesión × fase se permuta la dirección entre las ventanas no solapadas (misma marginal de direcciones; rompe sólo el vínculo flujo→precio). Semilla `crc32` por sesión.

## 4. Justificación económica
Si el desequilibrio agresivo de las últimas 20 s anticipa el sentido del precio en las 20 s siguientes por **más que el costo de cruzar el spread**, existiría un micro-edge de flujo en GC. Si Δ es indistinguible de cero o menor que ≈ 1 tick (el spread típico de GC es de 1 tick = $10), no hay base económica a ese horizonte, **aunque la correlación sea "significativa"**. Se reporta Δ en ticks y se compara con 1 tick.

## 5. Cómo podría refutarse
- P1: Δ con IC por sesión que incluya 0 y MDE < 1 tick ⇒ **sin persistencia detectable de flujo en 20 s**; la línea se archiva como información negativa.
- P2: IC por sesión de P2 que incluya 0 con MDE < 5 pp ⇒ el avance previo no contiene información sobre la ventana actual más allá del nivel base.
- Si las correlaciones de las celdas se invierten entre mitades del atlas (sesiones 61–120 vs 121–180) ⇒ no son una propiedad estable.

## 6. Pruebas del dataset (efecto colateral útil, no hipótesis)
La misma corrida emite un informe de integridad **independiente de la verificación de la release**, por sesión: contrato único, número de ticks, % de quotes válidos y cruzados/bloqueados, huecos > 10 s en horario regular, horas sin ticks, ticks con timestamps duplicados, saltos de precio > 50 ticks entre ticks consecutivos y distribución de estados de ventana. Un valor anómalo se registra y se explica; no se filtra para mejorar el resultado.

## 7. Límites y NO MEDIDO
Sin P&L, sin costos propios, sin modelo ni ajuste. No se evalúa la partición sellada. La dirección se infiere por cruce de bid/ask sin tick rule (los prints interiores son `UNKNOWN`, por diseño). El reloj RTH 08:30–15:00 CT no certifica el calendario particular de GC. La release es una candidata no aprobada: nada de esto promueve un gate (`G1`/`G2`).
