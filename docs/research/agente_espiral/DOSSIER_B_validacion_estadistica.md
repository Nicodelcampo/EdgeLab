Dossier B — anexo de docs/research/AGENTE_ESPIRAL_20261004.md — verificado 2026-10-04

# Dossier: validación estadística de estrategias bajo multiple testing y sesgo de selección, para un embudo GPU→CPU con agente siempre activo

**Cómo verifiqué esto.** Las referencias bibliográficas (revista, volumen, páginas, DOI) las confirmé en las páginas del editor, de SSRN o de arXiv. Las fórmulas de DSR, PBO/CSCV y MinBTL las saqué del texto de los PDF originales, que bajé y pasé a texto plano. Además recalculé con Python el ejemplo numérico del paper del DSR: el resultado coincide, DSR ≈ 0.90. El estado de cada librería lo revisé en sus repos de GitHub, PyPI y documentación entre octubre y septiembre de 2026. Lo que es **inferencia o derivación mía**, y no viene de la literatura, va marcado con **[inferencia]**.

---

## 0. Resumen ejecutivo

1. **Con datos históricos fijos, ningún umbral alcanza.** El *False Strategy Theorem* muestra que el máximo Sharpe esperado de N pruebas sin habilidad crece sin techo con N. Un agente que corre indefinidamente tiene N→∞, así que solo dos cosas lo protegen: llevar la cuenta acumulada de todas las pruebas y confirmar con **datos nuevos**, sea un holdout de una sola apertura o trading en vivo o en papel.
2. **Para miles o millones de celdas** sirven los tests de "max-estadístico" con bootstrap: Reality Check, SPA y StepM de Romano-Wolf, más FDR/FDP. Son paralelizables en GPU. **Para un puñado de finalistas** sirven el Model Confidence Set y el test de permutación de Masters, que reoptimiza todo el pipeline. Ambos son caros y no escalan.
3. **El DSR es barato**, con forma cerrada, pero su validez depende de estimar bien N_eff, el número efectivo de pruebas independientes, y la varianza del Sharpe entre pruebas. **PBO/CSCV** mide si el *proceso* de selección sobreajusta, no si una estrategia puntual es buena.
4. **Siempre activo = problema secuencial.** Monitorear p-values clásicos de forma continua invalida el error tipo I. Las herramientas correctas son: e-processes y secuencias de confianza para monitorear una estrategia, y FDR online (LORD/SAFFRON con p-values, e-LOND con e-values) para el flujo infinito de aperturas de holdout.
5. **Librerías:**
   - `arch`, de Kevin Sheppard, es la referencia para SPA, StepM, MCS y bootstraps con longitud de bloque óptima.
   - `skfolio` (BSD-3) trae CPCV.
   - `statsmodels` trae BH y BY.
   - mlfinlab **ya no es open source**.
   - Para DSR/PBO solo hay repos chicos: pypbo (AGPL), pbo en R, y fluke/backtest-overfitting, de 0 estrellas.

---

## 1. Deflated Sharpe Ratio (DSR) y False Strategy Theorem

**Referencias primarias**
- Bailey & López de Prado (2012), "The Sharpe Ratio Efficient Frontier", *Journal of Risk* 15(2). Introduce el **PSR** y el **MinTRL**. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", *JPM* 40(5):94-107. SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 · editor https://www.pm-research.com/content/iijpormgmt/40/5/94 · PDF https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- López de Prado & Bailey, "The False Strategy Theorem: A Financial Application of Experimental Mathematics", *American Mathematical Monthly* 128(9), 2021. SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3221798 · https://www.tandfonline.com/doi/abs/10.1080/00029890.2021.1965068
- López de Prado & Lewis (2019), "Detection of false investment strategies using unsupervised learning methods", *Quantitative Finance* 19(9):1555-1565. Estima el número efectivo de pruebas por clustering (ONC). https://econpapers.repec.org/article/tafquantf/v_3a19_3ay_3a2019_3ai_3a9_3ap_3a1555-1565.htm · PDF https://codemacher.com/wp-content/uploads/2021/02/Detection-of-false-investment-strategies-using-unsupervised-learning-methods_M.LopezDePrado_and_M.Lewis_2018.pdf

**Fórmulas (verificadas en el PDF y recalculadas)**

Umbral bajo H0, es decir, el máximo Sharpe esperado de N pruebas independientes:

SR₀ = √V[{SR_n}] · ((1−γ)·Z⁻¹[1−1/N] + γ·Z⁻¹[1−1/(N·e)])

con γ ≈ 0.5772 (constante de Euler-Mascheroni).

DSR = Z[ (SR̂ − SR₀)·√(T−1) / √(1 − γ̂₃·SR̂ + ((γ̂₄−1)/4)·SR̂²) ]

con γ̂₃ = asimetría, γ̂₄ = curtosis **cruda** (no la excedente) y SR̂ no anualizado. El DSR es un PSR cuyo umbral se ajusta por la multiplicidad de pruebas.

Ejemplo del paper, reproducido por mí:
- Datos: N=100, V[SR] anualizada = 1/2, T=1250 días, γ₃=−3, γ₄=10, SR̂ = 2.5 anualizado.
- Resultado: SR₀ ≈ 1.79 anualizado y **DSR ≈ 0.900**, por debajo del 95% exigido.

**N efectivo.** El Apéndice A.3 del paper propone interpolar por correlación media: N̂ = ρ̂ + (1−ρ̂)·M, con M = pruebas totales. Los mismos autores advierten dos cosas: la correlación es una medida lineal limitada, y con M > T la propia ρ̂ queda sobreajustada. ONC (López de Prado & Lewis) es la alternativa basada en clustering.

**False Strategy Theorem.** El óptimo de un número desconocido de simulaciones no tiene cota superior. Con suficientes pruebas, cualquier estrategia falsa alcanza el Sharpe que se le pida.

**Ficha del método**

