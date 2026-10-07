# AVCL-RACIMO-CONF — pre-registro: en racimos OFF, ¿el precio vuelve/atraviesa? — prueba única — 2026-10-06

**Escrito ANTES de calcular nada con estos datos.** Decisión de Nico ("dale").
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`. Información direccional, **no P&L**.

## Origen
AVCL-RACIMO (MNQ): en zonas OFF en racimo, `s` = lado × asim a H50 fue −0,039 en 50t (Holm 0,054) y −0,057 en 25t.
MNQ queda **excluido**, porque fue el dato de descubrimiento.

## Datos (nunca usados para AVCL)
- **ES, YM, RTY, MGC**: contratos líderes con sesiones aprobadas por el RESOLVER, 2025-07-01 → 2026-09-30, RTH.
- Holdout no leído.
- Se usaron antes sólo para VolTicksDef (VTD-VELA, VTD-BRACKET), nunca con aVolClusterPOI.

## Definición congelada (idéntica a AVCL-RACIMO, celda principal)
- aVolClusterPOI `run_full_fast`, barras de **50t**, parámetros base: p95, W10, k2, m2, invalidación None, MaxAge 500.
  La paridad está validada en MNQ y el código es el mismo.
- Racimo: `burst_count ≥ 3` (indicador). Aislada: `burst_count = 1` y ninguna zona a ≤ 40 ticks en ±200 barras.
- Sólo zonas **OFF**. `s_50 = lado × (U − D)/(U + D)`, con excursiones desde el close de creación en las 50 barras
  siguientes, en la misma sesión.
- Estimador: β de racimo contra aislada, con FE (contrato × franja, tercil de amplitud, decil de volumen del bloque) y SE
  por sesión.

## Prueba única
- Pooled de los 4 instrumentos.
- **Unilateral, H1: β < 0** (regreso/ruptura).
- **CONFIRMA** si p ≤ 0,05. Si no, **DESCARTADA** para esta definición.
- Se publica el MDE (≈ 2,5 × SE).

## Descriptivos (no cambian la decisión)
Por instrumento; H10; criterio denso; `y_pre` H50 (consolidación).

## Justificación económica
Las zonas apiladas marcan inventario defendido repetidamente. Si el nivel termina cediendo, la liquidación de esas
posiciones empuja el precio a través de él.

## Registro
1 prueba, familia `AVCL_RACIMO_CONF`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
