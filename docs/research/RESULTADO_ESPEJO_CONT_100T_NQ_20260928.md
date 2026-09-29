# ESPEJO-CONT-100T-FILTROS — NQ (Lucid) — resultado (2026-09-28)

Kaggle `edgelab-espejo-cont100t-nq-20260928`, nulo corregido. 196 sesiones; 57–108 mil candidatos por nivel, 8.000
simulados (sorteo con semilla fija). El reporte del notebook falló por un error de parseo («NQ» contiene «_N»); se
rearmó localmente con los trades guardados tras corregir `rsplit` (mismo cálculo).

**1.050 celdas; p global < 0,001; 71 sobreviven (t crítico 3,93) — todas con TP = 0,25 W** (41 con SL 0,25, 24 con SL 0,5,
6 con SL 1), repartidas en casi todos los filtros y niveles. Exceso +1,0 a +3,4 % de W; **R bruto −0,014 a −0,051 W**.
Promedios por nivel (todos, 15 celdas): exceso −0,003 a +0,007; R bruto −0,005 a +0,007. W mediano 33–47 t.

## Lectura
- Lo que sobrevive en NQ (y en YM) no depende del filtro: aparece con TP = 0,25 W en casi cualquier subconjunto. Un efecto
  del espejo o de la tendencia debería concentrarse en ciertos filtros; uno que aparece en todos con el TP más chico apunta
  a **un residuo del nulo en objetivos cortos** (orden intravela, discretización de 25t → 100t, SL-primero en empates),
  no a información de mercado.
- En ningún caso el R bruto es positivo: no hay configuración rentable.
- **Revisión pendiente del nulo en TP chicos** antes de leer estas celdas: comparar el nulo contra un control empírico
  (misma entrada en momentos al azar de la misma sesión) en TP 0,25 W. Si el control da el mismo exceso, es artefacto.

## Control empírico (28/09, Kaggle `edgelab-nullctl-nq-cont-n4-20260928`, 4.000 trades, nivel 4)
| TP / SL | Calibración del nulo en velas al azar | Exceso con nulo | Exceso empírico (vs azar) |
|---|---|---|---|
| 0,25 / 0,25 | **+0,012** [+0,009; +0,015] | +0,017 | +0,006 [0,000; +0,011] |
| 0,25 / 0,5 | **+0,012** [+0,008; +0,017] | +0,018 | +0,009 [+0,001; +0,017] |
| 1 / 1, 1,5 / 1, 2 / 1 | −0,019 a −0,021 | −0,005 a −0,031 | −0,009 a +0,016 (IC cruzan 0) |
**Confirmado: el nulo está sesgado en TP 0,25 W** (+1,2 % de W incluso en velas al azar). Dos tercios del «exceso» de esas
celdas es sesgo del nulo; lo que queda (+0,6 a +0,9 %) es marginal. Las 71 celdas de NQ y las de YM/MYM/MNQ con TP 0,25
**no son señal**. Para TP amplios el sesgo va al revés (−2 %). Regla: en estos estudios, el exceso se lee contra el control
empírico, no contra el nulo simulado.
