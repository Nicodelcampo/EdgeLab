# Manifiesto: impulsos de poco volumen por tick y el «espejo» de la franja (familia TBZX), ES, 2026-09-25

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** EXPLORACIÓN autorizada por Nico en chat («Medí vos. Jugá con los parámetros. Medí a, b y c», 25/09). Escrito y commiteado **antes** de ver cualquier número.
**Partición:** `P-TBZ-EXP` (ES, jul-2025 a mar-2026, rol EXPLORATION, ya declarada en el Brain). Abr–jun (`P-TBZ-CONF`) y el holdout no se tocan.
**Ledger:** `artifacts/hippocampus/tbzx_20260925.jsonl`. Herramienta: `tools/tbzx_espejo.py`.

## 1. Qué vio Nico y cómo se traduce

En el visor (diseñador de expansiones, borrador `docs/specs/TBZX_CONFIG_BORRADOR_20260925.json`) Nico nota que, en ciertos contextos, después de crearse la franja A→B el precio la **«espeja»**: vuelve y la recorre hacia A, a veces más allá. Si es frecuente, permite entradas con RR alto (stop corto detrás de B, objetivo en A o más allá).

**Justificación económica:** un impulso que recorrió muchos ticks con poco volumen dejó poca posición abierta adentro; al volver, hay poco que defender y la franja se atraviesa fácil (idea de hueco de volumen).
**Cómo podría refutarse:** la salida, la permanencia afuera, la excursión y el reingreso (profundidad, velocidad) de la franja real no se distinguen de los de la **misma geometría puesta a la misma hora del día en otra sesión** (control fantasma).

## 2. Detector (el mismo del visor, portado a Python)

Velas de 25 ticks por sesión. Un impulso arranca en la vela j si dentro de las últimas `maxBars` velas (sin retroceder más allá del extremo del impulso anterior) el precio recorrió ≥ `minW` ticks con eficiencia ≥ 0,6. Termina con retroceso ≥ max(2 t, 0,3·W) o al llegar a `maxBars` velas. Queda disponible al cierre de la vela que decide el fin (`iend`). Paridad con el visor verificada antes de medir.

**Grilla (12 configuraciones):** `maxBars` ∈ {10, 20, 40} × `minW` ∈ {8, 12, 17, 24}. Eficiencia 0,6 y retroceso 0,3 fijos (los eligió Nico). La de Nico es (20, 17).

## 3. Qué se mide (enmienda de Nico, 25/09, antes de ver números: **no se buscan entradas**)

Nada de stops, targets ni R. Se describe el camino del precio después de la franja, en un horizonte de H = 200 velas desde `iend`. «Afuera» = cierre de vela fuera de [min(A,B), max(A,B)]; lado **B** = hacia donde iba el impulso, lado **A** = el opuesto.

**Primera salida** (el primer episodio afuera después de `iend`):
1. **lado** (B o A) y velas hasta salir;
2. **cuánto se aleja:** excursión máxima más allá del borde, en ticks y en fracción de W;
3. **cuánto tiempo pasa afuera:** velas y segundos hasta volver a cerrar adentro;
4. **cuánto volumen hace afuera:** contratos durante el episodio, y en relación al volumen del impulso;

**Reingreso** (si vuelve a cerrar adentro dentro de H):

5. **reingresa o no** dentro de H;
6. **qué tanto ingresa:** penetración máxima en las 50 velas siguientes, medida desde el borde por el que entró, en fracción de W. 1 = llega al borde opuesto; 2 = espejo completo (una franja entera más allá);
7. **de qué manera:** velocidad del tramo de reingreso (ticks por vela y por segundo), su eficiencia y su volumen por tick, comparado con los del impulso.

**Totales en H** (todos los episodios): velas afuera de cada lado, volumen afuera de cada lado, excursión máxima de cada lado.

## 4. Nulo

**Fantasma:** para cada franja, 3 sesiones distintas de la misma partición, en la vela más cercana a la **misma hora del día (ET, ± 15 min)**. Se pone la misma geometría relativa al cierre de esa vela (misma dirección, mismos A y B relativos) y se miden las mismas cosas. Contesta si lo observado es propio de la franja o es lo que hace cualquier franja del mismo ancho a esa hora. Es un control de otra sesión, exento de CTRL_TIMING_V1, y se audita igual.

### 4b. Segundo nulo, agregado DESPUÉS de ver el primer reporte (25/09, más estricto, no relaja nada)

