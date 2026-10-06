# Idea pendiente — tendencias pobladas de OG/VI "desandadas" como filtro de dirección (Nico, 2026-10-06)

**Estado: PENDIENTE, no ejecutada.** Pertenece a la familia **LUX-IMB** (`H-COND-1_LUX-IMB_PROTOCOLO.md`), que sigue
**bloqueada** por sus prerrequisitos: parámetros reales exportados, ledger as-of, auditoría antirepintado y paridad
Pine→NT8. No se transportan resultados de VTD ni de AVCL.

## La idea (palabras de Nico + capturas MYM 12-26, 5 tick, ImbalanceDetectorLuxAlgoMTF)
Una tendencia deja tras de sí una "población" de imbalances (OG y VI) a favor de su dirección. Cuando el precio **arrasa
esa población desde el lado contrario** (invalida o atraviesa en secuencia los OG/VI que la tendencia había dejado), eso
marcaría que la tendencia se agotó, y la apuesta es **a favor de seguir desandándola** (continuación del giro).

En las capturas: bajada con línea de tendencia, OG/VI acumulados; el precio rompe la línea y recorre hacia arriba
barriendo los imbalances bajistas, y la suba continúa.

## Por qué es distinta de lo ya medido
- No es una zona aislada, sino un **estado acumulado** (densidad de imbalances de un lado) más un **evento de barrido**
  (consumo secuencial desde el lado opuesto).
- Da **dirección** (la del barrido), que es justamente lo que no apareció en AVCL, VTD ni en los filtros de VTD-DIR.

## Lo que hará falta para medirla bien (cuando se desbloquee LUX-IMB)
1. Parámetros exactos del indicador (los de la captura: `5 Tick, false, 50, 0, Points, false, 2, 10, 5, 50, 0,
   Points, ...`) exportados y congelados. **OG y VI activos, FVG apagado.**
2. Censo as-of de **todos** los imbalances, incluidos los mitigados. En el indicador de Nico las zonas no desaparecen
   por mitigación, pero igual hay que verificarlo con la auditoría antirepintado.
3. Definir de antemano, con alternativas escritas (regla de población):
   - "tendencia poblada": N imbalances del mismo lado en una ventana, o densidad por tick recorrido;
   - "arrasada": fracción de esa población invalidada desde el lado opuesto en M barras;
   - el evento: la barra en que la fracción cruza el umbral.
4. Resultado sin escala (asimetría de la excursión posterior, como en VTD-DIR) y **nulo**: el mismo barrido sobre una
   población **sorteada** (imbalances de otra ventana con la misma cantidad y geometría) y sobre una línea de tendencia
   rota **sin** población. Así se separa "barrido de imbalances" de "ruptura de una tendencia cualquiera".
5. Ojo con el sesgo de lectura visual: la ruptura de la línea de tendencia se dibuja después de ver el giro. La
   definición tiene que ser causal.
