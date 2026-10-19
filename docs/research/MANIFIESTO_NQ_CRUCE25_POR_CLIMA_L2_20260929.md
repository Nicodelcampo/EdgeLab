# Manifiesto NQ-CRUCE25-CLIMA: ¿el primer cuarto del cruce hacia B depende del clima L2? — PRE-REGISTRO (2026-09-29)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PRE-REGISTRO. OK de Nico para prepararlo; **se corre sólo después de la auditoría** (pedido de Nico).
**Clase A3:** análisis de **desarrollo** sobre jul–sep 2026 (adenda A3 para preguntas condicionadas a clima L2). No es
confirmación. Confirmación, si algo sobrevive, sólo forward desde la sesión del 1-oct-2026, una vez.

## 1. Hipótesis y refutación
- **Origen:** ESPEJO-REV-100T NQ (Lucid, descubrimiento): una vez que el precio empieza a cruzar de vuelta hacia B tras
  completar el espejo, llega al 25 % del camino más que el azar (+2,2 a +4,6 pp) en dos muestras disjuntas (~16–20
  sesiones cada una). ES va al revés; GC y YM, azar.
- **Hipótesis:** el exceso del cruce al 25 % se concentra en ciertos climas L2 de NQ (calm / normal / volatile / toxic).
  Bilateral. Aviso de Nico (efectos que se anulan): un efecto por clima puede promediar ≈ 0.
- **Refutación:** ningún clima difiere del control emparejado tras max-T; o el efecto global no aparece en NT8 jul–sep.

## 2. Datos (dataset privado `nicolasbuttaro/edgelab-nq-nt8-2026q3-l2ctx`)
- NQ NT8 canónico jul–sep 2026 (09-26 y 12-26, catálogo `NQ_ext_2026q3`). Velas 25t con el mismo código que el resto.
- Clima: `l2_contexts_NQ_labels.parquet` del modelo con PASS (`RESULTADO_CONTEXTOS_L2_NQ_20260928.md`). Sólo las
  **40 sesiones de evaluación** (29/07–23/09); las 20 de entrenamiento (el modelo las vio) quedan fuera.
- Reloj: etiquetas en ART → UTC = ART + 3 h. **Causalidad:** a cada evento se le asigna la etiqueta del último minuto
  con `available_utc_us ≤ t_evento`, `evaluation_eligible` y `context_as_of_ok`; sin eso, «sin clima» (se reporta).
- Deriva en el roll (15/09): se reporta además el resultado sin las sesiones posteriores al roll (sensibilidad).

## 3. Evento, resultado y referencia
- Mismo evento que ESPEJO-REV parte A: completación del espejo (niveles 3/4/5 del visor en 100t) y luego primer cierre
  del lado de B. O = alejamiento más allá de A antes del cruce.
- Resultado: llega al 25 % del camino hacia B antes de un extremo nuevo más allá de A; horizonte 150 velas o fin de sesión.
- **Referencia principal: control empírico emparejado** (lección LES-NULL-BIAS-BY-TP): 3 velas de OTRAS sesiones del
  mismo conjunto, misma franja ±30 min y mismo tercil de volatilidad previa, misma geometría relativa al cierre
  (objetivo y extremo de falla trasladados). Diferencia pareada evento − media de controles; bootstrap por sesión.
- `simulate_null` sólo como diagnóstico publicado.
- Tope: 300 eventos por sesión y nivel (balanceado), sin tope global.

## 4. Pruebas
**Primarias:** 3 niveles × 4 climas = **12 celdas** (x = 25 %), max-T sobre las 12. **Secundarias (descriptivas):**
x = 50 %, 75 %, 100 %; global sin clima; overshoot en terciles; sin sesiones post-roll.
Se publica el landscape completo, los n por clima y los eventos «sin clima» / «sin soporte de control».

## 5. Riesgos
- 40 sesiones: por clima, los menos frecuentes (volatile, toxic) pueden quedar sin potencia; se publica el MDE.
- NT8 vs Lucid: el efecto original salió de Lucid; un nulo acá puede ser proveedor, período o clima.
- Deriva de climas en el roll.
- El efecto original es chico (+2–4,6 pp) y se apaga hacia el 75 %: aun si sobrevive, su uso operable exige objetivos
  cortos, donde la ejecución tick a tick degrada (lección LES-BAR-FILL-OPTIMISM).

## 6. Enmienda v2 (2026-09-29, antes de correr nada) — respuesta a la Entrada 067 del auditor
Nada de esto se decidió mirando outcomes: el runner no se ejecutó nunca. Cambios, en orden de la 067:
1. **Procedencia (067 §1).** `entry.py` hace preflight y falla salvo: `CODE_COMMIT.txt` = commit esperado, sha256 de los 5
   archivos que deciden el resultado, sha256 de los **10** archivos del dataset privado que el notebook o el runner leen (manifiesto embebido; el README no se hashea: no se lee) — corregido de «11» por la Entrada 069 §3, fin del catálogo
   ≤ `HOLDOUT_NS` y `tbz_e2.HOLDOUT_NS` idéntico (ya no se sobreescribe: vale lo mismo). Publica `preflight.json`.
