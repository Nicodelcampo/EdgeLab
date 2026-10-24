# Falsos negativos del embudo: siete correcciones (2026-10-24)

Estado: VIGENTE — implementado en la rama `claude/embudo-falsos-negativos` (sin mergear). Modifica la regla de D1 (m del FDR) y la de D4 (el linaje deja de ser compuerta por defecto) de `DECISIONES_VALIDACION_20261024.md`. No toca archivos protegidos.

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`

Pedido de Nico: que el embudo no descarte candidatas reales (falsos negativos) y que siga controlando el error (FDR en el tamiz,
LORD++ en la confirmación). Una auditoría encontró que **el embudo de hoy habría descartado U1-CRUZADO**, el mejor candidato del
proyecto, por cuatro vías distintas. Cada una de esas vías se podía cerrar por separado.

Principio común: **elegir y confirmar son dos pasos.** El tamiz elige, con FDR sobre los datos de descubrimiento. La confirmación
se hace en datos que nadie miró, con un paso de LORD++ que controla el FDR de todas las confirmaciones del proyecto. Una regla que
mata en la elección lo que la confirmación podría salvar no agrega control: sólo agrega falsos negativos.

Código: `edgelab/research/embudo.py`, `edgelab/funnel/escalera.py`, `edgelab/research/grilla_masiva.py`,
`edgelab/research/grilla_generica.py`, `edgelab/research/etapas.py`, `edgelab/research/linaje.py`.
Tests: `tests/research/test_falsos_negativos_embudo.py` (cada corrección con un control de efecto plantado y uno de ruido puro) y
`tests/research/test_u1_recheck_falsos_negativos.py` (chequeo sobre los artefactos de v1.4).

## 1. Pistas a réplica (ATJ-25) restaurada como etapa `PISTAS`
- **Antes:** con D1, si DESC nominaba 0 por FDR, la campaña cerraba `SIN_CANDIDATAS`. En `escalera.evaluar`, una celda sin
  nominar quedaba «en reserva», pero nada consumía esa reserva. La práctica que encontró U1 (v1.4: 0 nominadas → 80 pistas a
  réplica) ya no existía en el embudo.
- **Ahora** (`Embudo._a_pistas`, `_fin_pistas`), D1 sigue siendo compuerta para nominar en DESC, pero 0 nominadas no cierra la
  campaña:
  1. Se toman las **top-k pistas** de los dos canales. k va en el JSON (`pistas_replica.k`, 20 por defecto). Se ordenan por la
     **cota inferior del IC90 por sesiones**, con desempate por t de Romano-Wolf, y **nunca por P&L máximo**
     (`escalera.elegir_pistas_replica`). Tienen que ser distintas entre sí (`min_dif`) y pasar los filtros de relevancia de la
     selección.
  2. Se **congelan** en el estado antes de registrarlas y de lanzar.
  3. Se **registran las k pruebas** en el contador global (`embudo/<cid>/pistas`) antes de correr.
  4. Se replican en una **ventana reciente no usada**: la declarada en `pistas_replica.ventana`; si no hay, el OOS cuando es
     posterior al DESC; si tampoco, la réplica de HOLDOUT-A3 (abr–sep 2026) para ES/NQ. El PREFLIGHT rechaza una ventana que toca
     el holdout, que no es posterior al DESC, que sale de A3 en ES/NQ o que se superpone con el OOS sin ser el OOS.
  5. **Un solo paso de LORD++ para todo el lote** (`LibroLord.probar` → `probar_lote`: Simes para la familia y BH adentro, al
     nivel del paso). Las pistas que rechazan con media > 0 quedan nominadas (`nominada_replica`) y siguen a INDAGA. Si la
     ventana era el OOS, el OOS no se vuelve a usar para ellas.
- `escalera.evaluar(..., pista_replicada=True)` permite confirmar una celda que entró por esta vía. Sin nominación y sin pista
  congelada sigue sin haber confirmación. La «reserva» ahora dice adónde va: a pistas a réplica.
- **Control del error:** el lote es una prueba más de la familia en LORD++, así que el FDR de las confirmaciones sigue
  controlado. Simes es válido con dependencia positiva (PRDS) entre las pistas.

## 2. El linaje (D4) pasa de compuerta a información
- **Antes:** `q_linaje = q_BH · (m + N_heredado) / m ≤ 0,10` era compuerta en DESC. Con 19,4 M pruebas heredadas, ninguna celda
  de U1 podía nominarse nunca (`q_con_linaje(1e-4, 1, 1000, 19e6) = 1`).
- **Ahora:** el campo `linaje_como` del JSON vale `"informacion"` por defecto o `"compuerta"`.
  - Con `"informacion"`, `q_linaje` se calcula y se publica por pista, pero no decide. El ACTA sigue anotando la multiplicidad
    total, el recorte de Harvey-Liu, el efecto esperado y la potencia del holdout.
  - `"compuerta"` se usa cuando se reusan, para confirmar, los mismos datos con los que se seleccionó.
  - Por qué: una prueba sobre datos que nunca se vieron es válida a su propio α, y el error del conjunto lo controla LORD++.
    Cobrar en la elección las pruebas que otros hicieron sobre otros datos no protege nada y bloquea la confirmación.
- **Campañas ya congeladas:** un estado sin `linaje.como` conserva la compuerta (`_como_linaje`). Si se aflojara con resultados ya
  vistos, sería relajar un gate después de mirar.

## 3. Número efectivo de pruebas (Li-Ji)
- `escalera.n_efectivo_o_bruto(n, matriz)` aplica Li-Ji (`n_efectivo`) cuando la matriz de P&L (observaciones × pruebas) cubre
  **todas** las pruebas contadas. Si no, cobra el bruto y deja un aviso. Nunca extrapola de una muestra de columnas, porque ese
  descuento quedaría sin respaldo.
- **Dónde se usa:**
  - En `linaje.multiplicidad`, cuando la declaración trae `matriz_pnl`. Si no la trae, cobra el bruto con `aviso`, que queda en
    el MEDIDO y en el ACTA.
  - En el REP de `grilla_generica`, con la matriz sesión × celda de las celdas congeladas (`matriz_sesiones`), para el recorte de
    la maldición del ganador.
  - En DESC (cientos de miles de celdas) sigue el bruto, con `aviso_n_pruebas`.

## 4. m del FDR = celdas evaluables (filtrado independiente)
- **Antes:** `criba` corría el tamiz sobre todas las celdas, y las que tenían menos de 30 operaciones entraban con p = 1. En v1.4
  eran 995.328 celdas, de las que 315.654 eran evaluables. Las no evaluables inflaban m (y π0 de Storey) sin poder rechazar nunca.
- **Ahora** el tamiz va sobre las evaluables (Bourgon, Gentleman y Huber 2010). El filtro n ≥ 30 depende sólo del conteo de
  operaciones, no del signo ni del tamaño del P&L, así que bajo la nula no cambia la distribución de los p que lo pasan.
- `criba` publica `m`, `evaluables`, `celdas` y `m_sobre`. `canales` publica `m_fdr` y `celdas` por canal, y cada pista lleva
  `m_fdr` y `celdas_canal`. `m_sobre="celdas"` reproduce la regla anterior. `resumen_nulo` calcula el MDE del tamiz con m =
  evaluables.
- El contador global **sigue registrando todas las celdas**, con lo que el conteo queda conservador.

## 5. La meseta ordena, no mata
- **Antes:** en la selección de DESC, `exigir_meseta` descartaba toda pista sin meseta. En v1.4, **4 de las 5 celdas de U1 no
  tenían meseta**.
- **Ahora:** primero van las pistas con meseta y después el resto, por cota inferior. No se descarta ninguna. El nombre
  `exigir_meseta` se conserva por compatibilidad con campañas congeladas.

## 6. Resolución del bootstrap
- **Antes:** el p del bootstrap no baja de 1/(B+1), que con B = 2000 da 5·10⁻⁴. El nivel de LORD++ de una familia con historia
  bajó a ≈2·10⁻⁵ (v1.4, réplicas 40 a 80): **rechazar era imposible por construcción**. `sin_resolucion` sólo avisaba, y además
  comparaba contra el nivel del lote, no contra nivel/m.
- **Ahora** `escalera.resumen_resuelto`:
  - Fija B ≥ 10·m/nivel (`n_boot_para`), con tope `N_BOOT_MAX` = 200.000. El bootstrap corre por bloques, con memoria acotada y
    el mismo sorteo.
  - Si el tope no alcanza, usa un **p analítico agrupado por sesión**: t con error CR1 sobre los aportes por sesión y referencia
    t de Student con k−1 grados de libertad (`t_cola_superior`, sin scipy).
- El embudo le pasa al kernel `resolucion = {nivel, m}` para el OOS y para PISTAS, con el nivel del libro al lanzar y el tamaño
  del lote. El HOLDOUT resuelve al nivel reservado por el acta.
- `sin_resolucion(nivel, n_boot, m, metodo_p)` compara contra nivel/m con el B que se usó de verdad. Con p analítico no avisa.
  Un «no rechaza» ya no puede salir sólo de la resolución.

## 7. Se evalúan todas las celdas nominadas por FDR
- **Antes:** `canales` evaluaba sólo las 60 primeras pistas distintas por t de Romano-Wolf. Una nominada fuera de ese corte nunca
  se evaluaba ni llegaba a candidata.
- **Ahora** se evalúa la unión de las 60 por RW y **todas** las nominadas por el FDR, tomadas de los q-valores completos y sin
  tope. Todas las nominadas relevantes van a `pistas`, marcadas. De las no nominadas van las K_PISTAS mejores. Cada canal declara
  `k_evaluadas` (`por_romano_wolf`, `nominadas_fdr`, `total`).

## 8. Descartes indebidos del pasado que estas correcciones habrían evitado

| caso | qué pasó | qué lo cierra |
|---|---|---|
| AREAS-EXP-1 v1.3 | BH sobre 1.990.656 celdas: 0 nominadas en las dos fuentes y familia casi cerrada | §1, pistas a réplica (fue la auditoría manual la que sacó U1) |
| Réplica v1.4 | 80 pistas pasadas **de a una** por LORD++: 0,011 la primera y ≈2·10⁻⁵ desde la 40.ª, con p mínimo del bootstrap 5·10⁻⁴. 0 de 80 | §1 (un paso por lote) y §6 (resolución) |
| Meseta en v1.4 | 4 de las 5 celdas de U1 sin meseta: la selección automática las habría descartado | §5 |
| Linaje D4 | `AREAS_EXP_1_CRUZADO` hereda 19,4 M: `q_linaje` = 1 para cualquier celda, así que nunca habría habido nominación | §2 |
| Tamiz con p = 1 | el m de v1.4 era 995.328 en vez de 315.654 evaluables | §4 |
| Canal reciente v1.4 (USATECH) | 4 nominadas por FDR que el artefacto no lista ni evalúa: sólo se evaluaba el top-60 por RW, y ninguna de las 20 pistas publicadas es nominada (además hubo 4 pistas descartadas por relevancia; no se puede saber si eran las mismas) | §7 (ahora toda nominada se evalúa y se publica marcada) |

## 9. Chequeo final sobre los artefactos de v1.4 (U1)
Se aplicó la lógica de selección nueva sobre `docs/research/areas_expansion_20261022/v14/AREAS_USATECH_DESC_v14.json` (las 40
pistas de los dos canales) y `REP_EVALUACION_LORDPP_v14.json` (los p de la réplica abr–sep 2026, B = 2000). No se corrió nada
nuevo. Todo es reproducible con `tests/research/test_u1_recheck_falsos_negativos.py::recheck`.

| escenario | pistas al lote | U1 en el lote | nivel del paso | p de Simes | resultado |
|---|---:|---:|---:|---:|---|
| USATECH, k = 20, primer paso de la familia | 20 | 2 de 5 | 0,010937 | 0,009995 | **rechaza: confirma las 2 de U1** (`[2,2,10,3,2,3,1]`, `[2,2,11,3,1,3,1]`) y ninguna otra |
| USATECH, k = 40 | 39 | 5 de 5 | 0,010937 | 0,009745 | rechaza: confirma 4 de U1 |
| USATECH al nivel del 2.º paso (si NQ hubiera ido primero) | 20 | 2 | 0,003608 | 0,009995 | **no rechaza** |
| NQ, k = 20 (o 40) | 20 (37) | — | 0,010937 | 0,070 (0,129) | no rechaza |
| v1.4 tal como se corrió (LORD++ de a una) | 80 | 5 | 0,011 → 1,0·10⁻⁵ | — | 0 de 80 |

Lectura honesta:
- **U1 llega a la réplica y la confirma el paso de LORD++ por lote**, pero sólo si es el primer paso de la familia. El margen es
  chico: 0,009995 contra 0,010937.
- Esos p tienen la resolución vieja (2/2001). Con el B de §6 podrían bajar o subir un poco.
- El resultado depende del orden de los pasos. Si NQ y USATECH se lanzan juntos, corresponde decidir antes, por escrito, qué lote
  va primero, o correrlos como un solo lote.
- Esta confirmación **no confirma U1-CRUZADO**: la operación en NQ, con la señal del CFD, es una derivación posterior. Sigue
  necesitando el holdout a N fijo desde el 2026-10-23.

## 10. Lo que queda abierto
- **Reuso de la réplica A3:** una ventana A3 ya consumida por la familia (la réplica de NQ abr–sep usada tres veces en el linaje
  AREAS-EXP-1) no se detecta. `_problemas_pistas` valida la forma de la ventana, no su historia. Hace falta un libro de ventanas
  de réplica, como el del holdout.
- **Orden de lotes simultáneos** entre campañas hermanas, como se ve en §9. Lo decide Nico.
- **Li-Ji del linaje:** ningún linaje declarado trae hoy `matriz_pnl`, así que se cobra el bruto con aviso.

Aporte al referente: el embudo vuelve a poder encontrar lo que encontró a mano (U1 confirmada en lote al primer paso), sin aflojar
el control del error. Cada descarte queda en el contador, el α sale de LORD++ y un «no rechaza» ya no puede venir de la resolución
del bootstrap.