El primer reporte (sha d4762a655722, ledger OBS-TBZX-ESPEJO-ES) dio diferencias grandes contra el fantasma en casi todo, y todas en la dirección de un mercado más rápido y fino: más excursión, más penetración, reingreso más veloz, menos segundos afuera y menos volumen por tick. Eso es lo que produce la volatilidad alta de después de un impulso, haya franja o no, y el fantasma a la misma hora no la tiene.

**N-VOL:** otra sesión, misma hora (± 1 h), en una vela cuyas últimas maxBars velas tuvieron **el mismo rango de precio y la misma duración en reloj (± 25 %)** que las del impulso real. Misma geometría relativa. Hasta 20.000 franjas por configuración (muestra aleatoria fija si hay más). Contesta si lo que se ve es propio de los niveles A/B o sólo de la actividad reciente. BH por nulo (dos familias de 96). **Si una diferencia desaparece contra N-VOL, se atribuye a la actividad, no a la franja.**

### 4c. Contexto de sobrecompra/sobreventa (pedido de Nico, 25/09, después del primer reporte; sólo descriptivo)

Estiramiento del precio al **inicio** del impulso respecto de EMA20, EMA50 y SMA200 de 1 min y del VWAP de sesión, en unidades de ATR14 de 1 min, **con el signo del impulso**: positivo = el impulso va en la misma dirección en que el precio ya estaba estirado (comprar ya sobrecomprado, vender ya sobrevendido). Cortes: terciles (bajo/medio/alto, donde «alto» es el percentil 67 a 90) y decil extremo (≥ p90) sobre la configuración de Nico, real contra los dos nulos. **No entra en las pruebas:** es sugerencia.

## 5. Reporte y multiplicidad (fijados ahora)

- Por configuración (12): cada medida real, fantasma y diferencia pareada, con IC por bootstrap por sesión (2.000 réplicas) y su MDE.
- Medidas primarias (8 por configuración: lado B, excursión/W, velas afuera, volumen afuera relativo, reingresa, penetración/W, llega al borde opuesto, velocidad de reingreso): **96 diferencias**, BH-FDR q = 0,10.
- **Combinaciones** («según qué combinación»): sobre la configuración de Nico, cortes descriptivos por fase de sesión, tercil de volumen por tick del impulso, tercil de velas del impulso y tercil de eficiencia, más un árbol honesto (mitad de sesiones arma, mitad estima). **Son sugerencias, no pruebas.**
- Se publica el paisaje completo.

## 6. Riesgos

- Selección de parámetros sobre los mismos datos: es exploración; la corrección y la reserva lo contienen.
- Sesgo de horario (de noche todo es fino): el nulo a la misma hora lo neutraliza.
- Velas de 25 ticks: los niveles se evalúan con cierres, máximos y mínimos de vela, no con ticks.

## 7. Resultado en ES (25/09; exploración, 181 sesiones; reporte sha `b6d5c964be5e`, ledger OBS-TBZX-ESPEJO-ES-V4)

Detector idéntico al del visor (707/707 y 11.594/11.594 franjas en enero). 12 configuraciones, de 1.067 a 136.195 franjas cada una.

**Contra el fantasma a la misma hora:** 73 de 96 diferencias pasan FDR. **Contra N-VOL (misma actividad previa):** 59 de 96. Más o menos la mitad del efecto era la volatilidad posterior al impulso; la otra mitad queda.

Configuración de Nico (20 velas, 17 t), franja real / fantasma N-VOL:

| medida | real | N-VOL | diferencia (IC 95 %) |
|---|---|---|---|
| sale primero por el lado B | 0,806 | 0,816 | −0,011 (−0,019; −0,002) |
| excursión afuera / W | 0,404 | 0,346 | +0,058 (+0,026; +0,099) |
| velas afuera | 23,4 | 22,6 | +0,8 (−0,3; +2,0), sin diferencia |
| volumen afuera / volumen del impulso | 1,56 | 1,45 | +0,11 (−0,03; +0,26), sin diferencia |
| reingresa en 200 velas | 0,935 | 0,931 | sin diferencia |
| penetración al reingresar / W | 0,581 | 0,487 | +0,094 (+0,068; +0,117) |
| llega al borde opuesto (A) | 0,152 | 0,094 | +0,057 (+0,043; +0,071) |
| velocidad del reingreso (t/vela) | 0,995 | 0,876 | +0,118 (+0,061; +0,179) |

**Lectura:** el tiempo y el volumen afuera no se distinguen del nulo. Lo que sí se distingue es que la franja real, cuando el precio sale, **se aleja algo más y al volver entra más hondo y más rápido**; llega a A 1,6 veces más que el nulo estricto. El «espejo completo» (una franja entera más allá de A) es raro: 1–2 %.

