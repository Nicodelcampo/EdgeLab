# ENMIENDA de protocolo — BigTrap2Absorption — 2026-08-22

**Autor**: Grok 4.6 (selector del chat de Notion; identidad no verificable desde adentro).
**Cierra**: seccion 4 de `REVISION_MULTIMODELO_BT2_OPUS5.md` @ `e96652f`.
**Cuando**: ANTES de abrir outcomes. Si se corre junio sin esto, la corrida no cuenta.
**Holdout**: agosto no se toca. H-GC-BT2-1 no se reabre.

**CONFIRMADO por Nico**, 2026-08-22 20:55 ART, chat Notion (thread de auditoria):
`ScoreMode = AbsMagnitude` y el resto del headline de la seccion 1. Ya no se veta el modo
sin acta nueva. Despues de abrir outcomes, no se cambia.

---

## 1. Headline congelado

```
ScoreMode            = AbsMagnitude
TapeWindowTicks      = 25
AbsorptionPct        = 90
AbsorptionLookback   = 500
MinHistoryBuckets    = 200
MinStackedRows       = 2
MinTrapFrac          = 0.20
RequireFlowSideMatch = true
```

`AbsDirectional` es **trial 2**, mismo export (`signed_flow`, `d_ticks`), mismo protocolo,
**despues** de cerrar o fallar el headline. No salva la Puerta 1.

El score se nombra **trade imbalance / |dPx| con percentil causal**. No se llama OFI. No se
llama residuo. No se llama escala-libre.

---

## 2. Enmienda de sesiones (el protocolo original no era ejecutable)

24–30 jun 2026 = lun 22 es anterior; 24=mie, 25=jue, 26=vie, 27–28=finde, 29=lun, 30=mar.
Trade dates CME en esa ventana: **5 dias habiles** (24, 25, 26, 29, 30), no 10.

**Piso operativo**: N = sesiones efectivamente presentes en la cinta de discovery de GC 08-26
con `trade_date < 2026-07-01`.

| N | que se hace |
|---|---|
| N < 5 | no se abren outcomes; falta cinta |
| 5 <= N < 10 | se corre; **debilitamiento declarado**; inferencia clusterizada por sesion obligatoria |
| N >= 10 | piso original, sin debilitamiento |

Si existe mas cinta pre-julio (p. ej. 22–23 jun), entra. No se inventan sesiones. El N real
se escribe en el acta de la corrida **antes** de mirar MFE/MAE.

---

## 3. Puertas, en orden

**Puerta 0 — tecnica, sin outcomes.** Hash y parametros congelados. `check_nt8_cs.py` verde.
Kernel Python versionado con cortes de sesion (`residual`, fuera del anillo). Paridad contra
el mismo tipo de export, con artefacto JSON en el repo. El string `EXACT` de `visor_server.py`
no cuenta. Fallar esto invalida la corrida.

**Puerta 1 — simetria, target-free.** Decil superior de `a_score` del headline.
`MFE p50 / MAE p50 >= 1,25`. n >= 200 eventos. Sesiones = N de la seccion 2. Inferencia
reagrupada por sesion. Si falla, se cierra. No hay SL/TP.

Prediccion ya escrita (Kimi K3, seccion 3): **no pasa**, ratio entre 0,95 y 1,15. Esta
enmienda no agrega otra.

**Puerta 2 — control S1, no cero.** Se **recomputa** S1 en las mismas sesiones de junio, con
el estimand de F2.9 (`r_i`). Contraste primario: `nuevo - S1` pareado por sesion. Pasa solo si
el limite inferior del IC 95 % es > 0. Comparar contra el +0,0383 historico **no vale** (mezcla
muestras). Si S1 no se puede instanciar en la ventana: puerta **no medida**, no aprobada.

**Puerta 3 — economia.** Una sola monetizacion, congelada ahora: `SL=13 / TP=30 / BE=off`.
Se declara: esa celda se vio en el holdout gastado (`h_gc_bt2x_path_overfit.json`, +0,7226 t).
Esta corrida es discovery, no confirmacion. Media bruta >= 2,5 ticks. La grilla es
exploratoria y no sustituye al headline.

Fallar cualquiera → acta en `EDGES_DISCOVERED.md`. Pasar las tres → `SURVIVES_DISCOVERY`,
no "edge". No queda holdout intacto.

---

## 4. Censos target-free, antes de la Puerta 1

Sobre el export de junio, sin caminos:

1. Fraccion de cubetas con `dFav <= 0` (donde `AbsDirectional` degenera; aca es diagnostico).
2. Fraccion de `a_pass` del headline con denominador = 1 vs > 1. Si la mayoria es 1, el
   indicador es volumen con otro nombre.
3. Estacionariedad de `a_thr` entre sesiones. Si deriva fuerte, el percentil mide regimen.

---

## 5. Prohibiciones (siguen)

No reabrir H-GC-BT2-1. No disenar con agosto. No tunear L2 (join junio = 3/20.486). No usar
`SizeScaling` ni `TopPercentFilter`. No medir contra cero. No barrer q/filas/fraccion para
elegir el headline despues de ver outcomes.
