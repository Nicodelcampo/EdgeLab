# Punto 1: canasta T + Franklin (+ SOM) — exploración y confirmación de Franklin en instrumentos nunca medidos (resultado, 2026-11-18)

Estado: RESULTADO — **Franklin: NO_CONFIRMADA por la regla pre-registrada (59,7 % de instrumento-año positivos contra 60 %), con
bruto significativo (+0,075 R/op, p 0,0004, LORD rechaza). La canasta sigue siendo una apuesta de NQ en la era de fricción baja; su
confirmación por forward es lenta.**
- **Pre-registro:** `PREREGISTRO.md`. **Datos:** `RESULTADO.json` y `docs/research/m1_largo_20261117/FRANKLIN_OPS_{YM,EMD,RTY,GC}.csv.gz`.
- **Herramienta:** `tools/m1_largo.py` (`correr … franklin`, `analizar_franklin_nuevos`).
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF5.

## 1. Qué datos quedan sin usar (hallazgo de la exploración)
- **El holdout A5 de T, Franklin y SOM ya está mirado.** Las mediciones de M1 largo (`m1_largo_20261117`) usaron años completos de
  2006 a 2025, incluidos los meses HOLDOUT de A5. No sirve para confirmarlas.
- **Lo limpio:** para Franklin, YM, EMD, RTY y GC. T y SOM ya se midieron en los cinco índices; les queda el forward desde la frontera
  (abierto el 16-nov: Franklin 28 ops +0,27 R y SOM 29 ops +0,16 R, los dos NO_CONCLUYENTE).
- **Auditoría del código de Franklin:** causal (K48), riesgo inicial y stop en su nivel salvo hueco (K40). Sin hallazgos.

## 2. Franklin en YM, EMD, RTY y GC (prueba única)
**Conjunto:** 5.640 operaciones, **+0,075 R bruto por operación** (EE 0,022, p 0,0004).
- **LORD++:** nivel 0,0109; rechaza.
- **Instrumento-año positivos:** 59,7 %, contra ≥ 60 % pre-registrado → **NO_CONFIRMADA**.
- **REFUTADA no aplica:** la cota superior (+0,112) supera 0,04.

| Instrumento | N | Bruto R/op (EE) | Neto mini | Neto micro | Bruto 2006–11 / 2012–19 / 2020–25 |
|---|---|---|---|---|---|
| EMD | 1.980 | **+0,123** (0,031) | +0,052 (costo estimado) | — | +0,18 / +0,10 / +0,09 |
| YM | 1.904 | +0,055 (0,033) | −0,042 | −0,088 | +0,30 / −0,04 / −0,05 |
| RTY | 904 | +0,050 (0,042) | +0,002 | — | — / +0,12 / +0,02 |
| GC | 852 | +0,034 (0,050) | −0,094 | −0,112 | −0,03 / +0,08 / +0,02 |

**Lectura:**
- **El mecanismo es real en bruto fuera de NQ/ES**, sobre todo en el MidCap, positivo en las tres épocas.
- **No es universal:** YM lo tuvo sólo en 2006–2011; en el oro no transfiere (Londres no basta).
- **Neto:** fuera de NQ (+0,08 en 2020–25) y quizás EMD (costo estimado), no paga. En 2020–2025 el bruto fuera de NQ/EMD es ≈ 0.
- **Para la canasta:** Franklin entra sólo en NQ, como señal chica (+0,04 R/día neto en 2020–25). EMD queda como candidato
  secundario, que necesita su costo medido (hoy estimado).

## 3. La canasta en NQ (descriptivo, datos ya mirados; no decide)
R neto por día, cada regla a 1 R, celdas vigentes: T (`FS_OPS_T2008`), SOM `sin_finde` y Franklin.

| Período | T | SOM | Franklin | Canasta (t) | Correlaciones T-SOM / T-FR / SOM-FR |
|---|---|---|---|---|---|
| 2008–2011 | −0,108 | +0,008 | −0,012 | −0,111 (t −1,8) | 0,14 / 0,32 / 0,30 |
| 2012–2019 | −0,039 | +0,019 | −0,010 | −0,029 (t −0,6) | 0,22 / 0,41 / 0,32 |
| 2020 → sep-2026 | **+0,144** | +0,053 | +0,042 | **+0,239 (t 4,8)** | 0,16 / 0,36 / 0,34 |

- **Neto, la canasta vive sólo desde 2020.** Antes, la fricción relativa se comía la señal bruta (F-FRICCION-RELATIVA-REGIMEN).
- **T pone el 60 % del resultado.**
- **Sumar ES y YM no ayuda:** el neto por R ahí es chico. Con todas, la información por mes baja: el forward pasa de 88 a 203 meses
  para decidir.

**Cuánto tarda el forward** (e-proceso, `plan_potencia`):
- con la mitad del efecto 2020–25: canasta NQ **88 meses**, T sola 68, SOM 342, Franklin 492;
- con el efecto completo: ≈ 22 meses.

**Conclusión:** el forward solo no confirma a tiempo. La distancia al edge se acorta subiendo el R neto por operación (punto 2:
ejecución) o la frecuencia con un mecanismo de la misma calidad (punto 4: día de tendencia).

## 4. Decisiones
- **Franklin:** pista viva, acotada a NQ (y EMD con costo medido). El mecanismo bruto está confirmado en significancia, no en
  estabilidad.
- **Canasta T + SOM + Franklin en NQ:** sigue en papel/forward con los seguimientos abiertos. No se da tamaño real hasta que el
  forward decida o el punto 2 suba el neto.
- **Propuesto y no medido (con motivo):** SOM y T en las aperturas de DAX, EuroStoxx, FTSE y Nikkei. Exige trasladar horarios con
  desfases de horario de verano y no hay costos canónicos de esos futuros: sería bruto no operable. Se deja como campaña de
  transporte del mecanismo, con sus costos medidos antes.
