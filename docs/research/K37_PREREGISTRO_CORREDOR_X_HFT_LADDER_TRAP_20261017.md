# K37 — manifiesto pre-registrado (BORRADOR, NO EJECUTADO) — corredor x HFT, exclusion de escalera opuesta

Estado: **PROPUESTA PARA NICO. STOP vigente: no se corre ninguna medicion sobre retornos sin su OK explicito.**
Fecha: 2026-10-17. Rama: `research/k37-prereg-corredor-hft-20261017`.
Referente rector: `docs/NORTH_STAR.md`, cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Antecedentes: k34 (censo, sin retornos), k35 (base simetrica), k36 (barrido de 7 variantes; auditoria en `docs/research/k36_audit_20261017/`).

## 0. Por que este manifiesto y por que es chico
k36 probo 7 variantes x 3 universos x 4 modelos de costo (DSR con 44 pruebas) y en el walk-forward de 178 sesiones
**ninguna** supero costos (neto con limite inmediato entre -0.6 y -1.7 ticks; ver `K36_WF178_VS_OOS32_TABLA.md`).
Lo unico que quedo como pista es un corte **mirado despues de ver los datos**: con escalera opuesta sin barrer el win rate
asimetrico es 26.5 % (n=257) contra 36.1 % con barrido (n=382), y el promedio del universo es 38.05 %.
Es decir: la pista es "la escalera empeora", no "el barrido mejora". Este manifiesto la pone a prueba **una sola vez**, con una unica
variante, sin ranking ni ML, y con la ejecucion realista como metrica primaria.

## 1. Hipotesis (con su refutacion)
- **H1 (unica primaria):** en la poblacion U1, excluir los impulsos con `opp_ladder_trap_flag = 1` deja una expectativa **neta positiva**
  por trade con ejecucion pasiva realista.
- **Justificacion economica:** una escalera de ordenes opuesta sin barrer es liquidez que frena el recorrido hacia el objetivo; excluirla
  reduce la cola de stops sin cambiar la geometria. Mecanismo plausible, no medido fuera de muestra.
- **Como podria refutarse:** si el limite inferior unilateral (97.5 %) de la media neta pasiva no supera 0, **o** el nulo de desplazamiento
  circular no se rechaza, la hipotesis queda no soportada. Se espera esto como resultado mas probable (ver 7).
- Secundaria (informativa, no decide): diferencia neta ARM_NOLADDER vs ARM_LADDER (Holm sobre las 2 pruebas).

## 2. Poblacion y espacio de eventos (regla de poblacion)
Espacio considerado: (a) todos los impulsos del corredor `DET_NT8` en 100T estricto por sesion; (b) impulsos con zona HFT **tocada** en W1
(U1 = preset 1, fija 600, 2.536 validos en k36); (c) impulsos con zona activa sin toque (estrato de 970 en k34); (d) extensiones dinamicas
(control chico, 1.100-1.400); (e) preset 2 (se solapa con preset 1, no es replica independiente).
**Elegida: (b) = U1.** Razon: es la unica con control de buen tamano y definicion cerrada en k34; (a) no tiene hipotesis de mecanismo;
(c) y (d) tienen n chico; (e) duplica zonas. Se declara que (a), (c), (d), (e) **no se miden aqui** ni se transportan resultados a ellas.
- Instrumento: **ES** unicamente (sin NQ/YM/6E). Barras 100T estrictas por sesion. HFT = `HFTZonesESPureV2Flat` (puerto Python, sin absorb).
- Ventana de datos: **replicacion HOLDOUT-A3 abril-septiembre 2026** (`docs/CURRENT.md`: "abr-sep = replicacion, una vez por familia").
  Descubrimiento (2025-07-18 a 2026-03-31, 178 sesiones) queda para fijar parametros **ya fijados abajo**: no se reajusta nada.
- Holdout forward desde 2026-10-01: **no se toca.**
- **Dependencia abierta:** confirmar que existen ticks ES 06-26 y 09-26 pre-2026-10-01 completos y auditados (continuidad entre sesiones, `outside_regular`,
  contratos). Si no, el manifiesto no se puede ejecutar.

