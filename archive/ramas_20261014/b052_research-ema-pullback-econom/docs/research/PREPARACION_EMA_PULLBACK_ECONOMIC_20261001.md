# Preparación EMA20 pullback económica — 2026-10-01

## Alcance
Nico autorizó continuar. Censo elegido antes de outcomes: 1min, MNQ154/878, RTY175/975, YM177/984. BASE y SEP anidados, sin rescheduling. Misma población de desarrollo, NO OOS ciego. Holdout julio+ cerrado. ES ausente del dataset verificado; no sustitución encubierta.

## Congelado
Salida fija30min; bidask posterior a close+250ms, máximo30s para entrada. Comisión supuesta/side MNQ0.60 RTY2.25 YM2.40 USD y slippage1/2/3ticks por leg. Spread ya incluido. No tarifas/fills reales confirmados.
Controles de misma sesión, contrato y tendencia, distancias31–60min, Uratio0.5–2; máximo5 por hash, sin outcomes. Mínimo3 completos y80% cobertura. Reutilización/solapamiento por sesión, no pseudoN. Net_U para todos y alpha_U sólo soporte común.12tests primarios; 20kpercentile diagnóstico/10kstudentized nativo cuando>=160sesiones; sensibilidad134 no presupuesto histórico certificado. G0/G2/G3 completos no aprobados. MAE/MFE sin medir.

17tests dirigidosPASS; código nativo reutilizado primero. Se persiste plan entero antes de replay. No rescate de salida/filtro/horario tras resultados.

Manifiesto SHA256: `56d3f991b1d72b803c911e0a5fa369a844048521a9087ae18628886954f7ae60`. Detector intacto `801b066b...` como censo v3.

Kaggle privado v1 enviado, fuente exacta MATCH y RUNNING confirmado. Kernel136675763. No resultado económico confirmado todavía.
https://www.kaggle.com/code/nicolasbuttaro/edgelab-ema-pullback-economic-20261001

## Reproducción/custodia
`run_economic.py` importa únicamente replay/costs de `economic.py`; NO correr la vieja rutina run/evaluate del módulo reutilizado. `census.py` es sólo dependencia de import, no el detector elegido. Productor/catálogo, URLs, expected ledger y fuentes permanecen privados; los hashes públicos no permiten fabricar los datos. Nativos de foundation3913149. No afirmar reproducción independiente exhaustiva.

Aporte al referente: frecuencia suficiente más contraste con momentos comparables, antes de afirmar rentabilidad.
