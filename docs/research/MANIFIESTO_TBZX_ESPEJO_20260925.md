# Manifiesto: impulsos de poco volumen por tick y el «espejo» de la franja (familia TBZX), ES, 2026-09-25

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** EXPLORACIÓN autorizada por Nico en chat («Medí vos. Jugá con los parámetros. Medí a, b y c», 25/09). Escrito y commiteado **antes** de ver cualquier número.
**Partición:** `P-TBZ-EXP` (ES, jul-2025 a mar-2026, rol EXPLORATION, ya declarada en el Brain). Abr–jun (`P-TBZ-CONF`) y el holdout no se tocan.
**Ledger:** `artifacts/hippocampus/tbzx_20260925.jsonl`. Herramienta: `tools/tbzx_espejo.py`.

## 1. Qué vio Nico y cómo se traduce

En el visor (diseñador de expansiones, borrador `docs/specs/TBZX_CONFIG_BORRADOR_20260925.json`) Nico nota que, en ciertos contextos, después de crearse la franja A→B el precio la **«espeja»**: vuelve y la recorre hacia A, a veces más allá. Si es frecuente, permite entradas con RR alto (stop corto detrás de B, objetivo en A o más allá).

**Justificación económica:** un impulso que recorrió muchos ticks con poco volumen dejó poca posición abierta adentro; al volver, hay poco que defender y la franja se atraviesa fácil (idea de hueco de volumen).
**Cómo podría refutarse:** la tasa de llegada a A (o al espejo) desde la franja no supera a la de la **misma geometría puesta a la misma hora del día en otra sesión** (control fantasma), ni a la ruina del jugador.

## 2. Detector (el mismo del visor, portado a Python)

Velas de 25 ticks por sesión. Un impulso arranca en la vela j si dentro de las últimas `maxBars` velas (sin retroceder más allá del extremo del impulso anterior) el precio recorrió ≥ `minW` ticks con eficiencia ≥ 0,6. Termina con retroceso ≥ max(2 t, 0,3·W) o al llegar a `maxBars` velas. Queda disponible al cierre de la vela que decide el fin (`iend`). Paridad con el visor verificada antes de medir.

**Grilla (12 configuraciones):** `maxBars` ∈ {10, 20, 40} × `minW` ∈ {8, 12, 17, 24}. Eficiencia 0,6 y retroceso 0,3 fijos (los eligió Nico). La de Nico es (20, 17).

## 3. Qué se mide (horizonte H = 200 velas después de `iend`)

- **a) Sobreextensión:** ticks más allá de B antes de llegar a la mitad de la franja; velas hasta reingresar. Descriptivo.
- **b) Permanencia:** fracción de las H velas con cierre dentro de la franja.
- **c) Bordes:** en cada toque de A o de B desde adentro (a ≤ 1 t), ¿rebota (vuelve 0,25·W hacia adentro) antes de cerrar ≥ 2 t del otro lado dentro de 10 velas? Tasa de rebote en A y en B por separado.
- **Espejo:**
  - `M1` = llega a A (lo atraviesa por 1 tick);
  - `M2` = llega al espejo completo A − d·W.

  Cada uno antes de tocar el stop, en dos entradas:
  - `E0`: cierre de la vela `iend`; stop = B + 1 t.
  - `E2`: tras pasar B por ≥ 2 t, primer cierre de vuelta adentro; stop = extremo más allá de B + 1 t.

  Si target y stop caen en la misma vela, cuenta como stop (conservador). Sin llegar en H velas = no llegó. Se reporta el acierto, su RR y el **R neto** con 1,4 t de costo por operación (spread 1 t + comisión), marcando a mercado al vencer.

## 4. Nulos

- **Fantasma (primario):** para cada evento, 3 sesiones distintas de la misma partición, en la vela más cercana a la **misma hora del día (ET, ± 15 min)**; se aplica la misma geometría relativa al cierre de esa vela (misma dirección, mismas distancias a A, B, stop y target). Control de OTRA sesión: exento de la regla CTRL_TIMING_V1 y auditado igual.
- **N1:** ruina del jugador con las mismas convenciones, p0 = s / (s + r + 1).

## 5. Pruebas y criterio (fijados ahora)

- Diferencia real − fantasma, pareada por evento, bootstrap por sesión (2.000 réplicas).
- Familia de pruebas: 12 configuraciones × {M1, M2} × {E0, E2} (48), más permanencia y rebote en A y en B (36): **84 pruebas**, BH-FDR q = 0,10.
- Se publica el **paisaje completo** (todas las celdas, con su N y su MDE), nunca la mejor sola.
- **Contextos** («en ciertos contextos»): fase de la sesión (Asia/Europa/RTH) y tercil de volumen por tick, **sólo descriptivos** sobre la configuración de Nico. No entran en la prueba.
- Lo que salga es **sugerencia**. Confirmar exige spec confirmada, campaña aprobada en el Brain y la reserva abr–jun, una sola vez.

## 6. Riesgos

- Selección de parámetros sobre los mismos datos: es exploración; la corrección y la reserva lo contienen.
- Sesgo de horario (de noche todo es fino): el nulo a la misma hora lo neutraliza.
- Velas de 25 ticks: los niveles se evalúan con máximos y mínimos de vela, no con ticks. La conversión a ejecución real va en una etapa posterior.
