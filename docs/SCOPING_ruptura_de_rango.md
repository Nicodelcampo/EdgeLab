# SCOPING — familia "ruptura de rango horario"

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md),
> sha256 `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`.
>
> **ESTADO: SCOPING. No es un manifiesto, no autoriza correr nada.** Sellar una
> grilla exige un manifiesto de campaña con su presupuesto de hipótesis.
> Registrado a pedido de Nico para que el auditor lo lea del repo.

## Justificación económica

La pregunta de Nico —*"¿qué rango horario al ser roto produce entrada, con qué
características, con qué SL y TP, estático o dinámico, y con los indicadores
encima?"*— describe una familia entera de hipótesis. Antes de escribir una sola
línea de estrategia hay que saber **qué falta de verdad** para correrla, porque
el orden de construcción depende de eso y equivocarse cuesta semanas.

## Cómo podría refutarse

Si al intentar generar señales de ruptura contra `edgelab/research/sim.py`
apareciera un campo requerido que el contrato de señal no admite (por ejemplo,
una salida que no sea target/stop/time-stop), la conclusión "sólo falta el
generador" quedaría refutada y habría que tocar la spec **sellada** del
simulador — que es trabajo de otro orden de magnitud.

---

## 0. CORRECCIÓN — dos afirmaciones mías eran falsas

En el chat del 2026-08-05 afirmé que faltaban walk-forward y el desglose de
costos. **Las dos son falsas.** Me apoyé en
[`edge_pipeline_inventory.md`](edge_pipeline_inventory.md), que dice textual
*"Walk-forward — No existe como función reutilizable"* y *"costos no
desglosados"*.

**Ese inventario está VENCIDO.** Es de FASE 3a, read-only, y es anterior a la
implementación del 2026-07-25. Verificado hoy:

| lo que afirmé | realidad | evidencia |
|---|---|---|
| walk-forward no existe | **existe y está testeado** | `edgelab/research/g2.py:196`, `tests/research/test_g2.py` **27/27 en verde** |
| costos no desglosados | **4 escenarios, fuente única** | `edgelab/research/costs.py` (`ideal/base/adverso/severo`) |
| motor tick vs bar-as-of sin decidir | **decidido**: simulador propio | `sim.py:6` — *"`edgelab/engine.py` (legacy) NO se usa para evidencia formal"* |

**Causa raíz:** leí un documento de inventario como si fuera estado actual. Un
inventario fechado no es una fuente de verdad sobre el presente; el código sí.

**Consecuencia para el repo, más allá de este scoping:** cualquiera que lea
`edge_pipeline_inventory.md` hoy —el auditor incluido— va a sacar las mismas
tres conclusiones falsas. El documento necesita un encabezado de vencimiento.
Queda anotado como pendiente, no corregido acá (sería mezclar dos cambios).

---

## 1. Lo que ya está construido

**El contrato de señal del simulador ya tiene los ejes de la pregunta.**
`sim.simulate` consume señales con:

```
signal_id · available_at · dir · target_ticks · stop_ticks · [time_stop_ms]
```

Esto tiene dos consecuencias fuertes:

- **SL y TP son parámetros por señal, no del motor.** Barrer anchos no toca el
  simulador.
- **"Estático vs dinámico" sale gratis.** Un SL dinámico es calcular
  `stop_ticks` desde el ATR **en el momento de la señal**. El simulador no
  distingue, y la causalidad la garantiza `available_at`.

Además ya está resuelto, y son las partes difíciles:

- **Ambigüedad target/stop en la misma barra** → `sim.py:148` *"GANA EL
  ADVERSO"*, con `exit_reason="stop_ambiguous"` contado aparte.
- **Firewall del holdout dentro del simulador** (`sim.py:86`): declara su propia
  ventana y la registra. No depende de que el investigador se acuerde.
- **G2 completo y verificado en los dos sentidos** — sobre ruido debe rechazar,
  sobre efecto plantado debe **aprobar**. Un gate que sólo sabe decir "no" no
  sirve para encontrar edges.
- **`evaluar()` trata todo gate no evaluado como FAIL.** No se puede aprobar por
  omisión.

Y la familia tiene un antecedente: [`strategies/orb.py`](../strategies/orb.py),
**config única sin grilla**, con prior BAJA pre-registrada. Con un comentario que
vale por sí solo (línea 75): el stop del short estaba anotado **como ganancia**,
cazado por la validación tick F6.1. Es el modo de falla que una fuerza bruta
sobre SL/TP amplifica hasta fabricar edges falsos, porque el bug tiene signo y
la búsqueda lo persigue.

## 2. Lo que falta de verdad

| # | falta | alcance |
|---|---|---|
| 1 | **generador de señales de ruptura** en el mundo bar-as-of: rango parametrizable, características de ruptura, SL/TP por señal | esta familia |
| 2 | **manifiesto de campaña** con la grilla sellada y su presupuesto | esta familia |
| 3 | **`COMMISSION_PER_SIDE_USD = 2.20` es una ESTIMACIÓN** | **TODAS** las campañas |

