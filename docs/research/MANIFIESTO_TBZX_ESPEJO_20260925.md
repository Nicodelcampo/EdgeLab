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
