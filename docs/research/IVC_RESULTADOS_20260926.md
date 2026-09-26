# IVC — mapa de información contra costo por horizonte: resultados (2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pre-registro:** `docs/research/MANIFIESTO_MAPA_INFO_COSTO_20260926.md` (con la enmienda §8, escrita antes de medir).
**Kernel:** Kaggle `edgelab-ivc-mapa` (ES 181, NQ 171, YM 161 sesiones; jul-2025 a mar-2026). Abr–jun y holdout sin leer.
**Artefactos:** `artifacts/ivc/ivc_mapa.csv`, `artifacts/ivc/ivc_resumen.json`.
**Cerebro:** `artifacts/hippocampus/ivc_20260926.jsonl` — partición `P-IVC-EXP` (declarada antes de medir),
observación `OBS-IVC-MAPA-20260926` (diseño `OTHER`: estado en grilla contra nulo entre sesiones) y 2 lecciones.

## Resultado

**477 celdas, 38 con FDR (q = 0,10), 0 prometedoras** (ninguna supera el costo con IC inferior > 0 en descubrimiento
y se sostiene en validación). Mediana por instrumento y horizonte, canal direccional:

| Inst. | Horizonte | \|IC\| mediano | MDE del IC | Borde bruto mediano (t) | Costo agresivo (t) | Celdas FDR |
|---|---|---|---|---|---|---|
| ES | 1–15 min | 0,008–0,015 | 0,013–0,021 | 0,09–0,13 | 2,47 | 13 |
| ES | 60–240 min | 0,014–0,015 | 0,036–0,043 | 0,6–1,5 | 2,47 | 0 |
| ES | cierre | 0,008 | 0,070 | 1,8 | 2,42 | 0 |
| NQ | 1–15 min | 0,009–0,014 | 0,015–0,025 | 0,4–1,6 | 6,5 | 7 |
| NQ | 60–240 min | 0,013–0,017 | 0,034–0,043 | 3,4–5,1 | 6,5 | 0 |
| NQ | cierre | 0,008 | 0,084 | 10,0 | 4,5 | 0 |
| YM | 1–15 min | 0,013–0,014 | 0,015–0,026 | 0,15–0,41 | 4,9 | 17 |
| YM | 60–240 min | 0,014 | 0,043–0,056 | 0,7–2,7 | 5,0–5,2 | 1 |
| YM | cierre / última ½ h | 0,023 / 0,073 | 0,081 / 0,234 | 4,6 / 9,6 | 3,7 / 3,4 | 0 |

## Lectura

1. **Horizonte corto: hay información y no paga.** Las 38 celdas con FDR son casi todas reversión de corto plazo
   (momentum y flujo de órdenes de 5–60 min con IC negativo contra el retorno de 1–15 min, sobre todo fuera de RTH).
   El borde por apuesta es 0,1–1,6 ticks y el costo agresivo 2,4–7 ticks. Confirma, en tres índices y con una
   medida única, el diagnóstico de las diez familias intradía anteriores.
2. **Horizonte largo: el borde bruto se acerca al costo, pero no hay potencia.** Con ~80 sesiones por mitad, el MDE
   del IC es 0,04–0,24: sólo se detectarían efectos grandes. Los márgenes puntuales grandes (gap al cierre, 240 min)
   tienen IC que cruzan cero y no se interpretan.
3. **Pista, no hallazgo:** primera media hora → última media hora, con IC −0,12 (ES) y −0,15 (YM) en descubrimiento y
   −0,12 / −0,11 en validación (mismo signo, **reversión**, contrario al momentum publicado para EE. UU.), sin
   significancia (p_null 0,26 y 0,15). Sin potencia con un punto por día.
4. El canal no direccional (`vol30` → |retorno|) es fuerte (IC 0,25–0,42) y estable en validación: el rango reciente
   predice cuánto se mueve el precio. No es un edge por sí mismo; sirve para dimensionar objetivos y stops.

## Qué implica (cómo reduce la distancia al referente)

- **Cerrar la búsqueda de reglas de horizonte < 60 min** en ES/NQ/YM con costo agresivo: el mapa mide que la
  información existe y es más chica que la fricción.
- **El cuello de botella es la longitud de la historia.** Las celdas donde el borde bruto se acerca al costo
  (≥ 60 min, cierre, última media hora, gap) necesitan años de datos de 1 minuto para tener potencia. Con 5 años
  (~1.250 sesiones) el MDE del IC baja ~4×, a ~0,01–0,06.
- Siguiente paso concreto: conseguir historia de 1 minuto de ES/NQ/YM (idealmente 2018 en adelante) y re-correr sólo
  las celdas de horizonte largo, con un pre-registro nuevo que herede esta grilla.

## Cómo podría refutarse

Con más historia, las celdas de horizonte largo seguirían sin superar el costo con IC inferior > 0 y signo sostenido.
