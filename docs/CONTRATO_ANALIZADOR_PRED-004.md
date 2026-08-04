# Contrato del analizador de PRED-004 — **v2**, re-congelado 2026-08-04

> **v1 (`52b0db7`) NO APROBADO.** Cuatro bloqueantes verificados por el auditor,
> los cuatro reproducidos en mi propio código antes de conceder. Esta es la v2.
>
> `contrato_sha` **v1** = `6d0e87b7…` (retirado)
> `contrato_sha` **v2** = **`109f41c1cfcdca97848482f3c3cb956fe0ae49db411be239342cc30370366f0c`**

> **Se congela ANTES de producir ningún EventLog nuevo.** Cambiar cualquiera de
> estas definiciones después de una captura invalida la medición: el porcentaje
> se podría mover sin tocar el `.cs`.
>
> Implementación: `tools/pred004_analyze.py` · Batería: `tests/bridge/test_pred004_analyze.py`
> (**30/30 en verde**, incluido el control negativo). Suite completa: 665 passed,
> 2 failed (los dos rojos declarados).

## Los cuatro bloqueantes de v1 — reproducidos y corregidos

### B1 · `sesion_de()` no convertía timezone

`SESION_TZ` estaba en el hash del contrato y **no aparecía en una sola línea de
código ejecutable**: sólo en su definición y en `CONTRATO_SHA_CAMPOS`. El hash
certificaba un parámetro inerte. Se leía `d.hour` directo de `Time[0]`, que viene
en hora del chart; con chart en ART y junio en CDT la frontera caía 2 h antes.

**v2:** conversión explícita a `America/Chicago` con `zoneinfo`, y `--tz-chart`
es **argumento obligatorio sin default**. Sin tz determinable ⇒ ABSTAIN.
Cubierto por `test_B1_la_tz_del_chart_cambia_la_sesion` y
`test_B1_sesion_tz_esta_realmente_en_uso` (inspecciona el fuente).

### B2 · `WARMUP_SESIONES=1` podía producir PASS por construcción

Construí el control negativo con el defecto REAL de v2.2/K=25 (485 mismatch en
las barras 1..2571 de 12.395) y medí la regla vieja:

| sesiones | estado | tasa interior | evidencia borrada |
|---|---|---|---|
| 4 | FAIL | **1,0544 %** | **80 %** |
| 5 | FAIL | 1,1799 % | 76 % |
| 6 | FAIL | 1,7530 % | 63 % |
| 8 | FAIL | 2,3241 % | 48 % |

No llegó a dar PASS, **pero con 4 sesiones el margen es 0,05 puntos** y se borra
el 80 % de la evidencia. El veredicto de un defecto conocido dependía de cuántas
sesiones tuviera la captura. **Eso no es un criterio.**

**v2:** warm-up por **conteo acotado de barras**, derivado del mecanismo y no de
los datos: se excluyen las barras anteriores al **primer `ANCLAJE_VERIFICADO`**,
que es cuando el `.cs` declara el ancla establecida (`BigTrap2.cs:453`), con tope
duro de 500 barras (superarlo ⇒ ABSTAIN).

Resultado sobre el mismo control: **FAIL, con `excluidos_por_warmup = 0` y tasa
interior = tasa total = 3,91 %** — que reproduce exactamente el `K25 = 3,91 %`
documentado en PRED-003. La regla nueva **no borra evidencia**, y ese 3,91 % es
el control externo del control.

### B3 · P4 era inalcanzable

v1 hacía `proc -= amb`: **asumía** la abstención en vez de verificarla. Si el
`.cs` procesaba una barra ambigua, v1 la quitaba del denominador y la reportaba
como abstención — ocultando justo la violación que P4 vigila. Misma forma que el
`ATTRIBUTION_MISMATCH` inalcanzable de `tickbar_diag.py`.

**v2:** P4 tiene veredicto propio y FAIL alcanzable. Violación = barra ambigua
que **además** emitió `ANCLAJE_VERIFICADO`, o que siguió emitiendo eventos
económicos. Tests: `test_B3_P4_barra_ambigua_que_igual_se_proceso_es_FAIL`,
`test_B3_P4_barra_ambigua_con_evento_economico_es_FAIL`.

