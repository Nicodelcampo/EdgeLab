# Requisitos de export — qué tiene que cumplir un parquet para entrar

**Escrito**: 2026-07-27, después de censar tres fuentes de datos y encontrar
defectos en las tres.
**Destinatario**: el export desde cero de **ES, MES, NQ y MNQ**.

Este documento existe por una razón concreta: **de los tres archivos que se
censaron, ninguno pasó limpio**, y dos de los defectos se encontraron por
casualidad. Lo que sigue no es una lista de buenas prácticas — es el catálogo de
lo que ya falló, con la firma de cada falla y el chequeo que la atrapa.

---

## Parte 1 — El catálogo de fallas

### D1 · Duplicación de bloque *(en las tres fuentes)*

Una subsecuencia de `(precio, volumen)` que aparece dos veces en el archivo.

| fuente | bloques reales | días tocados |
|---|---:|---|
| 6E 09-26 | 1 *(3577 ticks)* | 2026-06-22 → 07-02 (9 días) |
| `nq_ticks_clean` | **16** | 2026-06-09, 06-11 |
| `es_full_ticks` | **172** | 2026-02-04, 02-05, 06-19 |

En 6E la copia era la hora 13:00–14:00 CT reinyectada dentro de la ventana de
mantenimiento 16:00–17:00. Se demostró que el defecto es **del parquet, no del
feed**: el oráculo NT8 de esos mismos días tiene **0 eventos** ahí.

> **Lo que hace peligroso a D1 no es su tamaño: es que se encontró por accidente.**
> Cayó en la ventana de mantenimiento, donde no debía haber nada. La misma copia
> dentro de una hora activa habría sido **invisible** — el precio es continuo, el
> volumen plausible, y ninguna regla de sesión la delata.

**Chequeo**: hash rodante sobre `(precio_en_grilla, volumen)` con ventana de 256
ticks, confirmación por igualdad exacta. Está en `tools/censo_es_nq.py`.

Dos trampas ya pisadas, para no repetirlas:
- **Hashear bloques alineados da falso negativo.** Un bloque duplicado empieza en
  una posición arbitraria, así que los bloques alineados del original caen en
  posiciones no alineadas de la copia. Esa versión dio **0 duplicaciones sobre un
  parquet con una demostrada**. El hash tiene que ser **rodante**.
- **Hay que descartar la ventana degenerada.** 256 ticks seguidos al mismo precio
  y volumen coinciden con cualquier otra racha igual: es un mercado clavado, no
  una copia. Se cuenta `n_valores_distintos` y se descarta si es ≤ 2.

---

### D2 · Timestamp colapsado *(NQ; 6E limpio)*

Un bloque entero de ticks estampado **en un único instante**.

```
ORIGEN  2026-06-11 14:32:34.844  29168.125  1     <- microestructura real
        2026-06-11 14:32:34.848  29167.625  1
        2026-06-11 14:32:34.944  29166.625  1

COPIA   2026-06-11 14:35:06.036  29168.125  1     <- 3618 ticks, UN instante
        2026-06-11 14:35:06.036  29167.625  1
        2026-06-11 14:35:06.036  29166.625  1
```

`nq_ticks_clean`: máximo **3.618 ticks** en un timestamp idéntico, y **2.708**
timestamps con ≥100 ticks.

**Por qué importa**: rompe exactamente lo que se arregló en TICKBAR-001. Un
secuenciador de barras de tick no puede ordenar 3.618 eventos que comparten
instante, y cualquier frontera de sesión por timestamp del evento queda ciega ahí.

**6E pasa este chequeo**: máximo 202–246 ticks por timestamp en los cinco
parquets, que es lo normal en resolución de milisegundos.

**Chequeo**: `max(count(*)) group by timestamp`. Es una línea de SQL. **No estaba
en la batería** — se miró sólo porque NQ falló primero por otra cosa. Eso es
suerte, no método, y por eso queda escrito acá.

---

### D3 · Serie continua armada en vez de contrato crudo *(ES y NQ)*

Los dos archivos son series **back-adjusted**: se le restó a la historia el
escalón del roll para pegarla continua. Firmas medidas:

- **NQ: 55,16 % de los precios fuera de la grilla de 0,25** — media tick. El
  desplazamiento cambia de régimen exactamente dos veces (2025-12-14 y
  2026-06-14), los dos domingos de apertura después de un roll trimestral. Dentro
  del tramo desplazado, los 52.583.615 ticks caen **sin una sola excepción** en la
  grilla de 0,25 corrida +0,125.
- **Salto en el roll de junio**: ES **+177,75 pts** (z=9,0 contra la distribución
  de fines de semana del propio archivo), NQ **+326,63 pts**. Un spread de
  calendario ES Jun→Sep es de decenas de puntos y negativo. Es el escalón
  acumulado del ajuste: datos crudos del front month **pegados encima** de una
  historia ajustada.

