# IDEA (Nico, 25/09): la zona de volumen del extremo del impulso predice lo que sigue — PENDIENTE, sin medir

**Estado:** IDEA REGISTRADA. No es hipótesis congelada ni manifiesto. Próximo paso: **Nico la revisa en el visor** para fijar cómo interpretarla. No correr nada sobre retornos sin manifiesto y OK (regla STOP).
**Aprendizaje heredado de TBZX (muerto el 25/09):** todo nulo tiene que emparejar a la vez **actividad del mercado y estado de reversión** (N-REVVOL); el estiramiento vs medias no es propio de la zona.

## Lo que Nico observa (capturas del 25/09)
Después de un impulso A→B, el precio se queda un rato **cerca del extremo B** y negocia volumen ahí: un «POC del extremo», un rango chico con acumulación. Según **qué pasa adentro** de esa zona, lo siguiente cambia:
- a veces **sale en V** (el extremo de volumen es rechazado y el precio vuelve con fuerza);
- a veces el precio **vuelve más tarde a ese nivel de volumen y lo usa como techo o piso** (capturas 2–4: líneas en el borde del rango de volumen, «Vol»);
- a veces hay un rango lateral largo antes de decidir (caso marcado con «?»).
Suele pasar muchas veces en ciertas franjas horarias (captura: ES 28/01/2026, 11:00–14:30 hora local).

## Traducción a lenguaje aplicable
**Objeto:** la **zona de volumen del extremo (ZVE)**: rango de precios donde se negoció el volumen desde que se tocó B hasta que el precio se aleja de ahí (definición exacta a elegir en el visor).

**Lo que se mide DENTRO de la ZVE (sólo pasado, as-of):**
1. **tiempo** en la zona (velas y segundos);
2. **volumen** negociado, y relativo al volumen del impulso;
3. **distancia** de la zona respecto de B y **penetración** hacia A (fracción de W);
4. **lado del agresor** dentro del volumen (delta, compras vs ventas) — Nico la marca como «buenísima». **Ojo:** el agresor de research-v2 es válido en NQ (99 %) y **no en ES** (80 %, P-93). Usar NQ o L2 de NT8;
5. **velocidad y agresividad** de la entrada a la zona y de la salida;
6. **absorción e icebergs** (L2, detectores provisionales del visor);
7. **forma**: POC de la zona, anchura, si el POC está en el borde o en el centro.

**Lo que se quiere predecir (después de la ZVE):**
- **V:** salida rápida alejándose de la zona (reversión desde el extremo);
- **nivel respetado:** el precio vuelve más tarde a la zona y rebota en ella (techo o piso);
- **continuación:** atraviesa la zona y sigue en la dirección del impulso;
- **rango:** se queda lateral.

**Pregunta central de Nico:** ¿hay una configuración de la ZVE (alguna combinación de 1–7) que cambie por sí sola la probabilidad de V, de nivel respetado o de continuación? ¿Hay un **nivel de penetración** en el volumen que marque el punto de devolución en V?

## Nulos obligatorios (aprendidos)
- Otra sesión, misma hora, **misma actividad y mismo estado** (tramo que recién dio la vuelta): N-REVVOL.
- Separar evento de estado: la ZVE como **evento** (cuando se forma) y como **estado** (el precio está adentro).
- Todo nulo publica su MDE; efecto en canal direccional y no direccional.

## Pendiente para la próxima sesión
1. Nico, en el visor, decide la definición de la ZVE: desde cuándo, hasta cuándo, ancho, y cómo se ve «V» vs «nivel respetado».
2. Agregar al visor la capa de la ZVE con perfil de volumen y delta por nivel.
3. Recién ahí: manifiesto con event-space enumerado (creación, primer toque, toque n-ésimo, estado), nulos, presupuesto y STOP.

## Precisión de Nico (25/09): el resultado buscado es un BARRIDO en V
Lo que interesa no es cualquier V, sino una **V que barre las órdenes del rango**:
1. el precio sale de la zona de volumen del extremo **en la dirección del impulso original** (intenta continuar);
2. **atraviesa** el rango de volumen y lo supera (toma los stops y las órdenes que quedaron de ese lado);
3. **se invierte enseguida** hacia el otro lado (el intento de continuación falla).

En lenguaje aplicable es un **barrido con falla de continuación**: ruptura del borde de la zona de volumen en el sentido del impulso, seguida de un regreso rápido adentro y más allá del otro borde. A definir en el visor:
- cuántos ticks más allá del borde cuentan como barrido;
- en cuánto tiempo o cuántas velas tiene que volver para que sea «automático»;
- hasta dónde tiene que llegar la inversión para contar (el otro borde, el POC, A).

Lecturas candidatas dentro del barrido: volumen y delta **durante** la ruptura (¿agresores que quedan atrapados?), absorción en el extremo del barrido y velocidad del regreso. Es complejo: queda registrado, sin medir.

## Corrección de Nico (25/09): son PARÁMETROS, no definiciones a fijar a ojo
Lo de «cuántos ticks cuentan como barrido», «en cuánto tiempo vuelve» y «hasta dónde se invierte» no se decide en el visor como un número único: son **parámetros** del detector. Se exponen como controles deslizantes (igual que el diseñador de expansiones) y después se barren como grilla pre-registrada, con el paisaje completo publicado y la multiplicidad contada. Parámetros iniciales del barrido:
- `sweep_ticks`: penetración más allá del borde de la zona de volumen;
- `sweep_max_bars` / `sweep_max_s`: tiempo máximo del regreso para que sea «automático»;
- `reversal_target`: hasta dónde llega la inversión (otro borde de la zona, POC, A, o fracción de W);
- definición de la zona: inicio, fin, ancho y bins del perfil;
- lecturas en la ruptura (delta, volumen relativo, absorción, velocidad), como descriptores y no como filtros elegidos a mano.
En el visor, Nico elige qué rangos tiene sentido explorar; la medición barre esos rangos, no un valor elegido.
