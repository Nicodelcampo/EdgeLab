# Franklin sobre M1 real de futuros 2006–2025 (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — commiteado antes de correr. Pedido de Nico: «sí, seguí» (la medición de Franklin que faltaba en el veredicto).
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4. Herramienta: `tools/m1_largo.py correr …
franklin <INST>` y `analizar_franklin`. Celda: la que fue al holdout (`reels_20261116/FRANKLIN_MEJORAS.json`, «1000|rango|ninguno»).

Antecedentes: reels_20261116 (Franklin: A 2012–2019 neto en contra, B 2020+ a favor sobre el CFD; holdout +0,27 R NO_CONCLUYENTE),
F-FRICCION-RELATIVA-REGIMEN (lo de hoy: la señal BRUTA estable es lo que importa; el neto depende de la fricción de la época).

Potencia previa:
- plan de `holdout_ventanas.plan_potencia` con efecto = mitad de +0,15 R bruto (Franklin NQ/ES 2020+, CFD), sd 1,0 declarado, N ≈ 850
  (≈ 11,8 operaciones por mes en NQ + ES × 72 meses): potencia 0,706, n para decidir 1.100.
- El neto, con la mitad de +0,10 R, tendría potencia 0,43: por eso no es la prueba principal.

## 1. Datos y unidades
NQ y ES (los índices de Franklin), futuros M1 de NT8, 2006 → jul-2025; R = neto o bruto / riesgo; fricción canónica de cada futuro.

## 2. Prueba (una)
- **Qué se prueba:** el BRUTO por operación en los años limpios 2006-01-06 → 2011-12-30 (ninguna medición de Franklin los tocó), NQ y ES
  juntos.
- **Veredictos:**
  - **A_FAVOR** si IC90 inferior > 0 y ≥ 60 % de años positivos;
  - **EN_CONTRA** si media ≤ 0 con potencia ≥ 0,8 para la mitad del bruto de 2020–2025 en futuros;
  - si no, NO_CONCLUYENTE.
- **Descriptivo:** neto y bruto en 2006–2011, 2012–2019 y 2020–2025, y la fricción en R de cada período.

## 3. Contador, justificación y refutación
- **Contador:** 1 prueba, familia `M1LARGO_EXTERNAS_20261117`.
- **Justificación económica:** el sesgo de la sesión de Londres contra el VWAP predice la dirección de NY. Si es un mecanismo y no ruido de
  selección, la señal bruta tiene que estar también en años no usados.
- **Cómo podría refutarse:** bruto ≤ 0 con potencia en 2006–2011.