| Ítem | Detalle |
|---|---|
| H0 | El SR verdadero de la estrategia elegida es ≤ 0, dado que se eligió como la mejor de N |
| Inputs | Retornos de la estrategia elegida (T, asimetría, curtosis); varianza de los SR **de todas** las pruebas; N_eff. Retornos por período homogéneo (diario/barra), no por trade, porque el PSR asume una frecuencia fija |
| Costo | O(T) por celda para los momentos; la fórmula es cerrada. Lo caro es N_eff: una matriz de correlación es O(M²T), inviable con M=10⁶ **[inferencia: estimar ρ̄ con pares aleatorios o clusterizar solo representantes]** |
| Trampas | (a) Si los SR entre pruebas no son normales (el paper lo asume para la "clase de estrategia"), el umbral se descalibra. (b) Contar N de menos (*file drawer*). (c) Usar curtosis excedente en vez de cruda: el bug que tuvo quantstats, ver §8. (d) N tiene que ser **acumulado en la vida del agente**, no por corrida |

El mismo paper sugiere una regla de parada: la del "secretary problem" (1/e). Se samplea al azar ~37% de las configuraciones teóricamente justificables y después se sigue hasta encontrar una que supere a todas las anteriores. Es útil como presupuesto de pruebas para el agente.

---

## 2. PBO vía CSCV, y CPCV

**Referencias primarias**
- Bailey, Borwein, López de Prado & Zhu (2017), "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4):39-69. https://www.risk.net/journal-of-computational-finance/volume-20-number-4-april-2017 · PDF https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- López de Prado (2018), *Advances in Financial Machine Learning*, Wiley. Cap. 7 cubre purging/embargo y cap. 12 el CPCV. https://www.oreilly.com/library/view/advances-in-financial/9781119482086/c12.xhtml

**Algoritmo CSCV (verificado en el PDF)**
1. Se arma la matriz M de T×N con el rendimiento por período de las N configuraciones.
2. Se parte por filas en S bloques (S par).
3. Se forman las C(S, S/2) combinaciones de S/2 bloques. Cada combinación es el set IS y su complemento es el OOS.
4. Para cada combinación:
   - Se elige n* = la mejor configuración IS.
   - Se calcula ω̄ = su rango relativo OOS / (N+1).
   - Se calcula λ = ln(ω̄/(1−ω̄)).
5. **PBO = fracción de combinaciones con λ ≤ 0.**

Los autores recomiendan S=16. Ojo: el paper dice "12,780 combinaciones", pero **C(16,8) = 12,870**; es una errata del paper.

**Ficha del método**

| Ítem | Detalle |
|---|---|
| Qué mide | No es un test sobre una estrategia. Es P(la mejor IS rinde por debajo de la mediana OOS), o sea, la confiabilidad del **proceso de selección** |
| Inputs | Matriz T×N de P&L con calendario común. Por trade no sirve: hay que pasar a P&L diario o por barra |
| Costo | 12,870 × (métrica sobre T/2×N + ranking de N). **[Inferencia]** Para métricas tipo Sharpe alcanza con guardar, por columna y por bloque, Σr y Σr² (un arreglo de S×N×2). Así cada combinación se resuelve combinando sumas, sin tocar T, y con N=10⁶ queda en ~10¹⁰ operaciones, viable en GPU. Para drawdown no vale, porque depende del orden |
| Trampas (citadas del paper, §5) | (1) Hay que entregar **todas** las pruebas: esconderlas subestima el sobreajuste. (2) En búsquedas guiadas (GA, bayesiana), las columnas deben ser el **resultado final de cada búsqueda**, no los pasos intermedios. (3) No valida el backtest en sí (costos, look-ahead). (4) Solo contempla quiebres estructurales que estén dentro de T. (5) Un PBO alto puede salir con muchas estrategias igual de buenas. (6) N tiene que ser ≫ 10 para que la granularidad del rango tenga sentido. (7) Con autocorrelación fuerte del rendimiento, S grande distorsiona. (8) T debe ser el doble de lo que se usó para elegir |

**CPCV.** Se generan C(N_grupos, k) particiones con purging y embargo, y de ahí φ = (k/N)·C(N,k) caminos de backtest. Sirve cuando la estrategia **ajusta** algo (ML, filtros con fit), porque da una distribución de Sharpe OOS por camino. Para reglas sin fit, CSCV es lo natural.

**Implementaciones**
- `skfolio.model_selection.CombinatorialPurgedCV(n_folds, n_test_folds, purged_size, embargo_size)`, BSD-3, activo, v1.0.0 en 2026. https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html · https://github.com/skfolio/skfolio
- pypbo (Python, AGPL-3.0; 68 commits; PBO, PSR, MinTRL, MinBTL, DSR; el TODO dice que faltan tests). https://github.com/esvhd/pypbo
- pbo para R (está en CRAN; usa Omega como métrica por defecto). https://github.com/mrbcuda/pbo
- fluke (MIT, 2026, 8 commits, 0 estrellas, no está en PyPI). https://github.com/CH4RL3I/fluke — el repo CH4RL3I/backtest-overfitting tiene el mismo contenido: https://github.com/CH4RL3I/backtest-overfitting
- iqueipopg/backtest-overfitting (MIT, 4 commits, 0 estrellas; demo con 147 variantes sobre SPY, PSR naive 0.998 contra DSR 0.58). https://github.com/iqueipopg/backtest-overfitting
- Todos estos repos chicos sirven como **referencia para validar tu implementación, no como dependencia de producción**.

---

## 3. Reality Check, SPA, StepM de Romano-Wolf y MCS

