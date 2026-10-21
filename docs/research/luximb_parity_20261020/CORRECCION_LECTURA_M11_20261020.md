# Correccion de lectura de M11 (2026-10-20)

Estado: CORRECCION. Pedido de Nico: "¿por que antes no llegaste a la misma conclusion? registra bien esto".
Afecta a: `RESULTADOS_M11_GRILLA_SLTP_20261020.md` y a las respuestas en chat posteriores a M11. **No cambia ningun numero**:
cambia la lectura.

## Que se dijo
"Ninguna celda sobrevive"; "el +0,8 R del visor era sobre todo entrada optimista y periodo de diseno"; "el OOS positivo
es efecto del periodo, no de la configuracion"; al preguntar Nico si no tenia efecto: "no se distingue de cero y no se repite".

## Que muestran los datos (los mismos de M11 + tablero por periodo)
La regla del visor en version realista (entrada al cierre de la vela de marca, 1 tick, $4,50, TP en A, SL 1/5, sin BE) da
en NQ: 09-25 -6,4 (n 20); 12-25 +3,7 (99); 03-26 +5,7 (100); 06-26 +6,2 (130, no usado para disenar); 09-26 +5,6 (150,
periodo de diseno). Total 499: **+4,95 pts/op, IC [+0,55, +9,2]**. Positivo en 4 de 5 periodos con n >= 99. En ES ~0.

## Por que la lectura anterior fue incorrecta (causas)
1. **Se confundio "el ranking de parametros es ruido" con "no hay edge".** La correlacion IS-OOS de -0,04 entre las 40
   celdas dice que elegir SL/TP no aporta; no dice nada sobre si la entrada (fade hacia A) tiene valor. Que 40/40 celdas
   den positivo en OOS es compatible con un efecto de la ENTRADA, comun a todas las variantes.
2. **"Efecto del periodo" se afirmo sin probarlo.** Era una hipotesis alternativa, no un resultado; ningun calculo la sostenia.
   Viola "fuente antes que recuerdo" y "causa raiz obligatoria".
3. **Se juzgo periodo por periodo con ~100 operaciones**, donde ningun IC puede excluir 0 con este ruido, y no se miro la
   consistencia ni el agregado. Ausencia de significancia por tramo no es ausencia de efecto (falto el MDE por tramo).
4. **La regla de supervivencia de M11 (top-3 de IS, OOS > 0 y ES > 0) se uso como veredicto sobre la idea entera.** Su
   alcance correcto era: "ninguna variante elegida en IS es transportable NQ -> ES". La muerte se amplio mas alla de su
   alcance (viola "toda muerte tiene alcance preciso").
5. El resumen enfatizo la parte inflada (entrada en X: real, ~2-3x) y omitio que la version realista seguia positiva en NQ.

## Lectura corregida
- Muere (se mantiene): elegir SL/TP/BE en IS no mejora nada; la regla no transporta a ES.
- **Queda vivo como candidato en NQ**: la regla del visor con entrada realista, ~+5 pts/op neto, positiva en 4/5 periodos.
- No es edge declarado: (a) el agregado solo excluye 0 incluyendo el periodo de diseno y abr-jun; (b) hubo 14 mediciones
  en la familia (multiplicidad sin deflactar); (c) no transporta a ES. **Prueba limpia pendiente: holdout >= 2026-10-01, una vez,
  regla congelada.**

## Practica que se agrega
Antes de declarar muerta una idea con P&L: (i) separar "parametros" de "entrada"; (ii) reportar consistencia entre periodos
y el agregado con su IC, ademas de cada tramo; (iii) publicar MDE por tramo; (iv) no afirmar una explicacion alternativa
(periodo, regimen) sin un calculo que la sostenga.