**Consecuencia**: los niveles absolutos **no son precios operables**. 25758,125 no
existe en NQ. Una zona guardada ahí es ficción. Sólo **5 días pre-holdout** de NQ
y **2 de ES** tienen niveles reales.

*(Las diferencias dentro de un tramo sí son exactas en ticks — el desplazamiento
se cancela al restar — así que estadística de excursiones se puede hacer. Niveles,
zonas e indicadores, no.)*

**Chequeo**: fracción de precios que no son múltiplo entero del tick size, por
día. Tiene que dar **0,000000 %**.

---

### D4 · Sin columna de contrato *(ES y NQ)*

Sin `contract` no se puede aplicar el criterio de front month **medido por
volumen** — el que valida el universo de 6E (`volumen(nuevo) > volumen(viejo)`,
con la fecha medida y no estipulada). La procedencia queda no verificable.

---

### D5 · Sin oráculo NT8 *(ES y NQ)* — el que solo alcanza para rechazar

ES y NQ no salieron de NT8, así que **no hay nada contra qué validar paridad**.
Todo el pipeline — kernels, gate P3, store, visor — se apoya en "el Python
reproduce bit a bit lo que hace NT8". Sin oráculo, las zonas producidas no se
pueden confrontar contra nada.

---

### D6 · Sábados con ticks *(6E)*

7 días sábado con ticks en el censo de 6E. CME no tiene sesión los sábados.

**Diagnosticado y cerrado (2026-07-27)**: son 1–10 ticks sueltos por día, a horas
dispersas (17:15, 19:24, 16:34…). Uno de ellos —2025-09-13 en `6E_12-25` con **10
ticks**— salía **APTO**: con tan pocos ticks *cualquier* hueco cubre las 16:00 y
`hueco_mantenimiento` pasaba. Ahora hay dos chequeos que lo matan: `SABADO_SIN_SESION`
(fallo duro, sin umbral que discutir) y `cobertura_horaria`. Ver el apéndice.

---

### D7 · Viernes y domingos rechazados por la batería *(defecto del chequeo, no del dato)*

| día | n | APTO | % |
|---|---:|---:|---:|
| lun–jue | 226 | 163 | 69–77 % |
| **vie** | 56 | **0** | **0 %** |
| **dom** | 60 | **0** | **0 %** |

`chequeo_hueco_mantenimiento` exige un hueco ≥55 min que cubra las 16:00 CT. El
viernes cierra 16:00 y no reabre; el domingo abre 17:00. Ninguno de los dos
**puede** tener ese hueco dentro de su día calendario.

Los **163 días efectivos del atlas nulo son exactamente los 163 lun-jue APTO**: el
nulo está estimado sin un solo viernes ni domingo.

**RESUELTO 2026-07-27** — decisión delegada por Nico. Ver el **apéndice** al final
de este documento: el tipo de día se deriva del dato, `hueco_mantenimiento` se
aplica sólo donde la ventana existe, y se agregaron tres chequeos nuevos que
rechazan 77 días que antes pasaban. Universo **163 → 236**.

**Y destapó una brecha peor**: el atlas nulo había consumido **10 días del
holdout**, porque su filtro de fecha estaba en el docstring y no en el código.
Registrada en `docs/holdout_access_log.md`, nota 4.

---

## Parte 2 — Requisitos para ES, MES, NQ, MNQ

| # | requisito | cómo se verifica | falla que evita |
|---|---|---|---|
| R1 | **Un archivo por contrato**, nunca una serie continua ni back-adjusted | columna `contract` con un solo valor | D3, D4 |
| R2 | **Precios crudos en la grilla del exchange** | 0,000000 % fuera del múltiplo entero de tick size | D3 |
| R3 | Columna **`contract`** presente | schema | D4 |
| R4 | **Timestamps nativos de NT8**, sin lotear ni colapsar | `max(count) group by ts` en el orden de las centenas, no de los miles | D2 |
| R5 | **Bid y ask por tick** | schema | *(footprint)* |
| R6 | **Oráculo NT8 de la misma ventana** exportado junto con el parquet | existe el CSV | D5 |
| R7 | **Contratos solapados en el roll**: exportar el viejo y el nuevo cubriendo el cruce | dos archivos con rango solapado | permite medir el front month por volumen |

### Puerta de aceptación

Ningún archivo entra al universo sin pasar, **antes de cualquier otro uso**:

```bash
.venv/Scripts/python tools/censo_es_nq.py --solo <clave>
```