**Referencias primarias**
- White (2000), "A Reality Check for Data Snooping", *Econometrica* 68(5):1097-1126. https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152 · PDF https://users.ssc.wisc.edu/~bhansen/718/White2000.pdf
- Sullivan, Timmermann & White (1999), *Journal of Finance* 54(5):1647-1691. Aplican el RC a un universo de 7,846 reglas técnicas, el precedente directo de tu caso. https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163
- Hansen (2005), "A Test for Superior Predictive Ability", *JBES* 23:365-380, DOI 10.1198/073500105000000063. https://ideas.repec.org/a/bes/jnlbes/v23y2005p365-380.html
- Romano & Wolf (2005), "Stepwise Multiple Testing as Formalized Data Snooping", *Econometrica* 73(4):1237-1282. https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x · PDF https://users.ssc.wisc.edu/~behansen/718/RomanoWolf2005.pdf
- Romano, Shaikh & Wolf (2008), "Formalized data snooping based on generalized error rates", *Econometric Theory* 24:404-447. Controla k-FWER y FDP. https://www.researchgate.net/publication/23774218_Formalized_Data_Snooping_Based_On_Generalized_Error_Rates · FDR por bootstrap: https://home.uchicago.edu/amshaikh/webfiles/fdr.pdf
- Hsu, Hsu & Kuan (2010), Step-SPA, *Journal of Empirical Finance* 17:471-484. Une SPA y StepM para reglas técnicas. https://homepage.ntu.edu.tw/~ckuan/pdf/Step-SPA-20090720.pdf
- Hansen, Lunde & Nason (2011), "The Model Confidence Set", *Econometrica* 79(2):453-497. https://onlinelibrary.wiley.com/doi/abs/10.3982/ECTA5771

**Comparación**

| Test | H0 | Resultado | Inputs | Costo | Trampas |
|---|---|---|---|---|---|
| **RC (White)** | max_k E[d_k] ≤ 0 (ningún modelo supera al benchmark) | p-value de la familia | Matriz T×m de diferenciales de pérdida/retorno contra el benchmark, con calendario común | B×T×m | No estudentizado; se vuelve **conservador** cuando hay modelos malos o irrelevantes (Hansen 2005) |
| **SPA (Hansen)** | La misma | p-values lower/consistent/upper. El "consistent" usa un umbral log log T para recentrar | Igual | Igual | Más potente; conviene estudentizar. Solo dice si "existe alguno", no cuál |
| **StepM (Romano-Wolf)** | H0_k: E[d_k] ≤ 0 para cada k, con control del FWER | **Conjunto** de modelos superiores | Igual | Varias pasadas del max-stat reutilizando los mismos remuestreos | FWER es muy estricto con m=10⁶. Para descubrir más conviene k-FWER/FDP (RSW 2008) |
| **MCS (HLN)** | Todos los modelos del conjunto tienen igual pérdida esperada; se elimina iterativamente | **Conjunto** que contiene al mejor con confianza 1−α | Matriz T×m de pérdidas, **sin benchmark** | Hasta m−1 rondas de eliminación. La variante T_R es por pares, O(m²) | Con datos poco informativos devuelve un MCS enorme. Está pensado para decenas o cientos de modelos |

**¿Miles de celdas o un puñado?**
- Con miles o millones de celdas: **SPA/RC como compuerta de familia** ("¿hay algo acá?") más **StepM o FDP por bootstrap** para obtener el conjunto de descubrimientos.
- **[Inferencia]** Si cada réplica del stationary bootstrap se codifica como un vector de conteos w_b (B×T), las medias remuestreadas de todas las columnas salen de un producto W·R con R de T×m: es un **GEMM**, ideal para GPU. Así el max-estadístico de 10⁶ celdas con B=1000 y T≈2500 es un problema de multiplicación de matrices. La estudentización de la variante sin anidamiento usa varianzas fijas por columna.
- Con un puñado de finalistas: **MCS**. Responde exactamente "¿cuáles son estadísticamente indistinguibles del mejor?", y dentro de ese conjunto se elige por simplicidad o robustez. **[Inferencia]** Con m de miles no sirve: las rondas de eliminación hacen el costo ~O(m²·B) y además el conjunto resultante suele ser gigante.

**Implementación.** `arch` (K. Sheppard; Python con Cython/Numba; activo, 1,346 commits; licencia en LICENSE.md, que es tipo NCSA/BSD; no lo verifiqué textual). https://github.com/bashtage/arch
- `SPA(benchmark, models, block_size, reps, bootstrap, studentize=True, nested=False)`
- `StepM(...)`
- `MCS(losses, size, reps=1000, block_size=√T por defecto, method='R'|'max', bootstrap='stationary'|'circular'|'mbb')`
- Docs: https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html · https://arch.readthedocs.io/en/latest/multiple-comparison/generated/arch.bootstrap.MCS.html · https://arch.readthedocs.io/en/latest/multiple-comparison/generated/arch.bootstrap.SPA.html
- Ojo: el `block_size` por defecto es √T. Conviene pasarle el óptimo de Patton-Politis-White (§5).
- En R: el paquete MCS en CRAN https://cran.r-project.org/web/packages/MCS/MCS.pdf y StepwiseTest https://cran.r-project.org/web/packages/StepwiseTest/StepwiseTest.pdf

---

## 4. Control de FDR: BH, BY, Lucky Factors y t > 3

**Referencias primarias**
- Benjamini & Hochberg (1995), *JRSS-B* 57:289-300. https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1995.tb02031.x
- Benjamini & Yekutieli (2001), *Annals of Statistics* 29(4):1165-1188. https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-4/The-control-of-the-false-discovery-rate-in-multiple-testing/10.1214/aos/1013699998.full
- Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns", *RFS* 29(1):5-68. Sobre 316 factores proponen **t > 3.0**. https://academic.oup.com/rfs/article-abstract/29/1/5/1843824 · NBER https://www.nber.org/papers/w20592
- Harvey & Liu (2021), "Lucky Factors", *JFE* 141(2):413-435. https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001410 · PDF https://people.duke.edu/~charvey/Research/Published_Papers/P146_Lucky_factors.pdf · SSRN https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2528780
- Harvey & Liu (2020), "False (and Missed) Discoveries in Financial Economics", *JF* 75(5):2503-2553. Usan un doble bootstrap para fijar un umbral de t asociado a un FDR dado y calibran los errores tipo I y tipo II. https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12951 · arXiv https://arxiv.org/pdf/2006.04269
- Bajgrowicz & Scaillet (2012), *JFE* 106(3):473-491. FDR aplicado a reglas técnicas: incluso con FDR no se podía elegir ex ante las mejores reglas futuras, y con costos bajos el rendimiento desaparece. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1095202

