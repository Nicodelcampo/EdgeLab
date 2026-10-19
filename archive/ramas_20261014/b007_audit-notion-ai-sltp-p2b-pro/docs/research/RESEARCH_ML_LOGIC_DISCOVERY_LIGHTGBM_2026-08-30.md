# RESEARCH — ML que aprende lógicas por sí solo (LightGBM y el encuadre correcto) — 2026-08-30

**Autor:** Notion AI (auditor) · **Pregunta de Nico (textual, 2026-08-30 ~23:05 ART):** "¿se puede usar LightGBM para un modelo de ML que aprenda a hacer lo que nosotros hacemos definiendo todas las lógicas y parámetros a medir, pero que en lugar de definirlos a priori le enseñamos al modelo a aprender por sí solo y probar combinaciones y lógicas autoaprendidas?"
**Método:** búsqueda web 2026-08-30 + el propio board del proyecto (P-53, P-55, P-49). **No abre ninguna línea de trabajo** — adoptarla es decisión de Nico (P-59).

## 0. Respuesta corta

**Sí se puede, y hay exactamente un encuadre publicado para hacerlo sin engañarse: ML como generador de hipótesis, no como instrumento de confirmación.** Y el proyecto ya decidió la mitad de esta respuesta el 2026-08-19: P-53 ("lo que sí movería la aguja: sesiones, no modelos") y P-55 (el contexto como objeto) son la misma pregunta en versión anterior. Lo nuevo que aporta la pregunta de hoy es el paso siguiente: usar el modelo para **descubrir lógicas** en vez de medir lógicas escritas a mano.

La forma que cierra con la arquitectura del proyecto, en una oración:

> **El modelo explora y propone; el humano/auditor formaliza la propuesta como regla falsable escrita; la regla se prueba preregistrada sobre datos que el modelo nunca vio. El modelo nunca confirma lo que descubrió.**

## 1. Lo que la literatura respalda

- **Ludwig & Mullainathan, "Machine Learning as a Tool for Hypothesis Generation" (NBER w31017 / BFI 2025)**: el encuadre exacto — ML descubre patrones que los humanos no escribirían, y esos patrones entran al proceso científico como hipótesis a testear, no como resultados. Es la cita central de esta propuesta. https://www.nber.org/papers/w31017
- **LightGBM es la herramienta razonable para esto**: referencia establecida en datos tabulares financieros (rápido por histogramas, maneja interacciones no lineales, y es compatible con **SHAP TreeExplainer** para atribución exacta de features — la pieza que permite *traducir* lo aprendido a una regla escrita en lenguaje humano). Uso documentado en clasificación de régimen y predicción intradiaria con features de microestructura (173 features, walk-forward) y en forecasting de LOB. Fuentes: mdpi.com/2079-9292/15/6/1334; github.com/a-drain-on-life/qqq-regime-engine.
- **Gu, Kelly & Xiu, "Empirical Asset Pricing via Machine Learning" (RFS 2020)**: ML mejora la descripción de retornos esperados — en cross-section accionario mensual con cientos de features y décadas de datos. La escala de N que usa esa literatura es la que el proyecto NO tiene a nivel intradiario (ver P-53: nuestro N efectivo son ~234 sesiones, no las filas).

## 2. Las cinco trampas (todas con cita, todas ya nombradas por el proyecto en otra forma)

1. **El modelo ES una máquina de multiplicidad.** Búsqueda de hiperparámetros + selección de features + selección de modelo = un N_eff difícil hasta de acotar; por eso existen DSR/PBO — que el repo YA tiene (`validation/pbo.py`, g2*). La False Strategy Theorem: el máximo Sharpe entre N ensayos crece con N aunque todos sean ruido. (Bailey & López de Prado; AQR, "A Data-Science Solution to the Multiple-Testing Crisis".)
2. **Leakage temporal**: con etiquetas de ventana futura, un k-fold estándar mete el camino de precio del test dentro del train. La literatura de LOB lo marca como no negociable: features con autocorrelación >120 s ⇒ split aleatorio = métricas infladas sin contenido predictivo. Cura publicada: **purged k-fold CV + embargo** (López de Prado, AFML), y walk-forward.
3. **Poder de forecast ≠ señal accionable** (guía microestructural de LOB forecasting, 2024-25): un modelo puede predecir el próximo tick muy bien y aun así no pagar los 3,5-5,5 ticks de fricción. La evaluación final es económica (nuestro NetTicks neto de costos), no la métrica de ML.
4. **N efectivo = sesiones** (P-53, ya asentado): 16,2 M de ticks / 281,7 k barras / **228 sesiones**. Un modelo ve "muchas filas" y reporta intervalos angostos que son mentira; con ~228 sesiones un edge real de 2-5 pp no es detectable directamente — **el modelo no afloja esto, lo empeora si se le cree su propio ajuste**.
5. **Overfitting de backtest en la era ML** (ScienceDirect 2024, comparación en entorno sintético controlado): incluso con buena fe, el pipeline ML encuentra el ruido si la validación no está purgada/embargada y la multiplicidad no está contada.

