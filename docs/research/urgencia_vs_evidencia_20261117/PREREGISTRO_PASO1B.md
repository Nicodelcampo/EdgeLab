# Paso 1b: vida de una ventaja en el dominio de la cartera (M1 intradía de índices) — pre-registro (2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de lanzar el kernel. Nico: «dale con la propuesta». Etapa EF2 (diagnóstico; no elige reglas ni toca
el holdout). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Sigue a `RESULTADO_PASO1.md`, cuyo alcance
(catálogo SQX: 6E, CL, GC, 6J, diarios) no se transporta a la cartera (NQ/ES intradía).

Antecedentes: «vida de una ventaja ORB pre-rango banda VWAP M1 intradía índices régimen» — familias parecidas: M1_INTRADIA, ORB_RR_MENOR, ORB_VARIANTES; NO_REPETIR: F-VWAP-BANDA3-REVERSION, F-PRERANGO-0812, F-REELS-20261108, F-ORB-EMA20-NQ-STOP-OPUESTO; código: tools/kaggle_grilla/m1_vida_main.py:1, edgelab/research/vida_ventaja.py:24, tools/canasta_orb.py:28

Potencia previa: estimada por frecuencia (ORB y banda del VWAP ≈ 1 operación por día; ≈ 20 por mes por serie × 8 índices × ≈ 165 meses ≈ 26.000 por familia canónica; en el paso 1 «ruptura corta», con 18.900 operaciones, detectaba τ 0,05/ρ 0,95 con 0,78). La potencia exacta se calcula SOLO con el conteo de operaciones por mes (`tools/vida_ventaja_medir.py m1_potencia`, `POTENCIA_PASO1B.json`) antes de ajustar con R; un grupo con potencia < 0,5 para τ 0,05 pasa a descriptivo.

## Diseño
Mismo modelo y herramienta del paso 1 (`edgelab/research/vida_ventaja.py`, grilla de ρ extendida hasta 0,999 desde el inicio). Datos: el
mismo motor M1 conservador ya validado (`edgelab/research/m1_intradia.familia`: ORB, pre-rango 08:12, banda del VWAP; M1 de Dukascopy de 8
índices hasta 2026-09-29), agregado por mes en Kaggle (`tools/kaggle_grilla/m1_vida_main.py`, `tools/m1_intradia.py lanzar_vida`): n,
suma y suma de cuadrados del R neto y bruto recortado a [−3, 5].
**Crítica de la versión obvia**: sumar las 37 variantes de un índice como series independientes infla la evidencia (comparten casi las
mismas operaciones). Por eso **deciden variantes canónicas declaradas por nombre, no por resultado**: ORB 30 min, entrada a mercado tras el
cierre fuera del rango, stop en el extremo opuesto, salida al cierre (`ORB|<índice>|30|BRK|OPUESTO|0`); pre-rango base (`PRERANGO|<índice>`);
banda 3 del VWAP en reversión al VWAP con stop en la banda 4 (`VWAPB|<índice>|3|REV|VWAP|K+1`). Las demás variantes, juntas por familia,
son descriptivas (con la advertencia de dependencia).

## Decisión
- Grupos que deciden (si tienen potencia): canónica ORB (8 índices), canónica pre-rango (8), canónica VWAP (8), **dominio de la cartera**
  (las 3 canónicas en NQ, ES y YM: 9 series) y canónica conjunta (24). H0 τ = 0, nulo paramétrico (300 réplicas), BH q 0,10 sobre los que
  deciden, en R neto.
- «Régimen de mercado» exige además R **bruto** con τ > 0 y p < 0,05 (el paso 1 mostró que el neto puede ser fricción).
- Uso: si el dominio de la cartera tiene régimen de mercado, su (ρ, τ) entra a P(viva) del paso 3; si sólo hay régimen en neto, P(viva)
  se modela como fricción en R según la volatilidad; si no hay régimen con potencia, la política usa sólo la media estática contraída.

## Justificación económica / cómo podría refutarse
Las ventajas intradía de índices dependen de quién opera la apertura (institucionales, algoritmos, volatilidad): si eso cambia por
regímenes, la media de reglas fijas deriva con persistencia medible y la urgencia pesa. Se refuta si τ no se distingue de 0 con potencia, o
si lo que se distingue en neto desaparece en bruto (fricción, no mercado), o si las innovaciones no son ≈ N(0,1).

## Contador
`urgencia_vs_evidencia_20261117/PASO1B`, familia VIDA_VENTAJA, 5 pruebas que deciden. Mismo linaje (VIDA_VENTAJA ← SQX_CATALOGO; los datos son de
la familia M1_INTRADIA, ya registrada).
