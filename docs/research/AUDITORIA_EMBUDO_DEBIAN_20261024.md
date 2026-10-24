# Auditoría del embudo para correr en el Debian (2026-10-24)

Estado: VIGENTE
Fecha: 2026-10-24
Familia / módulo: embudo de grilla (`edgelab/research/embudo.py`, `etapas.py`, `embudo_runners.py`, `tools/embudo_correr.py`)
North Star: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Procedencia: rama `claude/project-thread-l4tr0z` desde `foundation/f0b-compatibility-probe` @ `baabe04c`

**Pedido de Nico (2026-10-24):** «auditar el funnel para dejarlo listo y sin errores para el Debian, cosa de que pueda empezar a
lanzar corridas con millones de variantes correctamente analizadas, filtradas, promovidas».

**Alcance.** Orquestador (`Embudo.avanzar` y sus compuertas), etapas (`etapas.ejecutar`), runners (Kaggle y local con datos
sellados), el ciclo del Debian (`edgelab/autopilot/__main__.py`) y la herramienta `tools/embudo_correr.py`. No se cambió
ninguna regla de validación (gates, FDR, mandato, archivos protegidos): lo que toca semántica queda como propuesta (§3).

## 1. Errores corregidos (con test en `tests/research/test_embudo_auditoria_debian.py`)

| # | Error | Efecto en una campaña real | Corrección |
|---|---|---|---|
| 1 | `LocalRunner` guardaba el resultado sólo en memoria y el ciclo del Debian arma un runner **nuevo en cada vuelta**. | La vuelta siguiente veía el handle como desconocido («error»); a la tercera el embudo cerraba la campaña como `BLOQUEADA`. **CONTEO y HOLDOUT no podían terminar nunca desde el ciclo.** | El runner persiste cada resultado en `<raiz>/_local/<handle>.json` (escritura atómica); el ciclo y `embudo_correr` le pasan la carpeta. |
| 2 | INTEGRIDAD, TOPES y el riesgo de REP armaban la lista por celda con `groupby("celda")`: una celda sin operaciones desaparecía. | Las celdas siguientes quedaban corridas un lugar: la compuerta leía latencia, placebo o topes **de otra celda** (o reventaba con `IndexError`). Con ejecución en otro activo o con latencia es esperable que una celda quede vacía. | `etapas.por_celda`: una entrada por celda en el orden congelado (`{n: 0}` si no operó). Las compuertas detectan un resultado desalineado de un kernel viejo y lo relanzan en vez de leerlo. |
| 3 | `_registrar` usaba `spec.get("n_celdas_por_canal", 1)`. | Una campaña sin ese campo registraba **2 pruebas** en el contador global para una grilla de millones (U1-CRUZADO no lo tenía: 1.492.992 celdas por canal). Tampoco se verificaba que lo registrado fuera lo que corría. | El PREFLIGHT compara `n_celdas_por_canal` con `grilla_generica.n_celdas(experimento)` y bloquea si falta o difiere; DESC verifica `res["celdas"]` contra lo registrado y bloquea si no coincide. `U1_CRUZADO.json` lleva ahora su número. |
| 4 | TOPES registraba siempre `celdas × 6`. | Con una lista de topes propia, el contador quedaba mal. | Cuenta las variantes con tope que se corren de verdad. |
| 5 | Las compuertas releían las reglas del JSON de la campaña en cada etapa, aunque el PREFLIGHT las escribía en `estado.json`. | Editar `seleccion`, `integridad` o `topes` después de ver el DESC cambiaba la compuerta **en silencio**. | `_reglas(spec, st, k)`: las compuertas usan las reglas congeladas en el PREFLIGHT. |
| 6 | Nada impedía editar la campaña a mitad de camino. | Cambiar `desc`, `oos`, sensor, ejecución, experimento o familia después de ver resultados pasaba inadvertido. | Si cambia un campo de `INMUTABLES` (o `holdout.desde` va hacia atrás), la campaña se cierra `BLOQUEADA`: es otra campaña, con cid y registro propios. Adelantar el holdout se permite (protege más). |
| 7 | Ningún chequeo temprano de que DESC/OOS no tocan el holdout. | `fuentes_ticks` corta en la frontera al leer, pero el error aparecía recién dentro de Kaggle. | `problemas_campana` en el PREFLIGHT: DESC y OOS terminan antes de `HOLDOUT_PRIMERA_SESION_INT`, y `holdout.desde` no es anterior a la frontera. |
| 8 | Un kernel de Kaggle con estado desconocido se consideraba «running» para siempre; las fallas se acumulaban para toda la campaña; un `traer` fallido (red) tiraba excepción. | Campañas colgadas sin aviso; tres cortes transitorios en etapas distintas bloqueaban la campaña. | Más de `MAX_HORAS_KAGGLE` (14 h; Kaggle corta a las 12) cuenta como falla; las fallas se cuentan **por etapa**; un `traer` que falla es una falla reintentable. |
| 9 | `tools/embudo_correr.py` abandonaba la campaña ante cualquier excepción. | Un corte de red en el Debian sacaba la campaña del bucle. | Reintenta en la vuelta siguiente; abandona tras `--max-errores` (5) seguidos. |
| 10 | TOPES descartaba una variante con drawdown 0 (`not f.get("drawdown_max")`). | La variante sin pérdida acumulada, la mejor posible, quedaba excluida. | Drawdown 0 → puntaje infinito; sólo se excluye si no hay dato. |
| 11 | El resultado de un kernel calculado con módulos que después cambiaron se consumía sin aviso (error 23 de la revisión). | Contra la regla «una corrida lanzada con código que después se corrigió no se mira». | Al traer cada resultado se compara con `preflight.codigo_vigente`; si cambió, queda en `estado.json` y en `MEDIDO.md` como AVISO (no relanza solo: decidir si el cambio toca la medición). |
| 12 | El p del bootstrap tiene piso `1/(n_boot+1)` (OOS 2000, holdout 5000) y LORD++ baja el nivel con cada paso de la familia. | Pasado cierto paso, rechazar es **imposible por construcción** y el «sin rechazo» se lee como evidencia en contra. | Aviso `sin_resolucion` en OOS y HOLDOUT (no cambia la decisión; ver §3.2). |

