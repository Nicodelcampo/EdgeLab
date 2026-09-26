# L3 PreRange Double Sweep — auditoria independiente de la carrera simetrica

**Fecha:** 2026-08-14
**Auditor:** Notion AI (replica independiente en sandbox)
**Objeto auditado:** `specs/prerange_sweep_v0.json`, `diag/tasa_senales/prerange_sweep_formal.py`, `docs/research/PRERANGE_SWEEP_PROTOCOL_2026-08-14.md`
**Estado del objeto:** `PREREGISTERED`, sin correr sobre datos reales
**Evidencia:** `tools/sandbox/l3_touch_rule_bias.py`, `tools/sandbox/l3_power.py`

---

## 0. Veredicto

**El estimand resiste la auditoria. Lo que no resiste es el resumen con el que se
presento.**

El protocolo hace bien lo mas difícil: reemplazo una cantidad tautologica (la
tasa de doble barrido) por una cuya distribucion nula es conocida sin simular
nada. Eso es correcto y esta bien implementado en lo esencial. Intente romperlo
con 72.962 sesiones sinteticas en cinco regimenes adversariales y **no pude**.

Pero el material de difusion que acompaña la linea afirma tres cosas que el
propio spec no respalda, y una de ellas invierte el signo de una conclusion:
**"si la reversion gana 58% de las veces demostraste un edge real"** es falso
bajo los gates del propio protocolo. Con 210 sesiones, un 58/42 produce
`PRERANGE_NO_EDGE`.

| Pregunta | Respuesta auditada |
| --- | --- |
| ¿Vale profundizar en L3? | **Si.** Es la linea mejor construida del proyecto. |
| ¿Esta "100% programado y listo para correr"? | **No.** Cuatro defectos de implementacion, uno de los cuales vuelve `PRERANGE_EDGE` inemitible sin aviso. |
| ¿Se resuelve con los 1.078 M de ticks de Kaggle? | **No.** El cuello de botella son las sesiones, no los ticks. |
| ¿58% consistente en 4 activos demuestra un edge? | **No.** Es el borde exacto de lo indetectable. |

---

## 1. Que se audito y como

No audite el resumen: audite el codigo. Y no verifique el argumento del nulo por
lectura, lo **medi**.

El spec afirma:

> "revert y cont son equidistantes del anchor. Bajo difusion sin drift
> P(revert primero)=P(cont primero) EXACTAMENTE, asi que E[r]=0 por geometria."

Esto es cierto para una difusion continua. Los precios reales no son continuos:
viven en una grilla de ticks y se mueven a saltos. Con saltos, el proceso
**sobrepasa** la barrera en vez de tocarla exactamente, y si el sobrepaso es
asimetrico entre las dos barreras, el optional stopping deja de dar 50/50:

```
E[X_tau] = X_0 = 0  =>  p_up * (d + E[over_up]) = p_dn * (d + E[over_dn])
=>  si E[over_up] > E[over_dn]  entonces  p_up < p_dn
```

O sea: **una martingala perfecta puede dar un split distinto de 50/50** si sube
a saltos grandes y baja a pasos chicos. Esa es la forma tipica de un mercado
real (la ruptura va en un estallido, la vuelta va arrastrandose). Si el sesgo
fuera del orden del efecto buscado, el protocolo estaria midiendo microestructura
y llamandola edge.

Asi que construi martingalas exactas y medi.

### Diseño del test (`tools/sandbox/l3_touch_rule_bias.py`)

Camino de precios en enteros de tick, con `E[incremento] = 0` verificable a mano:

- **Simetrico:** `+1 / -1` con `p = 1/2`.
- **Asimetrico:** con probabilidad `1/(k+1)` salta `+k` ticks; si no, baja 1 tick.
  Con `k = 8`: `E[dx] = k/(k+1) - k/(k+1) = 0`. Subir es raro y grande, bajar es
  frecuente y chico.

Sobre ese camino se replica **la logica exacta del runner** (ventana, primer
barrido, segundo barrido, anchor en el close de esa barra, `d = round(rango/2)`,
objetivos espejados) y se resuelve la carrera con tres reglas de toque:

