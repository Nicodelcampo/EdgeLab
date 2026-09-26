# Familia ABS-CTX: absorción como amplificador de contexto (NQ L2), registro y auditoría, 2026-09-24

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Origen:** pedido de Nico. Si el evento solo da ≈ 0 y la absorción sola da ≈ 0, ¿los dos juntos dan una ventaja? Las mediciones deben **sugerir** eventos. Manifiesto con OK: `MANIFIESTO_NQ_L2_SINERGIA_ABSORCION_20260924.md`.
**Ledger:** `artifacts/hippocampus/nq_l2_20260924.jsonl`. Particiones `P-NQL2-EXP` (medida) y `P-NQL2-CONF` (**intacta**).
**Herramienta:** `tools/nq_l2_synergy.py`. Reportes:
- corrida B: `artifacts/nq_l2_synergy/report.json`;
- corrida C: `artifacts/nq_l2_synergy_C/report.json`, sha `485b4772d04f…`.

## 1. Lo que pidió Nico registrar: la hoja de tendencia de 30 min (corrida B), y por qué se cayó

**Resultado B, tal cual salió.** El árbol honesto encontró que, cuando el precio **todavía no había corrido** hacia donde apunta la absorción (−374 < r30 ≤ 84 y r5 ≤ 63 ticks), el evento le ganaba a su control por **+13,7 ticks a 300 s**. IC [5,6; 21,8], 984 eventos en 21 sesiones de estimación. En el espejo (el precio ya había corrido a favor) daba −24,5 ticks. Quedó como SUG-NQ-SYN-B-1…3.

**Auditoría el mismo día** (`EP-NQL2-SYN-AUDIT-C`), antes de abrir cualquier reserva:

| sig 300 s (ticks, en la dirección de la absorción) | media | IC 95 % |
|---|---:|---|
| eventos | +0,3 | [−4,3; +4,4] |
| controles **antes** del evento, sin solaparse | **−6,6** | [−9,5; −4,0] |
| controles antes, **solapados** con la aproximación | **−20,7** | [−26,1; −15,7] |
| controles después, solapados | −2,5 | [−9,5; +5,3] |
| controles **después** del horizonte | −1,0 | [−4,5; +2,9] |

**Causa raíz.**
- Los controles se sorteaban en ±30 min alrededor del evento. Los anteriores **heredan el camino con el que el precio llegó al nivel absorbido**: un bid absorbido aparece al final de una bajada.
- La "ventaja" del evento era la **bajada de sus controles**, no una suba del evento.
- La tendencia de 30 min separaba justamente cuánto camino de aproximación tenían esos controles.
- Con controles posteriores al horizonte, la hoja da **+1,6 [−4,5; +8,2]** y el "agotamiento" da +3,6 [−6,3; +14,0]. **Las dos se caen.**

**Alcance de la muerte (regla del proyecto).**
- Muere la lectura "la tendencia de 30 min condiciona la **dirección** de la absorción", medida con esos controles.
- **No muere** la pregunta "la tendencia condiciona la absorción". Sigue abierta, y la etapa 1 de C no la ve.

**Queda en el ledger:**
- SUG-NQ-SYN-B-1…3 y OBS-NQL2-SYN-S2-B: `INVALIDATED_BY_MEASUREMENT_ERROR`;
- OBS-NQL2-A (familia A de la exploración, mismos controles): `REQUIRES_REAUDIT`;
- lección `LES-CTRL-TIMING-20260924` (PROPOSED/LOW): toda diferencia con signo entre evento y control usa controles **posteriores a t0 + h** o de **otras sesiones a la misma hora**.

**Lo que sí sobrevive con controles limpios:**
- absorción dentro de una zona HFT gastada (≥ 3 toques) → |movimiento| a 900 s = −20,8 ticks [−35,2; −8,8];
- a 60 s: −3,9 [−6,3; −1,0].

## 2. Corrida C (controles corregidos): etapa 1 completa

- **Controles:** t_c en (t0 + 960 s, t0 + 2.700 s], mismo tercil de actividad y misma distancia al tope del libro.
- **Resultado:** 900 celdas, **19 pasan el FDR**, 1 candidata según las reglas fijas y 0 hojas en el árbol.

**Hallazgo principal: la sinergia pura que buscaba Nico, con signo invertido.**

| | sig 60 s (ticks) | IC |
|---|---:|---|
| número redondo solo (controles cerca de un múltiplo de 100 pts vs lejos) | −1,3 | [−3,9; +1,1] |
| absorción sola (lejos de un número redondo) | +0,7 | ≈ 0 |
| **absorción a ≤ 8 ticks de un número redondo (interacción)** | **−10,5** | **[−16,3; −4,6]** |

