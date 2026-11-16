# Handoff 2026-11-16 — cartera v2, FundedSync, holdout nuevo y SQX

Estado: VIGENTE (punto de entrada de lo hecho del 14 al 16-nov en la sesión en la nube; rama `claude/vibrant-clarke-s9z6e2`).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Todo lo de abajo está commiteado y con su pre-registro antes.

## 1. Lo operable hoy: cartera v2 (`docs/research/cartera_20261116/`)
- **Selección congelada** (`SELECCION.json`, commit `b5f01f5d`, sólo desarrollo + octubre, regla de `PREREGISTRO.md` §5): CVGAP-ES-C,
  U1-RACIMOS-GRILLA-NQ, CONF-CVR-CFD-NQ-R, U1-ZONAS-BT2-ES, PREAPERTURA-NQ, U1-ORO-GRILLA, U1-ZONAS-BT2-NQ, CVGAP-CFD-ES-C (≈ 52 ops/mes,
  correlación diaria máx. 0,05).
- **Noviembre 2–13 (no mirado al elegir):** +0,56 R/sesión con el spot sellado (+0,73 sólo futuros); holdout oct+nov +0,47 R/sesión (t 1,17):
  lectura pre-registrada VERDE, sin significación y dependiente de PREAPERTURA-NQ (+9,5 R en 4 ops). `RESULTADO.md` (+ anexo), `NOVIEMBRE*.json`.
- **Mejoras** (`PREREGISTRO_MEJORAS.md` → `RESULTADO_MEJORAS.md`): A1 comisión mínima, A2 PREAPERTURA-NQ ×0,5 (sin inferencia); M1 no operar
  si fricción > 0,08 R (Δ −0,33 R, p 0,05) y M3 micros fijos por regla (t 1,46 → 2,42, p 0,026) confirmadas en generadoras + holdout; M2
  (fin de rueda) descartada. **v2: quema de una evaluación 50K 21 % → 3 %**, holdout +3.339 USD t 1,77. Hoja operativa: `CARTERA_V2_OPERATIVA.json`.
- **Pérdidas concentradas** (`PREREGISTRO_PERDIDAS_CONCENTRADAS.md`): el stop corto relativo pierde −0,11 R sólo por fricción (bruto igual);
  la fricción se come el 58 % del R bruto. Factor `F-STOP-CORTO-ES-FRICCION` (palanca de diseño).
- **Forward con e-proceso** (`PREREGISTRO_FORWARD_V2.md`, `tools/cartera_v2_forward.py`): desde la sesión del 2026-11-14; tarea programada
  «Forward cartera v2 (diario)» martes a sábado 02:23 UTC. EDGE si e ≥ 10.
- Pendiente de datos: GC de noviembre (U1-ORO-GRILLA se ejecuta en GC); U1-ES-GRILLA y U1-YM-GRILLA sin noviembre (Kaggle no los arrancó).

## 2. FundedSync (traducción de Nico/Antigravity, `docs/research/fundedsyncstack_20261115/`)
- Cadena (`PREREGISTRO_CADENA.md` → `RESULTADO_CADENA.md`): 15 módulos de fábrica, NQ M1 2012–2026, costos NQ, nulo de 15 módulos (p95 1,92 en
  2020–2023), causalidad por prefijo OK. **Pistas: T (ORB 15m + KNN, t 4,37, con stop, 19 ops/mes), Z y R (sin stop, 2–3 ops/mes).**
- **Holdout (única apertura, `ACTA_HOLDOUT.md` → `RESULTADO_HOLDOUT.md`): T +14,2 pts/op (n 26, t 0,54), Fisher 0,020 → CONFIRMADA por la
  regla del acta (descansa en el desarrollo); Z 7/7 +137 pts; R no concluyente.** El primer intento no leyó el sellado (corte por defecto
  `end="2026-10-01"` del paquete): 0 operaciones, nada mirado, relanzado en la misma apertura.
- 8 fichas en el banco de ideas (FS-*); idea transferible principal: filtro KNN entrenado con las operaciones sombra de la propia regla.
- Licencia del producto original: decisión de Nico; acá sólo se mide.

## 3. Holdout de otras familias (una apertura cada una)
- DELTASWEEP_NQ (SEQ2 AM): −0,24 R (n 30), en contra sin potencia. M1_INTRADIA (VWAP banda 3, futuros NQ+YM): +0,32 R (n 12), no concluyente.
- ASIA: su ventana es forward desde el 2-nov (octubre excluido por su pre-registro); enmienda 1 agregó H2 «noche alta» antes de mirar.

## 4. Datos
- Dataset sellado `nicolasbuttaro/edgelab-holdout-sellado` versión 7 (2026-11-16 03:45 UTC): futuros NQ/ES/YM diarios hasta 2026-11-13;
  spot USATECH, USA500, USA30, XAU y divisas 2026-10-01 → 2026-11-15. **Falta GC de noviembre.**
- Lección: Kaggle reusa el slug; si la versión nueva no arranca, `output` devuelve la vieja. Verificar por cantidad de velas leídas y relanzar
  con otro sufijo (`CN_SUFIJO` en `tools/cartera_nov.py`).

## 5. StrategyQuant X
- Lote 1 (D1/H4): ninguna estrategia supera al máximo de su nulo (S&P D1 tendencia, oro D1, S&P H4 reversión). Lote 2 pasó a intradía por las
  reglas de prop (enmienda 1); el par 1 (Nasdaq M30 tendencia) fue **inválido** (3 aceptadas, 0 operaciones 2017–2019); cola pausada, tarea horaria
  deshabilitada. Proyectos H4/D1 del lote 2 preparados sin lanzar. Configuración `-Xms2g -Xmx5g` aplicada.
- **Nada que guardar en SQX:** ninguna candidata; los resultados (comparaciones, K al contador, manifiestos) están en `sqx/corridas/` y en
  `docs/research/sqx_lote*`. Al cerrar, SQX sincroniza los databanks; se puede cancelar sin perder nada que haga falta.
- Siguiente (propuesto, sin aprobar): generación sin plantilla en M15/M30 con aceptación ≥ 200 operaciones, probando primero 15 min.

## 6. Tareas programadas vigentes
- «Forward cartera v2 (diario)» (`trig_01KM6SpNJxonFeBD3bzmEHLp`), martes–sábado 02:23 UTC.
- «Cola SQX lote 2 (cada hora)»: DESHABILITADA.

## 7. Decisiones pendientes de Nico
1. Pre-registrar T (FundedSync) en el forward junto a la cartera v2; diseñar Z con stop (hipótesis nueva).
2. Rediseño del lote 2 de SQX.
3. Sellar GC de noviembre.
4. Operar en real (sólo humano): la v2 respalda empezar una evaluación de prop con micros, 200 USD por R y PREAPERTURA-NQ ×0,5.
