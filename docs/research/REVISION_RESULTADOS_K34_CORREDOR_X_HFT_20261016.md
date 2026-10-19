# Revisión de los resultados k34 de Gemini — estudio CORREDOR × HFT (desenlaces y ML)

Estado: REVISIÓN — lectura del informe (las tres copias .docx son el mismo documento) y razonamiento sobre sus tablas; no se re-ejecutó el kernel `edgelab-corredor-hft-outcomes-ml-v1` (id 139066651)
Fecha: 2026-10-16
Familia / módulo: EXP-CORREDOR-HFT
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)
Objeto: `RESULTADOS_ESTUDIO_CORREDOR_X_HFT_DESENLACES_Y_ML_20261016` (Gemini, k34).

## Veredicto
**Útil como estudio descriptivo exploratorio; sus dos conclusiones centrales están sobredichas.** (1) Que la presencia de zonas HFT al inicio no cambie P(llegar) frente a un control geométrico es creíble, pero **no está demostrada la "equivalencia ±3 pp"**. (2) Que "lo que sí tiene poder predictivo" sea la geometría y frescura de la zona **no dice nada sobre las zonas HFT**: vale para cualquier nivel de precio.

## Lo sólido
- Reproduce el censo (7.841 zonas; 5.311 vs 5.312 impulsos; 1.270/173 y 599/153 exactos) y pasa tres pruebas causales (prefijos vs streaming, perturbación del futuro, `available_at` de zonas) con diferencia 0.
- Buenos controles: C1 (0-0 emparejado por distancia fraccional), C2 (pseudo-zonas), C3, C4 (banda común); SE clusterizado, DEFF empírico (0,68–1,01, menor que el 2 que yo supuse) y MDE80 empírico; Holm/BH; separa `inside_at_cls` y la censura de fin de sesión.
- Diagnóstico correcto de la "paradoja C2": una zona tocada en la 1.ª mitad queda geométricamente cerca del precio, y la distancia explica la llegada. El control C1/C4 lo neutraliza (−0,64 pp; −3,85 pp).
- Escalera coherente con lo esperado: elastic net/logística ≥ árboles ≥ hazard > CNN chica (peor que el baseline con N ≈ 2.000).

## Problemas
1. **Gobernanza (STOP).** El informe cita un "manifiesto congelado", pero no registra la **aprobación de Nico** para correr desenlaces. Mi handoff exigía manifiesto + OK explícito. Hasta que Nico lo confirme, los resultados quedan como **exploratorios**.
2. **"Equivalencia práctica ±3 pp" no está demostrada.** H1: diferencia −0,64 pp con IC95 [−3,84; +2,56]; el IC cruza −3 y el MDE80 (4,57 pp) es mayor que el margen. Una prueba de equivalencia (TOST con IC90) probablemente no pasa. Lo correcto: **sin efecto detectable; potencia sólo para ≈ ±4,6 pp**. Lo mismo vale para H4, H4b y E2_cz.
3. **El poder predictivo de B.2–B.4 es de la geometría, no de la HFT.** `dist_ticks`, `width_ticks`, edad y virginidad existen para cualquier nivel; que un modelo con la distancia a un nivel prediga la llegada (AUC 0,77) es esperable. El baseline M0 **no tiene ninguna distancia a un nivel**. Para afirmar información específica de zonas HFT hay que entrenar el **mismo modelo sobre las pseudo-zonas** (C1/C2) y comparar, o incluir `es_hft` como variable en un conjunto mixto y medir su aporte. El nulo por desplazamiento circular no lo resuelve (sólo prueba que las etiquetas importan).
4. **H6 está confundida por la distancia.** Con W2 ≥ 1 las zonas están cerca del extremo/del precio de decisión (y 22 % ya contiene a `cls_px`), así que llegar es más fácil; en la banda común C4 la diferencia cae a −4,2 pp. La explicación "absorción institucional" es una hipótesis, no un resultado. "Refutación directa" es excesivo.
5. **Multiplicidad parcial.** La familia Holm de 6 contrastes se aplica a E1; los resultados de E2 (llegada y cruce en contra, y rebote `E2_ci`) no figuran en la corrección. El titular "+6,48 pp, z = 3,89" es un contraste adicional (E2 | E1 condiciona en una variable posterior al tratamiento): hay que declararlo en el presupuesto (≥ 18 pruebas) y marcarlo como **hipótesis nueva**.
6. **Lectura de `monotone_constraints`.** El signo erróneo de "Por dónde" lo especificó el propio informe; y un modelo del evento conjunto E1 & E2 con un único signo por variable está mal especificado por construcción (el ancho cambia de signo entre etapas). La caída de AUC de 0,84 a 0,63 es demasiado grande para un solo signo: conviene revisar que no haya un error. La conclusión general "las restricciones monótonas son peligrosas" no está soportada.
7. **Semillas.** M3 muestra "± 0,00000" en 5 semillas: es determinista, no un estudio de semillas. M4 (CNN) peor que M0: esperable.
8. **Población del ML sin aclarar.** `n_oos = 2.229` vs 1.194 del contraste primario: falta decir qué población usa el ML (¿todos los impulsos con zona de referencia, incluidos W2 ≥ 1?).

## Qué sí vale la pena
- **Hipótesis nueva (a preregistrar):** tras llegar a una zona HFT del inicio, el precio **rebota a favor del impulso original** más a menudo (15,5 % vs 9,0 %; +6,5 pp; z = 3,9), sobre todo en impulsos alcistas. Las zonas HFT del inicio se comportan como escalones de defensa del impulso, no como imanes de inversión.
- La **distancia, edad y virginidad** de un nivel predicen la llegada; sirve como baseline que cualquier señal de inversión debe superar.

## Pautas para Gemini
1. Registrar la aprobación de Nico (o declarar la corrida exploratoria) antes de citar conclusiones.
2. Reemplazar "equivalencia" por "sin efecto detectable (MDE)" o correr TOST con el margen declarado de antemano.
3. Repetir la escalera ML con **pseudo-zonas a la misma distancia** y reportar el aporte de `es_hft` sobre ellas.
4. Ajustar la familia de multiplicidad para incluir E2 y E2_ci; marcar el rebote como hipótesis nueva.
5. Controlar por distancia en H6 antes de interpretar mecanismos; declarar la población del ML.
6. Revisar el modelo conjunto E1 & E2 (dos etapas con signos propios) y descartar un error de especificación.
7. Para la hipótesis del rebote: preregistrar y probar en datos no usados (NQ con su propia fricción y su detector, o una réplica declarada con su historia de exposición).

*Aporte al referente:* separa lo que el estudio mide bien (el efecto nulo de la presencia frente a un control geométrico) de lo que sobredice (equivalencia, poder predictivo de las zonas HFT), y rescata una hipótesis nueva y concreta para confirmar sin gastar la réplica.
