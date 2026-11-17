# Paso 1: vida de una ventaja — resultado (2026-11-17)

Estado: CERRADO — pre-registro `PREREGISTRO_PASO1.md` (con enmienda 1). Datos: `RESULTADO_PASO1.json`, `DIAGNOSTICO_PASO1.json`,
`POTENCIA_PASO1.json`. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Pruebas que deciden (R neto, grilla pre-registrada)
| Grupo | τ (desvíos por operación) | ρ | p (τ = 0, nulo paramétrico) | BH q 0,10 |
|---|---|---|---|---|
| ruptura corta (6 series, 18.888 ops) | 0,07 [0,05–0,10] | 0,99 [0,97–0,99, borde] | 0,002 | régimen detectado |
| conjunto (65 series, 23.989 ops) | 0,05 [0,03–0,07] | 0,99 [0,97–0,99, borde] | 0,004 | régimen detectado |
Sin potencia (descriptivos): tendencia τ 0, reversión 0,05, COT 0,20, volumen 0,16, todos con p ≥ 0,26.

## Diagnóstico (enmienda 1)
| | R neto | R bruto |
|---|---|---|
| ruptura corta | ρ 0,999 [0,97–0,999], τ 0,16, p 0,003 | ρ 0,999 [0,90–0,999], τ 0,10, **p 0,06** |
| conjunto | ρ 0,999 [0,97–0,999], τ 0,16, p 0,003 | ρ [0–0,999], τ 0,10, **p 0,11** |
Innovaciones estandarizadas: media ≈ 0, desvío 0,94–1,01, 1 % fuera de ±3: el modelo describe las series (no se refuta).

## Lectura
1. **No hay regímenes que se prendan y se apaguen en meses.** Lo que se detecta es una deriva MUY lenta de la media (ρ en el borde 0,999;
   vida media de años, con el intervalo hasta ≈ 2 años como mínimo).
2. **La mayor parte de esa deriva es fricción, no mercado**: en bruto la evidencia cae de p 0,003 a 0,06–0,11. La fricción es fija en puntos
   y pesa distinto en R según la volatilidad (que cambia lento): cuando la volatilidad baja, el stop se achica y el mismo costo se come más R.
   Es la misma lección que K2 / F-ATLAS-CONTEXTO-ES-FRICCION, ahora en el tiempo.
3. **Para el equilibrio urgencia-evidencia** (`PROPUESTA.md`): en este dominio L ≫ T de las canastas (meses), así que confirmar en
   forward y después escalar NO llega tarde; la urgencia pesa sólo en reglas sueltas cuyo T ya es de años (SOM 49, Franklin 71 meses) —
   y ahí la salida es canastear, no apurarse. P(viva) no conviene modelarla como una vida en el tiempo sino como **fricción en R del
   estado de volatilidad actual** (medible antes de operar): es la palanca F-STOP-GRANDE-FRENTE-A-FRICCION aplicada al tamaño.
4. **Alcance**: catálogo SQX (6E, CL, GC, 6J, índices diarios). La cartera es NQ/ES intradía: hace falta el **paso 1b** (grillas completas
   de M1 intradía de 8 índices, en Kaggle, misma herramienta) antes de usar esto para dimensionar la cartera.
