# Resultado TOXIC-ES-1: capa *toxic* de ES — FAIL por deriva entre mitades (2026-09-29)

Pre-registro `PREREG_TOXIC_ES_ESTABILIDAD_20260929.md` (commit previo a medir). Target-free. Salida:
`l2_contexts_ES/TOXIC_ES_1_resultado.json` (`tools/toxic_es_estabilidad.py`). 43.238 minutos de evaluación (32 sesiones),
21.896 de entrenamiento.

| Criterio | Valor | Umbral | |
|---|---|---|---|
| E1 deriva entre mitades | 13,3 % → 8,4 % (razón 1,59); IC 90 % de la dif. [+0,018; +0,080] | razón ≤ 2 **y** IC ∋ 0 | **FAIL** |
| E2 evaluación vs entrenamiento | 10,8 % vs 9,6 % (×1,13) | [0,5×; 2×] | PASS |
| E3 persistencia | mediana 7 min; 25 % de rachas ≤ 3 min | ≥ 5 y < 50 % | PASS |
| E4 no es la hora | máx. 23 % en una franja de 2 h; sólo-hora 0,899 vs mayoría 0,892 | ≤ 50 % y ≤ +2 pts | PASS |
| E5 no es un par de días | máx. 8,3 % en una sesión; 100 % de sesiones con *toxic* | ≤ 15 % y ≥ 75 % | PASS |

Sensibilidad sin 11/08 y 12/08: mismo patrón (12,7 % → 8,7 %, IC [+0,006; +0,074]) → FAIL.
Proporción semanal: W30 14,5 % · W31 7,4 · W32 13,7 · W33 16,4 · W34 10,5 · W35 12,0 · W36 7,5 · **W37 4,5**.

## Lectura
La capa es persistente, no es la hora ni unos pocos días, y su nivel en evaluación coincide con el de entrenamiento; pero
**cae de forma sostenida hacia septiembre** (la última semana a un tercio de las primeras), y la regla pre-registrada exige
estabilidad entre mitades. **FAIL: la capa *toxic* de ES no se usa.** No se ajustan umbrales ni se re-parte la muestra.
Queda abierto (no medido) si la caída refleja un cambio real del mercado en septiembre (p. ej. menos estrés) o deriva del
score: distinguirlo exigiría más sesiones (oct+) y un pre-registro propio. El paso 2 (costos/riesgo) no se propone.