| Regla | Definicion | Quien la usa |
| --- | --- | --- |
| **A. Contencion** | `b["lo"] <= target <= b["hi"]` | `reversion_race()` hoy |
| **B. Cruce** | objetivo abajo: `b["lo"] <= target`; arriba: `b["hi"] >= target` | fix propuesto |
| **C. Tick** | primer tick del camino que alcanza un objetivo | verdad de terreno |

---

## 2. Lo que resistio: el nulo se sostiene

72.962 sesiones sinteticas, cinco regimenes:

| Regimen | n | d (ticks) | recorrido de barra | d / recorrido | `mean r` (tick) | z | discrepancia A vs C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. simetrico, ventana 60 | 10.855 | 30 | 7 | 4,29 | +0,0078 | +0,84 | **0,00 %** |
| 2. asimetrico 8:1, ventana 60 | 10.630 | 84 | 20 | 4,20 | −0,0064 | −0,68 | 0,04 % |
| 3. simetrico, ventana 6 | 17.039 | 10 | 7 | 1,43 | −0,0082 | −1,07 | 0,15 % |
| 4. asimetrico 8:1, ventana 6 | 16.894 | 26 | 20 | 1,30 | +0,0074 | +0,96 | 0,13 % |
| 5. asimetrico 8:1, ventana 3 | 17.544 | 18 | 20 | **0,90** | +0,0079 | +1,05 | **0,78 %** |

**Conclusiones medidas:**

1. **El nulo es 0 en los cinco regimenes.** Ningun `z` supera 1,07 en valor
   absoluto. Cota superior del sesgo del nulo al 95 %: **|sesgo| <= 0,023**, o
   sea **<= 15 % del MDE** (0,15). El sobrepaso asimetrico existe pero es de
   segundo orden a las escalas de `d` que produce el protocolo.
2. **El nulo no necesita simulacion.** Confirmado: el aparato del "nulo browniano
   68,33 %" era innecesario **y ademas fragil**, porque ese numero no es una
   constante universal — depende del ancho del rango frente a la volatilidad y
   del horizonte. En el propio dataset sintetico del test suite del protocolo la
   tasa de doble barrido dio **60,6 % con cero edge**; en mis regimenes cambia
   con la ventana. Comparar un 72,38 % observado contra un unico numero de
   referencia (68,33 %) no puede sostener nada: la dispersion del propio nulo
   entre parametrizaciones (60,6 % vs 68,3 %) es **el doble** del exceso que se
   estaba celebrando (+4,06 %).
3. **`d` escala con el rango, y eso salva la tautologia de la compresion.**
   Verificado: el ratio `d / recorrido_de_barra` se mantiene ~4,2 tanto en el
   regimen simetrico como en el asimetrico, porque el rango de 60 barras es
   ~`sqrt(60)` veces el de una barra. El estimand es adimensional en volatilidad.

---

## 3. Defectos encontrados

### D1 — La regla de toque es de CONTENCION, no de CRUCE (P-19)

```python
if hit_r is None and b["lo"] <= revert <= b["hi"]:
```

Esto exige que la barra **contenga** el objetivo. Si la barra pasa de largo
(todo su rango queda mas alla del objetivo), el toque **no se registra** y la
carrera sigue: el runner puede adjudicar al objetivo **opuesto** un caso en el
que el primero ya fue alcanzado. No es solo censura, es **misclasificacion de
direccion**.

Medido contra la verdad de terreno a nivel tick:

| d / recorrido de barra | discrepancia |
| --- | --- |
| 4,29 | 0,00 % |
| 4,20 | 0,04 % |
| 1,43 | 0,15 % |
| 1,30 | 0,13 % |
| **0,90** | **0,78 %** |

**Honestidad sobre el hallazgo:** el sesgo en la media es nulo (las columnas A y
C coinciden dentro del ruido en los cinco regimenes), asi que **esto no invalida
el protocolo**. Pero: (a) misclasifica casos individuales, (b) la tasa crece
monotonamente cuando `d` se acerca al recorrido de una barra, o sea **peor en el
estrato de rango comprimido**, que es exactamente el que el analisis original
reportaba como su hallazgo mas fuerte, y (c) el fix es gratis.