**Ficha de cada método**

| Método | H0 / error controlado | Inputs | Costo | Trampas |
|---|---|---|---|---|
| **BH** | FDR ≤ α bajo independencia o PRDS | Vector de p-values, uno por celda | O(m log m) | Las celdas vecinas están muy correlacionadas: positivo en general, pero el PRDS no está garantizado. Un preprint de 2026 muestra fallos de BH con tests gaussianos bilaterales correlacionados: https://arxiv.org/pdf/2607.12208 |
| **BY** | FDR bajo dependencia arbitraria | Igual | Igual | Divide α por Σ1/i ≈ ln m + 0.577 ≈ **14.4 con m=10⁶**: mata la potencia |
| **Lucky Factors** | El candidato no agrega poder explicativo; la H0 se impone centrando antes del bootstrap | Panel de retornos | B regresiones o estadísticos | Es un max-estadístico que preserva la dependencia cruzada. **[Inferencia]** Para estrategias equivale a: centrar cada serie en 0, remuestrear índices de tiempo **en conjunto** y tomar el máximo t; es pariente del RC |
| **t > 3** (HLZ) | Regla rápida derivada de Bonferroni, Holm y BHY sobre la historia de la literatura | t-stat | Nulo | Calibrada para ~316 factores **académicos**; con 10⁶ celdas propias el umbral correcto es mucho mayor (√(2 ln 10⁶) ≈ 5.3) |