### B4 · P3 sin veredicto y con contador contaminado

`pares_procesados_sin_igualdad_ohlcv` contaba **todos** los
`FOOTPRINT_MISMATCH`, sin intersectar con `proc` ni excluir warmup/tail, y no
afectaba el estado. Verificado en vivo: mi propio test de warmup daba **PASS con
el contador en 30**.

**v2:** P3 tiene `p3_estado` propio, población explícita (**sólo pares
PROCESADOS**) y FAIL alcanzable. Tests:
`test_B4_P3_tiene_veredicto_propio_y_es_alcanzable`,
`test_B4_P3_no_cuenta_mismatch_de_barras_no_procesadas`.

## No bloqueantes

- **N1** — P5 compara `seq` absoluto, contaminado porque `eventSeq++` es
  compartido con los diagnósticos que el contrato excluye. **Pendiente**: falta
  agregar inventario de tipos y reportar el corrimiento de `seq` como hallazgo
  separado. Declarado, no resuelto.
- **N2** — **P6 no puede detectar overwrite** y queda declarado: cubre append,
  meta única, monotonía de `seq` y filas malformadas. El overwrite se verifica
  **por procedimiento**: inventario de `oracles\` antes y después, tres archivos
  nuevos, ninguno preexistente. Es paso obligatorio del reporte de captura.
- **N3** — sin `# meta` ahora es **ABSTAIN**, nunca medición
  (`test_N3_sin_meta_es_ABSTAIN_nunca_medicion`).
- **N4** — `TAIL_BARRAS` queda en **0** y se registra como **decisión nueva
  post-oráculo**: `parity.py` define su frontera de madurez por `max_age_bars`,
  que es ciclo de vida de ZONAS; una barra atribuida no tiene ciclo de vida, así
  que no hay antecedente que reconciliar.
- **N5 — P5 ABRE EL HOLDOUT, y es peor de lo señalado.** Medí la ventana real del
  oráculo histórico: **`2026-07-07T19:04` → `2026-07-24T17:59`**. Está
  **entero** dentro del holdout sellado (≥ 2026-07-01) **y entero dentro de la
  cuarentena de INC-005** (07-01 → 07-24). Correr P5 exige registrar la apertura
  en `docs/holdout_access_log.md` con propósito `target_free_validation` **antes**
  de leerlo. **Gate duro, sin resolver.**

## Exigencia transversal de reporte

Toda salida de `p1-p2-tick` publica: `tasa_mismatch_total` (sin exclusiones),
`tasa_mismatch_interior`, `footprint_mismatch_total`, `excluidos_por_warmup`,
`excluidos_por_tail` y `desglose_por_sesion`. **La exclusión no puede ser
invisible** — verificado por
`test_exigencia_transversal_publica_total_interior_y_exclusiones`.

## 0. Por qué existe — los tres defectos del instrumento anterior

El preflight (`e8f187a`) proponía medir PRED-004 con `run_nt8_bridge.py` y
`correr_gates.py`. **Verificado en el código: los dos miden otra cosa.**

| # | defecto | evidencia |
|---|---|---|
| 1 | `run_nt8_bridge.py --oracle <log nuevo>` compara **Python vs NT8 v2.3**, no v2.1 vs v2.3 | `tools/run_nt8_bridge.py:233` → `oracle.parse_nt8_log(...)` + `match_zones(...)` |
| 2 | `correr_gates.py` sí usa el CSV histórico, pero por el **matcher de paridad** con tolerancia temporal, geometría y ciclo de vida — no igualdad bit a bit | `tools/correr_gates.py:55` |
| 3 | El `FOOTPRINT_MISMATCH` reportado sale de `p1a_gate(ticks, bars, fps)` — **los tres argumentos son objetos Python** | `edgelab/bridge/bars.py:212-222` |

### La colisión de nombres, que es la causa raíz