```python
# fix (2 lineas): cruce en vez de contencion
rev_is_down = revert < cont
hr = (b["lo"] <= revert) if rev_is_down else (b["hi"] >= revert)
hc = (b["hi"] >= cont)   if rev_is_down else (b["lo"] <= cont)
```

### D2 — `int(round(...))` es banker's rounding (P-19)

```python
d = int(round(ev["rng"] * d_frac))
```

El modulo define `price_to_tick()` con `floor(x + 0.5)` **precisamente para
evitar** el redondeo bancario de Python, y despues lo usa en el calculo de `d`.
Con `rango = 109` ticks, `round(54.5) = 54` (redondea al par), no 55. Es
simetrico entre objetivos, asi que no sesga direccion, pero es inconsistente con
la disciplina declarada del propio archivo. Usar `int(math.floor(rng*d_frac + 0.5))`.

### D3 — El gate de familia exige datos overnight, y falla en silencio (P-20)

```python
PLACEBO_OFFSETS = [o for o in range(-480, 331, 30) if abs(o) >= 60]   # 25
MIN_USABLE_PLACEBOS = 19
```

Con la primaria en 08:12, los offsets de −480 a −90 dan arranques entre **00:12 y
07:12**: son **14 de los 25 placebos**. Si el M1 de entrada es un export solo-RTH
(lo habitual en NT8), esos 14 mueren por `window_coverage` y quedan **11
usables**. Como `11 < 19`, `family_ok = False` y **`PRERANGE_EDGE` es inemitible
por construccion**.

