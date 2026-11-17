# Paso 1: vida de una ventaja (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de mirar R. Nico aceptó la propuesta (`PROPUESTA.md`) y pidió «razonala bien». Etapa EF2
(diagnóstico; no elige reglas ni toca el holdout). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Antecedentes: «vida de una ventaja régimen persistencia media que cambia en el tiempo» — familias parecidas: EL_DIA_TENDENCIA, ESPEJO_MACRO_10T_ANCHO_ES, ESPEJO_MACRO_10T_ANCHO_YM; NO_REPETIR: F-VWAP-BANDA3-REVERSION, F-REBOTE-NIVEL-SESION-B, F-DELTASWEEP-PATRONES, F-REGIMEN-OFFLINE; código: edgelab/research/vida_ventaja.py:1, edgelab/research/persistencia.py:55, edgelab/cartera/afinidad.py:1

Potencia previa: (`tools/vida_ventaja_medir.py potencia`, sólo operaciones por mes, sin R; `POTENCIA_PASO1.json`) ruptura_corta 6 series y 18.888 operaciones: detecta τ 0,05/ρ 0,95 con 0,78 y τ 0,1 con 1,00; conjunto 65 series y 23.989 operaciones: 0,74 y 1,00; tendencia 0,10/0,44; reversión 0,20/0,30; COT 0,02/0,02; volumen 0,10/0,22 → sólo ruptura_corta y conjunto deciden.

## Diseño (v0 → crítica → v1)
**v0**: R móvil de 12 meses por regla, duración de los tramos positivos, Kaplan-Meier. **Crítica**: (1) con media constante las ventanas
solapadas fabrican rachas largas: mediría la ventana, no el mercado; (2) sobre reglas ELEGIDAS por andar en 2020–2026 (Franklin, SOM,
Turtles) cualquier historia parece un régimen que se encendió (sesgo del ganador en el tiempo); (3) confunde calidad estática con régimen
(E7: lo que persiste es la calidad estática); (4) un mes con 1 operación pesa igual que uno con 20.
**v1** (`edgelab/research/vida_ventaja.py`): espacio de estados por regla, en desvíos por operación (z = R recortado a [−3, 5] / σ de la
regla): media mensual observada con varianza 1/n; media verdadera = m_i (estática, estado difuso) + d_t, con d_t = ρ d_{t−1} + ruido de
varianza estacionaria τ². τ = tamaño del régimen; ρ = persistencia; vida media L = ln 0,5 / ln ρ meses. Máxima verosimilitud en grilla
(ρ, τ comunes al grupo), intervalos por perfil. Tests: recupera ρ 0,9 / τ 0,15 y no inventa régimen con τ = 0.

## Población (no elegida)
Las 68 reglas × instrumento del catálogo SQX en su variante original (todas, sin mirar resultado; 65 con operaciones), medidas el
2026-11-17 con el motor corregido (`sqx_catalogo_20261117/ops`), desde su primer mes con operaciones hasta 2026-09 (nada del holdout).
Grupos por mecanismo: tendencia (Turtles 55/20 y 20/10, ADX), reversión (MR A/B, buy dips, price dip, Double 7), ruptura corta (rango
13:00, inside bar), COT (3), volumen (POC USDJPY), y el conjunto. Excluidas por selección: Franklin, SOM, Turtles-oro elegida, carteras.

## Decisión
- **Pruebas que deciden** (con potencia ≥ 0,5 para τ 0,05): ruptura_corta y conjunto. H0: τ = 0. p por nulo paramétrico (τ = 0, misma
  estructura de operaciones, 500 réplicas); BH q 0,10 sobre las 2. «Régimen detectado» si la nomina BH y τ > 0: se publica ρ, L e IC.
- Los otros 4 grupos: descriptivos, **SIN_POTENCIA** (un τ = 0 ahí no dice nada).
- Uso: si hay régimen, (ρ, τ) alimentan P(viva) y la incertidumbre del paso 3 (filtro de Kalman); si no, la política usa sólo la media
  estática contraída (sin término de urgencia) en ese dominio. **Alcance**: el catálogo es 6E/CL/GC/6J/índices diarios; no se transporta
  a la cartera (NQ/ES intradía) sin el paso 1b (grillas completas de M1 intradía de 8 índices, en Kaggle, con su propio pre-registro).

## Justificación económica / cómo podría refutarse
Si las ventajas son de régimen (se encienden y apagan por cambios de participantes, volatilidad o microestructura), su media verdadera
varía con persistencia medible y esperar años para confirmar llega tarde; si no, lo que se ve como régimen es ruido más calidad estática.
Se refuta la urgencia (en este dominio) si τ no se distingue de 0 con potencia; se refuta el modelo si sus residuos estandarizados no son
≈ N(0,1) o si el ajuste depende del recorte de colas declarado.

## Contador
`urgencia_vs_evidencia_20261117/PASO1`, familia VIDA_VENTAJA, 6 pruebas (2 deciden, 4 descriptivas). Linaje: VIDA_VENTAJA ← SQX_CATALOGO.

## Enmienda 1 (2026-11-17, después de ver el resultado; no cambia la decisión)
ρ quedó en el borde de la grilla (0,99), así que L era sólo una cota. Se agregan, como DIAGNÓSTICO (`tools/vida_ventaja_medir.py
diagnostico`, `DIAGNOSTICO_PASO1.json`): grilla de ρ extendida hasta 0,999; la misma medición sobre R **bruto** (¿régimen de mercado o
fricción que cambia con la volatilidad? lección K2); innovaciones estandarizadas (refutación declarada del modelo). Las dos pruebas que
deciden y su BH quedan como estaban.
