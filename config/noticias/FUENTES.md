# Fuentes del calendario de noticias USD (`calendario_usd_tier1.csv`)

Estado: VIGENTE
Fecha: 2026-10-25 (todas las consultas de este documento son de esta fecha)
Familia / módulo: `costos` (`config/modules.json`) — `edgelab/noticias.py`
Procedencia: transcripciones en `config/noticias/crudo/`; el CSV se regenera con `python tools/noticias_calendario.py`
(y `--check` verifica que el CSV committeado sale de esas transcripciones; lo corre `tests/test_noticias.py`).

## Para qué

Pedido de Nico (2026-10-25): «las operaciones no pueden ser durante noticias, por fricciones y por reglas de prop
firms». El CSV da el minuto exacto (UTC) de cada publicación USD de alto impacto entre 2023-01-01 y 2026-12-31.
Hora ET → UTC con `zoneinfo("America/New_York")` (EST/EDT lo resuelve la zona). Columnas: `ts_utc` (ISO al minuto,
sufijo Z), `evento`, `fuente_url`, `impacto` (`tier1` / `tier2`).

## Qué es tier1

La regla numérica más estricta del catálogo de firmas que admiten algoritmos es la de **LucidDaily fondeada**:
plano desde 1 minuto antes hasta 1 minuto después de toda noticia `Impact = High`, `Currency = USD` (carpeta roja de
ForexFactory) — `artifacts/propfirm/crawl/Lucid/inventario.md` línea 849. TakeProfitTrader PRO pide lo mismo sólo para
FOMC (14:00 ET), NFP y CPI (`artifacts/propfirm/crawl/TakeProfitTrader/inventario.md`). Tier1 = la lista mínima del
pedido, que ForexFactory marca `high` en todas las muestras consultadas: CPI, NFP, PPI, FOMC (decisión, conferencia,
minutas), Retail Sales, PIB (avance/segunda/tercera), PCE/Personal Income, ISM Manufacturing y Services, JOLTS,
testimonio semestral y Jackson Hole del presidente de la Fed.

**Tier2 = Initial Jobless Claims.** ForexFactory los marca `high` sólo en algunos tramos (medium hasta 2023-03-09, el
2023-12-28, el 2025-07-03 y desde 2026-04-09; high en el resto de 2023-03-16 → 2026-04-02). Para cumplir LucidDaily
literal en los tramos rojos: `impactos=("tier1", "tier2")`.

**No incluido (y LucidDaily sí lo bloquearía si FF lo marca rojo):** ADP, Average Hourly Earnings/Unemployment Rate
(salen junto con NFP, mismo minuto), Core PCE (mismo minuto que Personal Income), Flash PMI de S&P Global, UoM
Consumer Sentiment, CB Consumer Confidence, Durable Goods, Empire State, ECI y discursos sueltos del presidente de la
Fed o de otros miembros del FOMC. Son candidatos a una ampliación; no están fechados acá.

## Fuentes por evento

