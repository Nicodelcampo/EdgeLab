# Resultado MNQ-ESCALONADAS-ESCALAS, descubrimiento ago-2025 → ene-2026 (2026-09-30)

Manifiesto `MANIFIESTO_MNQ_ESCALONADAS_ESCALAS_20260930.md` + enmiendas 1 (meses) y 2 (6 entradas), ambas antes de
ver resultados · runner `tools/mnq_escalonadas_grid.py` (commit `c59560c`) · salida `es_escalonadas/mnq_grid_descubrimiento.json`.
175 sesiones (feb-2026 excluido), replay tick a tick con bid/ask y 3 ticks de comisión, control con la misma mecánica.

## Resultado
- **0/648 sobreviven max-T** (t crítico 4,28). Ninguna celda inconclusa por potencia (todas ≥ 30 op. y ≥ 8 sesiones).
- R neto > 0 en 140/648 celdas, casi todas en 150t/500t y **todas dentro del ruido** (t ≤ 2,1).
- **25t: negativo en todas las entradas** (−0,43 a −0,61 R/op de media; el bruto ya es negativo): el costo fijo manda.
- **150t:** medias cerca de cero (precio_stop +0,03, precio_lim50 +0,04; las demás negativas); mejor celda
  velas_w2 SL56 TP10R BE2 +0,32 R (n 294, IC 90 % [−0,06; +0,73]); MDE típico ≈ 0,5 R.
- **500t:** pocas operaciones (63–100); mejor precio_lim25 SL26 TP5R BE2 +0,66 R (n 63, t 1,94) — no distinguible de
  la selección entre 648.
- **Entrada anticipada con 2 picos:** negativa en 25t y 150t, cerca de cero en 500t: entrar antes de que se forme la
  zona no ayuda.
- Contra el control: las celdas de 150t/500t superan al control (controles −0,1 a −0,25 R) pero sin alcanzar el umbral
  familiar.

## Veredicto
Según el manifiesto, nada sobrevive → **no se abre la réplica de marzo**. La familia ESCALONADAS PLANAS transferida a
MNQ (ES ×4,5 / ×12,42 / ×23,49, sin marcas de MNQ), con estas 6 entradas, estos SL/TP/BE y estas 3 escalas, **queda sin
efecto detectado en MNQ** en descubrimiento. El +0,25 R/op de la exploración de febrero en 150t fue un caso elegido
mirando: con 6 meses y control, 150t queda en ≈ 0 neto. Lo que sigue vivo (sin potencia, no promovido): escalas grandes
con SL amplio, donde el bruto es ligeramente positivo.
