# IVC-L — horizonte largo con años de historia (proxies ETF): resultados (2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pre-registro:** `docs/research/MANIFIESTO_IVC_LARGO_20260926.md` (escrito antes de medir).
**Herramienta:** `tools/ivc_largo.py` (prueba nula sobre random walk: 0 FDR, 0 prometedoras).
**Artefactos:** `artifacts/ivc/ivcl_celdas.csv`, `artifacts/ivc/ivcl_resumen.json` (sha256 de las fuentes).
**Cerebro:** `artifacts/hippocampus/ivc_20260926.jsonl`: partición `P-IVCL-EXP`, `OBS-IVCL-20260926`, 2 lecciones.

**Datos.** Yahoo diario: SPY desde 1993, QQQ desde 1999 y DIA desde 1998, todos hasta 2026-03-31, sin días
ex-dividendo. SPY 1 min, 2008-01 a 2021-05: 3.294 días. Se eliminaron 638.054 filas duplicadas idénticas (en 724
días) y se verificó que no hubiera minutos repetidos con valores distintos. Costo: 1,5 pb ida y vuelta; sensibilidad a 3 pb.

## Resultado: 8 celdas, 4 FDR, 0 prometedoras

| Celda | IC desc. (p) | IC val. | Borde desc. / val. (pb) | Margen val. IC inf. | FDR |
|---|---|---|---|---|---|
| SPY diario: gap → apertura-cierre | 0,005 (0,75) | 0,029 | −1,6 / 0,1 | −4,2 | no |
| QQQ diario: gap → apertura-cierre | 0,006 (0,73) | 0,013 | −3,5 / 0,1 | −4,8 | no |
| DIA diario: gap → apertura-cierre | 0,023 (0,17) | 0,023 | −0,5 / −0,6 | −5,3 | no |
| SPY 1m: primera ½ h → última ½ h | 0,044 (0,08) | −0,021 | 0,8 / −0,4 | −3,0 | no |
| SPY 1m: gap → última ½ h | 0,097 (0,000) | −0,028 | 4,6 / −1,0 | −3,9 | sí |
| SPY 1m: primera ½ h → 10:00-15:30 | 0,060 (0,013) | 0,039 | 3,6 / 1,0 | −4,1 | sí |
| SPY 1m: gap → primera ½ h | −0,051 (0,034) | −0,006 | 3,3 / 1,8 | −1,6 | sí |
| **SPY 1m: gap → 10:00-cierre** | **0,080 (0,0015)** | **0,050** | **7,9 / 1,8** (extremos 14,4 / 9,5) | −3,9 | sí |

## Lectura

1. **El gap diario no dice nada del día.** Con ~30 años en los tres índices, el IC entre el gap y el retorno de
   apertura a cierre es ≈ 0 (MDE ~0,03). La pista F4 de la campaña de ticks (cierre del gap por toque) no tiene apoyo
   direccional en el proxy. Alcance: no se midió la probabilidad de tocar el cierre previo, que es otro estimand.
2. **Las celdas FDR están concentradas en 2008–2014** (IC de la década del 2000: 0,12–0,14) y en validación se
   debilitan o cambian de signo. La mayor parte es régimen de crisis, no una regularidad estable.
3. **Una sola pista con el mismo signo en las dos mitades: el gap predice la continuación de 10:00 al cierre.**
   IC 0,080 en descubrimiento y 0,050 en validación; por década 0,12 / 0,05 / 0,12; borde en validación de 1,8 pb en
   promedio y 9,5 pb en los días de gap extremo. No es prometedora: el margen de validación cruza cero. Queda como
   sugerencia para re-medir en ES/NQ/YM con datos de NT8.
4. **El tamaño del gap predice cuánto se mueve el día** (IC no direccional 0,24–0,30, estable). Sirve para
   dimensionar, no para dirección.

## Qué implica

Con años de historia, las pistas de horizonte largo del proyecto **no se sostienen como edge**: el gap no predice el
día, y el momentum de la última media hora no aparece en SPY 2008–2021. Queda una única pista direccional, que
tampoco supera el costo en validación. El mapa completo (IVC + IVC-L) no tiene todavía una celda que justifique
pre-registrar una regla.

## Cómo podría refutarse

Con datos de futuros (ES/NQ/YM de NT8, varios años), la continuación del gap de 10:00 al cierre superaría el costo
con IC inferior > 0 en una muestra fuera de la usada acá.