| Evento (`evento`) | Fuente | URL | Hora ET | Notas |
|---|---|---|---|---|
| `CPI`, `NFP_EMPLOYMENT_SITUATION`, `PPI` | BLS, «Schedule of Selected Releases» por año (vía Firecrawl; bls.gov devuelve 403 a curl) | https://www.bls.gov/schedule/2023/home.htm, `/2024/`, `/2025/`, `/2026/` | 08:30 | La página 2025 está revisada tras el cierre de gobierno (Last Modified 2025-11-20 / 2025-12-11): trae las fechas efectivas, no las originales. |
| `JOLTS` | BLS, ídem | ídem | 10:00 | |
| `FOMC_DECISION`, `FOMC_PRESS_CONFERENCE`, `FOMC_MINUTES` | Federal Reserve, FOMC calendars | https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm | 14:00 / 14:30 / 14:00 | Decisión = 2.º día de la reunión. Horas verificadas en ForexFactory (2024-01-31 y 2026-09-16: Statement 13:00 CT, Press Conference 13:30 CT). Las minutas de dic-2022 (publicadas 2023-01-04) están incluidas. |
| `GDP_ADVANCE/SECOND/THIRD` y `PCE_PERSONAL_INCOME_OUTLAYS` 2023 | BEA, 2023 News Release Schedule (PDF) | https://www.bea.gov/sites/default/files/2022-10/2023-News-Release-Schedule.pdf | 08:30 | Programa publicado en oct-2022; verificado puntualmente (GDP Q2-2023 segunda, 2023-08-30 08:30 EDT, coincide con el comunicado). |
| ídem 2024 | BEA, 2024 News Release Schedule (PDF) | https://www.bea.gov/sites/default/files/2024-06/2024-News-Release-Schedule.pdf | 08:30 (PIO 2024-11-27: 10:00) | Programa (revisión jun-2024). |
| ídem 2025-2026 | BEA, `release_dates.json` (oficial, en UTC) + títulos de https://www.bea.gov/news/schedule/full-2025 y /full | https://apps.bea.gov/API/signup/release_dates.json | según JSON (08:30; PIO 2025-04-30, 2025-12-05 y 2026-01-22 a las 10:00) | Cierre de gobierno: el avance del PIB Q3-2025 (2025-10-30) no se publicó; salió como `GDP_INITIAL` (2025-12-23) y `GDP_UPDATED` (2026-01-22). Q4-2025 se corrió a feb/mar/abr-2026. |
| `RETAIL_SALES` | Census, Economic Indicator Calendar por año | https://www.census.gov/economic-indicators/calendar-listview-2023.html (…-2024, -2025, -2026) | 08:30 | Advance Monthly Sales for Retail and Food Services. 2025 sin oct (cierre); 2026 trae 13 (nov-2025 salió el 2026-01-14). |
| `ISM_MANUFACTURING_PMI`, `ISM_SERVICES_PMI` 2026 | ISM, Report Release Date Calendar (vía Firecrawl) | https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/ | 10:00 | El ISM sólo publica el calendario del año en curso. |
| ídem 2023-2025 | ForexFactory, historial del indicador (`event_history`, Firecrawl Alexandria `forexfactory-com`) | https://www.forexfactory.com/calendar/252-us-ism-manufacturing-pmi, …/253-us-ism-services-pmi | 10:00 (regla del ISM; FF muestra 9:00 CT en las muestras) | **No es fuente oficial**: el ISM no publica calendarios de años pasados. FF es la fuente que citan Lucid y TakeProfitTrader para sus reglas. |
| `INITIAL_JOBLESS_CLAIMS` (tier2) | ForexFactory, historial (`event_history` 136523, 136564, 147020) | https://www.forexfactory.com/calendar/11-us-unemployment-claims | 08:30 | dol.gov devuelve 403. Sin publicaciones entre 2025-09-25 y 2025-11-18 (cierre); el 2025-11-18 y el 2025-11-20 salieron semanas atrasadas en lote. |
| `FED_CHAIR_TESTIMONY` | Fed `ne-testimony.json` (hora de publicación del texto) + ForexFactory (audiencias de los dos días, 10:00 ET) | https://www.federalreserve.gov/json/ne-testimony.json; páginas `/newsevents/testimony/powell20230307a.htm` etc.; FF por evento | 08:30 (texto, cuando la Cámara va primero) y 10:00 (audiencias) | Una fila por instante distinto: texto + día 1 + día 2. |
| `FED_CHAIR_JACKSON_HOLE` | Fed `ne-speeches.json` | https://www.federalreserve.gov/json/ne-speeches.json; `/newsevents/speech/powell20230825a.htm`, `…20240823a`, `…20250822a`, `warsh20260828a` | 10:05 (2023), 10:00 | |

