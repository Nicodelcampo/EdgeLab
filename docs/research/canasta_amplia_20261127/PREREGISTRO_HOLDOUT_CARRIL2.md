# CANASTA-AMPLIA: apertura del HOLDOUT A5 de la canasta Carril 2 sellada (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO — **BLOQUEADO por K27** (potencia 0,25 con la mitad del efecto, 0,63 con el efecto completo). No se abre sin
autorización escrita de Nico que levante K27 para esta apertura, como en `a20_terminal.py`. La lectura está implementada
(`tools/canasta_amplia.py holdout_carril2`) y se niega a correr sin esa autorización.

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF4** (confirmación en datos no mirados). **Familia:** `CARRIL2_A5` (su única apertura de HOLDOUT A5). **Pruebas:** 1.

Cambio respecto a falla previa: cada regla de Carril 2 sola quedó «sin evidencia» (sin potencia). Acá se prueba **una sola hipótesis
de canasta**, sin elegir reglas mirando la réplica. Quedan afuera C2_VZ y C2_EVRP, porque sus meses HOLDOUT ya los recorrieron las
corridas NT8 (`candidatas_nt8_20261125/NOTA_HOLDOUT_A5_VISTO_EN_NT8.md`).

Antecedentes:
- `REGISTRO_POSTERIOR.md` y `EXPLORACION.json` de esta carpeta: canasta Carril 2 completa DESC t 2,98, REP t 3,11; sin VZ ni EVRP,
  DESC t 2,77 (Sharpe 0,80, 143 meses) y REP t 2,01 (Sharpe 1,07, 42 meses, 76 % de meses positivos);
- encogimiento del pozo DESC → HOLDOUT b 0,70.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K27 potencia: no pasa, ver arriba; K36: R por operación, sumado por día y
ponderado; K49 una lectura).

Potencia previa: canasta mensual con DESC+REP: media 1,257, sd 5,069 (unidades de R ponderado), Sharpe 0,86, 185 meses. Lectura fija de
63 meses HOLDOUT: potencia 0,25 con la mitad del efecto (protocolo), 0,40 con b 0,70, 0,63 con el efecto completo → K27 NO (hacen falta
101–403 meses).

Diagnóstico de mecanismo: sin grilla. Aporte en REP de la canasta completa, en orden:
- VZ 27 %, EVRP 21 %, TT 18 %, D7 15 %, IBS 12 %, ROT 9 %, TOM 5 % y VBB −7 %;
- sin cada regla, la réplica sigue con t 2,48–3,96;
- por instrumento, ES 44 % y NQ 40 %.

## Regla congelada
- **Canasta:** 16 regla-instrumento de Carril 2 (lotes 1 y 2, sin controles `N`, sin C2_VZ ni C2_EVRP) con media mensual DESC > 0:
  `C2_D7_{ES,GC,NQ}`, `C2_IBS_{ES,NQ}`, `C2_ROT_{ES,GC}`, `C2_TOM_{NQ,RTY,YM}`, `C2_TT_{ES,NQ,YM}` y `C2_VBB_{ES,NQ,YM}`.
- **Pesos:** fijos, de DESC (1/sd mensual, media 1), en `PESOS_CARRIL2_SELLADA.json`.
- **Reglas, costos y motor:** los de `tools/carril2.py` sin cambios.
- **Operaciones leídas:** las que **entran** en meses HOLDOUT de A5 (cualquier salida), 2006 → 2026-09-30. Ninguna desde 2026-10-01.
- **Medida:** suma diaria del R ponderado, agregada por mes.

## Cómo se lee (decidido antes)
- **CONFIRMA:** t mensual de una cola ≥ 1,645 en los meses HOLDOUT.
- **NO_CONCLUYENTE:** 0 < t < 1,645. Se informa con la potencia que tenía.
- **EN_CONTRA:** media ≤ 0.
- **Combinación declarada (modo exploratorio, Nico 2026-11-08):** Stouffer de REP y HOLDOUT, z = (t_REP + t_HOLDOUT)/√2, informada aparte,
  no decide. La probabilidad de azar de desarrollo es la de la canasta en DESC: t 2,77, p ≈ 0,003.

## Justificación económica
Reversión de corto plazo (IBS, Double 7), calendario (cambio de mes, Turnaround Tuesday), régimen de volatilidad (VBB) y rotación entre
activos: primas documentadas en índices, con correlación baja entre sí (0,12 en el pozo). En canasta, la información se suma.

## Cómo podría refutarse
Media ≤ 0 en los meses HOLDOUT (EN_CONTRA), o t < 1,645 con la potencia declarada (NO_CONCLUYENTE: no mata la canasta, la deja en el
forward).
