# Confirmación congelada — «el cluster HFT grande no defiende el nivel» (réplica abr → sep 2026)

Estado: PRE-REGISTRO (2026-11-10, antes de generar la tabla de la réplica). Familia `HFT_RUPTURA` (su réplica abr–sep, una vez).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF4 (réplica).
Origen: `ESTABILIDAD_CLUSTERS.md` (estable en activos independientes, 4/5 bloques, p azar 0,088). Decisión de Nico: confirmar.

## Datos y evento
Réplica 2026-04-01 → 2026-09-30 (no usada por la familia), NQ, ES, RTY, YM; definiciones de cluster congeladas por los E0-b
(NQ K8_A050, ES K12_A100, RTY K12_A050, YM K4_A025; `HFTC_e0b.json`, `HFTC_e0b_otros.json`). Evento: primer regreso D0 (mismo
generador `hft_ruptura.ruptura_del_dia`), real y control (pseudo-cluster ±1.200/±2.400 s sin superposición). Desenlace `rompe`
(carrera ±X, X = fricción / 0,08). El kernel `ruptura_replica` sólo guarda la tabla; el análisis lo hace
`tools/confirmar_no_defiende.py`, committeado ANTES de que exista la tabla.

## Hipótesis (lote de 2, LORD++ reservado: nivel 0,0109, `LIBRO_LORD.json` reserva `rep_no_defiende_20261110`)
- **H1 (principal):** en NQ + RTY + YM juntos, la media por sesión de (ruptura real − ruptura control) > 0. p de una cola por
  inversión de signo por sesión (`banco_eventos.real_menos_control`). ES se informa aparte como diagnóstico (en DESC va al revés).
- **H2 (secundaria):** en NQ y ES, los toques reales con `tendencia_alineada` en el tercil bajo (cortes CONGELADOS de DESC: NQ
  −5,7607; ES −3,2444) rompen: media > 0, p por inversión de signo por sesión (`banco_eventos.estabilidad`).
- Decisión: Simes + BH al nivel reservado (`LibroLord.resolver`). **Confirmada** = nominada por el lote Y ≥ 3/5 sub-bloques
  positivos (regla 08/11 adaptada a medio año). Se informa siempre el efecto por activo, los 5 bloques y el MDE.

## Orden declarado
La tabla de la réplica se analiza DESPUÉS de correr el banco de REBOTE_NIVEL_SESION (que usa la misma ventana con otros eventos),
para que nada de esta confirmación (en particular el rebote del control) se mire antes de esa familia.

## Justificación económica
Un nivel cualquiera de la sesión revierte en su primer regreso; donde se ejecutó tamaño grande (cluster HFT) esa liquidez ya se
consumió y el precio sigue. Si es mecanismo, aparece en datos posteriores con el mismo signo.

## Cómo podría refutarse
H1 no nominada o con menos de 3/5 bloques positivos en la réplica; o positiva sólo en un activo.

## Pruebas
2, registradas como `hft_ruptura/rep_no_defiende` en el contador global.