**Hay dos cosas distintas llamadas `FOOTPRINT_MISMATCH`**, y el propio repo lo
dice en `edgelab/bridge/bars.py:116`: *"no lo mide `FOOTPRINT_MISMATCH` (que
compara NT8 contra sí mismo)"*.

| nombre | quién lo emite | qué compara | ¿mide P1/P2? |
|---|---|---|---|
| `FOOTPRINT_MISMATCH` (EventLog) | `nt8/BigTrap2.cs:529,589` | bloque atribuido vs barra primaria, **dentro de NT8** | **SÍ** |
| `FOOTPRINT_MISMATCH` (`p1a_gate`) | `edgelab/bridge/bars.py:221` | footprint Python vs volumen de barra Python | **no** |

Por eso el instrumento equivocado habría devuelto un número **con la etiqueta
correcta**: podía reportar cero mismatch con la atribución de NT8 rota. Es
exactamente la clase de instrumento que estas iteraciones vienen a eliminar.

## 1. Formato del EventLog (verificado en el `.cs`, no supuesto)

```
# meta indicator=BigTrap2,version=2.3,attribution=...,instrument=...
{seq}|{Time[0]:o}|{TYPE}|{k=v;k=v;...}
```

`LogEvent`, `nt8/BigTrap2.cs:879`:
`"{0}|{1:o}|{2}|{3}", eventSeq++, Time[0], type, payload`

**Los diez tipos que emite v2.3:** `ANCLAJE_AMBIGUO`, `ANCLAJE_VERIFICADO`,
`ERROR`, `FOOTPRINT_MISMATCH`, `SESION_RESINCRONIZADA`, `TRAP`, `ZONE_CREATED`,
`ZONE_EXPIRED`, `ZONE_INVALIDATED`, `ZONE_TOUCHED`.

### Corrección al preflight: el nombre de archivo no es `time1`

`nt8/BigTrap2.cs:852`:

```csharp
string bs = BarsPeriod.BarsPeriodType.ToString() + BarsPeriod.Value.ToString(...);
```

La API de NT8 identifica las barras de minuto por **`BarsPeriodType.Minute`**,
así que el sufijo real es **`__Minute1`**, no `__time1` como decía el preflight.
Para tick es `__Tick25` / `__Tick10` (consistente con el oráculo existente
`tickbar_frontera3_10t__Tick10.csv`).

**El analizador nunca asume el nombre:** recibe la ruta real y verifica la
resolución declarada contra ella (`p6-file --resolucion`).

## 2. Definiciones congeladas

### Warmup

**`WARMUP_SESIONES = 1`.** Toda barra cuya sesión sea la **primera presente en el
log** queda excluida. Operacionaliza la regla del contrato de paridad
(`docs/nt8_indicator_parity_contract.md`): *"Ninguna barra de la primera sesión
posterior a la carga del chart entra a una comparación de paridad"*.

### Maturity tail

**`TAIL_SESIONES = 1`.** La **última sesión presente** queda excluida. Es
simétrico y por un motivo estructural, no estético: esa sesión está truncada por
donde terminó la captura, así que sus bloques de atribución pueden estar
incompletos **por la ventana, no por el kernel**.

### Frontera de sesión

**17:00 hora de Chicago**, convención `[inicio, fin)`: un evento a las ≥ 17:00
pertenece a la sesión que cierra al día siguiente. Misma regla que
`edgelab/bridge/bars.py:session_ids`.

### Denominador

**`barras_procesadas_interior`** = barras con `ANCLAJE_VERIFICADO` dentro del
interior (fuera de warmup y tail), **menos** las que abstuvieron.

| caso | numerador | denominador | reporte |
|---|---|---|---|
| barra verificada, sin mismatch | no | **sí** | — |
| barra verificada, con mismatch | **sí** | **sí** | — |
| barra con `ANCLAJE_AMBIGUO` | **no** | **no** | abstención, por separado |
| barra en warmup o tail | no | no | `excluidos_por_warmup_o_tail` |

