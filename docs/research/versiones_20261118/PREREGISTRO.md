# Versiones nuevas en papel después del veredicto del M1: v2.1, v3.1, v4.1, B' y SEÑAL_ESTABLE (pre-registro, 2026-11-18)

Estado: PRE-REGISTRO — commiteado antes de la primera sesión forward de estas versiones. Pedido de Nico: «sí, seguí» (y «que funcione
desde 2020 es bastante bueno, el mercado cambia»). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa EF5 (forward). Base: `docs/research/VEREDICTO_M1_20261117.md`.

Antecedentes: VEREDICTO_M1_20261117 (refutadas CVGAP-ES-C, CVGAP2-GC#11 y COMEX; T frágil; SOM y R con señal bruta estable),
PREREGISTRO_FORWARD_V2.md (mismo esquema de e-proceso), PREREGISTRO_CARTERA_B.md.

Potencia previa: m1l_SOM.csv (SOM sin_finde NQ 2020+): 19.7 ops/mes, R/op +0.079, sd 0.98, n para decidir 957, 48.6 meses → OK; las
canastas suman frecuencia (B': ≈ 5 ops/mes; v2.1 y v3.1: la de la v2 menos una regla; SEÑAL_ESTABLE: ≈ 22 ops/mes).

## 1. Versiones (congeladas; archivos en esta carpeta)
| Versión | Composición | Por qué | Archivo |
|---|---|---|---|
| v2.1 | v2 sin CVGAP-ES-C | REFUTADA_ATRAS | `CARTERA_V2_1_OPERATIVA.json` |
| v3.1 | v3 sin CVGAP-ES-C | ídem | `CARTERA_V3_1_OPERATIVA.json` |
| v4.1 | cosecha v4 sin CVGAP2-GC#11 ni COMEX | EN_CONTRA_ATRAS | `CANASTA_V4_1.json` |
| B' | R + Z (stop de catástrofe 0,5 × ATR20), sin T | T sin señal bruta antes de 2020 | `CARTERA_B_PRIMA_OPERATIVA.json` |
| SEÑAL_ESTABLE | SOM sin_finde (no opera si fricción/riesgo > 0,08 R) + R AtrPhase en NQ con stop de catástrofe, en MNQ | las dos con señal bruta estable 2006–2025 | `CANASTA_SENAL_ESTABLE.json` |

**Las versiones originales (v2, v3, v4, B con T) siguen en forward en paralelo, sin cambios.** Esto respeta que «funciona desde 2020»
también es evidencia: el forward decide entre B y B' y entre cada versión y su original.

## 2. Medición (forward, sesiones desde la primera sellada después de este commit)
- **Estadístico:** e-proceso por versión (`edgelab/funnel/secuencial.py`), H0 E[x] ≤ 0.
- **Cotas:** por sesión [−15, 40] R de cartera para v2.1, v3.1 y v4.1, como la v2; por operación [−6, 30] R para B' y SEÑAL_ESTABLE.
- **Decisión:** EDGE si e ≥ 10.
- **Futilidad:** R total ≤ 0 tras 60 sesiones con operaciones.
- **Comparación pareada por sesión,** descriptiva, de cada versión contra su original (v2.1 − v2, B' − B).
- **Cálculo:** las versiones se derivan de las operaciones forward que ya produce `tools/seguimiento_forward.py`, filtrando reglas; el
  cálculo se agrega a esa herramienta con los primeros datos sellados.

## 3. Contador, justificación y refutación
- **Contador:** 5 pruebas (un e-proceso por versión), familia `VERSIONES_20261118` (linaje: CARTERA_20261116, FUNDEDSYNC, SOM,
  COSECHA_POZO_20261117).
- **Justificación económica:** sacar lo refutado no cambia la ventaja esperada de lo que queda, pero deja de pagar fricción por reglas
  sin señal. SEÑAL_ESTABLE junta las dos únicas señales brutas estables de la historia larga.
- **Cómo podría refutarse:** e-proceso sin cruzar y futilidad (R total ≤ 0 tras 60 sesiones con operaciones), o que la versión rinda menos
  que su original en la comparación pareada.

## Nota (2026-11-18, después de commitear; no cambia el diseño)
La premisa «T sin señal bruta antes de 2020» se corrigió (`docs/research/m1_largo_20261117/RESULTADO_T_2020.md`): medida en R, T es pista fuerte
en NQ. B (con T) es la principal y B' queda como comparación pareada en el forward, como ya estaba previsto.