Transcripción: `crudo/bls_<año>.txt` (fechas BLS), `crudo/oficiales_extraidos.txt` (extraído por script de los HTML/JSON/PDF
de Fed, BEA y Census; los originales no se versionan), `crudo/ff.txt` (ForexFactory), `crudo/manual.txt` (ISM 2026,
etiqueta de la estimación del PIB 2025-2026, audiencias de testimonio).

## Cobertura (filas por evento y año)

| evento | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|
| CPI | 12 | 12 | 11 | 12 |
| NFP_EMPLOYMENT_SITUATION | 12 | 12 | 11 | 12 |
| PPI | 12 | 12 | 10 | 13 |
| JOLTS | 12 | 12 | 11 | 12 |
| FOMC_DECISION / FOMC_PRESS_CONFERENCE | 8 / 8 | 8 / 8 | 8 / 8 | 8 / 8 |
| FOMC_MINUTES | 8 | 8 | 9 | 6 |
| RETAIL_SALES | 12 | 12 | 11 | 13 |
| GDP_ADVANCE / SECOND / THIRD | 4/4/4 | 4/4/4 | 3/3/3 (+ INITIAL) | 4/4/4 (+ UPDATED) |
| PCE_PERSONAL_INCOME_OUTLAYS | 12 | 12 | 10 | 13 |
| ISM_MANUFACTURING_PMI / ISM_SERVICES_PMI | 12 / 12 | 12 / 12 | 12 / 12 | 12 / 12 |
| FED_CHAIR_TESTIMONY (filas) | 5 | 5 | 5 | 3 |
| FED_CHAIR_JACKSON_HOLE | 1 | 1 | 1 | 1 |
| INITIAL_JOBLESS_CLAIMS (tier2) | 52 | 52 | 47 | 42 |

Total: 736 filas (543 tier1, 193 tier2).

## Qué faltó (no se inventó)

1. **Cierre de gobierno oct-nov 2025:** CPI de octubre-2025 (cancelado), Employment Situation de oct-2025, JOLTS de
   sept-2025, PPI de oct-2025, Retail Sales y Personal Income de oct-2025 y el avance del PIB Q3-2025 no tienen fila
   propia: o no se publicaron o se publicaron combinados con el mes siguiente (la fila es la de la publicación
   combinada). Las solicitudes semanales del 2025-10-02 al 2025-11-13 no se publicaron.
2. **Solicitudes semanales desde el 2026-10-29:** ForexFactory sólo tiene historial hasta el 2026-10-22; las futuras
   no se fecharon (son todos los jueves 08:30 ET salvo feriados, pero eso es una regla, no una fuente).
3. **Minutas del FOMC de las reuniones del 27-28 oct y 8-9 dic de 2026:** la Fed no las fecha todavía (se publican
   tres semanas después de cada reunión).
4. **Testimonio semestral del 1.er semestre de 2026:** `ne-testimony.json` no trae un «Semiannual Monetary Policy
   Report» entre ene y jun de 2026 (año de transición de presidente: Powell → Warsh); sólo el del 2026-07-14/15.
5. **Hora de la publicación en lote del 2025-11-18 (claims):** se asumió 08:30 ET como el resto; no verificada.
6. **BEA 2023-2024:** son los programas oficiales publicados (PDF); no se cotejó cada comunicado. 2025-2026 sí son
   fechas efectivas (JSON y páginas revisadas tras el cierre).
7. **Futuros (nov-dic 2026)** de BLS, BEA, Census, ISM y FOMC son programas oficiales vigentes al 2026-10-25: pueden
   moverse; regenerar con las mismas fuentes antes de usarlos en vivo.
8. Discursos del presidente de la Fed fuera de testimonio y Jackson Hole (FF los marca `high`) no se incluyeron.

## Cómo actualizar

Agregar las fechas nuevas al archivo de `crudo/` que corresponda (con la URL y la fecha de consulta en el
comentario), correr `python tools/noticias_calendario.py`, y `python -m pytest tests/test_noticias.py -q`.
