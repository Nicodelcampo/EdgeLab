# T (FundedSync) como edge de régimen: ¿vale descartar lo que sólo funciona desde 2020? (propuesta, 2026-11-18)

Estado: VIGENTE — prueba 1 corrida (`RESULTADO.md`: REGIMEN_ROBUSTO); pruebas 2 y 4 pendientes.
como campaña; las cifras de §2 son exploración sobre desarrollo ya mirado (sin holdout).
- **Pedido de Nico:** «Investiga en Internet para determinar si realmente es válido descartar estrategias que sólo funcionan desde
  2020. Para mí no, y 6 años que funcione me parece un tiempo decente … Otra cosa sería que esté sobreajustada desde 2020.»
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Regla vigente que ya lo decía** (Nico, 2026-10-22, CLAUDE.md «Edges actuales»): el pasado no mata; la ventana reciente se declara
  y se confirma en lo más reciente sin usar. Las respuestas del 18-nov que leían los 12 años negativos de T como descalificantes la
  contradijeron.

## 1. Literatura (fuentes primarias)
| Fuente | Qué dice | Qué implica para T |
|---|---|---|
| Pesaran y Timmermann (2007), *J. of Econometrics*, «Selection of estimation window in the presence of breaks» | Con quiebres, los datos previos sesgan el pronóstico; lo óptimo es la ventana posterior (más algo previo sólo si el quiebre es chico) | No exigir que T haya funcionado en 2008 si hubo quiebre |
| McLean y Pontiff (2016), *J. of Finance*, 97 anomalías | −26 % fuera de muestra, −58 % tras publicarse; no desaparecen (se rechaza 100 %); la caída fuerte llega 3–5 años después | Esperar retener 50–75 % del efecto el año siguiente, no cero |
| Bajgrowicz y Scaillet (2012), *JFE*, reglas técnicas con FDR | Entre miles de reglas, las mejores no se podían elegir ex ante; con costos chicos el resultado desaparece | El riesgo es la SELECCIÓN (vendedor y nosotros miramos 2020+), no la edad |
| Baltussen, Da, Lammers y Martens (2021), *JFE* | Momentum intradía en futuros 1974–2020 causado por cobertura de gamma corta (market makers de opciones, ETF apalancados), «cada vez más prominente» | Mecanismo publicado compatible con un ORB que mejora en índices con mucho flujo de opciones |
| Adams, Fontaine et al. (2025, SSRN 5641974), 0DTE | La presencia de 0DTE amortigua el momentum y la volatilidad intradía del S&P 500 en promedio (gamma neta positiva de los market makers) | Coherente con que T rinda en NQ y casi nada en ES |
| Bailey, Borwein, López de Prado y Zhu (2017), PBO por CSCV | Probabilidad de sobreajuste del backtest con validación cruzada combinatoria | Herramienta para la prueba 1 de §3 |

## 2. Medido (exploración, NQ, `docs/research/m1_largo_20261117/FS_OPS_T2008_NQ.csv.gz`, neto en R)
- **Un quiebre en la media, ubicado sin elegirlo a mano** (sup-F, recorte 15 %): 2021-02-10. Media −0,062 R antes y +0,189 R
  después; p = 0,003 contra 300 permutaciones de meses.
- **Todos los años desde el quiebre positivos:** 2021 +0,149 · 2022 +0,220 · 2023 +0,152 · 2024 +0,271 · 2025 +0,155 ·
  2026 (hasta sep) +0,182 R/op; ≈ 229 operaciones por año, sd 1,16 R/op.
- **Probabilidad de que los próximos 12 meses den neto > 0** (normal, incluye el error de estimación de la media 2020+):
  retiene 100 % → 0,97 (+37 R); 75 % → 0,93; 50 % → 0,85 (+18 R); 25 % → 0,70. No modela un corte abrupto del régimen.
- **Contexto ya medido:** el bruto de ES y YM también salta en 2020 (+0,10 / +0,11 R) y el de MidCap + Russell no
  (`RESULTADO_T_2020.md`); holdout oct–nov 2026 +14,2 pts/op con n 26 (no significativo solo).

## 3. Pruebas propuestas para separar régimen real de sobreajuste (a pre-registrar al retomar)
1. **Meseta de parámetros y PBO** en 2021+: largo del rango de apertura, k del KNN, multiplicador del stop; meseta → no sobreajuste.
2. **Fuera de muestra verdadero del vendedor:** medir T sólo desde la fecha en que FundedSync fijó sus parámetros (preguntar a Nico la
   fecha de compra o de la versión). Nada posterior pudo usarse para elegirlos.
3. **Mecanismo:** ¿T rinde más con gamma negativa (GEX desde 2011) o con más volumen de 0DTE? Una sola prueba direccional,
   pre-registrada, K48 (gamma del cierre previo) y K49 (potencia en días).
4. **Vigilancia secuencial en papel:** CUSUM / e-proceso sobre el R de T (`edgelab/funnel/secuencial.py`) que corte cuando el nivel
   posterior a 2021 deja de sostenerse.
- **Etapa EF:** EF3 exploratorio (1, 3) y EF4 (2: datos que el vendedor no vio). Familia: `FUNDEDSYNC` (linaje existente).
- **Cómo podría refutarse:** PBO > 0,5 o pico aislado en la grilla (1); R ≤ 0 desde la fecha del vendedor con potencia (2); sin
  relación con gamma ni 0DTE deja a T como régimen sin mecanismo, no la mata (3).
- **Decisión que cambia:** si 1 y 2 pasan, T sube de pista a candidata con tamaño chico (micro) y vigilancia 4.
