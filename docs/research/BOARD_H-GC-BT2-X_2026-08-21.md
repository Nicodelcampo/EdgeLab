# Board — entradas de la sesión sandbox 2026-08-21 noche

**Asentar en `PENDIENTE.md` en el mismo commit local** si este dump no reescribió
el board (el archivo es enorme y no se tocó a ciegas). El board manda.

---

## P-58 — H-GC-BT2-1 gastó el holdout de GC agosto; no reusar para elegir gestión

**Asentada 2026-08-21.** Commit `5814f1f`.

H-GC-BT2-1 midió carrera de barreras ±B (sin BE, sin MAE/MFE) sobre GC 12-26,
11–21 ago, **autorizado por Nico**. 16/16 celdas primarias no superan p*.

**Regla:** esa ventana **no** se usa para elegir SL, TP, BE, tickframe ni params
de BigTrap2. Un estimando nuevo (trade con BE) sobre los mismos días **no** es
confirmación independiente.

Discovery viva: GC 08-26 **24–30 jun** (y más pre-1-jul si aparece).

---

## P-59 — el atlas GC no tiene libro usable (3/20.486)

**Asentada 2026-08-21.** Artefacto: `docs/research/atlas_bigtrap2_gc.json`.

`con_estado_de_libro=3`, `frac_con_libro=0.0001`, `sin_l2=5370`.
`h_gc_bt2_barreras.py` no lee L2. El mensaje de commit implicaba contexto de libro;
el JSON lo desmiente.

**Regla:** no filtrar por spread / OFI / profundidad hasta que un join L2↔ticks
pegue en casi todos los eventos (primero en **junio**).

---

## P-60 — `vol≥30` no es «burbuja» en todos los tickframes

**Asentada 2026-08-21.** Barrido `h_gc_bt2x_sweep_frames.json`.

El piso `min_trap_volume=30` está en **contratos**, no en fracción de la barra.
En tick:25 hay 96 burbujas / 21.544 barras. En tick:500 hay **691 / 1.081**.
Ahí se mide «el oro se mueve», no BigTrap2.

**Criterio de cierre:** definir burbuja por frame (p.ej. percentil de `vol` o
`vol / bar_vol`) **antes** del próximo barrido, por escrito.
