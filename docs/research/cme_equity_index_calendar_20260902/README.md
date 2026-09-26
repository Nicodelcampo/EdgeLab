# Calendario CME Equity Index con evidencia — 2026-09-02

**`cme_equity_index_session_calendar_v1.json` valida contra
`edgelab/data/cme_equity_index_calendar.py`.** 322 sesiones (2025-08-01 → 2026-06-18):
220 `NORMAL`, 94 `CLOSED`, 8 `EARLY_CLOSE`. `calendar_sha256`
`1425d7139beef4d1b427ce7de307bfcbb84182b62134b674404e2557b99d3ad5`.

## Cómo se obtuvo la evidencia

CME bloquea el acceso automatizado: `curl` devuelve **HTTP 403** (WAF) para las páginas
HTML y para los PDFs de settlement times, y el fetcher da timeout. Navegando el sitio se
identificó el **endpoint JSON oficial** que la propia página consume:

```
https://www.cmegroup.com/services/trading-hours-by-product?id=...&fromEventDate=YYYY-MM-DD&toEventDate=YYYY-MM-DD
```

Llamado desde el origen `cmegroup.com` responde `200`. Es **mejor evidencia que el PDF**:
datos estructurados por producto y por `tradingDate`, y sirve fechas históricas — con lo
que el tramo 2025 (que la página ya no publica) también quedó cubierto. Producto usado:
**ES, E-mini S&P 500** (`id=133`), mismo grupo Equity Index que NQ y por tanto mismas horas
de Globex. Cada override cita su URL, el **SHA-256 de la respuesta** y `retrieved_at`.

## Feriados congelados

| trade date | clase | cierre CT | feriado |
|---|---|---|---|
| 2025-09-01 | EARLY_CLOSE | 12:00 | Labor Day |
| 2025-11-27 | EARLY_CLOSE | 12:00 | Thanksgiving |
| 2025-11-28 | EARLY_CLOSE | 12:15 | Day after Thanksgiving |
| 2025-12-24 | EARLY_CLOSE | 12:15 | Christmas Eve |
| 2025-12-25 | **CLOSED** | — | Christmas Day |
| 2026-01-01 | **CLOSED** | — | New Year's Day |
| 2026-01-19 | EARLY_CLOSE | 12:00 | Martin Luther King Jr. Day |
| 2026-02-16 | EARLY_CLOSE | 12:00 | Presidents Day |
| 2026-04-03 | EARLY_CLOSE | 08:15 | Good Friday |
| 2026-05-25 | EARLY_CLOSE | 12:00 | Memorial Day |

## Corroboración contra el dato (no inferencia)

El calendario se construyó **sólo** con la fuente oficial. `calendar_vs_observed_v1.json`
lo contrasta después contra los minutos activos observados en el scan v2:

| trade date | esperados | observados | Δ |
|---|---|---|---|
| 2025-09-01 | 1140 | 1140 | **0** |
| 2025-11-27 | 1140 | 1140 | **0** |
| 2025-11-28 | 1155 | 508 | 647 |
| 2025-12-24 | 1155 | 1152 | 3 |
| 2026-01-19 | 1140 | 1140 | **0** |
| 2026-02-16 | 1140 | 1139 | 1 |
| 2026-04-03 | 915 | 909 | 6 |
| 2026-05-25 | 1140 | 1140 | **0** |

Siete de ocho coinciden dentro de 0–6 minutos, y el patrón de **1140 minutos** que el scan
había detectado queda explicado: es el early close de las **12:00 CT**. Christmas, marcado
`CLOSED` por la fuente, aparece con 1 tick residual.

La excepción es **2025-11-28**: la fuente muestra un patrón discontinuo para ese trade date
(`07:00 preopen`, `07:30 open`, `12:15 closed`), es decir la sesión **no** corrió de forma
continua desde las 17:00 del día anterior. Los 508 minutos observados son consistentes con
esa interrupción, pero el modelo de sesión continua del calendario no la representa.
Queda anotado, no resuelto.

## Lo que falta

**2026-06-19 (Juneteenth) no está resuelto.** La respuesta del endpoint es ambigua para ese
trade date (`2026-06-22 12:00 closed`, y el 18-jun salta directo al open del 22), lo que
sugeriría mercado cerrado — pero el dato observado tiene **115.146 ticks y 1320 minutos
activos** en NQ 09-26 ese día. La discrepancia no se adjudica acá.

Por eso el calendario se emite hasta **2026-06-18**. Construirlo hasta 2026-06-30 con
Juneteenth en `holiday_review_dates` **falla a propósito** (`feriados sin override:
[20260619]`) — fail-closed verificado.

El rango emitido cubre íntegramente el intervalo operable de NQ 06-26 (2026-03-17 →
2026-06-16) y el roll del 16-jun, que es lo que EF0 necesita.
