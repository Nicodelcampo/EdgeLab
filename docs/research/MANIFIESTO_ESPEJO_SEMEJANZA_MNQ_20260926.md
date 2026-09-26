# Manifiesto ESPEJO-SIM: ¿la vuelta que se parece al impulso completa el espejo? (MNQ, exploratorio, 2026-09-26)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Pedido de Nico (2026-09-26):** cuando un impulso fuerte empieza a revertirse con una acción del precio muy parecida
pero en sentido contrario, termina espejándose. «Parecida» = **velocidad y forma de las ondas** (respuesta de Nico,
antes de medir).
**Estado:** exploratorio y descriptivo; sin entradas, costos ni P&L. Escrito y commiteado antes de ver números.
**Antecedente:** TBZX-ESPEJO (`MANIFIESTO_TBZX_ESPEJO_20260925.md`).
- ES: llega a A +5 pp sobre N-VOL.
- NQ: contra N-REV el efecto desaparece. Lo que predice en NQ parece ser cómo empieza la vuelta, que es lo que mide
  este manifiesto.

**Familia:** subfamilia ESPEJO-SIM dentro de TBZX, con ledger y multiplicidad propios. No hereda los resultados de
TBZX-R3 ni de TBZX-ESPEJO.

## 1. Población

- **Impulso:** detector TBZX de `tools/tbzx_espejo.py` (paridad con el visor ya verificada), velas de 25 ticks.
  - Configuración fija `maxBars` = 20, `minW` = 68 ticks, eficiencia 0,6, retroceso 0,3.
  - Es la «NQ equivalente» que eligió TBZX-ESPEJO sólo por conteo. MNQ tiene el mismo tick que NQ.
  - No se barre nada.
- **Evento:** el primer instante en que la vuelta (desde el extremo B) llega a una fracción x del impulso, con
  x ∈ {0,4; 0,5; 0,75}, sin haber marcado antes un extremo nuevo más allá de B. En `iend` la vuelta ya recorrió 0,3.
- **Espacio de eventos considerado y descartado:** creación (sin vuelta todavía), cada vela de la vuelta como estado
  (queda para después si esto no alcanza), segundo intento de vuelta.
  - **Por qué el primer cruce de x:** es el momento en que un operador vería «esto se está espejando».
  - **Cómo podría refutarse esta población:** si la semejanza sólo predice en el estado continuo y no en el evento.

## 2. Semejanza (medida en el evento, sólo con información pasada)

La vuelta hasta el evento se compara contra el **tramo final del impulso invertido en el tiempo**: el espejo recorre
primero lo último que recorrió el impulso.

| Componente | Definición |
|---|---|
| `vel` | −\|log(velocidad de la vuelta / velocidad del tramo espejo)\|, en ticks por segundo |
| `efi` | −\|eficiencia de la vuelta − eficiencia del tramo espejo\| (neto / recorrido) |
| `forma` | −RMSE entre los dos caminos normalizados (precio en [0, 1], tiempo en velas en [0, 1], 20 puntos) |
| `ondas` | −\|ondas por W de la vuelta − del tramo espejo\|; zigzag con umbral 0,1·W |
| **S** | promedio de los rangos percentiles de los cuatro. Es la medida principal y va fijada ahora. |

## 3. Resultado y nulo

- **Espejo completo:** después del evento, el precio llega a A (retroceso del 100 %) antes de marcar un extremo nuevo
  más allá de B. Horizonte: 200 velas o el fin de la sesión. Los censurados se reportan y no entran en la tasa.
- **Nulo exacto:** en un precio sin memoria, estando en la fracción f realmente alcanzada, P(llegar a A antes que a B)
  = f. **Exceso = espejo − f**, por evento.
- **Control de semejanza:** el tercil de S bajo (vueltas poco parecidas), mismo x.
- También se reporta cuánto se pasa de A (en W) y en cuánto tiempo.

## 4. Pruebas y regla de sostenido (fijadas ahora)

- **Principal (3 pruebas, una por x):** exceso del tercil alto de S − exceso del tercil bajo. Los terciles se fijan
  en el descubrimiento y se reusan en la replicación.