2. **Reloj (067 §2).** La conversión ART→UTC queda versionada en `tools/l2_labels_utc.py` (una sola vez, sobre
   `feature_available_at_us`, enteros, falla ante doble conversión); reproduce **exactamente** el parquet subido (83.421 filas,
   todas las columnas iguales). Las velas guardan `t_ns` entero y el evento usa ese tiempo, no segundos float.
   Regla: la fila con mayor `available_utc_us` ≤ t debe ser válida por sí misma (elegible, as-of ok) y tener edad ≤ 120 s;
   si no, «sin clima» (no se salta a una fila válida anterior).
3. **Control del mismo clima (067 §3) — primaria.** Cada vela candidata de control recibe clima con la misma regla; el control
   primario exige mismo clima + franja ±30 min + tercil de volatilidad + otra sesión. Sin 3 controles así: «sin control del
   mismo clima» (se reporta). El control sin condición de clima queda como **secundario** (otra pregunta).
4. **Potencia (067 §4).** Celda evaluable sólo con **≥ 30 eventos y ≥ 8 sesiones distintas**; si no, «inconclusa por potencia»,
   fuera de la familia max-T. Se publican n_eventos, n_sesiones, n_controles, MDE y soporte de control por clima.
   No se fusionan climas ni se cambia la regla después.
5. **max-T conjunto (067 §5A).** Pesos multinomiales comunes sobre las 40 sesiones de evaluación por réplica, aplicados a la
   sesión del evento y a la sesión fuente de cada control; mismo vector para todas las celdas de la familia.
6. **Sesiones (067 §5B).** Universo = las 40 `eval_ids` congeladas del plan del modelo (sha256 de la lista ordenada
   `f59aee57…3958`), no las que tienen etiquetas válidas; sesiones sin velas o sin etiquetas se cuentan.
7. **Volatilidad (067 §5C).** Congelada: RMS de los cambios firmados de cierre 100t en las 20 velas previas. Se publica el
   acuerdo de terciles con la definición v1 (std de |Δ|), sólo descriptivo.

Fixtures sintéticos (sin outcomes): `tests/test_nq_cruce25_clima_design.py` — ida y vuelta de reloj y doble conversión, frontera
de disponibilidad, edad, fila inelegible, control del mismo clima y sin soporte, volatilidad firmada, bootstrap conjunto,
hash de sesiones y frontera del holdout.

## 7. Enmienda v3 (2026-09-29, antes de correr nada) — respuesta a la Entrada 069
1. **Script ejecutado (069 §1).** Un script no puede contener su propio hash, y `kaggle kernels push` lanza la corrida al
   subir, así que no hay pull previo posible. Protocolo congelado: (a) antes del push, `git hash-object`/sha256 del
   `entry.py` local = blob del commit declarado en la entrada de lanzamiento; (b) el preflight calcula el sha256 del archivo
   que efectivamente se ejecuta (`__file__`) y lo escribe en `preflight.json` (sin archivo legible, aborta); (c) después de
   la corrida, `kaggle kernels pull` de esa versión y comparación con el mismo blob. **Se lee `preflight.json` ANTES que
   `nq_cruce25_clima.json`; si (a), (b) o (c) no coinciden con el blob, el resultado se descarta sin interpretarlo** y se
   documenta. Prueba de sabotaje local: cambiar un byte de un archivo de código o de datos hace fallar el preflight.
2. **Objetivo respecto del cierre de señal (069 §2).** Pregunta congelada: la (b) del auditor — **operación ejecutable al
   cierre de `j`**. Entrada = cierre de `j`; barreras desde `j+1`; si `C[j]` ya está en o más allá del objetivo, el evento
   se clasifica «objetivo ya alcanzado al cierre», no hay operación, se excluye de esa x y se cuenta por celda
   (`ya_alcanzado_al_cierre`). Una mecha de `j` que toca el objetivo con cierre antes no cuenta. El control usa la misma
   regla con la geometría trasladada al cierre (su objetivo siempre queda del lado correcto, así que nunca se excluye).
   Fixtures: cierre de `j` ya pasado, sólo mecha de `j`, toque posterior. Se eligió (b) porque es la única operable; (a) y (c)
   no se corren.

## 8. Enmienda v4 (2026-09-29, antes de correr nada) — respuesta a la Entrada 071
1. **Soporte por clima.** Cada celda primaria publica su reconciliación: `senales` = `evaluables` + `ya_alcanzado_al_cierre` +
   `sin_control_mismo_clima`, con las sesiones sin control y un flag `cierra`. Las «sin clima» se publican por nivel (no
   tienen clima). La lista de señales sin control queda en el JSON (`detalle[nivel].sin_control`). Nada se imputa. Fixture:
   `test_reconciliacion_soporte_por_clima`.
2. **Alcance.** Es un **estudio de barreras desde el cierre de señal**. No prueba una entrada ejecutable ni rentabilidad; el
   JSON lo etiqueta así en cada celda. Una afirmación de trading exigiría una prueba aparte: entrada en la primera cotización
   ejecutable posterior, con costos y latencia NQ fijados de antemano.
