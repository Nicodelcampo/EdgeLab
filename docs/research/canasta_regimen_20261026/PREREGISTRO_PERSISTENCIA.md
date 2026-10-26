# Pre-registro — CANASTA-REGIMEN-1: ¿persiste el rendimiento de las celdas de U1? (condición necesaria de una canasta de régimen)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-26. Etapa: **EF2** (diagnóstico exploratorio; no promueve nada).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia: `CANASTA_REGIMEN_U1` (linaje ← `U1_ES_GRILLA`, `U1_YM_GRILLA`, `U1_ORO_GRILLA`, `AREAS_EXP_1_CRUZADO`).
Pedido de Nico (2026-10-26): «dale con la canasta, registrando bien qué se midió y qué no, para no descartar la idea general de régimen».

## 1. Tesis y por qué esto va primero
Tesis de Nico: la ventaja económica de EdgeLab sería una **canasta de estrategias de régimen**, renovada rápido (ponderar, retirar,
sumar). Una canasta que rota hacia lo que viene funcionando gana sólo si **el rendimiento reciente de una estrategia predice el
siguiente** (persistencia). Esto mide esa condición sobre TODA la grilla de U1, sin elegir celdas, y además corre la canasta como una
sola regla.

## 2. Población y espacio del que sale (regla de población)
Espacio enumerado: las 4.478.976 celdas de la grilla U1 (U1-INDAGA × escala, `edgelab/research/u1_cfd.py` / `u1_oro.py`), cada una una
«estrategia». Alternativas consideradas y no elegidas hoy: otras gramáticas (LUX-IMB, ZGAP, GAP-RTH, U1-ZONAS) —quedan como NO MEDIDO—;
celdas elegidas por el DESC —descartado: mediría la persistencia de lo seleccionado, con sesgo de selección—. Se usa la grilla completa
porque es la población de la que una canasta real elegiría.

## 3. Datos
Dukascopy, sensor y ejecución sobre el mismo CFD con la fricción canónica de su futuro (`embudo_runners.friccion`):
USA500 (→ ES), USA30 (→ YM), USATECH (→ NQ), XAUUSD (→ GC). Período **2023-01-02 → 2026-03-31** (≈ 39 meses; descubrimiento; la
réplica A3 abr–sep 2026 y el holdout desde la sesión del 2026-10-01 no se tocan). Cortes de las variables: E0 del propio período
(target-free).

## 4. Qué se mide (etapa `PERSIST`, `edgelab/research/persistencia.py`)
Matriz celda × mes del P&L neto. Para cada instrumento:
- **Persistencia de sección cruzada**: Spearman entre el rendimiento por operación de cada celda en la formación y en la prueba, y el
  diferencial del decil superior de formación en la prueba. Horizontes (formación → prueba, meses): 1→1, 3→1, 3→3, 6→3; mínimo de
  operaciones en formación 10/10/20/30 y en prueba 5. Ventanas de prueba sin solapamiento; **la unidad de inferencia es la ventana**.
- **Separación régimen / estática**: cada horizonte con desfase 0 (formación inmediatamente antes) y desfase 12 meses. La calidad fija
  de una celda (p. ej. pierde siempre por costos) aparece en los dos; la persistencia de **régimen** es la diferencia
  ρ(desfase 0) − ρ(desfase 12).
- **Canasta como una regla** (`meta_regla`): cada mes, las k ∈ {10, 100} celdas con mejor formación (1 o 3 meses; criterio t o media;
  mínimo 10 / 20 operaciones) se operan el mes siguiente; P&L neto por operación por mes. 8 reglas por instrumento.
Pruebas con desenlace: 8 de persistencia + 8 reglas = 16 por instrumento, **64 en total**, registradas en el contador global antes de
lanzar. Controles (`tests/research/test_persistencia.py`): ruido puro → ρ ≈ 0 y canasta ≈ 0; régimen plantado → ρ > 0 con desfase 0 y
≈ 0 con desfase 12; calidad estática → ρ > 0 en los dos.

## 5. Cómo se lee (decidido antes)
- **Hay persistencia de régimen** en un horizonte si ρ(0) − ρ(12) > 0 con t entre ventanas ≥ 2 en ≥ 2 de los 4 instrumentos.
  Entonces la canasta tiene una base y se diseña con ese horizonte (pre-registro nuevo, con costos de rotación y su propio OOS).
- **La canasta como regla** cuenta como prometedora si su neto por operación tiene t entre meses ≥ 2 en algún instrumento; con 64 pruebas
  se informa también el ajuste por BH (q 0,10). Ninguna regla se promueve desde acá: si alguna es prometedora, va a un pre-registro
  propio con réplica abr–sep 2026 (ES/NQ) y holdout.
- **Sin persistencia** (ρ(0) − ρ(12) ≈ 0 con potencia) **refuta sólo esto**: «el rendimiento mensual a trimestral de las celdas de la
  grilla U1, en estos 4 CFD, 2023–2026T1, persiste lo suficiente para una canasta que rote por rendimiento reciente». No refuta la idea
  general de régimen (ver §6).
- Potencia: con 13–38 ventanas por horizonte, el error estándar de la ρ media entre ventanas se estima de los datos y se publica junto
  con el efecto mínimo detectable; un nulo sin MDE no se interpreta.

## 6. Qué NO mide (registro NO MEDIDO, para no matar la idea general de régimen)
- **Régimen definido por el mercado** (volatilidad, tendencia, horario, macro) en lugar de por el rendimiento pasado de la estrategia:
  una canasta que pondera por un estado observable del mercado puede funcionar aunque el rendimiento pasado no persista.
- **Otras gramáticas**: LUX-IMB, ZGAP, GAP-RTH, U1-ZONAS, aVolClusterPOI, escalonadas, etc.
- **Otros instrumentos y datos**: futuros con ticks reales (sólo desde jul-2025), 6E/EURUSD, L2.
- **Horizontes** menores a un mes (semanas, días) y mayores a 6 meses.
- **Otras reglas de canasta**: ponderación por riesgo, retiro por drawdown, mínimo de diversificación, combinación entre instrumentos.
- **El período posterior** (abr-2026 en adelante): el régimen actual puede ser distinto del de 2023–2026T1.

## 7. Justificación económica
Si los edges intradía son efímeros (los arbitran, cambian los participantes, cambia la volatilidad), una celda que funcionó el último
trimestre tiene más probabilidad de seguir funcionando el próximo que una al azar; eso, y no una regla eterna, sería lo explotable.

## 8. Cómo podría refutarse
ρ(0) − ρ(12) ≈ 0 en todos los horizontes e instrumentos con potencia publicada; canastas con neto por operación ≤ 0 después de costos.

## 9. Riesgos
Las celdas están muy correlacionadas (perillas acumulativas): por eso la unidad es la ventana. El CFD no es el futuro (spread nocturno,
horario). 39 meses dan pocas ventanas en los horizontes largos (6→3: ≈ 10): ahí el resultado puede quedar sin potencia.
