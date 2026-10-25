# Resultado — GAP-RTH, descubrimiento (C-TICKS F4 relanzada con años de datos)

Estado: VIGENTE (EF2/EF3; la réplica abr–sep 2026 está corriendo). Fecha: 2026-10-25.
Pre-registro: `PREREGISTRO_GAP_RTH.md`. Kernel `nicolasbuttaro/gap-rth-desc`; datos crudos `GAP_RTH_desc.json` (todas las celdas).

## Tamiz
480 pruebas registradas, 416 evaluables (≥ 30 operaciones), Storey π0 0,77, **2 nominadas** (q 0,072), las dos en **NQ, canal reciente**.

| celda (g · objetivo · salida · stop) | ops | media neta pts/op | IC90 | canal desarrollo en el futuro NQ (misma celda) |
|---|---:|---:|---|---|
| 0,6 ATR · cierre previo · 120 min · sin stop | 49 | +58,0 | [+29,1; +87,1] | ver JSON |
| 0,6 ATR · cierre previo · fin del día · stop 1 gap | 49 | +79,4 | [+39,8; +118,9] | +100,3 [+52,8; +148,4] (n 40) |

## Lectura del paisaje (descriptivo, todas las celdas en el JSON)
- NQ: 70/80 celdas con media > 0 en el total (2023–2026), 44/64 en reciente, 41/64 en el futuro. El mejor del total: g 0,6, objetivo
  el cierre previo, hasta el fin del día: +35 pts/op, IC90 [+14; +57], n 182 (q 0,13, no nomina).
- ES: 59/80 > 0 en el total; mejor +4,2 pts/op [+0,65; +7,8] (q 0,25). Apunta igual que NQ, más chico.
- YM: 34/80 > 0; reciente 10/48: no transporta.
- Patrón común: gaps grandes (≥ 0,6 ATR diario) que se cierran enteros. Los umbrales chicos (0,15–0,3) no ganan.

## Qué sigue (fijado en el pre-registro)
Réplica en el futuro NQ abr → sep 2026 (sesiones no miradas por GAP_RTH) de las 2 nominadas congeladas, en un lote: paso de LORD++
reservado antes de lanzar (`GAP_RTH::GAP-RTH-REP`, t = 1, nivel 0,010937). Kernel `nicobuttaro/gap-rth-rep`. El código del kernel de
réplica difiere del de DESC sólo en el lector de Dukascopy (13× más rápido, salida idéntica, `tests/research/test_fuentes_ticks.py`);
la réplica lee sólo el futuro, que no usa ese lector.

## Riesgos
n chico por celda (49); la nominación es del canal reciente (desarrollo); en el total la misma regla rinde menos (+35); el CFD no es el
futuro (el canal de desarrollo en el futuro coincide en signo y tamaño).
