# Resultado EURUSD-ESCALONADAS-ESCALAS, descubrimiento ago-2025 -> ene-2026

Estado: VIGENTE

Manifiesto `MANIFIESTO_EURUSD_ESCALONADAS_ESCALAS_20261021.md` (antes de correr) · runner `tools/eurusd_escalonadas_grid.py`
· salida `eurusd_grid_descubrimiento.json`. 129 sesiones FX, replay tick a tick con bid/ask, comision 3,5 ticks (0,35 pip), control
con la misma mecanica, max-T sobre 648 (t critico 3,98).

## Resultado
- **0/648 sobreviven max-T.** 576 evaluables, 72 inconclusas por potencia (500t con pocas operaciones).
- Por escala (promedio de celdas): **25t R neto -0,77** (bruto -0,36; control -0,82) · **150t -0,33** (bruto -0,19; control -0,30)
  · **500t +0,15** (bruto +0,23; control -0,10; n medio 62).
- Mayores t: celdas de 25t con limite (lim50/lim25) que pierden MENOS que su control (p. ej. lim50 SL20 TP2R: -0,21 vs -0,39,
  t 3,18) — siguen con R neto negativo; mejor 500t: precio_stop SL104 TP1R +0,45 R (n 39, t 2,73), no alcanza 3,98.
- Mismo patron que MNQ: en 25t el costo fijo domina; solo las escalas grandes quedan cerca o por encima de 0, sin potencia.

## Veredicto
Nada sobrevive -> **no se abre la replica abr-jun 2026**. La familia de picos escalonados (PLANAS, 6 entradas, 3 escalas) queda
**sin efecto detectado en EURUSD**, como en MNQ y ES. Vivo sin potencia (no promovido): 500t con SL amplio (+0,15 R medio vs
control -0,10), igual que en MNQ.
Simulacion visual del visor (SL a mitad entre deteccion y 1.er pico, TP 3R, 25t): +0,30 R sin costos, ~-0,45 R con spread+comision
(SL mediano 1 pip, costo ~0,75 pip) — consistente con este resultado.
