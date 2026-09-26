# GEX — fuentes y primer gate (2026-08-13)

Estado: `DRAFT_NON_EXECUTABLE`
Hermana de F2.7–F2.10. No adjudica. No toca ticks de 6E.

## Decisiones que se mantienen

- Datos públicos oficiales o datasets libres documentados. Vendors sólo como idea.
- Resolución **diaria**, no radar intradía.
- Primer éxito: **reproducir agregados oficiales desde crudo**. Paridad antes de interpretar gamma.
- Instrumento primario: 6E. Calibración: ES/NQ, SPY/QQQ.
- W2 sigue bloqueado si no hay texto estable del Daily Bulletin. No inventar números desde PDF binario a ojo.

## Fuentes oficiales localizadas

CME publica el Daily Bulletin como PDF, no como CSV:

- Índice: https://www.cmegroup.com/market-data/daily-bulletin.html
- FX volume/OI (01B): https://www.cmegroup.com/daily_bulletin/current/Section01B_Summary_Volume_And_Open_Interest_FX_Futures_And_Options.pdf
- Equity index (01C): …/Section01C_Summary_Volume_And_Open_Interest_Equity_Index_Futures_And_Options.pdf
- Final ≈ 10:00 a.m. CT del día hábil siguiente (wiki de clientes CME).

Eso desbloquea el *inventario* de W2. No desbloquea todavía un parser: el archivo es PDF.

## Primer gate ejecutable (aún no corrido)

`GEX-M0` — paridad de **volumen y open interest** de 6E (y ES/NQ) contra 01B/01C.

1. Bajar el PDF `current` de 01B.
2. Extraer texto (pdftotext), no “leer el dibujo”.
3. Parsear filas FX: contrato, volume, OI.
4. Comparar contra un fixture sellado o contra la misma página al día siguiente.
5. Si el texto no es estable: `ABSTAIN_SOURCE`. Cero números inventados.

Hasta que GEX-M0 pase, no hay pin, no hay gamma flip, no hay cruce con aVol ni BigTrap2.

## Qué no es GEX todavía

- SpotGamma / SqueezeMetrics como verdad.
- Intradía.
- Hedging interpretado sin paridad de OI.
- Subir Market Data de CQG a Kaggle.
