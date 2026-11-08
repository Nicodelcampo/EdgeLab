# Pre-registro: CANASTA-ORB estable, diversificada y confirmada en el holdout (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de calcular las series; regla global de Nico en `docs/DECISIONES_20261108.md`). Referente
`docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF4 (selección por
estabilidad + confirmación en holdout). Familia CANASTA_ORB, hija de ORB_VARIANTES (hereda su linaje).

**Universo:** las 72 reglas de ORB-VARIANTES (NQ/ES/YM × caja × stop × salida C/1R/2R/3R); no entran las de RR menor (descartadas).
**Datos de selección:** serie diaria (R neto por sesión) de cada regla del 05/08/2025 al 18/06/2026, cortada en **5 sub-bloques
consecutivos** de igual número de sesiones.

**Selección (fija):**
1. Estable: R medio > 0 en al menos 4 de los 5 sub-bloques **y** t diario > 1 en todo el período.
2. Orden por t diario. Se agregan reglas en ese orden si su correlación diaria con cada una ya elegida es < 0,3, hasta 6 reglas.
3. Diversificación: como máximo 3 reglas por instrumento y al menos 2 instrumentos; si no se cumple, la canasta queda vacía.
4. Canasta = media igual ponderada por sesión de las reglas elegidas.

**Probabilidad de azar de la selección:** nulo por inversión de signo por sesión (el mismo signo para todas las reglas ese día),
B = 1.000, repitiendo los pasos 1–4; estadístico = t diario de la canasta. p = fracción de réplicas con t ≥ el observado (canasta
vacía cuenta como t = 0). **Objetivo de Nico: p < 0,10.**

**Confirmación:** la canasta congelada (reglas y pesos) se corre en el holdout (sesiones desde el 01/10/2026, excluidas las de
`edgelab/holdout.py`), una apertura por protocol (`edgelab/autopilot/holdout_apertura.py`), con LORD++. Confirma si el R medio
diario de la canasta es > 0 con p ≤ nivel LORD (una cola, inversión de signo por sesión). Con ≈ 27 sesiones la potencia es baja: se
reporta el MDE y el resultado se sigue en papel (e-proceso) si no hay potencia.

**Limitaciones declaradas:** los ticks sellados del holdout no traen bid/ask: allí la entrada y la salida se modelan con el último
precio más el spread canónico de `edgelab/costos.py` (en desarrollo se usó bid/ask real); se reporta la diferencia del modelo
sobre desarrollo. El horario regular se toma por reloj (09:30–16:00 ET) y las sesiones de cierre temprano se excluyen.

**Cómo podría refutarse:** p de la selección ≥ 0,10, o la canasta no es positiva en el holdout.

## Enmienda del 08/11: apertura del holdout por decisión explícita de Nico (antes de abrirlo)

La selección dio p = 0,37 (`RESULTADO_CANASTA.md`), así que por la regla acordada no correspondía abrir. Nico decide abrirlo igual:
«Abrí el holdout igual, quizás su resultado reduce la probabilidad de que sean azar». Es una excepción humana al protocolo de
apertura (`edgelab/autopilot/holdout_apertura.py` exige un candidato confirmado); queda registrada como tal y **consume la única
apertura de la familia CANASTA_ORB / ORB_VARIANTES**.
- Canasta congelada: `YM|30|O|2.0` y `NQ|30|O|C`, igual ponderadas por sesión. Modelo de llenado last ± medio spread canónico.
- Sesiones del holdout desde el 01/10/2026 hasta la última sellada, menos las excluidas de `edgelab/holdout.py`.
- p del holdout: R medio diario de la canasta > 0, una cola, inversión de signo por sesión (B = 10.000).
- **Combinación fijada ahora:** Fisher sobre p_selección (0,37, desarrollo) y p_holdout (datos independientes):
  χ² = −2(ln p1 + ln p2) con 4 grados de libertad. La meta de Nico (< 0,10) se evalúa sobre ese p combinado.
- Con ≈ 25 sesiones el holdout tiene poca potencia; el resultado se sigue en papel si no es concluyente. No se usa para elegir,
  ajustar ni reintentar.
