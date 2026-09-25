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

## 5. Reporte y multiplicidad (fijados ahora)

- Por configuración (12): cada medida real, fantasma y diferencia pareada, con IC por bootstrap por sesión (2.000 réplicas) y su MDE.
- Medidas primarias (8 por configuración: lado B, excursión/W, velas afuera, volumen afuera relativo, reingresa, penetración/W, llega al borde opuesto, velocidad de reingreso): **96 diferencias**, BH-FDR q = 0,10.
- **Combinaciones** («según qué combinación»): sobre la configuración de Nico, cortes descriptivos por fase de sesión, tercil de volumen por tick del impulso, tercil de velas del impulso y tercil de eficiencia, más un árbol honesto (mitad de sesiones arma, mitad estima). **Son sugerencias, no pruebas.**
- Se publica el paisaje completo.

## 6. Riesgos

- Selección de parámetros sobre los mismos datos: es exploración; la corrección y la reserva lo contienen.
- Sesgo de horario (de noche todo es fino): el nulo a la misma hora lo neutraliza.
- Velas de 25 ticks: los niveles se evalúan con cierres, máximos y mínimos de vela, no con ticks.