**Contextos (descriptivos, llega a A: real / N-VOL):**
- **Estiramiento extremo al inicio del impulso** (decil superior, impulso a favor de un precio ya estirado respecto de la EMA20): 0,214 / 0,132. Excursión afuera 0,62 W y espejo completo 5,0 % / 1,6 %. Igual con EMA50 y SMA200; más débil con VWAP (0,186 / 0,106).
- **Poco volumen por tick en el impulso** (tercil bajo): 0,223 / 0,120. Tercil alto: 0,113 / 0,083.
- **Fase:** Asia 0,186 / 0,126, Europa 0,187 / 0,111, cierre 0,165 / 0,098; RTH 0,070 / 0,031.

**Lo que falta antes de creerlo:**
1. **Estado de reversión:** en `iend` la franja real ya retrocedió 0,3·W desde B; el N-VOL no tiene ese estado. Parte del residuo puede ser inercia de corto plazo del retroceso y no los niveles. Es el próximo nulo.
2. Los cortes por contexto no están emparejados por estiramiento en el nulo.
3. Velas de 25 ticks: los niveles se evalúan con máximos y mínimos de vela.
4. Réplica en NQ y confirmación en abr–jun (una sola apertura, con spec y campaña).

## 8. Iteración 2 (25/09): lo que puede engañar y lo que da robustez. Escrita antes de correr

Autorizada por Nico: «iterá sobre todo lo que tenga riesgo de engañar, y sobre todo lo que aporte robustez». Sigue siendo exploración.

**Riesgos de engaño:**
- **R1. Estado de reversión (nulo N-REV).** Otra sesión, misma hora (± 1 h), un tramo del precio del **mismo tamaño** (± max(1 t, 10 %)) que también **acaba de retroceder 0,3 de su recorrido**, con **sus propios** A y B, pero que **no** califica como impulso: tardó más de `maxBars` velas o tuvo eficiencia < 0,6. Tramos detectados con la misma regla y ventana de 3·`maxBars` sin exigir eficiencia. Contesta si importa que el tramo haya sido rápido y limpio, o si cualquier tramo del mismo tamaño que recién dio la vuelta hace lo mismo. Hasta 20.000 franjas por configuración.
- **R2. Métrica limpia.** «Llega al borde opuesto» mezclaba dos casos: salir por B y llegar a A, y salir por A y llegar a B. Se agrega `llega_A_por_B` (salió por B y reingresando llegó a A) como medida principal del espejo.
- **R3. Contexto de estiramiento con nulo emparejado.** Sólo con la configuración de Nico: N-VOL que además tenga el mismo estiramiento alineado respecto de la EMA20 en la vela final (± 0,5 ATR de 1 min). Contesta si «estirado» agrega algo o si sólo es más actividad.
- **R4. Ventana de penetración.** Con la configuración de Nico, `llega a A` medido a 20 y a 100 velas después del reingreso, además de 50.

**Robustez:**
- **B1. Estabilidad en el tiempo:** mitades jul–nov 2025 y dic 2025–mar 2026, y signo mes a mes.
- **B2. Por sesión:** fracción de sesiones con real > N-VOL.
- **B3. Réplica en NQ** (exploración jul-2025 a mar-2026, partición propia `P-TBZX-NQ-EXP`). Grilla `maxBars` ∈ {10, 20, 40} × `minW` ∈ {12, 17, 24, 34, 48, 68}. **Configuración equivalente**, elegida sólo por conteo y sin mirar resultados: `maxBars` = 20 y el `minW` cuya cantidad de franjas por día sea la más cercana a la de ES (20, 17). **Criterio de réplica:** en esa configuración, `llega_A_por_B` y `pen_W` contra N-VOL con el mismo signo que en ES e IC 95 % que excluye 0. El resto de NQ es paisaje descriptivo.

**Multiplicidad:** N-REV es una familia nueva (96 en ES, BH q = 0,10). La réplica de NQ son 2 pruebas pre-registradas. Lo demás es descriptivo.

## 9. Resultado de la iteración 2 (25/09; reporte `artifacts/tbzx/report_iter2.json`, sha `6a6be242886d`, OBS-TBZX-ITER2)

Referencia: ES (20 velas, 17 t). NQ equivalente por conteo: (20 velas, 68 t). `llega_A_por_B` = salió por B y al volver llegó a A.

