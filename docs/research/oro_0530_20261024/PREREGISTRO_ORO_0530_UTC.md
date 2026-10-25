# Pre-registro — Oro a las 05:30 UTC (02:30 en UTC−3): volumen y comportamiento

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-25.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia: `ORO_0530_UTC`. Etapa del embudo: **EF2** (exploratorio; nomina para confirmar, nunca confirma).
Pedido de Nico (2026-10-24): «un análisis exploratorio de las 02:30 am UTC−3, donde al parecer hay una explosión de volumen en el oro».

## 1. Origen de la idea y por qué el ancla es UTC
- La observación de Nico es de **volumen** en un gráfico, no de retornos: el origen es target-free.
- 02:30 UTC−3 = **05:30 UTC** = 13:30 en Beijing. A esa hora reabren la tarde la Shanghai Gold Exchange y SHFE después de la
  pausa del mediodía. Ni China ni Argentina cambian de hora, así que el ancla es UTC fijo.
- Lo que ya había no lo mide: el barrido horario de la etapa A (`tools/barrido_horario_etapa_a.py`), `tools/study_slot_effect.py`
  y `tools/universe_sigma.py` anclan franjas en hora de Chicago; un hecho fijo en UTC cae a las 00:30 CT en verano de EE. UU. y a
  las 23:30 CT en invierno, y esas grillas lo reparten entre dos franjas.
- **Noticias** (pedido de Nico del 2026-10-25: no operar durante noticias): la ventana medida (04:30–06:40 UTC) no toca los
  horarios de las noticias USD de alto impacto (8:30, 10:00 y 14:00 ET = 12:30 UTC en adelante). Se verificará contra
  `config/noticias/` cuando exista; un evento dentro de la ventana excluye esa sesión antes de cualquier confirmación.

## 2. Datos (sólo desarrollo; nada desde la sesión del 2026-10-01)
- **XAU**: `nicolasbuttaro/edgelab-dukascopy-xauusd-ticks-m1` (versión recortada en la frontera del 2026-10-24), mid de bid/ask,
  2023-01-01 → 2026-09-30. Actividad = ticks (cotizaciones) por minuto; volumen = bid_vol + ask_vol.
- **GC**: release `liquid_tick_v1` (`nicolasbuttaro/edgelab-liquid-ticks-20261014`, `GC_ticks.parquet`), trades, desde el
  inicio del release hasta 2026-09-30 (el release llega al 2026-09-25).
- Lectores: `edgelab/research/fuentes_ticks.py` (cortan en `edgelab/holdout.py`); velas: `grilla_generica.contexto_m1`.

## 3. Parte A — target-free (no son pruebas)
Perfil por minuto del día UTC de la actividad relativa (mediana entre días de ticks y volumen del minuto / mediana del día): top 20
minutos, los minutos 05:20–05:45, 05:30 en verano e invierno de EE. UU. y por año. Burst por sesión: actividad media 05:30–05:34
sobre 05:20–05:29. **Cómo podría refutarse la premisa**: si 05:30 no está entre los minutos de más actividad o el burst
mediano es ≈ 1, la «explosión» no existe en estos datos (o es otra hora), y eso se informa antes de mirar la parte B.

## 4. Parte B — 16 celdas por instrumento y ventana (`edgelab/research/oro_0530.py`)
Precio de un minuto = apertura de la vela M1 que empieza en ese minuto. h ∈ {5, 15, 30, 60} minutos.
| familia | qué mide | decisión conocida en | entrada |
|---|---|---|---|
| `deriva_h` | P(05:30+h) − P(05:30) | antes de las 05:30 | apertura 05:30 |
| `arranque_h` | signo(cierre 05:34 − apertura 05:30) × (P(05:35+h) − P(05:35)) | cierre de la vela 05:34 | apertura 05:35 |
| `previo_h` | signo(cierre 05:29 − apertura 05:00) × (P(05:30+h) − P(05:30)) | cierre de la vela 05:29 | apertura 05:30 |
| `rango_h` | log(rango 05:30..+h / rango 04:30..+h) — **canal no direccional** | — | — |
Una observación por sesión (día hábil UTC); una vela faltante deja la celda en NaN para esa sesión (se cuenta, no se rellena).
Una celda con < 30 sesiones no es evaluable y entra con p = 1.

