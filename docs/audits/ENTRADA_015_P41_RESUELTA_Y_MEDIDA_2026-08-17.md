# Entrada 015 · Opus 5 → Auditor · P-41 resuelta y medida (2026-08-17)

**Commit de referencia**: ver el commit que acompaña esta entrada.
**Rama**: `foundation/f0b-compatibility-probe`.
**Reasignación**: la entrada 014 §8 puso P-41 (C1) en la otra máquina. **Nico la
reasignó a ésta el 17-ago**, con un motivo operativo: la otra máquina no tiene los
parquets, así que podía escribir el fix pero **no verificarlo**. El test que cierra
P-41 necesita el dato.

---

## 1. P-41 estaba mal medida — por 6,1×

La entrada 014 §3 estimó el leak en **«> 871 ticks»**, extrapolando de P-17 (que midió
871 sólo en la franja 17:00→19:00 CT). Medido directo sobre el parquet canónico
`6E_09-26` (`6ffcdf04…`, 2.784.986 ticks):

| | |
| --- | --- |
| Apertura sesión trade date 20260701 | `1782856800000000000` ns = 2026-06-30 **22:00 UTC** |
| Corte del runner (23:59:59 CT) | `1782881999000000000` ns = 2026-07-01 **04:59 UTC** |
| **Ventana de fuga** | **7,0 horas** |
| Ticks conservados con el corte **viejo** | 1.089.664 |
| Ticks conservados con el corte **nuevo** | 1.084.345 |
| **Ticks de holdout que entraban** | **5.319** |

La estimación no era conservadora: era **6,1× menor** que el número real. El razonamiento
que la produjo («P-17 midió 871 en 17:00–19:00, esto admite además 19:00–23:59, así que
es más») era correcto en dirección y equivocado en magnitud, porque la actividad no se
reparte parejo en esas siete horas.

**No es un detalle de estilo.** El criterio de cierre de un firewall no se negocia con
un orden de magnitud: «>871» y «5.319» habilitan conversaciones distintas sobre si el
censo podía correr igual.

## 2. El fix, en los tres puntos que pedía el criterio

1. **Corte por trade date, no por calendario.**
   `FIREWALL_CUTOFF_NS = session_bounds_utc_ns(20260701)[0]`, aplicado en el firewall
   global y **también en el borde de cierre de `mask_p2`** (l. 332), que arrastraba el
   mismo defecto — su borde de arranque ya usaba el estilo correcto (17:00 CT), que es
   justamente lo que hacía el error difícil de ver: el archivo parecía saber la regla.

2. **Test** — `tests/research/test_p41_firewall_trade_date.py`, 5 casos:
   - el tick de las **17:30 CT del 06-30** queda afuera con el corte nuevo, y se fija
     explícitamente que **entraba** con el viejo;
   - **16:59:59 CT** del 06-30 sigue adentro (el borde simétrico);
   - la brecha regalada era de **7,0 horas** — fija la magnitud, para que nadie lo lea
     como un caso de borde de un segundo;
   - el cutoff **coincide con el del re-corte físico**: un solo origen de verdad. Si
     divergieran, un artefacto podría declararse limpio contra una frontera y sucio
     contra la otra;
   - `holdout_included` se **deriva** del contenido.

3. **`holdout_included` computado**:
   `bool(ticks_formal.ts_ns.max() >= FIREWALL_CUTOFF_NS)`. Antes era `False` escrito a
   mano. Ahora, si un solo tick alcanza la apertura de la sesión de holdout, **el
   artefacto se autodelata**. Se agregó un bloque `firewall` al payload con criterio,
   cutoff, ticks conservados, ticks excluidos y `ts_max` conservado.

## 3. Confirmación independiente que nadie había pedido

El corte nuevo conserva **1.084.345** ticks de `6E_09-26`. Ése es **exactamente** el
número de filas de `data/nt8_research_v2/6E/6E_09-26_ticks.parquet`, producido por
`tools/recut_holdout.py`.

**Dos caminos de código que nunca se hablaron coinciden al tick.** El runner ahora
sella la misma frontera que el re-corte físico, y la coincidencia es empírica, no de
diseño: ninguno de los dos lee el resultado del otro.

## 4. Dos cosas de registro, que valen más que el fix

**a) El commit que decía asentar P-41 no la asentó.** `f247e797…` se llama
«board + indice: P-41 asentada y fila 014 del canal», pero su `--stat` muestra un solo
archivo: `docs/audits/CANAL_AUDITOR.md`. `PENDIENTE.md` **nunca fue tocado** y el board
terminaba en P-40. Es la **cuarta** ocurrencia del patrón que el propio header del board
nombra, y la primera en que el mensaje del commit afirma lo que el commit no hizo.

**b) La nota de la lección tampoco cierra.** `CANAL_AUDITOR.md` dice que la 014 salió
sin asentar P-41 «y se reparó en el commit siguiente en vez de enmendar». El commit
siguiente reparó **el índice**, no el board. La nota que documenta el incidente
reproduce el incidente.

Nada de esto es reproche: el punto es que **el registro no se verifica solo**, y ambas
cosas eran detectables con un `git show --stat`, que es la regla permanente que el
propio proyecto se dio tras el incidente de procedencia del 2026-08-10.

## 5. El patrón, ya nombrado cuatro veces

P-41 es, en su tercera parte, otra instancia de lo mismo:

| Punto | Etiqueta que no se derivaba del contenido |
| --- | --- |
| **P-34** | `version=` en `.cs` y kernels: tres etiquetas, un comportamiento |
| **P-35** | `gate=WARN` sellado como `parity_exact` |
| **P-39** | `gex_dollar` sin dólares; `zone_age` en ms sin unidad |
| **P-41** | `holdout_included: False` escrito a mano |

Es el patrón **más repetido del board**. Sugerencia para la línea activa: cuando
`validity.py` absorba P-39, que absorba la familia entera — la propiedad común no es
«los nombres mienten» sino **«hay etiquetas que se escriben en vez de computarse»**, y
esa sí se puede chequear mecánicamente.

## 6. Lo que sigue

P-41 desbloquea el censo H-Z2A. **No lo corro**: el censo es C2 y sigue asignado a la
otra sesión, y además el manifiesto necesita el STOP de Nico.

Lo mío queda: **C4** (inventarios L2/GEX), **C5** (P-33(a) + re-correr `verify_tree`
sin `--no-source-hash`), **C6** (paridad formal de HFTZones2 y aVolCellPOI2 — de la que
HFTZones2 ya dio **PASS 4.821/4.821** el 15-ago).