| | ES real / nulo | NQ real / nulo |
|---|---|---|
| contra N-VOL (misma actividad) | 0,139 / 0,086, **+0,053** (+0,042; +0,063) | 0,225 / 0,153, **+0,071** (+0,055; +0,085) |
| contra N-REV (mismo tamaño, recién dio la vuelta, lento o sucio) | 0,145 / 0,079, **+0,066** (+0,048; +0,085) | 0,229 / 0,237, **−0,007** (−0,030; +0,013) |
| contra N-VOLSTR (actividad y estiramiento) | 0,132 / 0,109, +0,023 (+0,010; +0,035) | 0,220 / 0,184, +0,036 (+0,018; +0,053) |

- **Réplica pre-registrada (contra N-VOL): PASA** en `llega_A_por_B` y en `pen_W`.
- **Contra N-REV, NQ NO replica:** en NQ la franja rápida no se distingue de cualquier tramo del mismo tamaño que recién dio la vuelta, y en casi todas las configuraciones queda por debajo. En ES sí se distingue, con 71 de 96 celdas que pasan FDR.
- **Estiramiento extremo:** el efecto desaparece contra el nulo emparejado por estiramiento en los dos instrumentos (ES −0,012; NQ −0,011). Lo que parecía propio de la franja en contexto estirado es lo que hace cualquier precio igual de estirado. **Descartado como rasgo de la franja.**
- **Estabilidad (ES contra N-VOL):** positivo en 8 de 9 meses y en las dos mitades; sesiones con real > nulo: 57 %. NQ: negativo en ago–sep, positivo desde oct.
- **Ventana de penetración:** el signo se mantiene a 20, 50 y 100 velas.
- **Excursión afuera:** con N-VOLSTR ya no se distingue en ES; en NQ, poco.

**Veredicto de exploración:** el reingreso más hondo y la llegada a A son robustos a la actividad previa en ES y en NQ. En ES son además robustos al estado de reversión, **en NQ no**. El único rasgo que sobrevive a todos los controles es «reingreso hasta A en ES», de unos +5 a +7 puntos. Es chico, depende del instrumento y no hay nada de ejecución. El contexto de estiramiento queda descartado.

**Integridad pendiente:** la selección de contrato por sesión usa la regla «más ticks el mismo día» y no la canónica (`contract_regime`, líder de volumen de la sesión anterior). Difieren en 3 sesiones de ES y 2 de NQ dentro de la exploración, siempre el día del vencimiento. Se corrige antes de cualquier confirmación.

## 10. Próxima medición en ES: plan (25/09, NO ejecutado; corre sólo con OK de Nico)

**Corregido ya:** selección de contrato canónica en `tools/tbzx_iter2.py` (`canonical_sessions`: líder de la sesión anterior, sólo hacia adelante; proxy de volumen = ticks). Se reconstruyeron ES 15/09 y 16/03, NQ 16/09 y 16/03; las cachés viejas quedaron apartadas como `.npz.otro_contrato`.

**Debilidades que salda:**
1. **Nulo primario = N-REV** (el más duro), no N-VOL. N-VOL y el fantasma común quedan como diagnóstico.
2. **Una sola métrica principal:** `llega_A_por_B` (la limpia). Las demás son secundarias, con su propia familia FDR.
3. **Efecto de promedio (57 % de sesiones):** se reporta la distribución por sesión y la fracción de sesiones positivas, con el piso escrito antes: ≥ 60 %.
4. **Estiramiento:** descartado; no vuelve como contexto.
5. **Resolución de vela:** en una muestra de 30 sesiones, el toque de A se verifica tick a tick.

**Fortalezas en las que se apoya:** el detector es idéntico al del visor; el efecto es robusto a la actividad en ES y NQ y a la reversión en ES, con signo estable en 8 de 9 meses; más fuerte con impulsos cortos (10 velas) y anchos.

**Abanico que se abre** (descriptivo, contra N-REV, sólo exploración):
- **Qué del impulso explica la diferencia:** velas, eficiencia, velocidad en segundos, volumen por tick, cantidad de retrocesos internos. Árbol honesto (mitad de las sesiones arma, mitad estima).
- **Cómo es la llegada a A:** velas y segundos hasta A, si llega de un solo tramo o en escalones, y si después de A sigue hacia el espejo.
- **Dónde está B respecto del día:** B en máximo o mínimo de sesión, del día anterior o de un número redondo.
- **Por qué NQ difiere:** misma grilla en NQ con W escalado por volatilidad (ATR) en lugar de por conteo, para ver si la diferencia es de escala.

**Presupuesto:** una sola métrica principal contra N-REV en 12 configuraciones (12 pruebas, BH q = 0,10). Todo lo demás es descriptivo. La reserva abr–jun se abre sólo después, con spec confirmada y campaña.