El unico sintoma visible seria una etiqueta `PRERANGE_WINDOW_UNSPECIFIC`, que
parece un resultado cientifico ("hay reversion pero no es propiedad de esta
ventana") cuando en realidad es un problema de cobertura del archivo de entrada.
El test suite no lo caza porque genera sesiones sinteticas completas.

**Mitigacion:** gate explicito previo — si `n_usable < MIN_USABLE_PLACEBOS`,
emitir `ABSTAIN_DATA` con el motivo `placebo_family_starved`, no
`WINDOW_UNSPECIFIC`. Una abstencion y una etiqueta negativa no son lo mismo.

### D4 — Fecha calendario vs trade date, y exchangeabilidad de la familia (P-21)

```python
def group_sessions(bars):  ses.setdefault(b["date"], [])   # b["date"] = t.date()
mod = t.hour * 60 + t.minute                               # minuto del dia calendario
```

La sesion CME arranca **17:00 CT del dia previo**. Agrupar por fecha calendario
no afecta a la ventana primaria (08:12–16:00 cae dentro de un mismo dia), pero
**los 14 placebos overnight mezclan la cola de la sesion del trade date
anterior**. Ya existe `edgelab.kaggle.sessions_cme.trade_date()` commiteado
(Push A) que resuelve esto con tz real, DST incluido.

Hay algo mas serio detras. La validez del `p_perm` de permutacion **no requiere
independencia entre placebos, requiere exchangeabilidad con la primaria**. Una
ventana overnight en los indices no es exchangeable con una ventana RTH: tiene
otra liquidez, otra volatilidad y otro proceso de formacion de rango. Como 14 de
25 miembros de la familia son estructuralmente mas debiles, **ganarles rank 1 es
mas facil de lo que el test supone: el `p_perm` de la familia completa es
anti-conservador**.

**Mitigacion, ejecutable hoy porque nada se corrio todavia sobre datos reales:**
familia primaria = grilla de **15 minutos restringida a RTH** (07:00–14:12,
excluyendo `|offset| < 60`), que da **23 placebos** y un piso de
`1/24 = 0,042 < 0,05`. Los miembros se solapan entre si, lo cual **reduce
potencia pero no invalida el test** (la exchangeabilidad se conserva; la
independencia no era necesaria). La familia completa con overnight pasa a
secundaria declarada.

---

## 4. Las tres afirmaciones del resumen que los numeros no respaldan

Aritmetica exacta del spec (`tools/sandbox/l3_power.py`):

```
r en {-1, 0, +1};  f = fraccion resuelta;  p = P(revert | resuelta)
mean(r) = f * (2p - 1)
Var(r)  = f - f^2 * (2p-1)^2      ->   bajo H0:  sd = sqrt(f),  SE = sqrt(f/n)
MDE(80% potencia) = (z_{1-a/2} + 0,8416) * SE
split equivalente:  p = 0,5 + mean / (2f)
```

Con `f = 0,6` y `n = 210` esto reproduce exactamente el `SE ~ 0,054` y el
`MDE ~ 0,15` del spec, o sea que estoy usando su misma aritmetica.

### 4.1 "Si la reversion gana 58% o 62%, demostraste un edge real"

| Claim | `mean r` | z | IC95 | Etiqueta que emite el codigo |
| --- | --- | --- | --- | --- |
| 58 / 42 | 0,096 | 1,80 | [−0,009 ; +0,201] | **`PRERANGE_NO_EDGE`** |
| 62 / 38 | 0,144 | 2,69 | [+0,039 ; +0,249] | emitible |

Umbral exacto con un activo y 210 sesiones: **62,5 / 37,5**. Un 58/42 necesita
**511 sesiones** (~2 años); un 55/45 necesita **1.309** (~5,2 años).

**Y sumar activos no multiplica el n:**

| Pooling | k efectivo | n efectivo | SE | Umbral detectable |
| --- | --- | --- | --- | --- |
| ES+NQ+YM | 1,3 | 261 | 0,048 | 61,2 / 38,8 |
| ES+NQ+YM+GC | **2,3** | 462 | 0,036 | **58,4 / 41,6** |
| contarlos como 4 independientes | 4,0 | 804 | 0,027 | 56,4 / 43,6 *(ilusion)* |

Y con multiplicidad (3 ventanas × 4 activos = 12 tests, Bonferroni):

| Tests | z critico | MDE | Umbral |
| --- | --- | --- | --- |
| 1 | 1,96 | 0,101 | 58,4 |
| 3 | 2,39 | 0,117 | 59,7 |
| **12** | **2,87** | **0,134** | **61,1** |
| 25 | 3,09 | 0,142 | 61,8 |

**Lectura:** el 58 % no es una demostracion, es **el borde exacto de lo
detectable**, y solo si pooleás los cuatro activos con clustering explicito y
no testeás mas de una ventana. Si testeás tres ventanas, el umbral sube a 61,1 %
y el 58 % vuelve a ser indistinguible de ruido.

### 4.2 "Puede evaluar rango asiatico, de Londres y pre-market NY en minutos"

Esto contradice el propio spec en dos lugares:

- `prohibiciones.no_barrer_parametros`: *"d_frac, duracion, horizonte y familia
  de placebos quedan fijos por este spec. Cualquier variante es una linea nueva
  con spec nuevo."*
- `apply_provenance_cap()`: una ventana elegida mirando estos datos es
  `chosen_from_this_data` y **degrada a `WINDOW_UNSPECIFIC`**. Barrer tres
  ventanas y quedarse con la mejor produce, **por construccion, cero etiquetas
  `PRERANGE_EDGE`**. El codigo esta escrito para negarse.

Ademas cada ventana nueva arrastra su propio **lema de identificacion**: la
ventana de Londres contiene los datos macro del Reino Unido y de la zona euro, y
la asiatica los de Japon y China. El lema del spec ("ningun placebo puede
contener las 08:30") hay que rederivarlo para cada una; no se hereda.

Y un footgun de zona horaria que la amenaza T3 declara pero no resuelve: **el
Reino Unido cambia de horario de verano en fechas distintas de EE. UU.** (ultimo
domingo de marzo y de octubre, contra el segundo domingo de marzo y el primero de
noviembre). Hay **~3 semanas al año** en las que un offset fijo desalinea la
"ventana de Londres" una hora entera. Con un offset fijo, esos dias entran al
promedio midiendo otra ventana.

### 4.3 "Si el segundo barrido coincide con un BigTrap2, ¿sube al 70 %?"

Condicionar colapsa el n. Con el pool de 4 activos (462 observaciones):

| Coocurrencia BigTrap2 | n condicional | SE | Umbral detectable |
| --- | --- | --- | --- |
| 50 % | 231 | 0,051 | 61,9 |
| 30 % | 139 | 0,066 | 65,3 |
| **20 %** | **92** | **0,081** | **68,9** |
| 10 % | 46 | 0,114 | 76,7 |

La pregunta "¿sube al 70 %?" es respondible **solo si la respuesta real es
>= 69 %**, y solo pooleando los cuatro activos. Con un activo solo es
inrespondible. Ademas es un **estimand distinto**: necesita su propio spec, su
propia familia de placebos y entrar a la correccion de multiplicidad junto con
todo lo demas.

---

## 5. El punto estructural: el cuello de botella son las sesiones, no los ticks

La carrera simetrica produce **una observacion por sesion**. No una por tick, ni
una por barra: una por sesion, con los ceros adentro.

| Magnitud | Valor |
| --- | --- |
| Ticks en el dataset de Kaggle | 1.078.414.656 |
| Sesiones por activo (aprox) | ~201 |
| Observaciones utiles por sesion | **1** |
| **Ticks por observacion util** | **487.750** |

**Kaggle no aporta potencia a L3.** Aporta otra cosa, que si es valiosa:
**resolucion intrabar**, que es exactamente lo que arregla D1 y lo que elimina el
gate `ties` (T4). A nivel tick no hay empates dentro de la barra, no hay
ambigüedad de orden y la regla de toque es exacta.

Pero el port a ticks **es un spec nuevo**, no una corrida del script actual:

1. `load_m1()` lee CSV con `Time,Open,High,Low,Close`. El dataset son parquets de
   ticks con `ts_utc_ns, price_ticks, volume, bid_ticks, ask_ticks, sequence`.
2. El anchor es *"el close de la barra del segundo barrido"*. **A nivel tick no
   existe ese objeto.** Hay que redefinirlo: el trade que completa el barrido, o
   el mid del quote en ese instante. **No es indistinto:** si el segundo barrido
   bajista imprime al bid y la carrera se mide sobre precios de trade, el rebote
   de medio spread se cuenta como reversion. En 6E medi
   `spread_ticks_mean = 1,127`; con `d` de decenas de ticks el sesgo es chico,
   pero es **direccional** y hay que anclar en el **mid** y publicar la
   sensibilidad a `d`.
3. Los datos sellados cortan **2026-06-30**, y el build local de 90 dias da
   ~62-66 sesiones por activo: `MDE = 0,267`, umbral **72 / 28**. Insuficiente
   para cualquier claim realista. Para llegar a las 201 sesiones hay que usar el
   universo completo, que es justo lo que **P-18** tiene bloqueado (la v1 del
   dataset no cumple Fase 0).
4. El firewall del spec pide **forward-only desde 2026-08-14, minimo 60
   sesiones** como unico set limpio de T5. Correr sobre el dataset actual es
   `CONFIRMATORY_WITH_CAVEATS`, no un test limpio.

---

## 6. Discrepancia de ventana: 08:12 vs 08:30

| Fuente | Ventana |
| --- | --- |
| `specs/prerange_sweep_v0.json` + runner (`PRIMARY_START_MIN = 8*60+12`) | **08:12–09:12 EST** |
| Resumen de difusion de la linea | **08:30–09:30 ET** |

No son la misma ventana y la diferencia **es material** por el lema de
identificacion:

- **08:12–09:12** contiene la publicacion de 08:30 **en el interior**: el rango
  se forma antes del dato y los barridos ocurren durante la reaccion.
- **08:30–09:30** tiene el dato **en el borde de arranque**: el rango se forma
  **durante** la reaccion al dato. Es otra hipotesis, con otro mecanismo.

Y hay un costo de gobernanza: la ventana declarada tiene procedencia
`a_priori_external` ("lo vi en internet"). Cambiarla a 08:30 porque suena mejor
la convierte en `unknown` o `chosen_from_this_data`, y el `provenance_cap` la
degrada a `WINDOW_UNSPECIFIC`. **Hay que fijar una sola, con URL y autor de la
fuente**, antes de la primera corrida. El propio spec ya lo tiene como pendiente
(`window_provenance.pendiente`).

---

## 7. Orden recomendado

1. **Aplicar D1 y D2** (2 + 1 lineas) y correr los 12 bloques de
   `tests/research/test_prerange_sweep_formal.py` **antes** de tocar datos
   reales. Si los bloques siguen verdes, congelar blob.
2. **Reescribir la familia de placebos** a la grilla de 15 minutos restringida a
   RTH (23 miembros, piso 0,042) y agregar el gate `ABSTAIN_DATA /
   placebo_family_starved` de D3. Legitimo hoy porque nada se corrio.
3. **Agrupar por trade date CME** con `edgelab.kaggle.sessions_cme`, no por fecha
   calendario (D4).
4. **Fijar la ventana unica con su fuente** y registrarla en el pre-registro
   `docs/research/PREREG_KAGGLE_2026-08-14.md` como iteracion declarada: una
   ventana, un `d_frac`, el pool multiactivo con clustering por
   `market_session_key`, y la regla de decision con multiplicidad Romano-Wolf.
5. **Recien entonces correr**, y sobre M1 derivado del parquet sellado, con el
   split `--macro-dates` obligatorio (T1 no se controla con placebos: lo dice el
   lema del propio spec).

### Entradas para `PENDIENTE.md` (a fusionar en el proximo commit)

- **P-19 — regla de toque por contencion y banker's rounding en `d`.**
  `reversion_race()` usa contencion en vez de cruce: discrepancia medida vs
  verdad-tick de 0,00 % a 0,78 % segun `d / recorrido_de_barra`, peor en rango
  comprimido. `int(round())` contradice `price_to_tick`. **Abierta, no
  bloqueante** (no sesga la media; verificado en 5 regimenes).
- **P-20 — la familia de placebos exige datos overnight y falla en silencio.**
  14 de 25 placebos arrancan 00:12–07:12; con M1 solo-RTH `n_usable <= 11 < 19`
  y `PRERANGE_EDGE` es inemitible, pero el runner emite `WINDOW_UNSPECIFIC` como
  si fuera un resultado. **Abierta, bloqueante para emitir cualquier etiqueta
  L3.**
- **P-21 — fecha calendario vs trade date CME y exchangeabilidad de la familia.**
  `group_sessions` agrupa por `t.date()`; 14 placebos overnight cruzan el borde de
  sesion de 17:00 CT y no son exchangeables con una ventana RTH, lo que hace el
  `p_perm` anti-conservador. **Abierta, bloqueante para interpretar `p_perm`.**
- **P-22 — L3 fuera del pre-registro.** La ventana, el pool multiactivo, la
  grilla de `d` y la interaccion con BigleTrap2 no estan congelados en
  `PREREG_KAGGLE`. Sin eso, cada ventana adicional es un test no contado.
  **Abierta, bloqueante para la primera corrida.**

---

## 8. Reproduccion

```bash
python3 tools/sandbox/l3_touch_rule_bias.py   # 5 regimenes, 72.962 sesiones, ~30 s
python3 tools/sandbox/l3_power.py             # tablas de potencia y MDE
```

Entorno de la corrida: Python 3.13.13, numpy 2.5.1, sandbox Amazon Linux 2023,
semilla `20260814`, sin dependencias externas. Salidas:
`touch_rule_bias2.json`, `power_l3.json`.

**Nota de alcance:** todo lo medido aca es sintetico y adversarial por diseño.
No toque el holdout, no computé el estimand sobre datos reales y no hay ninguna
afirmacion sobre si existe o no un edge de reversion en rangos. Este documento
auditа el **instrumento**, no el mercado.
