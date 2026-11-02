# Acta: U1-CRUZADO sobre TODO el holdout sellado disponible (2026-11-02), registrada antes de correr

Estado: VIGENTE. Pedido de Nico: «corré el mejor candidato en todo el holdout, sólo ese». Lo aprueba el agente, por la decisión
del 2026-10-20 sobre quién aprueba aperturas. Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Regla congelada
Es la misma del acta exploratoria (`ACTA_HOLDOUT_EXPLORATORIO_U1_CRUZADO.md`), sin ningún cambio:
- U1 sobre USATECH (Dukascopy): N ≥ 3 zonas LUX-IMB en 40 pts, A/H ≥ 8, regreso al 75 %.
- Ejecución en NQ con E1A/T3/S3 y tope de 3× la distancia al objetivo.
- Fricción canónica de NQ (1,5455 pts).
- Código: `edgelab/research/u1_cruzado_papel.py`, etapa `OPERAR`, que llama a `u1_cruzado.operar`. La paridad contra el desarrollo
  está verificada (52/52 operaciones; ver `docs/research/cartera_20261101/u1_cruzado/`).

## Datos y ventana
- Dataset `nicolasbuttaro/edgelab-holdout-sellado`, versión del 2026-11-02 12:06 UTC:
  - `USATECHIDXUSD_ticks.parquet`;
  - NQ: `NQ_12-26_ticks.parquet` más `NQ_20261030_ticks.parquet`.
- Sesiones **2026-10-01 → 2026-10-30**: todo lo sellado que tienen las dos fuentes. Las zonas se arman sólo con datos del holdout,
  igual que en la mirada exploratoria.

## Estado de la familia `AREAS_EXP_1_CRUZADO`
- 2026-10-01 → 10-22: ya miradas en la exploración (8 operaciones, +29,4). Hay reuso autorizado **sólo con e-proceso** (decisión
  de Nico del 2026-10-24, `HOLDOUT_VENTANAS.jsonl`).
- 2026-10-23 → 10-30: nunca miradas.

## Pruebas, declaradas antes de mirar
1. **Principal: e-proceso de edge** (`MonitorCandidato`), una observación por operación, en orden de tiempo, sobre todo 10-01 → 10-30.
   - Cotas: −655 / +735 pts (3 × peor y mejor operación de desarrollo).
   - `mu_util`: 10,63.
   - **Nivel LORD++ reservado**: α = 0,010937 (`LIBRO_LORD.json`, reserva `U1-CRUZADO/holdout_completo_20261102`, t = 1).
   - **CONFIRMADA** si e_edge ≥ 1/α = 91,4. **REFUTADA** si e_futilidad ≥ 10. Si no, **NO_CONCLUYENTE**.
2. **Sólo las sesiones no miradas** (10-23 → 10-30): n, media neta, IC90 por sesiones. Es informativo, porque el tramo 10-01 → 10-22
   ya se conocía.
3. Se informa también el total de 10-01 → 10-30: n, media y aciertos.

**Expectativa honesta.** En la exploración hubo unas 8 operaciones en 3 semanas, así que acá se esperan unas 10–20 en total. Con ese n,
confirmar a α = 0,011 exigiría un efecto enorme: lo más probable es NO_CONCLUYENTE. El resultado no se usa para ajustar la regla, el
tope ni la ejecución.

## Registro
Apertura en `docs/research/HOLDOUT_VENTANAS.jsonl` (cid `U1-CRUZADO`, desde 20261001, estadístico e_proceso) antes de lanzar.
Conteo: 1 prueba en `TRIAL_REGISTRY_GLOBAL.jsonl`.