**Una barra que abstuvo no fue procesada.** Meterla al denominador convertiría
una abstención fail-closed en un acierto — está cubierto por el test
`test_p1p2_ambigua_con_mismatch_no_infla_el_denominador`.

**Denominador 0 ⇒ ABSTAIN**, nunca PASS.

### Umbral

**`UMBRAL_MISMATCH = 0.01`** (1 %), del JSON pre-registrado.

## 3. Los tres modos

### `p5-time` — histórico v2.1 vs nuevo v2.3

Compara, en este orden: cantidad de eventos económicos, y por cada uno **tipo,
timestamp, `seq` y todos los campos del payload**.

**Metadata que PUEDE diferir — lista CERRADA:**

| clave | por qué |
|---|---|
| `version` | 2.1 → 2.3 es justamente lo que se está probando |
| `attribution` | clave nueva en v2.3, ausente en v2.1 |
| `anchor` | idem |

**Cualquier otra clave que difiera ⇒ FAIL.** Verificado con
`test_p5_metadata_NO_permitida_cambiada_es_FAIL` (cambiar `imbalance_ratio` rompe).

**`P5_PAYLOAD_IGNORABLE` está vacío a propósito.** Si alguna vez hiciera falta
agregar un campo, se agrega acá **en el mismo commit que lo introduce**, nunca
después de ver un log.

**Tipos comparados:** `TRAP`, `ZONE_CREATED`, `ZONE_TOUCHED`,
`ZONE_INVALIDATED`, `ZONE_EXPIRED`. Los diagnósticos quedan fuera porque v2.3
los introduce o los cambia **por diseño** — es el cambio autorizado — y
compararlos haría fallar P5 por el cambio que P5 no está evaluando.

**Formatos no comparables ⇒ ABSTAIN, nunca PASS** (sin `# meta`, o un log sin
eventos económicos).

### `p1-p2-tick` — atribución, leyendo el EventLog de NT8

Emite: `sesiones_totales`, `sesiones_interior`, `barras_procesadas_interior`,
`footprint_mismatch_interior`, **`tasa_mismatch_interior`**,
`barras_ambiguas_interior`, `candidatos_cero`, `candidatos_multiples`,
`pares_procesados_sin_igualdad_ohlcv`, `excluidos_por_warmup_o_tail`.

**La tasa interior y la abstención se reportan por separado.** Nunca se suman ni
se compensan.

### `p6-file` — integridad del archivo

Exactamente una `# meta` · exactamente un inicio de `seq` · secuencia monótona ·
cero filas malformadas · resolución del nombre coherente · `sha256`.

Cubre el defecto real de `BigTrap2_tick25_6E_0926_v22.csv` (tres corridas
appendeadas, cada una arrancando en `seq=0`, con una sola `# meta`) —
`test_p6_dos_corridas_appendeadas_es_FAIL`.

**P6 no se aprueba por inspección de código.** El código *parece* correcto
(`BigTrap2.cs:853-858` compone `<base>__<bar_spec>` y prueba `_2`, `_3`… antes de
abrir), pero el PASS exige verificar los archivos reales.

## 4. Salida content-addressed

Cada corrida emite un JSON con `contrato_sha`, el contrato completo embebido, el
`sha256` de cada archivo de entrada y su propio `resultado_sha256`. **El veredicto
no se redacta a mano.** Si el `contrato_sha` difiere entre dos corridas, los
números no son comparables y el reporte lo dice.

## 5. Batería sintética — 24/24

Los logs se **fabrican** en el test. **No se usó el oráculo nuevo ni se abrió
ningún outcome**: el instrumento queda validado *antes* de que exista la captura
que va a medir, o se estaría calibrando contra el resultado.