- 224 eventos en 39 sesiones. El efecto sin una sesión (leave-one-out) sigue siendo al menos 9,2 ticks del mismo signo. Cuesta ~4 ticks de spread.
- **Lectura:** cuando la absorción ocurre en un número redondo, **el nivel absorbido tiende a romperse**: el precio va ~10 ticks **contra** la dirección que implicaba la absorción en 60 s.
- La regla de candidatas exigía I > 0, así que marcó el complemento ("no redondo"). La celda sustantiva es "sí redondo", con signo negativo, y se opera **a favor de la ruptura**. Queda escrito para que la confirmación declare el signo de antemano.
- **Encaja con Osler (2003, 2005):** las órdenes límite se agrupan **en** el número redondo y los stops **justo después**. La absorción consume esa pared; cuando cede, los stops aceleran la ruptura.

**Otras celdas FDR (descriptivas):**
- **Nivel no roto en los 5 min previos (C12 = no):** |movimiento| a 300 s +11,9 [5,9; 18,4]. Sinergia pura en volatilidad: la primera defensa de un nivel virgen precede a un movimiento grande, sin dirección clara.
- **Absorción en Asia:** menos movimiento (−14,7 ticks a 900 s).
- **Dentro de una zona HFT:** si la zona apunta en contra de la absorción, más movimiento (+6,4 a 60 s); si va a favor, menos (−4,7).

## 3. Por qué puede estar cerca un fenómeno más fuerte de la misma naturaleza

Lo que sobrevive tiene un patrón común: **la absorción no dice hacia dónde va el precio, dice que un nivel está siendo disputado.** Qué pasa después depende de **qué hay detrás del nivel**:
- stops (número redondo, extremo) → ruptura;
- nada (nivel virgen) → movimiento grande sin dirección;
- zona gastada → calma.

La absorción funciona como **detector de disputa**, y el contexto decide el desenlace. Por eso sola da ≈ 0: promedia desenlaces opuestos. Es la regla "un efecto real bidireccional puede promediar cero" del proyecto, vista en vivo.

La hipótesis de familia que se desprende, **H-DISPUTA**, se enuncia así: *una absorción anticipa un movimiento de magnitud mayor a la normal, y su dirección la fija la asimetría de órdenes condicionales detrás del nivel (stops, grupos de números redondos, extremos).*

**Cómo podría refutarse:**
- V-RND no se replica en otros instrumentos (I-4) ni en `P-NQL2-CONF`;
- no hay dosis y respuesta con la redondez y la distancia (I-1);
- no aparece la cascada de agresivos después de romper (I-2).

## 4. Maneras de investigarlo (ninguna abre `P-NQL2-CONF`)

| # | Qué | Por qué | Datos |
|---|---|---|---|
| I-1 | **Dosis y respuesta del número redondo:** distancia 0–4, 4–8, 8–16 y 16–32 ticks; múltiplos de 100, 50 y 25 pts | Si es Osler, el efecto crece con la "redondez" y decae con la distancia. Si es azar, no tiene forma | EXP de NQ |
| I-2 | **Mecanismo:** ¿hay aceleración de trades agresivos justo después de romper el redondo (cascada de stops)? Volumen agresivo 0–10 s después de cruzar | Es la firma causal que predice la hipótesis | EXP de NQ, trades |
| I-3 | **Pared en el libro (L2 profundo):** tamaño del nivel en el libro antes y durante la absorción (reposición tipo iceberg vs consumo) | Separa "defensa real" de "pared que se vacía" | `l2_depth`, EXP |
| I-4 | **Replicación en otros instrumentos:** GC, 6E, y ES/MES cuando termine la descarga, cada uno con sus números redondos | Es la mejor evidencia sin gastar reserva. MNQ **no** cuenta: es el mismo subyacente | Particiones EXP propias |
| I-5 | **Versión sin L2 (sólo trades con regla de tick) sobre `research-v2` pre-holdout** (NQ y ES, 2025 a jun-2026) | Multiplica la muestra por 5 a 10. Antes hay que validar la regla de tick contra el agresor por cotización en julio y agosto (target-free) | Ticks canónicos pre-holdout |

## 5. Variantes para registrar (cada una con su propio ledger si se abre)

