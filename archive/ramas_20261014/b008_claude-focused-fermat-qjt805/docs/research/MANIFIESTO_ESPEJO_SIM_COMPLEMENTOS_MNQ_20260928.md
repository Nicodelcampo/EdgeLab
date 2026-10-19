# Manifiesto ESPEJO-SIM-COMP: ¿la semejanza replicada en MNQ gana tamaño complementada? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`

**Estado:** PRE-REGISTRO, escrito antes de mirar cualquier cruce.
- Nico pidió escribirlo el 28/09: «dale, pre-registralo después de PIVOTES-BARRIDO».
- **Orden:** se corre **después** de que se publique el resultado de `MANIFIESTO_PIVOTES_BARRIDO_MES_20260928.md`.
- **Es búsqueda sobre resultados: STOP hasta el OK de Nico para correrlo** (manifiesto + número efectivo de hipótesis +
  riesgos + datos faltantes, abajo).

**Familia:** ESPEJO-SIM, subfamilia **COMP**, con presupuesto de multiplicidad propio.
- No hereda el FDR de ESPEJO-SIM ni el de ESPEJO-NICO.
- Reusa sólo código y definiciones: el kernel `EspejoImpulsos` y el nulo N1.

## 1. Pregunta, justificación y refutación

**Hipótesis (Nico, 28/09).** La semejanza de la vuelta con el impulso tiene un efecto chico pero replicado en MNQ:
+2 a +5 pp, 43 de 52 pruebas, con el contraste parecidas − poco parecidas, que no depende del nulo. Ese efecto
promedia contextos donde actúa fuerte con contextos donde no actúa o actúa al revés. Complementada con el contexto
correcto, gana tamaño. Es el aviso de Nico sobre efectos que se anulan.

**Justificación económica.** Una vuelta parecida al impulso indica un participante del otro lado de tamaño
comparable. Tiene sentido que eso pese más:
- cuando el impulso fue forzado (ineficiente, la tesis original);
- cuando el precio ya negoció en otra área antes de volver (aceptación en B, el encuadre de la «zona no lista»);
- según vaya a favor o en contra de la tendencia de fondo.

Sólo un efecto más grande tiene chance de pagar la fricción. En MNQ a 17–24 t, costo/W ≈ 14 pp.

**Cómo podría refutarse:**
- ningún cruce supera la corrección; o
- los cruces que pasan no replican en los dos contratos; o
- el efecto dentro de cada estrato no es mayor que el agregado (no hay concentración).

Si eso pasa, la semejanza queda como la vimos: real, chica y sin complemento conocido.

## 2. Población (regla de población)

**Eventos enumerados:**
- confirmación del impulso;
- cruce de x ∈ {0,25; 0,50; 0,75};
- completado;
- fracaso;
- vencimiento;
- estado continuo.

**Se congela el cruce de x ∈ {0,50; 0,75}.** Son las alturas donde la semejanza tiene tramo suficiente y donde
ESPEJO-SIM replicó. x = 0,25 queda afuera porque el 91 % de las vueltas dura ≤ 2 velas (diagnóstico §7 del registro
ESPEJO-IND).

**Detector:** kernel `EspejoImpulsos` en velas de 25 ticks, con W ≥ 17 t, ≤ 20 velas, e_min = 0,3 y r = 0,3.
- Es la configuración que Nico congeló para 25t.
- Incluye impulsos **eficientes e ineficientes**. TBZX exigía eficiencia ≥ 0,6, y por eso el cruce C1 nunca se pudo
  medir.

**Cómo podría refutarse la población:** si con e_min = 0,3 la semejanza deja de replicar incluso en el estrato
eficiente. En ese caso el cambio de detector, y no el cruce, explica cualquier diferencia. Por eso C1 reporta el
estrato eficiente como control.

## 3. Resultado y nulo

**Resultado:** el precio completa el espejo (toca A antes de un extremo nuevo más allá de B). El horizonte es
3 × la duración del impulso, con tope en el fin de la sesión. Es el mismo resultado del kernel.

**Exceso por evento:** `completa_i − p0_i`, con `p0` del nulo simulado N1.
- Lo calcula `edgelab/research/espejo_nulo.py::simulate_null`, en la rama `foundation`.
- Usa velas de 25t anteriores al evento, las mismas barreras y horizonte, y toque por mecha.
- Se promedia sobre **todos** los eventos; la censura se publica aparte.