| exigencia del auditor | test |
|---|---|
| P5 idéntico salvo versión permitida → PASS | `test_p5_identico_salvo_version_permitida_es_PASS` |
| evento cambiado → FAIL | `test_p5_evento_cambiado_es_FAIL` |
| fila agregada → FAIL | `test_p5_fila_agregada_es_FAIL` |
| fila eliminada → FAIL | `test_p5_fila_eliminada_es_FAIL` |
| metadata no permitida → FAIL | `test_p5_metadata_NO_permitida_cambiada_es_FAIL` |
| formatos no comparables → ABSTAIN | `test_p5_formatos_no_comparables_es_ABSTAIN_no_PASS` |
| archivo con dos corridas → FAIL | `test_p6_dos_corridas_appendeadas_es_FAIL` |
| candidato cero nunca procesada | `test_p1p2_candidato_cero_nunca_cuenta_como_procesada` |
| candidatos múltiples nunca procesada | `test_p1p2_candidatos_multiples_nunca_cuenta_como_procesada` |
| mismatch en warmup excluido | `test_p1p2_mismatch_en_warmup_se_excluye` |
| mismatch en tail excluido | `test_p1p2_mismatch_en_tail_se_excluye` |
| mismatch interior contado | `test_p1p2_mismatch_interior_se_cuenta` |
| denominador cero → ABSTAIN | `test_p1p2_denominador_cero_es_ABSTAIN_no_PASS` |
| K25 y K10 sin cambiar reglas | `test_p1p2_K25_y_K10_usan_las_MISMAS_reglas` |

Extras: timestamp cambiado → FAIL · dos `# meta` → FAIL · resolución que no
corresponde → FAIL · sin interior → ABSTAIN · contrato hasheable · resultado
content-addressed.

## 6. Uso

```bash
cd E:\ProyectosQuant\EdgeLab-sync-desktop

# P5 — el histórico va del lado izquierdo, siempre
.\.venv\Scripts\python tools\pred004_analyze.py p5-time \
  --historico oracles\BigTrap2_time1_6E_0926_v2.csv \
  --nuevo     oracles\<nombre REAL generado, __Minute1> \
  --out runs\pred004\p5.json

# P1 / P2 — la resolución se verifica contra el nombre real
.\.venv\Scripts\python tools\pred004_analyze.py p1-p2-tick \
  --log oracles\<real __Tick25> --resolucion Tick25 --out runs\pred004\p1_k25.json
.\.venv\Scripts\python tools\pred004_analyze.py p1-p2-tick \
  --log oracles\<real __Tick10> --resolucion Tick10 --out runs\pred004\p2_k10.json

# P6 — uno por cada archivo generado
.\.venv\Scripts\python tools\pred004_analyze.py p6-file \
  --log oracles\<real> --resolucion <Minute1|Tick25|Tick10> --out runs\pred004\p6_<res>.json
```

## 7. Correcciones al preflight que quedan asentadas

1. **K=10 se ejecuta aunque K=25 refute.** P2 está pre-registrada y el orden
   completo es `time:1 → K25 → K10`. Frenar después de K=25 eliminaría una
   predicción ya registrada.
2. **P6 no se aprueba por inspección**, se verifica sobre los archivos reales.
3. **No se asumen los nombres** `__time1`/`__Tick25`: se usa el generado y se
   verifica su metadata. Minuto es `Minute1`.
4. **`TickBarDiag` queda fuera de alcance** — no resuelve ninguno de estos tres
   defectos; el instrumento que hacía falta es éste.

## 8. Estado

**El bloqueo no está en NinjaTrader ni en BigTrap2 v2.3.** Estaba en que el
proyecto no tenía un instrumento que midiera PRED-004 como fue escrita. Ejecutar
antes habría producido un PASS que no responde la pregunta pre-registrada.

**Nada ejecutado:** no se copió el `.cs`, no se abrió NT8, no se corrió ninguna
captura, no se movió el pin, no se resolvió 2.3/2.2, no se copió ningún oráculo
entre carpetas. `outcomes_accessed: false` sigue siendo cierto.

**Aporte al referente:** convierte PRED-004 de una predicción no medible en una
medible, cerrando la vía por la que una captura cara habría devuelto un PASS con
la etiqueta correcta y el contenido equivocado — el modo de falla más caro que
tiene este proyecto, porque no deja rastro.