## 3. Variante congelada (sin ranking, sin ML, sin tope de frecuencia)
- Entrada/ejecucion primaria: **maquina de estados pasiva con trade-through**, costo ida y vuelta 1.546 ticks (mismos supuestos que k36).
- Geometria: salida simetrica de 2 etapas del baseline k35 (C0): objetivo = riesgo = d1 del impulso; nada de stops asimetricos ni de R:R extremo.
- Filtro unico: `opp_ladder_trap_flag == 0` (definicion exacta del kernel k36, congelada por hash del codigo).
- Todos los impulsos validos que pasan el filtro se operan (sin ranking, sin seleccion por `p_win`). No se usa `target_mirage_flag`
  (diagnostico: 0 activaciones en U1; se retira, no se reajusta).
- Los parametros de k36/k35 quedan congelados por hash: `tools/k36_audit/kernel_k36_v1_source.py` sha256
  `eff8bdf6ead2f3f4da1b1456fb24554bfc4fd32bc6d6eca678ef1739e3e3d198` + parche de prefijo `prefix_test_nontrivial.patch`.

## 4. Estimando, inferencia y multiplicidad
- Estimando: media de ticks netos por trade (pasivo realista, 1.546t). Tambien se publican bruto, neto limite inmediato y por mes (descriptivo).
- Error estandar **clusterizado por sesion**; limite unilateral 97.5 %.
- Pruebas decisoras: m = 1 (H1). Secundaria: Holm sobre 2. El DSR se reporta con m = 44 (numero heredado de k36) como cota conservadora.
- Nulo: desplazamiento circular de zonas HFT dentro de la sesion, 1.000 repeticiones (k36 uso 100), mismo numero de trades por dia.
- Dos canales: se publica ademas la distribucion completa (cuantiles de ticks por trade) y MAE/MFE medianos; el efecto no direccional no aplica a esta salida.

## 5. Potencia (estimacion, no medicion)
Base k35 sin filtrar: 2.219 trades en 145 sesiones, se clusterizado del bruto 0.378 ticks. En ~125 sesiones de replicacion y ~14 trades/dia (supuesto: el filtro
quita ~10 %), se ~ 0.41-0.45 ticks. **MDE (80 %, unilateral 2.5 %) ~ 1.2 ticks netos.** Es un supuesto de clustering heredado, a medir al correr.

## 6. Criterios (definidos antes de mirar)
- **SOPORTADA:** limite inferior 97.5 % de la media neta pasiva > 0 **y** p del nulo circular <= 0.025 **y** prueba de prefijo v2 con >= 200 zonas verificadas.
- **NO SOPORTADA (cierra la linea):** limite superior 97.5 % de la media neta pasiva < +0.5 ticks.
- **ABSTENCION (sin poder):** cualquier otro caso; no se promueve ni se reintenta sobre la misma ventana.
- Un resultado positivo no es un edge: pasaria a replicacion forward (holdout >= 2026-10-01, una sola apertura) y a ejecucion real.

## 7. Prior honesto (para que nadie lea esto como expectativa de ganar)
El bruto base es ~0.7 ticks contra un costo de 1.546 ticks. Excluir ~10 % de trades de -0.35 ticks mueve el promedio ~0.04-0.2 ticks.
**Cerrar la brecha de ~0.9-2.0 ticks con este filtro no es plausible.** Se espera NO SOPORTADA o ABSTENCION.
Gastar la unica replicacion de la familia en esto solo tiene sentido si se quiere un cierre definitivo.

## 8. Decision que se le pide a Nico
1. **(A) Ejecutar** con este manifiesto (consume la replicacion abr-sep de la familia corredor x HFT), o
2. **(B) No ejecutar** y archivar la linea como "sin efecto detectado, replicacion no abierta" (**mi recomendacion**: la brecha costo/efecto no es cerrable con este filtro), o
3. (C) cambiar la hipotesis antes de congelar (por ejemplo, pasar a una linea con mas margen sobre costos).

## 9. Requisitos tecnicos previos a cualquier corrida
- Aplicar `prefix_test_nontrivial.patch` y **correr** la prueba en Kaggle (el parche esta escrito y verificado solo de sintaxis; no se ejecuto).
- Congelar este manifiesto por hash en un commit antes de abrir los datos de replicacion.
- Registrar la familia/variante en `docs/research/*_MEDIDO_Y_NO_MEDIDO.md` en el mismo commit que el resultado.
