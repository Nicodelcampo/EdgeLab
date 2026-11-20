# Seguimiento forward de la cartera v2 con e-proceso (pre-registro, 2026-11-16)

Estado: PRE-REGISTRO — commiteado antes de la primera sesión forward. Pedido de Nico. North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5 (forward). Herramienta: `tools/cartera_v2_forward.py`.

- **Objeto (congelado):** las 8 reglas de `SELECCION.json` con la v2 de `CARTERA_V2_OPERATIVA.json` (A1 comisión mínima, A2 PREAPERTURA-NQ
  ×0,5, M1 no operar si el stop < piso de fricción 0,08 R, M3 micros fijos). Nada se cambia; un cambio de código que altere operaciones
  invalida el seguimiento.
- **Ventana:** sesiones desde **2026-11-14** (la primera no sellada al congelar), hacia adelante, del dataset sellado (el logger de NT8 sube
  futuros cada día; el spot de USATECH, USA500 y XAU y el GC requieren su sellado diario — sin él, esas reglas no suman sesiones).
- **Unidad:** R de cartera = USD / 200 por operación (micros fijos).
- **e-procesos (válidos mirando cada día; `edgelab/funnel/secuencial.py`):** H0 E[x] ≤ 0, por regla (cotas por operación [−6, 30]) y de
  la cartera (cotas por sesión [−15, 40]); fracciones de apuesta por defecto. **EDGE si e ≥ 10 (α 0,10).** Un valor fuera de las cotas detiene
  ese e-proceso con LIMITE_VIOLADO (no se recorta).
- **Lectura:** EDGE de la cartera → evidencia forward para escalar (decisión humana). Mientras no cruce, SIN_DECIDIR. Si tras 60 sesiones
  con operaciones el R total de la cartera es ≤ 0, se revisa la v2 en un pre-registro nuevo (no se retoca sobre la marcha).
- **Frecuencia:** cada día hábil, después del sellado diario (≈ 00:05 UTC): `lanzar` y `traer` con `--hasta` = última sesión sellada.
- Contador global: 1 prueba (familia `CARTERA_20261116`, forward).

Justificación económica / cómo podría refutarse: la del `PREREGISTRO.md`. Refutación: R forward ≤ 0 con 60 sesiones, o futilidad.
