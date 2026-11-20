# RQ5-REGIMEN: la banda de ruido de Zarattini en el régimen actual — meseta, cinco índices y una mejora declarada (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — se commitea antes de calibrar y de correr.
- **Pedido de Nico:** «iterá y profundizá … releé las estrategias, cálculos y mecanismos que se usaron para invalidar el descarte;
  indagá para mejorar rentabilidad o reconocer la que ya tienen; pruebas de robustez de picos o mesetas y multiactivo; que pasen por la
  cadena entera; luego abrimos el holdout».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF4** (régimen + robustez sobre DESC de A5; confirmación en el holdout A5). **Familia:** `RQ5_REGIMEN`; linaje padre
  `ROBOQUANT_A5` (información).
- **Herramientas:** `edgelab/research/rq5_regimen.py` (contrato de `tablas.py`; la definición de fábrica reproduce exactamente la RQ5 de
  `roboquant_a5.py`: 162/162 eventos de NQ en 2024, mismos stops y objetivos), `tools/a5_campana.py` (calibración M1 contra ticks y
  corrida) y `tools/rq5_regimen.py` (lectura pre-registrada). `registro_global.exigir_contada` al inicio (K51).

Antecedentes:
- **ROBOQUANT** (`../roboquant_20261118/RESULTADO.md`): RQ5 bruto +0,062 R en DESC 2006–2025, parejo en ES/NQ/YM; neto −0,011 sobre toda la
  ventana.
- **REVISION_DESCARTADAS** (`../REVISION_DESCARTADAS_20261119.md`): neto 2006–2017 −0,050, neto 2018–2025 +0,051, y el control (ruptura
  tardía) en contra.
- **Factores:**
  - F-ROBOQUANT-BRUTO-SIN-NETO;
  - F-VIDA-VENTAJA-INTRADIA-FRICCION (la media no se apaga, la gobierna la fricción);
  - F-SALIDA-TECNICA-REGALA-LA-GANANCIA y F-RUPTURA-VIVE-DEL-DIA-DE-TENDENCIA (mantener hasta el cierre);
  - F-STOP-GRANDE-FRENTE-A-FRICCION.
- **Error a declarar:** la REP de RQ5 (2018–2025) se miró en la revisión del 19-nov, aunque el acta de ROBOQUANT decía que no se había
  leído. **La REP queda contaminada para RQ5:** se informa pero no decide nada. El holdout A5 nunca se calculó.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K33 costos estimados, K36 escalas, K40 motor calibrado, K48 causalidad, K49
potencia, K51 conteo antes de correr, K52 tamaño, K55/K56 diagnóstico y episodios).

Potencia previa:
- **Base:** `tools/potencia_previa.py` sobre la fábrica en DESC 2018–2025 de NQ+ES+YM da 24 ops/mes (sólo meses DESC), R/op +0,051, sd 1,04 y
  107 meses para decidir.
- **Holdout de esos tres índices:** una lectura de N 860 tiene potencia 0,18 con la mitad del efecto. Con eso **NO se abre**.
- **Por eso:** se suman RTY y EMD (≈ ×1,67 de operaciones; holdout A5 2018–2025 ≈ 1.430) y la apertura se declara en **modo exploratorio**
  (decisión de Nico del 2026-11-08), con la combinación de Fisher entre DESC y holdout.
- **Plan de potencia de la apertura:** se calcula y se registra con `holdout_ventanas.registrar_apertura` antes de abrir. Un holdout no
  significativo no mata (K49).

Diagnóstico de mecanismo:
- **Perillas:** L (memoria de la banda) y m (ancho) mueven cuántos días califican; corte mueve la hora; s y tp mueven la geometría de salida.
  Se espera que L y m sean casi un solo eje de severidad (como en Z).
- **Antes de leer el R de las celdas** se publican, con `edgelab.research.diagnostico_grilla`:
  - las operaciones por celda;
  - el número efectivo de variantes;
  - las perillas inertes;
  - el Spearman entre operaciones y R;
  - los episodios por mes.
- **Si hay eje de severidad**, la lectura es dosis-respuesta y no «la mejor celda».

## Justificación económica
- **Mecanismo:** un movimiento temprano que sale de la banda de ruido histórica del mismo horario, a favor del VWAP, señala flujo
  direccional del día: cobertura de gamma corta y fondos de momentum intradía (Zarattini, Aziz y Barbon 2024; Baltussen et al. 2021).
  Continúa hasta el cierre más de lo que revierte.
- **Quién pierde:** quien opera la reversión a la apertura.
- **Por qué el neto cambió en 2018:** la fricción relativa (fricción / riesgo) cayó de ≈ 0,09 a ≈ 0,03 con el nivel de precio de los
  índices.

## Pruebas y decisión (fijas)
Datos:
- M1 real de futuros de NT8 de NQ, ES, YM, RTY y EMD.
- EMD con spread ESTIMADO, declarado (K33, `costos.estimados_permitidos` citando este archivo); no tiene ticks, así que no calibra y se
  informa aparte.
- Ventana de eventos 2006-01-06 → 2025-07-31.
- **Régimen declarado: 2018-01-01 → 2025-07-31**, sólo meses DESC de A5. Es la convención por época de RE_INDAGACION y FRECUENCIA_PROP,
  anterior a esta campaña. Se informan también 2006–2017 y un corte sup-F.
- R neto = r bruto − fricción / riesgo.

**P1 — meseta (grilla de 324 celdas = 27 definiciones × 12 ejecuciones, NQ+ES+YM+RTY juntos):**
- se publican todas las celdas, el diagnóstico K55 y los 8 vecinos de la fábrica (una perilla a un paso);
- pasa si la fábrica tiene R > 0 con p < 0,05 (bootstrap por sesión) **y** ≥ 70 % de las celdas evaluables (≥ 30 op.) son positivas **y**
  ≥ 6 de 8 vecinos son positivos.

**P2 — multiactivo (fábrica):** pasa si es positiva en ≥ 3 de los 4 índices calibrados (NQ, ES, YM, RTY). EMD se informa sin votar.

**P3 — mejora declarada (una sola):**
- salida al cierre (tp = cierre) contra la fábrica (tp 2), por el mecanismo de día de tendencia;
- la mejora se adopta sólo si el contraste pareado por evento es > 0 con p < 0,05 en DESC del régimen;
- si no, la regla congelada sigue siendo la fábrica.

**Veredicto:**
- REGIMEN_ROBUSTO si pasan P1 y P2;
- INTERMEDIO si pasa una;
- SIN_REGIMEN si ninguna.

Con REGIMEN_ROBUSTO:
- se registra la apertura exploratoria del holdout A5 (meses HOLDOUT 2018–2025, cinco índices, regla congelada = fábrica o la mejora de P3,
  N fijo = todas las operaciones);
- p de desarrollo = la de la fábrica en DESC del régimen; combinación de Fisher;
- **una sola apertura**, que vale también por la familia padre ROBOQUANT_A5.

**Contador:** 3.569 pruebas = `tablas.conteo` del módulo (3.564: 27 definiciones × 12 ejecuciones × (1 + 10 filtros comunes), que se cuentan aunque no se usan: conservador) + 4 de P2 + 1 de P3, registradas antes de correr.

## Cómo podría refutarse
- La fábrica con R ≤ 0 en DESC del régimen con los cuatro índices.
- Menos del 70 % de celdas positivas o vecinos en contra: era un pico, no una meseta.
- Positiva sólo en uno o dos índices.
- El holdout con media ≤ 0, en contra con potencia.
- Calibración M1 contra ticks fallida (K40).