- **V-RND (principal):** absorción en número redondo → ruptura. Primario: sig 60 s con controles post-horizonte y cortes ya fijados (≤ 8 ticks, múltiplo de 100 pts). Es la candidata a confirmar.
- **V-EXT:** lo mismo en el máximo o mínimo del día o de la sesión previa (C7). Mismo mecanismo de stops; en B y C no tuvo potencia (n chico). Hay que medirlo con más datos (I-5).
- **V-VIRGEN:** absorción en un nivel no roto en 5 min → movimiento grande. Opera en volatilidad: opciones o tamaño, no dirección.
- **V-GASTADA:** absorción en una zona HFT con ≥ 3 toques → calma. Sirve para stops y tamaño.
- **V-TBZ:** absorción en el borde de una franja TBZ como marcador de rechazo vs travesía. Conecta con el mecanismo de la familia TBZ. En NQ no tuvo potencia.
- **V-EMPUJE (no se mide todavía):** "empuje de X ticks en 5 min que termina en absorción" contra "empuje de igual tamaño sin absorción". Es la versión correcta de lo que la hoja B confundió: la absorción como fin del empuje. El control sería el empuje sin absorción, no un instante al azar.

## 6. Próximo paso propuesto (STOP: necesita OK)

1. **Protocolo de confirmación de V-RND** en `P-NQL2-CONF` (24/08–31/10):
   - una sola celda: sig 60 s, ≤ 8 ticks de un múltiplo de 100 pts;
   - controles posteriores al horizonte, bootstrap por sesión;
   - se acepta si el límite superior del IC < 0 y |efecto| ≥ el spread p50.
   - Hoy hay ~12 sesiones; a fin de octubre, ~34. El MDE con 12 sesiones es de ~15 ticks, así que conviene esperar a octubre o sumar I-4 e I-5 antes.
2. Mientras tanto, **I-1, I-2 e I-4 sobre las particiones EXP**. Son descriptivos, cada uno con su manifiesto corto.

## Anexo: el detector no es ruido en NQ (nulo causal, target-free)

`artifacts/l2_phase0/NQ_NQ_09-26/detector_nulls_abs_causal_dev.jsonl`, NQ 09-26 del 01/07 al 11/09. Cuenta absorciones reales contra el mismo tape con los trades permutados. No mira el precio posterior.

- **EXP (49 sesiones):** 1,59× el nulo, IC [1,53; 1,66]; real > nulo en 43 de 49 sesiones.
- **Todo el tramo (67 sesiones):** 1,57× [1,51; 1,63].

Mismo orden que junio (1,60×). La absorción que usa ABS-CTX es un fenómeno del tape, no un artefacto del umbral.

## Réplica pre-registrada de V-RND en ES, GC y 6E (2026-09-24)

Protocolo `PROTOCOLO_REPLICA_VRND_ES_GC_6E_20260924.md` (commit `96c664f`, antes de mirar). Reporte `artifacts/vrnd_replica/report.json` (sha `fb35c6b128de…`). Ledger `artifacts/hippocampus/vrnd_20260924.jsonl`.

| Inst. | Sesiones | Eventos en R | I sig 60 s (ticks) | IC | MDE | NQ escalado | Veredicto |
|---|---:|---:|---:|---|---:|---:|---|
| ES | 41 | 197 | −0,58 | [−1,70; +0,51] | 1,58 | −2,7 | **NO_REPLICA** |
| GC | 31 | 164 | +1,11 | [−2,59; +4,64] | 5,19 | −3,6 | **SIN_POTENCIA** |
| 6E | 38 | 114 | −0,40 | [−1,05; +0,18] | 0,87 | −2,0 | **NO_REPLICA** |

**Decisión de familia según el protocolo: `NO_CONCLUYENTE`.** Ningún instrumento independiente replica. Ninguno contradice, y GC no tiene potencia.

**Lectura:**
- En ES y 6E el signo es el predicho, pero el tamaño es **menos de 1/4 del de NQ escalado**, y el MDE alcanza para descartar el tamaño de NQ.
- Aunque existiera en ES, −0,6 ticks no llega al spread (1 tick).
- **V-RND no se transporta como edge económico.**
- Lo más probable es que el −10,5 de NQ esté inflado por haber salido de 900 celdas (maldición del ganador), o que sea propio de NQ (libro fino, 3 contratos en el tope).
- Eso lo decide solamente `P-NQL2-CONF`, con el protocolo de una celda de §6, cuando haya suficientes sesiones.

**Sensibilidades (no deciden):**
- Denominación siguiente (ES 50 pts, 6E 0,0100): mismo signo, IC que cruza 0.
- GC 25 USD: +5,7 [0,1; 11,1], signo opuesto con n = 54, que no se interpreta.
