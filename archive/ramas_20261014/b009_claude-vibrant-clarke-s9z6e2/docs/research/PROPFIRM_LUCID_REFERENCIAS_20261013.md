# Referencias de Lucid para el mandato (crawl del 2026-10-13)

**Qué existía:** un scraper y analizador completo en la rama `feat/propfirm-ev-20260926` (`edgelab/propfirm/`: `scraper.py`, `crawl.py`, `taxonomy.py`, `rules.py`, `ev.py`, `requirements.py`; datos en `config/propfirms/`; diseño en `docs/research/PROPFIRM_EV_DISENO_20260926.md` y `PROPFIRM_REGLAS_DETALLADAS_20260926.md`). **No estaba en esta rama ni en main**: lo traje tal cual (12 tests pasan) y lo uso. No hacía falta un scraper nuevo.
**Qué hice:** re-corrí el crawler de Lucid (61 páginas leídas, 338 oraciones con reglas; la corrida del 2026-09-26 tenía 59 y 307: las reglas cambiaron), leí las páginas de LucidFlex/Pro/Daily/Black y armé `config/propfirms/catalogo_lucid_50k.json` (Flex y Pro, `verified: false`). `tools/propfirm_refresh.py` compara el crawl contra una línea base (`config/propfirms/lucid_pages_sha.json`) y avisa si cambió alguna página.

## Productos (cuenta de 50K; todos con evaluación sin límite de tiempo y pago único)
| | LucidFlex | LucidPro | LucidDaily | LucidBlack |
|---|---|---|---|---|
| Objetivo / piso (MLL) | 3.000 / 2.000 | 3.000 / 2.000 | 3.000 / 2.000 | 3.000 / 2.000 |
| Drawdown | fin de día (EOD), bloqueo en saldo + 100 al superar 52.100 | EOD (igual) | a elección: intradía (más barato) o EOD | (ver páginas) |
| Límite diario en la evaluación | no (opcional al comprar) | 1.200 | — | no |
| Consistencia en la evaluación | 50 % (mayor día / beneficio) | no | 50 % | 60 % |
| Tamaño máx. | 4 minis o 40 micros | igual | igual | igual |
| Funded | sin consistencia, 90/10, DLL opcional, escalado de contratos por beneficio, retiros: 5 días con ≥ 150, neto positivo, mín. 500, máx. 50 % hasta 2.000, hasta 5 retiros y luego Live | DLL opcional, sin escalado, retiros con consistencia 40 % del ciclo, meta 500, colchón MLL+100, máx. 2.000 el primero y 2.500 del segundo en adelante | retiros diarios, noticias de alto impacto USD prohibidas (flat ±1 min) | — |
Fuentes: `support.lucidtrading.com/en/articles/` — `12945790-lucidflex-evaluation-account`, `12945815-lucidflex-drawdown`, `12945796-lucidflex-payouts`, `12890029-lucidpro-evaluation-account`, `12890092-lucidpro-payouts`, `15996664-luciddaily-evaluation`, `13424894-lucidblack-evaluation-account`, `11404729-allowed-trading-times`, `11404617-maximum-number-of-accounts`.

## Reglas de conducta
Cierre antes de las 16:45 ET (15:45 CT); HFT y microscalping prohibidos (se marca si > 50 % de las ganancias vienen de operaciones de ≤ 5 s); cobertura entre cuentas prohibida (incluye cuentas propias); noticias permitidas en Flex/Pro/Direct y prohibidas en Daily; se puede escalar entradas/DCA; hasta 10 cuentas de evaluación y 5 fondeadas por hogar.

## Control sin ventaja (1 contrato, costo de ida y vuelta USD 4,80, `ev.report`, eval sin límite)
| Bracket | operaciones/día | pase sin ventaja |
|---|---:|---:|
| TP = SL = 100 | 2 | 3,5 % |
| TP = SL = 200 | 2 | 15,9 % |
| TP = SL = 60 | 4 | 0,1 % |
Techo geométrico (sin costos ni trailing): 40 %. Lección del diseño previo (Hall 2026): pasar la evaluación no prueba habilidad; hay que comparar con el mismo pipeline sin ventaja y mirar la compuerta de pago.

## Qué no sabemos (a completar por una persona)
Precio de la evaluación y del reset (no está en el centro de ayuda); qué producto se usa; si la regla de retiro es sobre beneficio del ciclo o total; número exacto de días mínimos de la evaluación (se asume 2 por el «pase en dos días»).

## Cómo refrescar
`python tools/propfirm_refresh.py` (compara contra la línea base y escribe `RULES_CHANGED` si hay cambios); `--accept` toma el crawl actual como línea base tras revisar los cambios. En el Debian corre semanalmente (`edgelab-propfirm-refresh.timer`).