Suite: los 17 tests nuevos y los 1.058 del área (`tests/research`, autopilot, LORD, escalera) en verde; suite completa en el PR.

## 2. Lo que se revisó y está bien

- **Holdout:** `fuentes_ticks` corta todas las lecturas de desarrollo en `HOLDOUT_APERTURA_UTC_NS`; las lecturas selladas exigen acta
  y `desde >= 2026-10-01`; `holdout_ventanas` impide reusar sesiones consumidas y una segunda apertura por familia; CONTEO devuelve
  sólo el número de operaciones (test existente).
- **Reproducibilidad:** semillas fijas (Romano-Wolf 7, bootstrap por sesiones 20261022, placebo 0–4); el kernel registra el SHA
  de cada módulo embebido; el estado se escribe atómico.
- **Costos:** sólo `edgelab.costos` (sin spread medido no se lanza; un spot usa el costo de su futuro).
- **LORD++:** libro persistente e idempotente por `run_id`.

## 3. Hallazgos que NO se corrigieron acá (deciden Nico u otros hilos)

1. **Promoción sin evidencia de multiplicidad.** En EXPZ-NQ y EXPZ-CFD el DESC dio **FDR 0** y umbral de Romano-Wolf ≈ 4,11 con
   t máximos ≈ 2,6, y aun así promovió 3 candidatas cada una (con `conservado = 0`: el recorte de Harvey-Liu espera efecto nulo fuera
   de muestra). La selección mira pistas, no nominaciones. Nico ya aprobó el FDR q 0,10 como compuerta dura: lo implementa el hilo
   «Aplicar las cuatro decisiones de validación».
2. **Piso del bootstrap contra el nivel de LORD++** (ítem 12). Propuesta: elegir `n_boot` antes de correr, a partir del nivel que el
   libro ya conoce (p. ej. `n_boot >= 20 / nivel`), para que el p pueda bajar del nivel. Es regla de validación: decide Nico.
3. **Réplica abr–sep una vez por familia (HOLDOUT-A3).** EXPZ-NQ y EXPZ-CFD son la misma familia (`EXPANSION_ZONAS`) y las dos
   declaran OOS abr–sep. Las dos consumen un paso del libro de la familia, pero la partición A3 dice «réplica una vez por familia».
   Decide Nico si la segunda campaña debe usar otro período o si cuenta como la misma réplica.
4. **Memoria y velocidad a millones de celdas** (asignado al hilo «Potenciar al agente del Debian», que reescribe esas funciones):
   `romano_wolf` guarda `M` de B × celdas evaluables en float32 y `np.nanstd(M, 0)` y `np.where(activos, M, -inf)` crean copias del
   mismo tamaño: el pico es ≈ 3 × M (5 M de celdas con B = 200 ≈ 12 GB). `estadisticas` usa `np.vectorize` sobre cada celda y
   `simular_ops`/`_trasladar` recorren las operaciones en Python.
5. **La regla congelada con tope no pasa por OOS.** INTEGRIDAD y OOS miden la celda sin tope; TOPES elige el tope sobre el DESC y el
   acta congela celda + tope. El holdout es la única medición limpia de la regla con tope. Es diseño, no error: queda escrito.
6. **INTEGRIDAD e INDAGA no suman al contador global.** Reusan los datos del DESC y no prueban hipótesis nuevas sobre datos nuevos;
   INTEGRIDAD filtra por `r0 > 0` en esos mismos datos. Consistente con el registro actual; se deja anotado.

## 4. Cómo correrlo en el Debian

- Ciclo autónomo: `python -m edgelab.autopilot --root <raiz> --config <config.json> --candidates <cands.json> --loop 600` con
  `"embudo": {"activo": true, "sellado": {...}}`. Los resultados locales quedan en `<raiz>/embudo/_local/`.
- A mano: `python tools/embudo_correr.py config/autopilot/grillas/campanas/<CID>.json --raiz <estado> --libro <libro_lord.json>
  [--sellado '{...}'] [--intervalo 300] [--max-errores 5]`.
- Campaña nueva: además de los campos de siempre, **`n_celdas_por_canal` = `grilla_generica.n_celdas(experimento)`**; si no
  coincide, el PREFLIGHT la bloquea antes de gastar Kaggle.

Aporte al referente: el embudo ya no puede cerrar el holdout por un error del runner, decidir sobre la celda equivocada ni contar
de menos la multiplicidad; las decisiones que quedan (FDR duro, resolución del bootstrap, réplica por familia) están escritas para
que las tome Nico antes de gastar la única apertura del holdout de cada familia.
