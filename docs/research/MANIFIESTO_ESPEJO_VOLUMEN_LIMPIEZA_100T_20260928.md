# Manifiesto ESPEJO-VOLLIMP-100T: ¿la vuelta con más volumen y menos limpia que la ida completa distinto? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PRE-REGISTRO. Mira desenlaces: **STOP hasta el OK de Nico.** Nada corrido.
**Familia:** ESPEJO-IND, sub-familia nueva con presupuesto de multiplicidad propio. Mismo objeto, evento, resultado y nulo que
ESPEJO-NICO-100T (`MANIFIESTO_ESPEJO_SEMEJANZA_NICO_100T_20260928.md` + enmienda N1); cambia sólo el rasgo que ordena.

## 1. Hipótesis, justificación y refutación
- **Hipótesis (Nico, 28/09):** la probabilidad de completar el espejo, en exceso sobre el nulo, difiere cuando la vuelta
  lleva **más volumen por tick** que la ida y/o es **menos limpia** (menos derecha) que la ida. Sin dirección declarada:
  pruebas bilaterales.
- **Justificación económica:** una ida limpia y con poco volumen es un recorrido sin aceptación. Una vuelta que trae más
  volumen y avanza a los tirones indica que alguien está absorbiendo o repartiendo en el camino de vuelta, lo que cambia la
  chance de que el precio termine de deshacer la ida.
- **Cómo podría refutarse:** el exceso sobre p0 no difiere entre terciles alto y bajo de cada rasgo (IC que cruza cero en
  todas las celdas), o la diferencia desaparece al controlar por la velocidad de la vuelta (sería momentum).

## 2. Rasgos (causales: sólo velas hasta la del evento)
- **R-VOL:** (volumen de la vuelta / ticks recorridos por la vuelta) ÷ (volumen de la ida / W).
- **R-LIMP:** eficiencia de la vuelta ÷ eficiencia de la ida; eficiencia = avance neto / camino recorrido por cierres.
  Menor = vuelta más sucia que la ida.
- **R-VL (conjunción):** R-VOL en el tercil alto **y** R-LIMP en el tercil bajo, contra el resto (el volumen y la
  suciedad están del lado de la **vuelta**).
- **R-VL-INV (conjunción invertida, Nico 28/09):** R-VOL en el tercil bajo **y** R-LIMP en el tercil alto, contra el resto
  (el volumen y la suciedad están del lado de la **ida**; la vuelta vuelve limpia y liviana).
- R-VOL se reporta con sus dos extremos por separado: vuelta con más volumen que la ida (R-VOL > 1) e ida con más volumen
  que la vuelta (R-VOL < 1), además del contraste de terciles.
- Terciles fijados por x sobre todo el descubrimiento, sólo con el rasgo, sin mirar resultados.

## 3. Alturas («a qué altura»)
x ∈ {0,25; 0,50; 0,75}: primer cierre de vela 100t en que la vuelta recorrió x de W sin extremo nuevo más allá de B.
0,25 es nueva respecto de ESPEJO-NICO (señal más temprana, menos información).

## 4. Pruebas primarias
| Rasgo | Contraste | Celdas |
|---|---|---|
| R-VOL | exceso(tercil alto) − exceso(tercil bajo) | 3 x × 2 estratos = 6 |
| R-LIMP | exceso(tercil bajo) − exceso(tercil alto) | 6 |
| R-VL | exceso(conjunción) − exceso(resto) | 6 |
| R-VL-INV | exceso(conjunción invertida) − exceso(resto) | 6 |

**24 pruebas**, BH q = 0,10, bilaterales. Exceso = completa − p0 (nulo N1, todos los eventos, censura aparte). Bootstrap
por sesión (1.000); se publican MDE, n por celda, distribución completa y los dos canales (completa; excursión máxima en W).
Descriptivo no contado: control por velocidad de la vuelta (terciles de duración), trade frente a midquote.

## 5. Datos y particiones — riesgo principal declarado
- **Descubrimiento:** ES, Lucid, jul-2025 → mar-2026 (181 sesiones, las mismas de ESPEJO-NICO-100T). **Estos datos ya se
  miraron** para el rasgo de semejanza: la idea nace después de ver ese negativo. Por eso ningún resultado de esta etapa se
  promueve solo.
- **Confirmación (una sola vez, sólo celdas sobrevivientes):** ES abr–jun 2026, **Lucid** (no se mezcla con NT8).
  Es la parte Lucid de la replicación A3 que ESPEJO-NICO no llegó a abrir.
- **Holdout:** oct-2026 en adelante, intacto.

## 6. Economía
Mismo umbral que ESPEJO-NICO: con W mediano ≈ 39 t y fricción ES ≈ 2,5 t, hace falta ≈ 6,4 puntos de exceso sobre p0 en la
geometría «entrada en x, objetivo A, stop más allá de B». Una diferencia entre terciles menor que eso es información, no sistema.

## 7. Riesgos
- Potencia: en ESPEJO-NICO el MDE por celda fue 0,07–0,16; con terciles y 24 celdas (las conjunciones tienen ~1/9 de
  los eventos cada una: son las celdas con menos potencia) se espera similar. x = 0,25 suma eventos.
- R-VOL depende del volumen de trade de Lucid; el de NT8 difiere en ticks sueltos (paridad 054): la confirmación usa Lucid.
- R-LIMP y la velocidad están correlacionadas: por eso el control por velocidad va como descriptivo obligatorio.

## 8. Costo
Mismo runner (`tools/espejo_nico_descubrimiento.py` con los rasgos nuevos), minutos de cómputo.
