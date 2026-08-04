# Contrato del analizador de PRED-004 — congelado 2026-08-04

> **Se congela ANTES de producir ningún EventLog nuevo.** Cambiar cualquiera de
> estas definiciones después de una captura invalida la medición: el porcentaje
> se podría mover sin tocar el `.cs`.
>
> `contrato_sha` = **`6d0e87b7cf43d1ca6d0c94aafae0d85ee3ad5deea1f41f052b2ff27e20f6f9e8`**
>
> Implementación: `tools/pred004_analyze.py` · Batería: `tests/bridge/test_pred004_analyze.py`
> (**24/24 en verde**). Suite completa: 659 passed, 2 failed (los dos rojos declarados).

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