**Contraste base:** exceso del tercil alto de semejanza − exceso del tercil bajo, dentro de cada estrato.
- Al restar dos excesos, el sesgo del nulo que comparten se cancela.
- Precio de trade, que es lo que hay en caché para MNQ. Se publica también sobre midquote si existe.

## 4. Pruebas primarias (10) — número efectivo de hipótesis: 10

Para todas las pruebas:
- Los terciles de semejanza se fijan por x sobre el descubrimiento, sólo con el rasgo, sin mirar desenlaces.
- Las medianas de los condicionantes se fijan igual.

| Código | Cruce | Contraste | x | Pruebas |
|---|---|---|---|---|
| C1a | Semejanza × eficiencia | T3 − T1 de S (v1) en impulsos **ineficientes** (0,3 ≤ e < 0,6) | 0,50 / 0,75 | 2 |
| C1b | Semejanza × eficiencia | interacción: (T3 − T1)ineficiente − (T3 − T1)eficiente | 0,50 / 0,75 | 2 |
| C2 | Semejanza × aceptación en B | interacción: (T3 − T1) con `aceptacion_B` ≥ mediana − (T3 − T1) con < mediana | 0,50 / 0,75 | 2 |
| C3 | Semejanza × dirección | interacción: (T3 − T1) a favor − en contra de la pendiente de la media de 60 min | 0,50 / 0,75 | 2 |
| C4 | Semejanza v2 por nivel | T3 − T1 de `sim_abs` (v2) sobre todos los eventos | 0,50 / 0,75 | 2 |

**Qué se reporta en cada celda:**
- las dos direcciones del efecto (T3 − T1 y T1 − T3);
- la distribución completa de la excursión hacia A y hacia B;
- el MDE;
- n por celda: con n < 30 no se prueba y se publica igual.

**Estadística:** bootstrap por sesión (1.000), p bilateral y **BH q = 0,10 sobre las 10**.

## 5. Datos y particiones

- **Descubrimiento:** MNQ 09-25, Lucid, 25t.
- **Replicación:** MNQ 12-25 y 03-26, Lucid, recortado al 2026-04-01.
  - **Ya se usaron para replicar el efecto principal de ESPEJO-SIM.**
  - **Ninguno de estos cruces se miró sobre ellos.**
  - Se deja anotado; por eso se agrega una tercera muestra.
- **Tercera muestra, confirmatoria:** NQ 25t Lucid del mismo período, sólo para las celdas sostenidas. Si no hubiera
  NQ 25t Lucid disponible, se usa MES NT8 y se etiqueta como tal, sin mezclar proveedores.
- **Sostenido:**
  1. pasa BH en el descubrimiento;
  2. tiene el mismo signo con IC 95 % > 0 en MNQ 12-25 **y** 03-26;
  3. tiene el mismo signo en la tercera muestra.
- Holdout (oct+) y la confirmación abr–jun intactos. abr–jun se abre una sola vez y sólo para lo que sostenga.

## 6. Qué habilita y qué no

**Si algo sostiene:**
- Hace falta un pre-registro económico **aparte**, que lleve la señal a una escala donde costo/W sea chico: la
  semejanza como filtro dentro del evento macro o de impulsos mayores.
- Nada de esta corrida es P&L.

**Si nada sostiene:**
- La semejanza MNQ queda «real, chica y sin complemento conocido».
- **No** se abren más cruces sin un mecanismo nuevo escrito. El presupuesto de esta subfamilia se da por gastado.

## 7. Riesgos y datos faltantes

**Riesgos:**
- **Potencia:** cada interacción usa alrededor de un sexto de los eventos por celda. Se espera un MDE de 8–12 pp.
  Un efecto menor no se verá, y eso se publica.
- **Cambio de detector** (e_min 0,3 contra 0,6). Se controla con el estrato eficiente de C1b.
- **Replicación sobre contratos ya vistos** para el efecto principal: por eso está la tercera muestra.
- **Precio de trade** en MNQ, con el rebote bid/ask que ya mató IPC 25t. El contraste T3 − T1 lo comparte y en parte
  lo cancela. Si hay midquote, se reporta.

**Datos faltantes:**
- confirmar que exista NQ o MES 25t Lucid para la tercera muestra;
- traer `espejo_nulo.py` de `foundation` a la rama donde se corra;
- el kernel ya está en `edgelab/bridge/indicators/espejo_impulsos.py`.