El "haircut" de Harvey & Liu, "Backtesting" (*JPM* 42(1):13-28, 2015), funciona así: SR → t = SR·√T → p → ajuste por Bonferroni, Holm o BHY → SR "recortado". Sus inputs son el SR, T, el número de pruebas y la correlación media. Muestra que el corte del 50% es una regla gruesa, porque el recorte es no lineal. Hay programas en el sitio de Harvey (http://faculty.fuqua.duke.edu/~charvey/backtesting) y una versión en R en quantstrat (`SharpeRatio.haircut`): https://rdrr.io/github/braverock/quantstrat/man/SharpeRatio.haircut.html · paper: https://papers.ssrn.com/abstract=2345489 · PDF https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF

**Contrapunto honesto**
- Jensen, Kelly & Pedersen, "Is There a Replication Crisis in Finance?" (*JF* 78(5), 2023), usan un modelo bayesiano jerárquico y concluyen que la mayoría de los factores replican. Código: https://github.com/bkelly-lab/ReplicationCrisis · paper: https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13249
- Chen, "Do t-Statistic Hurdles Need to be Raised?" (arXiv 2204.10275), defiende el empirical Bayes y el FDR frente a subir los umbrales: https://arxiv.org/abs/2204.10275
- **[Inferencia]** En una búsqueda ciega por GPU la probabilidad a priori de un edge real por celda es bajísima, así que lo conservador está justificado. El argumento bayesiano aplica a hipótesis motivadas por teoría económica.

**Implementación.** `statsmodels.stats.multitest.multipletests` (v0.15.0) incluye bonferroni, sidak, holm, holm-sidak, simes-hochberg, hommel, fdr_bh, fdr_by, fdr_tsbh, fdr_tsbky, fdr_gbs. https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html

---

## 5. Test de permutación Monte Carlo (Masters) y bootstrap en bloques o estacionario

**Referencias**
- T. Masters, *Permutation and Randomization Tests for Trading System Development: Algorithms in C++* (2020, ISBN 9798607808105). Cubre sobreajuste temprano, suerte contra habilidad, validar una "fábrica" de sistemas y remover sesgo de selección al filtrar muchos indicadores. https://books.google.com/books/about/Permutation_and_Randomization_Tests_for.html?id=SiJczQEACAAJ
- T. Masters, *Testing and Tuning Market Trading Systems* (Apress 2018). Tiene un capítulo de permutación y walk-forward anidado contra el sesgo de selección. https://www.springerprofessional.de/en/testing-and-tuning-market-trading-systems/16228482 (el capítulo en O'Reilly devolvió 403; no pude leer su texto).
- Politis & Romano (1994), "The Stationary Bootstrap", *JASA* 89(428):1303-1313, DOI 10.1080/01621459.1994.10476870.
- Politis & White (2004), *Econometric Reviews* 23(1):53-70, más la corrección de **Patton, Politis & White (2009)**, *Econometric Reviews* 28(4):372-375. https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf

**Ficha del método**

| Ítem | MCPT (Masters) | Bootstrap estacionario o en bloques |
|---|---|---|
| H0 | No hay estructura temporal explotable: se permutan los cambios por barra, preservando la distribución marginal y la deriva total | Se usa para inferencia (IC, p-values) de una estadística bajo dependencia débil; la H0 se impone centrando |
| Clave | Para capturar el sesgo de selección, **en cada permutación se reoptimiza todo el pipeline** y se compara el máximo permutado contra el real | La longitud media del bloque viene de Politis-White/PPW |
| Inputs | **Precios OHLC** más el código completo de estrategia y optimizador | Serie de P&L diario o matriz T×m |
| Costo | B × (una optimización completa). Con B=1000 la resolución del p-value es 0.001 | B×T×m, que es un GEMM en GPU **[inferencia]** |
| Trampas | **[Inferencia]** Permutar retornos destruye también el agrupamiento de volatilidad. Si la estrategia explota volatilidad, la H0 queda mal especificada | La longitud de bloque por defecto de `arch` es √T; mejor usar `optimal_block_length`. Con quiebres de régimen no es estacionario |

Que el test reoptimiza en cada permutación lo verifiqué en el código de neurotrader888/mcpt: `optimize_donchian(train_perm)` se llama dentro del loop, con 1000 permutaciones. Tiene versiones in-sample y walk-forward. MIT, 424 estrellas, solo 2 commits. Es código de demostración, no una librería. https://github.com/neurotrader888/mcpt · https://raw.githubusercontent.com/neurotrader888/mcpt/main/insample_donchian_mcpt.py

Otras implementaciones:
- dpatschke/mcpt (MIT, 3 commits, de una charla): https://github.com/dpatschke/mcpt
- mcpt-lab (derivado de neurotrader, agrega costos y un ledger): https://github.com/dnd8639-byte/mcpt-lab
- `arch.bootstrap.optimal_block_length(x)` devuelve `b_sb` (estacionario) y `b_cb` (circular): https://arch.readthedocs.io/en/latest/bootstrap/generated/arch.bootstrap.optimal_block_length.html

---

## 6. Largo mínimo de backtest y tamaño muestral

- **MinBTL**: Bailey, Borwein, López de Prado & Zhu, "Pseudo-Mathematics and Financial Charlatanism", *Notices of the AMS* 61(5):458-471, 2014. https://www.ams.org/notices/201405/rnoti-p458.pdf · SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659

  Teorema 2, verificado en el PDF:

  MinBTL ≈ ((1−γ)Z⁻¹[1−1/N] + γZ⁻¹[1−1/(N·e)])² / E[max_N]² < 2·ln N / E[max_N]²   (en años, con SR anualizado)

  El ejemplo del paper: con 5 años de datos, no más de **45** configuraciones independientes para un SR IS de 1 con SR OOS esperado de 0. Lo reproduje: N=45 da 5.0 años. Los autores lo presentan como condición **necesaria, no suficiente**. También señalan que con memoria en la serie hay un "efecto compensación" y que optimizar IS puede **empeorar** el resultado OOS.

  Tabla calculada por mí con la forma exacta:

  | N | Años para SR=1 | Años para SR=2 |
  |---|---|---|
  | 10³ | 10.6 | 2.6 |
  | 10⁴ | 14.9 | 3.7 |
  | 10⁵ | 19.3 | 4.8 |
  | **10⁶** | **23.7** | **5.9** |
  | 10⁷ | 28.1 | 7.0 |

  **Leelo así:** si el GPU prueba 10⁶ celdas independientes sobre menos de ~24 años, un SR IS de 1 es exactamente lo que esperarías por puro ruido. El N relevante es N_eff, no el número bruto de celdas.
- **MinTRL / PSR**: Bailey & López de Prado 2012 (§1). Ver también el análisis de portfoliooptimizer.io: https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/
- **Harvey & Liu (2015), "Backtesting"**: da el "profit hurdle", la rentabilidad mínima para ser significativo dadas la volatilidad, el T y el número de pruebas, y el haircut (§4).

---

## 7. Alternativas secuenciales y bayesianas para un agente siempre activo

**El problema.** Si el agente recalcula p-values a medida que llegan datos o pruebas, y se detiene cuando algo "da significativo", el error tipo I se infla.
- Johari, Koomen, Pekelis & Walsh, "Always Valid Inference: Continuous Monitoring of A/B Tests", *Operations Research* 70(3):1806-1821. https://pubsonline.informs.org/doi/10.1287/opre.2021.2135 · arXiv https://arxiv.org/pdf/1512.04922
- Bax & Shtoff (arXiv 2408.02821) prueban que en tests de largo no acotado es imposible mantener un umbral constante en cada mirada. Solo se puede aproximar exigiendo confirmaciones repetidas. https://arxiv.org/abs/2408.02821

**Marco SAVI (safe anytime-valid inference)**
- Ramdas, Grünwald, Vovk & Shafer (2023), *Statistical Science* 38(4):576-601: los e-processes y las secuencias de confianza son válidos en **cualquier tiempo de parada**, vía la desigualdad de Ville. https://arxiv.org/pdf/2210.01948 · https://projecteuclid.org/journals/statistical-science/volume-38/issue-4/Game-Theoretic-Statistics-and-Safe-Anytime-Valid-Inference/10.1214/23-STS894.full
- Grünwald, de Heide & Koolen, "Safe testing", *JRSS-B* 86(5):1091-1128 (2024). Se puede re-testear la misma H0 con más datos sin perder el control del tipo I. Ver la discusión en https://arxiv.org/pdf/2402.14574
- Vovk & Wang (2021), "E-values: calibration, combination and applications", *Annals of Statistics* 49(3). https://projecteuclid.org/journals/annals-of-statistics/volume-49/issue-3/E-values-Calibration-combination-and-applications/10.1214/20-AOS2020.full
- Libro de referencia: Ramdas & Wang, *Hypothesis Testing with E-values* (Foundations and Trends in Statistics 1(1-2), 2025). https://arxiv.org/abs/2410.23614
- Secuencias de confianza: Howard, Ramdas, McAuliffe & Sekhon (2021), *Annals of Statistics* 49(2):1055-1080, https://arxiv.org/pdf/1810.08240 . Waudby-Smith & Ramdas (2024), "Estimating means of bounded random variables by betting", *JRSS-B* 86(1):1-27, https://arxiv.org/abs/2010.09686 . **Requiere variables acotadas**. **[Inferencia]** Los retornos se pueden acotar normalizándolos por la pérdida máxima por período, por ejemplo con stops duros.

**FDR online, para un flujo infinito de hipótesis (cada familia nueva o cada apertura de holdout)**
- Alpha-investing (Foster & Stine 2008), LORD (Javanmard & Montanari), LORD++/GAI++ (Ramdas et al. 2017, https://proceedings.neurips.cc/paper_files/paper/2017/file/7f018eb7b301a66658931cb8a93fd6e8-Paper.pdf ), SAFFRON (Ramdas et al. 2018, https://arxiv.org/pdf/1802.09098 ) y ADDIS. Funcionan con un **presupuesto de α ("alpha-wealth")** que se gasta en cada test y se recupera con cada descubrimiento. Requieren independencia o PRDS local: https://arxiv.org/pdf/2110.08161
- **e-BH**, de Wang & Ramdas (*JRSS-B* 84(3):822-852, 2022), controla el FDR bajo **dependencia arbitraria**. https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/rssb.12489
- **e-LOND**, de Xu & Ramdas (AISTATS 2024), es FDR online con e-values bajo dependencia arbitraria. https://arxiv.org/abs/2311.06412
- Trabajo de 2025-2026 con advertencias técnicas:
  - **Stopped e-BH** (Wang, Dandapanthula & Ramdas) mantiene el FDR en cualquier parada solo bajo una "condición causal". https://arxiv.org/abs/2502.08539
  - "**Carefree multiple testing with e-processes**" (Tavyrikov, Goeman & de Heide) muestra que e-BH aplicado al supremo de e-processes **no** controla el FDR sin "adjusters". https://arxiv.org/abs/2501.19360
  - Mejoras online por e-closure: https://arxiv.org/html/2603.24792

**Qué dice la literatura y qué implica para el agente** (lo segundo es **[inferencia]**)
1. Monitorear una estrategia ya promovida (paper o live) se resuelve con una secuencia de confianza o un e-process sobre la media de retornos. Promover o matar en cualquier momento es válido.
2. El flujo de aperturas de holdout es FDR online. Las aperturas comparten datos y régimen, así que son dependientes; por eso conviene **e-LOND** antes que LORD.
3. **Ojo con el alpha-wealth:** se agota si no hay descubrimientos. Es el análogo secuencial del False Strategy Theorem: no existe "testear gratis para siempre".

**Implementaciones**
- `online-fdr` (Python, BSD-3; 138 commits, 6 estrellas; LORD, SAFFRON, ADDIS, LOND, alpha-spending, e-BH, e-LOND, BatchBH; tests de paridad contra el paquete de R): https://github.com/OliverHennhoefer/online-fdr
- `onlineFDR` (R/Bioconductor, la referencia): https://bioconductor.org/packages/devel/bioc/vignettes/onlineFDR/inst/doc/onlineFDR.html
- `confseq` (C++ header-only con bindings de Python y R, MIT; el autor la marca "no estable"): https://github.com/gostevehoward/confseq
- **e-backtesting** (arXiv 2209.00991) existe, pero es para backtesting de **medidas de riesgo** (VaR/ES), no de estrategias: https://arxiv.org/html/2209.00991v5
- No encontré una implementación establecida de un e-process específico para el Sharpe de estrategias. Es un hueco real.

---

## 8. Estado de las librerías (verificado en sept-oct 2026)

| Librería | Qué aporta | Lenguaje / licencia | Estado |
|---|---|---|---|
| **mlfinlab** (Hudson & Thames) | AFML completo | Python, **"all rights reserved", NO open source**, licencias Business/Enterprise | El repo público es solo para issues. QuantConnect lo sacó porque "el sistema de licencias estaba roto" y quedó "en limbo". https://github.com/hudson-and-thames/mlfinlab · https://www.quantconnect.com/forum/discussion/16833/mlfinlab-where-is-the-hudson-amp-thames-lean-engine/ |
| mlfinpy / forks viejos de mlfinlab | AFML | Python; los forks traen la licencia BSD-3 antigua | Comunitarios y sin garantías. https://mlfinpy.readthedocs.io/en/latest/ · https://github.com/jjakimoto/finance_ml (MIT) |
| **skfolio** | CPCV, purged/embargo, `optimal_folds_number` | Python, BSD-3 | Activo, v1.0.0 en 2026. No vi DSR/PBO en la página principal. https://github.com/skfolio/skfolio |
| **quantstats** | Reportes, PSR | Python, Apache-2.0 | Activo. **El PSR estaba mal hasta hace poco**: el issue #550 (abierto el 25-sep-2026, cerrado) documenta curtosis excedente en vez de cruda (SE ~8% más chico), probabilidades mayores a 1 con `annualize=True` y rf inconsistente. Lo corrigió v0.0.82 ("#551"); la última es v0.0.86. Usá ≥0.0.82 o calculalo vos. https://github.com/ranaroussi/quantstats/issues/550 · https://github.com/ranaroussi/quantstats/releases |
| **vectorbt** | Backtest vectorizado masivo (Numba, motor Rust opcional) | Python, Apache-2.0 + **Commons Clause** | v1.1.1, 26-sep-2026. **Sin tests de multiplicidad.** https://pypi.org/project/vectorbt/ · https://github.com/polakowo/vectorbt |
| **vectorbt PRO** | Más features | **Propietario**, repo privado de pago (USD 25/mes, 240/año o 500 de por vida) | v2026.9.5. https://vectorbt.pro/ |
| **arch** | SPA, StepM, MCS, IID/estacionario/circular/MBB, `optimal_block_length` | Python + Cython/Numba | Activo; **la mejor pieza para la etapa de finalistas** |
| **statsmodels** | `multipletests` (BH, BY, Holm…) | Python, BSD | v0.15.0 |
| pypbo | PBO, PSR, MinTRL, MinBTL, DSR | Python, **AGPL-3.0** | Mantenimiento bajo, faltan tests |
| pbo (R) | PBO/CSCV | R, en CRAN | Estable |
| fluke / backtest-overfitting | PBO, DSR, MinTRL | Python, MIT | Nuevos (2026), 0 estrellas: solo como referencia |
| online-fdr / onlineFDR / confseq | FDR online, e-values, secuencias de confianza | Python BSD-3 / R / C++ MIT | Ver §7 |

---

## 9. Pipeline recomendado

### Etapa 0 — Contabilidad, transversal a todo
- **Registro de pruebas append-only**: toda celda, familia y búsqueda, con su resultado, incluidas las descartadas.
- **M y N_eff acumulados en la vida del agente.** Es lo que alimenta el DSR y el MinBTL. Lo exigen el False Strategy Theorem y la limitación de "file drawer" del paper de PBO.
- Holdout **sellado**: hash del rango de fechas y prohibición de leerlo antes de la etapa 4.
- Presupuesto de pruebas: regla 1/e del paper del DSR, o alpha-wealth (etapa 4).

### Etapa 1 — Screen masivo en GPU (10⁵–10⁷ celdas)
- **Por celda, todo en forma cerrada:** SR, t, asimetría, curtosis cruda y PSR(SR*=0). Además, estadísticas suficientes por bloque (S=16: Σr y Σr²), que permiten correr CSCV después sin rehacer backtests **[inferencia]**.
- **Compuerta de familia:** SPA de Hansen, estudentizado, con bootstrap estacionario y bloque PPW, sobre la matriz T×m de la familia frente al benchmark. Si p > α, **se mata la familia completa** y se registra.
  - Justificación: SPA/RC están diseñados para "el mejor de m frente al benchmark" (White 2000; Hansen 2005) y STW 1999 los aplicó a 7,846 reglas.
  - **[Inferencia]** El cálculo es un GEMM W(B×T)·R(T×m).
- **Conjunto de descubrimiento:** StepM de Romano-Wolf o, mejor para la potencia, control de **FDP/k-FWER** por bootstrap (Romano-Shaikh-Wolf 2008) con los **mismos** remuestreos. Así se respeta la dependencia sin asumir PRDS.
  - BH solo como filtro barato, aceptando el riesgo de dependencia.
  - **No usar BY** con m=10⁶: el factor ≈14.4 destruye la potencia.
- **Piso de ruido:** SR₀ = E[max] con N_eff y V[{SR}] de la familia. Lo que no lo supere ni siquiera es candidato.
- **Lo que no se hace acá:** MCS (no escala) ni MCPT con reoptimización (B × 10⁶ backtests completos es demasiado salvo para familias chicas).

### Etapa 2 — Meseta de familia (10²–10⁴ representantes)
- **Agrupar** celdas por correlación de P&L (ONC, López de Prado & Lewis 2019) para obtener **N_eff** y un representante por cluster.
  - **[Inferencia, no está en la literatura citada]** Elegir el centro de la meseta, una región de parámetros con SR estable, en vez del pico. Reduce la sensibilidad a la reoptimización y encaja con la lógica del CSCV.
- **PBO vía CSCV** (S=16, 12,870 combinaciones) sobre la matriz de representantes. Si hubo optimizador guiado, **una columna por búsqueda terminada**. Reportar también la degradación IS→OOS.
  - El paper no fija un umbral universal (sus ejemplos van de PBO 74% a 0.04%). Hay que definirlo y pre-registrarlo.
- **CPCV** (skfolio) solo si la estrategia tiene componentes que se ajustan.
- **DSR ≥ 0.95** con el N_eff acumulado, más **MinBTL** (§6): si los años disponibles son menos que el MinBTL para el SR objetivo, el candidato no puede pasar por diseño.

### Etapa 3 — Finalistas en CPU (≤ 10–50)
- **MCS** (`arch.MCS`, método 'max' o 'R', bootstrap estacionario con bloque PPW) sobre pérdidas = −retornos netos de costos. Del conjunto resultante se elige el más simple o robusto. Es el uso para el que HLN diseñaron el método.
- **SPA** de los finalistas contra un benchmark realista (buy & hold o cero), con costos.
- **MCPT de Masters reoptimizando todo el pipeline de la familia** sobre barras permutadas, in-sample y walk-forward, con B ≥ 1000. Es el único test que evalúa el **proceso completo** de selección, incluido el optimizador, y con N=1 encaja en CPU.
  - Ojo con estrategias que explotan agrupamiento de volatilidad: la permutación lo destruye. Complementar con bootstrap en bloques.
- Intervalos de confianza por bootstrap estacionario para SR y drawdown, y haircut de Harvey-Liu como control de cordura.

### Etapa 4 — Apertura única del holdout
- **Pre-registrar** antes de abrir: finalista o finalistas, estadístico (PSR con SR*=0, o t sobre la media neta) y α.
- Si se abren varios finalistas a la vez: Holm o Bonferroni dentro de la apertura.
- **α global de por vida del agente:** cada apertura es una hipótesis en un flujo infinito. Usar **e-LOND** (dependencia arbitraria; las aperturas comparten régimen) o LORD++/SAFFRON si se acepta PRDS. Se implementa con `online-fdr`.
- Una vez abierto, el holdout **queda consumido**: pasa a ser datos de investigación y se registra en el ledger. Bailey et al. (2017, §1) critican justamente el holdout reutilizado o contaminado.

### Etapa 5 — Recomendada: paper o live con monitoreo anytime-valid
- e-process o secuencia de confianza (betting CS de Waudby-Smith & Ramdas, o boundaries de Howard et al.; `confseq`) sobre retornos acotados.
- Promover o matar en **cualquier** momento sin inflar el error tipo I. Es la única fuente de datos realmente nuevos para un agente que corre indefinidamente.

**Por qué este orden.** Los tests baratos y escalables (forma cerrada, max-estadístico en GEMM, FDR) van donde m es enorme. Su función es descartar y estimar el ruido, no "probar". Los tests caros que responden la pregunta correcta para pocos modelos (MCS, MCPT con reoptimización) van donde m es chico. Al final, la confirmación tiene que venir de datos no usados, porque con datos fijos y N creciente cualquier umbral termina siendo superado (False Strategy Theorem, MinBTL). Para un agente perpetuo, esa confirmación se organiza como inferencia secuencial válida en cualquier tiempo de parada (SAVI, FDR online), no como p-values repetidos.

---

## 10. Advertencias de verificación
- La errata del paper de PBO (12,780 en vez de C(16,8) = 12,870) la verifiqué en el PDF.
- La licencia exacta de `arch` y los detalles internos del libro de Masters (el capítulo devolvió 403) no los pude leer textualmente.
- Las afirmaciones sobre los métodos de Masters vienen de la descripción del editor y del código de neurotrader888.
- "Lucky Factors" está formulado para factores en regresiones de panel; su adaptación a estrategias es **[inferencia]**.
- Lo marcado **[inferencia]** (truco GEMM, estadísticas suficientes por bloque para CSCV, costo del MCS, meseta) es diseño mío. Hay que validarlo empíricamente antes de producción.

## URLs usadas
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 · https://www.pm-research.com/content/iijpormgmt/40/5/94 · https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643 · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3221798 · https://www.tandfonline.com/doi/abs/10.1080/00029890.2021.1965068 · https://econpapers.repec.org/article/tafquantf/v_3a19_3ay_3a2019_3ai_3a9_3ap_3a1555-1565.htm · https://codemacher.com/wp-content/uploads/2021/02/Detection-of-false-investment-strategies-using-unsupervised-learning-methods_M.LopezDePrado_and_M.Lewis_2018.pdf · https://www.risk.net/journal-of-computational-finance/volume-20-number-4-april-2017 · https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf · https://www.oreilly.com/library/view/advances-in-financial/9781119482086/c12.xhtml · https://www.ams.org/notices/201405/rnoti-p458.pdf · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659 · https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152 · https://users.ssc.wisc.edu/~bhansen/718/White2000.pdf · https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00163 · https://ideas.repec.org/a/bes/jnlbes/v23y2005p365-380.html · https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-0262.2005.00615.x · https://users.ssc.wisc.edu/~behansen/718/RomanoWolf2005.pdf · https://www.researchgate.net/publication/23774218_Formalized_Data_Snooping_Based_On_Generalized_Error_Rates · https://home.uchicago.edu/amshaikh/webfiles/fdr.pdf · https://homepage.ntu.edu.tw/~ckuan/pdf/Step-SPA-20090720.pdf · https://onlinelibrary.wiley.com/doi/abs/10.3982/ECTA5771 · https://cran.r-project.org/web/packages/MCS/MCS.pdf · https://cran.r-project.org/web/packages/StepwiseTest/StepwiseTest.pdf · https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1995.tb02031.x · https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-4/The-control-of-the-false-discovery-rate-in-multiple-testing/10.1214/aos/1013699998.full · https://arxiv.org/pdf/2607.12208 · https://academic.oup.com/rfs/article-abstract/29/1/5/1843824 · https://www.nber.org/papers/w20592 · https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001410 · https://people.duke.edu/~charvey/Research/Published_Papers/P146_Lucky_factors.pdf · https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2528780 · https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12951 · https://arxiv.org/pdf/2006.04269 · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1095202 · https://papers.ssrn.com/abstract=2345489 · https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF · https://rdrr.io/github/braverock/quantstrat/man/SharpeRatio.haircut.html · https://onlinelibrary.wiley.com/doi/full/10.1111/jofi.13249 · https://github.com/bkelly-lab/ReplicationCrisis · https://arxiv.org/abs/2204.10275 · https://books.google.com/books/about/Permutation_and_Randomization_Tests_for.html?id=SiJczQEACAAJ · https://www.springerprofessional.de/en/testing-and-tuning-market-trading-systems/16228482 · https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf · https://arch.readthedocs.io/en/latest/bootstrap/generated/arch.bootstrap.optimal_block_length.html · https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html · https://arch.readthedocs.io/en/latest/multiple-comparison/generated/arch.bootstrap.MCS.html · https://arch.readthedocs.io/en/latest/multiple-comparison/generated/arch.bootstrap.SPA.html · https://github.com/bashtage/arch · https://github.com/neurotrader888/mcpt · https://raw.githubusercontent.com/neurotrader888/mcpt/main/insample_donchian_mcpt.py · https://github.com/dpatschke/mcpt · https://github.com/dnd8639-byte/mcpt-lab · https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/ · https://pubsonline.informs.org/doi/10.1287/opre.2021.2135 · https://arxiv.org/pdf/1512.04922 · https://arxiv.org/abs/2408.02821 · https://arxiv.org/pdf/2210.01948 · https://projecteuclid.org/journals/statistical-science/volume-38/issue-4/Game-Theoretic-Statistics-and-Safe-Anytime-Valid-Inference/10.1214/23-STS894.full · https://arxiv.org/pdf/2402.14574 · https://projecteuclid.org/journals/annals-of-statistics/volume-49/issue-3/E-values-Calibration-combination-and-applications/10.1214/20-AOS2020.full · https://arxiv.org/abs/2410.23614 · https://arxiv.org/pdf/1810.08240 · https://github.com/gostevehoward/confseq · https://arxiv.org/abs/2010.09686 · https://proceedings.neurips.cc/paper_files/paper/2017/file/7f018eb7b301a66658931cb8a93fd6e8-Paper.pdf · https://arxiv.org/pdf/1802.09098 · https://arxiv.org/pdf/2110.08161 · https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/rssb.12489 · https://arxiv.org/abs/2311.06412 · https://arxiv.org/abs/2502.08539 · https://arxiv.org/abs/2501.19360 · https://arxiv.org/html/2603.24792 · https://arxiv.org/html/2209.00991v5 · https://github.com/OliverHennhoefer/online-fdr · https://bioconductor.org/packages/devel/bioc/vignettes/onlineFDR/inst/doc/onlineFDR.html · https://github.com/hudson-and-thames/mlfinlab · https://www.quantconnect.com/forum/discussion/16833/mlfinlab-where-is-the-hudson-amp-thames-lean-engine/ · https://mlfinpy.readthedocs.io/en/latest/ · https://github.com/jjakimoto/finance_ml · https://github.com/skfolio/skfolio · https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html · https://github.com/ranaroussi/quantstats/issues/550 · https://github.com/ranaroussi/quantstats/releases · https://github.com/polakowo/vectorbt · https://pypi.org/project/vectorbt/ · https://vectorbt.pro/ · https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html · https://github.com/esvhd/pypbo · https://github.com/mrbcuda/pbo · https://github.com/CH4RL3I/fluke · https://github.com/CH4RL3I/backtest-overfitting · https://github.com/iqueipopg/backtest-overfitting