Batería completa por día + duplicación de bloque sobre el archivo entero +
timestamp colapsado + grilla de precios. **Fail-closed**: lo que no se puede
evaluar no se declara limpio.

> **Los parquets son inmutables.** Un archivo que falla no se parchea: se
> reexporta. Prohibido "arreglar" el parquet para conseguir un PASS.

### Lo que conviene exportar de más

- **Solape en el roll** (R7): sin dos contratos cubriendo el cruce, la fecha de
  front month hay que estipularla a ojo en vez de medirla.
- **Warm-up antes de la ventana de interés**: la ventana de datos **no es** la
  ventana de comparación. Ya costó una corrida: el arnés recortaba los ticks a la
  ventana de comparación y `aVolCellPOI2` producía 0 zonas por falta de warm-up.
- **MES y MNQ**: son los micros de ES y NQ. Si el objetivo es ejecutar ahí,
  hay que censarlos por separado — el volumen y el spread no son los del grande, y
  el footprint tampoco.

---

## Apéndice — decisión sobre viernes y domingos (2026-07-27)

Delegada por Nico y resuelta acá. La batería rechazaba **0 de 56 viernes y 0 de
60 domingos**, y aprobaba un sábado con **10 ticks**. Los dos errores tienen la
misma raíz: un chequeo de *forma* (`hueco_mantenimiento`) aplicado donde la forma
no existe, y sin ningún chequeo de *densidad* que lo respalde.

**Lo que se hizo** — el tipo de día se **deriva del dato**, no del calendario, así
feriados y cierres tempranos se clasifican solos:

| tipo | derivación | día | horas con ticks (medido) | mínimo exigido |
|---|---|---|---:|---:|
| `COMPLETO` | ticks antes de 16:00 **y** después de 17:00 | lun–jue | mediana 23 (p05 22) | **20** |
| `CIERRE_SEMANAL` | ticks antes de 16:00, ninguno después | vie | mediana 16 (p05 13) | **12** |
| `APERTURA_SEMANAL` | ninguno antes de 16:00, ticks después | dom | mediana 7 (mín 6) | **5** |
| `SIN_ESTRUCTURA` | ninguna de las dos | — | — | falla |

`hueco_mantenimiento` se aplica **sólo a `COMPLETO`**. Los otros dos ya tenían su
chequeo propio (`cierre_semanal`, `apertura_dominical`).

**La batería quedó más estricta, no más laxa.** Tres chequeos nuevos rechazaron
**77 días que antes pasaban**:

| chequeo nuevo | qué atrapa | rechazos |
|---|---|---:|
| `cobertura_horaria` | días vacíos que pasaban porque con pocos ticks *cualquier* hueco cubre las 16:00 | 42 |
| `tipo_de_dia` | un lun-jue al que le falta la tarde haciéndose pasar por viernes | 28 |
| `SABADO_SIN_SESION` | CME no opera sábados; había 7 días con 1–10 ticks | 7 |

Universo: **163 → 236** días aptos (lun 42, mar 42, mié 39, jue 37, **vie 43**,
**dom 33**).

### Alcance del atlas: entra el viernes, sale el domingo

El nulo se computa sobre `COMPLETO` + `CIERRE_SEMANAL` — **lunes a viernes**. Se
excluye el domingo, y la exclusión **entra al hash de la config**:

- el bootstrap resamplea **por día como bloque**; un fragmento de 7 h no es
  intercambiable con un día de 23 h y subestimaría la varianza;
- 7.544 ticks de mediana contra 62.857–77.775 — entre **8 y 10 veces más fino**.
  Spread y slippage de otro régimen: es ejecutabilidad (jerarquía #4), no
  geometría.

**Enforcement**: el arnés de EXPLORE debe **negarse** a evaluar una zona cuyo
tipo de día no esté en el alcance del nulo. Si aparecen zonas de domingo, que
falle ruidoso en vez de compararlas contra el nulo equivocado. *Esa* es la
diferencia con la exclusión de los viernes: aquélla era accidental e invisible,
ésta es declarada y verificable.

### Aviso de método

Esto se decidió **después** de ver que los viernes estaban excluidos, y **sube
la muestra un 25 %** (153 días legítimos → 191). Es exactamente la forma que
tiene un arco movido, así que queda dicho:

- el argumento es **estructural** — el chequeo no puede pasar en un viernes por
  construcción — y vale igual sin haber visto ningún resultado del atlas;
- las cotas de cobertura son **medidas** sobre los 5 parquets, no elegidas;
- el cambio **agrega** tres chequeos y no afloja ninguna tolerancia
  (`HUECO_MIN_MINUTOS` sigue en 55);
- del atlas viejo **no se declaró ningún resultado**, así que no hay conclusión
  que este cambio pueda estar rescatando a posteriori.