- **Secundarias:**
  - exceso del tercil alto contra 0;
  - lo mismo con cada componente por separado (4 componentes × 3 x).
- Bootstrap por sesión (1.000), BH-FDR q = 0,10 sobre todas.
- **Descubrimiento:** MNQ 09-25. **Replicación:** MNQ 12-25 y 03-26, recortado al 2026-04-01.
- **Sostenido:** pasa FDR en el descubrimiento **y** tiene el mismo signo con IC > 0 en las dos replicaciones.
- Todo se publica. Holdout y abr–jun intactos.

## 5. Justificación económica y cómo podría refutarse

- **Mecanismo candidato:** una vuelta con la misma velocidad y estructura que el impulso indica un participante de
  tamaño comparable del otro lado. Los que entraron en el impulso quedan atrapados, y sus stops alimentan el recorrido
  completo.
- **Alternativa:** el recorrido de la vuelta es el de un precio sin memoria (exceso ≈ 0 en todos los terciles), o
  sólo refleja volatilidad (la velocidad sola explica todo y la forma no suma).
- **Se refuta** si la prueba principal no sostiene. Si sólo sostiene `vel` y no `forma` ni `ondas`, lo que hay es
  momentum de la vuelta, no espejo.

## Enmienda 1 — nulo al cierre (después de ver el descubrimiento, 2026-09-26)

- **Qué se vio:** en MNQ 09-25 todas las pruebas de exceso contra f dieron entre −10 y −14 pp.
- **Causa probable:** f se toma del extremo de la vela del evento. El evento recién se conoce al cierre de esa vela,
  cuando el precio pudo haber rebotado, así que la posición real es menor que f y el nulo queda inflado.
- **Cambio:** se agrega `f_cierre` (el retroceso al cierre de la vela del evento) como **segundo** nulo. El nulo
  original **no se reemplaza** y los dos se publican.
- **Qué no toca:** la prueba principal (tercil alto − tercil bajo de S) sigue igual.
- **Alcance:** este cambio es posterior a ver datos, así que ningún resultado contra `f_cierre` se promueve por sí
  solo. Sólo cuenta si replica en 12-25 y 03-26.

## Enmienda 2 — grilla del detector para ganar muestra (pedido de Nico, 2026-09-26)

**Contexto:** el descubrimiento en (20, 68) dio 854 eventos, unos 60 por tercil. Nico pide más zonas. La grilla se fija
ahora y se publica **entera**; no se elige la mejor configuración.

- **Grilla:** `maxBars` ∈ {10, 20, 40} × `minW` ∈ {17, 24, 34, 48, 68} ticks = 15 configuraciones. Eficiencia 0,6 y
  retroceso 0,3 fijos. Piso de 17 ticks (4 pts): por debajo, el impulso es ruido de vela y el espejo no tiene tamaño
  económico.
- **Pruebas:**
  - la principal de §4 (S T3 − T1 en cada x), en cada configuración;
  - las secundarias, iguales;
  - BH-FDR q = 0,10 sobre **todas las pruebas de todas las configuraciones juntas**.
- **Referencia y terciles:** propios de cada configuración, fijados en 09-25 y reusados en la replicación.
- **Sostenido:** la misma configuración y la misma prueba pasan FDR en 09-25 y tienen el mismo signo con IC > 0 en
  12-25 y en 03-26.
- **Alcance:** la configuración (20, 68) ya fue vista y queda incluida sin privilegio: su resultado de x = 0,75 cuenta
  como una prueba más de la grilla.
- **Costo:** los impulsos chicos tienen más fricción relativa. Si sólo sostienen los de 17–24 ticks, el paso siguiente
  es estimar si el espejo cubre el costo antes de seguir.

---
**Alcance (2026-09-26, pedido de Nico):** este estudio es un **tamiz** («¿seguir con la idea del espejo?»), no un
veredicto sobre el espejo. Qué midió exactamente, qué no y la regla para cerrar la familia:
`docs/research/ESPEJO_MEDIDO_Y_NO_MEDIDO.md`. Un NO de acá invalida sólo su población, su detector (impulsos
**eficientes**, eficiencia ≥ 0,6), su semejanza y su horizonte.
