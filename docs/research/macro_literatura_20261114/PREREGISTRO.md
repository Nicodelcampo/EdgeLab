# Ideas de la literatura medidas directo (sin Builder) — pre-registro (2026-11-14)

Estado: VIGENTE. Etapa EF3 (réplica de efectos publicados; prior alto). North Star sha256 16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345.
Código: `edgelab/research/macro_literatura.py`; kernel `tools/kaggle_grilla/macro_literatura_main.py` (lo lanza `tools/macro_literatura.py`).
Datos: barras D1 (27 activos) y H1 (8 índices, oro, crudo) de Dukascopy exportadas de SQX (`tools/sqx_barras.py`), hasta 2026-09-29
(dataset privado `nicolasbuttaro/edgelab-sqx-barras`). Fichas: LIT-TSMOM, LIT-FIN-DE-MES, LIT-NOCHE, LIT-INTRADAY-MOM (`docs/research/ideas/BANCO_IDEAS.md`).

## Reglas (fijas, pocas perillas; nada abierto el fin de semana)
| Regla | Activos | Perillas | Variantes |
|---|---|---|---|
| TSMOM: signo del retorno de L días al cierre del viernes; lunes apertura → viernes cierre | 27 | L ∈ {20, 60, 120, 250} | 108 |
| FINMES: cierre del penúltimo día hábil → cierre del día hábil N del mes siguiente (sale el viernes si cruza fin de semana) | 8 índices | N ∈ {1, 3} | 16 |
| NOCHE: cierre NY (16:00) → apertura (≈ 09:00–09:30), lunes a jueves | 8 índices | — | 8 |
| IMOM: signo 16:00 previo → 10:00; operar 15:00 → 16:00 | 8 índices | — | 8 |
| Canastas de igual riesgo por regla y perilla | — | — | 8 |
Total: **148 variantes** (registradas en el contador). R = retorno / (2 × desvío móvil causal de las 60 operaciones previas), neto del
spread de Dukascopy por ida y vuelta. Swap no incluido (tenencias de horas a 4 días; se mide aparte en la cuenta).

## Inferencia (fijada antes)
- Nulo de la búsqueda: la familia completa (las 148) sobre series sintéticas (semanas del propio activo re-encadenadas al azar), 200
  réplicas; umbral = p95 del máximo t en DESC.
- Pista: t DESC > umbral **y** R > 0 en OOS 2020–2023 **y** en RECIENTE 2024-01 → 2025-07. PSEUDO (2025-08 → 2026-09-29) se lee como réplica
  ex ante (no se usó para nada). Lo que pase va al contrato de calidad (`docs/infra/CONTRATO_CALIDAD_ESTRATEGIAS.md`).
- Las canastas son la lectura principal (diversificación y menos multiplicidad); los activos sueltos, el detalle.

## Justificación económica y cómo podría refutarse
En las fichas del banco. Refutación: ninguna variante supera el umbral, o las que lo superan son negativas en OOS o en RECIENTE
(efecto publicado que ya no está: decaimiento post-publicación).

## Corrida v1 descartada (2026-11-15, antes de concluir)
La v1 usó spreads con la unidad mal convertida desde el catálogo de SQX en plata (0,6 → 98 pb) e índice dólar (5 → 495 pb), y 0 en los
bonos; esos activos dominaban el promedio de las canastas (TSMOM canasta t −5 a −8 por eso). Se corrigen a spreads típicos de Dukascopy
(plata 0,025; índice dólar 0,03; bonos 0,02–0,03) y se relanza (v2). Se agrega el R BRUTO (sin spread) para separar señal de fricción.
Archivo de la v1 conservado: `RESULTADO_v1_DESCARTADO_spreads.json` (no se usa para concluir). Lectura de la v1 que no depende del
error: IMOM en S&P da ≈ 0 en bruto (−0,003 R) y −0,04 en neto: la hora final no paga el spread.
