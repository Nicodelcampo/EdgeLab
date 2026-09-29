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
