# Pre-registro — Ruptura direccionalmente neutra a las 05:30 UTC en el oro (bracket OCO)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `ORO_0530_UTC` (misma familia que el exploratorio). Etapa del embudo: **EF2** (desarrollo: usa los datos donde se vio la expansión).

## 1. Por qué esta regla
El exploratorio (`RESULTADO_ORO_0530_UTC.md`) nominó la **expansión de volatilidad** a las 05:30 UTC (16/16, rango ×1,8 a 5 min) y
ninguna regla direccional (0/48). La forma operable de una expansión sin dirección es un bracket: no elige el lado, lo elige el mercado.

## 2. Regla (fijada ahora; `edgelab/research/oro_0530.py::ruptura`, simulador `edgelab/research/bracket.py`)
- Rango previo = máximo y mínimo de las velas M1 de 05:00 a 05:29 UTC (conocido al cierre de 05:29; ≥ 25 de 30 velas presentes).
- A las 05:30:00 se colocan **compra stop en máximo + 1 tick** y **venta stop en mínimo − 1 tick**; la primera que se llena cancela la otra.
  Ventana para llenarse: 15 minutos.
- Llenado: primer tick que cruza el nivel, **a su precio real** (con el hueco), sin mejorar.
- Salida: por tiempo, `hold` ∈ {15, 30, 60} minutos desde la vela del llenado, o por stop:
  `opuesto` (el otro lado del rango previo + 1 tick) o `medio` (a medio rango de la entrada). Sin objetivo.
- 6 reglas × {XAU 2023-01 → 2026-09 (spot con costos de GC, proxy declarado), GC 2025-08 → 2026-09} × {total, reciente ≥ 2026-04-01}
  = **24 pruebas**.
- Costos: fricción canónica de GC (`edgelab/costos.py`: 0,605 USD por viaje base; 0,805 adverso). El llenado al precio real del hueco ya
  paga el deslizamiento de la orden stop en el burst; la fricción canónica se resta igual (conservador).
- Noticias: a las 05:30 UTC no hay noticias USD tier 1 (`edgelab/noticias.py`); con hold de 60 min la operación cierra antes de las 06:45.

## 3. Estadístico y decisión
Media neta por operación llenada, bootstrap de sesiones (20.000), p unilateral (H1: media > 0), MDE publicado, `escalera.tamiz_fdr`
(q 0,10) sobre las 24. **NOMINADA** si q ≤ 0,10 y la media neta es > 0 también con la fricción adversa. EF2: nada confirma. Una nominada
en GC pasa a confirmación forward (sesiones ≥ 2026-10-01, frescas para esta familia) con el monitor secuencial y cotas estructurales
(la pérdida máxima está acotada por el stop y el hueco declarado).

## 4. Justificación económica
La reapertura de Shanghai a las 13:30 de Beijing concentra flujo en un minuto conocido y el rango se expande ~1,8×. Si la expansión
continúa en el sentido de la ruptura más que lo que revierte, un bracket la cobra; si es un pico que revierte, pierde por los dos lados.

## 5. Cómo podría refutarse
Media neta ≤ 0 en GC para las 6 reglas; o positiva sólo en el proxy XAU. Una expansión que revierte dentro del hold mata la regla aunque
la volatilidad exista.

## 6. Multiplicidad, riesgos y código
- Registro global `oro_0530/ruptura`, 24 pruebas, antes de correr. Linaje: el de `ORO_0530_UTC`.
- Riesgos: las mismas sesiones que nominaron la expansión (desarrollo, no réplica); el hueco del burst puede comerse la ventaja; el spot
  no es el futuro a horizonte corto.
- sha256: `edgelab/research/oro_0530.py` `d83c223ff266354e7c4cf1717acec7efee0f1dda9033a8390c3676b38fe09a0f` · `edgelab/research/bracket.py`
  `11a1bb356ef379da1a0258c70dd8fad79e4de69013dc97424f07ace1d2d3918f` · `tools/kaggle_grilla/oro_0530_ruptura_main.py`
  `e2dedb9eca747f43f63efdadfe98a44cc633d32a897d122e9d7069a66036ac66`.