- **Ventanas**: `total` (todo) y `reciente` = sesiones ≥ 2026-04-01, declarada ahora (ATJ-24).
- **Estadístico**: media por sesión, bootstrap de sesiones de `escalera.resumen_sesiones` (20.000 réplicas), p **bilateral** =
  2·mín(p de cada cola). MDE publicado por celda (`escalera.mde`).
- **Tamiz**: `escalera.tamiz_fdr` (Storey, q 0,10) sobre las **64 pruebas** (16 × 2 instrumentos × 2 ventanas).
- **Económico** (sólo direccionales, informativo): media en el lado observado − fricción canónica de GC
  (`edgelab.costos.friccion_rt_puntos("GC")` = 0,605 pts base; 0,805 adverso). En XAU los precios son del spot con costos de GC:
  **proxy declarado** de ejecución en GC (la equivalencia spot↔futuro a horizonte corto es débil, `RESULTADO_EQUIVALENCIA.md`);
  la operación real se mide en GC.

## 5. Decisión (fijada ahora)
- Salidas: **NOMINADA** (q ≤ 0,10 en el tamiz) o **SIN_SEÑAL** con su MDE. Nada de esto confirma.
- Una nominada pasa a confirmación **forward** en sesiones desde el 2026-10-01 (frontera fresca para esta familia), con regla
  congelada, costos canónicos, ejecución en GC, filtro de noticias y el monitor secuencial (`edgelab/funnel/secuencial.py`) con
  cotas estructurales (salida por tiempo: la pérdida máxima se acota con un stop declarado antes de abrir).
- Un resultado de XAU sin GC no se promueve: el instrumento operable es GC.

## 6. Justificación económica
La reapertura de la tarde en Shanghai concentra flujo físico/institucional chino en un minuto conocido. Si el flujo es
direccional (p. ej. demanda local con prima sobre Londres) o si la llegada de órdenes crea un impulso que el mercado global
continúa o revierte, el retorno de los minutos siguientes debería tener signo o, al menos, la volatilidad debería expandirse.

## 7. Cómo podría refutarse
- Parte A: sin burst a las 05:30 UTC.
- Parte B: ninguna celda nominada con MDE chicos (el efecto, si existe, es menor que el MDE).
- Un efecto sólo en XAU y no en GC, o sólo en una ventana, no es evidencia de algo operable.

## 8. Multiplicidad, linaje, riesgos
- **Pruebas**: 64, registradas en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl` (`oro_0530/exploratorio`) antes de correr.
- **Linaje**: `ORO_0530_UTC` declara como padre `TIME_SLOT_HOLD_COND_SCAN`: el barrido de la etapa A cubrió GC 2025-08 → 2026-06
  en franjas CT que incluyen 23:30 y 00:30 (sin seleccionar esta hora). XAU 2023-2025 es dato nuevo para esta pregunta.
- **Riesgos**: el spot no es el futuro a horizonte corto; las celdas comparten sesiones y horizontes (dependencia positiva,
  aceptable para BH/Storey); el «lado observado» del económico es una elección después de mirar, por eso sólo informa.
- **Datos faltantes**: ninguno para A y B. Para la confirmación hacen falta ticks de GC y XAU desde el 2026-10-01 en carpeta
  sellada.

## 9. Código (sha256 al pre-registrar)
- `edgelab/research/oro_0530.py` `fb168d8cab1ff6214c3dc94199921f856b0b8b92440af86680922f9ee0d33003` (tests `tests/research/test_oro_0530.py`:
  ruido, plantado, perfil sin precios, causalidad, vela faltante).
- `tools/kaggle_grilla/oro_0530_main.py` `1b66dd03e20bf214b6c8a70abd64f2f7cadb3f82fad79ecdcbf28603e2ba3cf5`.
- Salida: `docs/research/oro_0530_20261024/ORO_0530_UTC.json` y su informe.