## 3. La arquitectura disciplinada (si Nico la adopta)

Embudo de 3 capas, con fronteras explícitas:

1. **Descubrimiento (EF1, pre-holdout)**: LightGBM sobre la tabla de eventos ya construida (los event stores son exactamente la tabla de features que el modelo necesita) + features de contexto (P-55 ya exige guardarlas desde el principio). Validación interna con purged/embargoed CV y walk-forward; TODO el espacio de búsqueda queda logueado (qué se probó = el N_eff del descubrimiento, para DSR/PBO). SHAP para extraer qué aprendió.
2. **Traducción (el paso que la mayoría salta y es el que vale)**: lo aprendido se convierte en **una regla escrita, falsable, con su lógica en lenguaje humano** ("cuando X e Y, el precio tiende a Z"). Si el modelo aprendió algo intraducible, no es una hipótesis — es un lookup table del pasado, y se descarta o se reformula.
3. **Confirmación preregistrada**: la regla traducida entra por la vía normal del proyecto — hipótesis escrita, spec, presupuesto de multiplicidad, y test sobre **datos que el modelo nunca vio** (partición virgen o holdout con su única apertura). ATJ-13 aplicado al modelo: lo que EF1 genera, no confirma.

## 4. Qué NO cambia y qué NO reemplaza

- No reemplaza ni toca la línea actual (Gate 1 NQ → campaña SL/TP): esas son preregistradas y siguen. D3 (prioridad) intacta.
- El modelo nunca escribe specs, nunca se auto-ejecuta, nunca accede al holdout. Corre data-bound en Kaggle como todo lo demás (licencia CME).
- P-49 ("la firma") es la puerta natural de entrada: la pregunta ya registrada "¿qué features medibles ANTES del evento predicen el resultado de barrera?" es exactamente el formato LightGBM sobre población preregistrada — el F4 del addendum 007, después de ledgers, costos y población.

## 5. Recomendación

Adoptable como **línea nueva separada** ("fábrica de hipótesis ML"), con su propio manifiesto, contabilidad de búsqueda y traducción obligatoria — y ordenada DESPUÉS de la línea actual (D3) y de P-44 (sin parámetros que transportan entre instrumentos, el modelo aprendería los artefactos de escala de cada activo, no el mercado). LightGBM como primer instrumento: tabular, rápido, interpretable vía SHAP, y corre liviano en la TPU-VM (P-58).

## Fuentes

- Ludwig & Mullainathan, ML as a Tool for Hypothesis Generation: https://www.nber.org/papers/w31017
- López de Prado, AFML (purged k-fold + embargo): resumen en luxalgo.com/library/concept/purged-cross-validation/ y stats.stackexchange.com (CPCV)
- Bailey & López de Prado, DSR: pm-research.com/content/iijpormgmt/40/5/94 · PBO: papers.ssrn.com/abstract_id=2326253 · AQR multiple-testing crisis: aqr.com (JFDS Winter 2019)
- Backtest overfitting era ML (sintético controlado): sciencedirect.com/science/article/abs/pii/S0950705124011110
- Gu, Kelly & Xiu, RFS 2020: academic.oup.com/rfs/article/33/5/2223/5758276
- LOB forecasting, poder ≠ accionable: pmc.ncbi.nlm.nih.gov/articles/PMC12315853 · walk-forward no negociable (autocorrelación LOB): github.com/alexbrookes-ai/limit-order-book-project
- LightGBM en financiero tabular + SHAP: mdpi.com/2079-9292/15/6/1334