El #3 no es mío: está declarado en `costs.py:19-20` como *"pendiente de
confirmar con estados de cuenta reales de Nico (dato faltante #1)"*, y **bloquea
G3**. Ninguna campaña puede declarar viabilidad económica hasta que ese número
sea real. Es el único bloqueo transversal vigente, y **no se resuelve
programando**: se resuelve con un estado de cuenta.

## 3. La multiplicidad NO es el obstáculo

Reproducible: `python diag/multiplicidad/costo_fuerza_bruta.py`

Calibrado contra los dos puntos ya registrados en
[`ESPEC_TEST_EXPLORE-001.md`](ESPEC_TEST_EXPLORE-001.md) —`M_eff=21,2 → z=3,041`
y `M_eff=106 → z=3,496`— que el script reproduce con `assert`, no con un
comentario. Confirma que la regla en uso es **Bonferroni bilateral**.

| espacio | M | MDE | vs base |
|---|---|---|---|
| las 3 hipótesis actuales | 21,2 | 1,14 t | — |
| + barrido de resolución (ya pagado) | 106 | 1,27 t | ×1,12 |
| 10.000 celdas | 10⁴ | 1,59 t | ×1,39 |
| **fuerza bruta completa** | **1.327.104** | **1,86 t** | **×1,63** |

**Un millón de celdas cuesta +63% de MDE, no un orden de magnitud**, porque
`z ~ √(2·ln M)`. Y es **cota superior**: el `M_eff` honesto es mucho menor que
`M` —un SL de 12 ticks y uno de 13 son casi la misma hipótesis— igual que
`M_eff=21,2` salió de una correlación de 0,669 entre 40 series.

Contra el margen medido a f=10 (**1,60×**) la fuerza bruta entera queda **al
borde**: ×1,63 vs 1,60. Apretado, no imposible.

**El gate que mata esta familia es PBO, no Bonferroni.** Con una grilla así,
`pbo_cscv` sobre la matriz completa configs × tiempo tiende a 0,5 por
construcción, y el umbral duro es ≤ 0,50. Recortar la grilla para "ahorrar
multiplicidad" no compra casi nada; lo que compra margen es que las celdas sean
**mecánicamente distintas**, no menos.

---

## 4. Rúbrica de comparación — **declarada ANTES de leer la tarea del auditor**

Nico pidió comparar el aporte al referente de esta propuesta contra la tarea que
el auditor está preparando. La rúbrica se fija ahora, sin conocerla, por la
misma razón por la que se pre-registra todo lo demás: **elegir el criterio
después de ver las opciones es elegir el resultado.**

Criterios, en orden lexicográfico (el primero que discrimina, decide):

1. **¿Desbloquea un gate cerrado?** Un gate cerrado invalida **todo** lo que está
   aguas abajo, sin importar cuánto trabajo se acumule ahí. Máxima prioridad.
2. **¿Sirve a todas las campañas o a una?** Transversal > específico, a igual
   costo.
3. **¿Qué pasa si NO se hace?** Si la respuesta es *"se puede correr igual, pero
   el resultado no es interpretable"*, es bloqueante disfrazado de opcional —
   trabajo que produce evidencia no interpretable tiene aporte **negativo**,
   porque consume presupuesto de multiplicidad sin poder decidir.
4. **¿Consume recursos irreversibles?** Aperturas de holdout y presupuesto de
   hipótesis no se recuperan. A igual aporte, gana lo reversible.
5. **¿Es sustrato o es medición?** El sustrato (paridad, determinismo) no acerca
   por sí solo, pero sin él la medición es ruido con formato de resultado.

**Autoevaluación de esta propuesta, escrita antes de la comparación** (si no se
escribe ahora, después se ajusta para ganar o perder según convenga):

| criterio | esta propuesta |
|---|---|
| 1 · gate cerrado | **NO.** G2 y G3 están construidos; el único bloqueo (comisión real) **no lo resuelve esta tarea** |
| 2 · alcance | **específico** — el generador de ruptura sirve a esta familia |
| 3 · si no se hace | no pasa nada: no hay evidencia pendiente que dependa de esto |
| 4 · irreversible | **sí consume** — sella grilla y cobra presupuesto |
| 5 · sustrato | medición |

**Lectura honesta: aporte MEDIO-BAJO en el margen.** Es una hipótesis nueva
sobre un aparato que ya funciona, y cobra presupuesto. No desbloquea nada.

Con el criterio 1, **cualquier tarea que desbloquee un gate cerrado le gana**, y
hoy hay dos candidatos obvios a eso: la comisión real (dato faltante #1, bloquea
G3 para todo) y PRED-004 (bloquea la validez técnica de BigTrap2 en barras de
tick, que es el insumo de H1).

**Sesgo declarado:** la propuesta es mía, así que la autoevaluación tiene
conflicto de interés. Está escrita antes de leer la alternativa justamente para
que se pueda auditar si después la muevo.
