# MNQ y GC — escalonadas × L2: muestra observable y potencia

**Pedido de Nico (30/09/2026): muchas señales para potencia; sumar GC con adaptación propia.** Investigación target-free; NO permiso de outcomes. GC no sustituye MNQ ni hereda su configuración/costos. La configuración visual GC de Nico está por identificar/confirmar.

## 1. Tres denominadores, no uno

1. Zonas/señales geométricas por sesión y hora (H/L separado, bar size y confirmación publicados).
2. Señales con snapshot causal y nivel realmente observable (durante formación/último pico/al confirmar), edad del snapshot, causas de no observabilidad y fracción retenida por filtro.
3. Eventos independientes: quitar duplicados exactos, declarar solapamientos y zonas/episodios compartidos. Reportar concentración por día y clusters temporales; no tratar 1.000 señales correlacionadas como 1.000 observaciones independientes.

Una sesión MNQ: 31 detecciones, sólo 4 con nivel observable al confirmar, una true de filtro. No extrapolar tasa estable ni potencia de un día. Medir distribución por sesión (mediana/rango y días sin eventos), no sólo total agregado. Número de señales filtradas y del control importa, no sólo la población inicial.

## 2. Diagnóstico de soporte antes del barrido

V2 candidato observa el libro ya publicado antes/al trade del último extremo, el grupo de ese extremo cuando se publica, y el momento de confirmación. Son mediciones distintas, no filtros intercambiables. No se asigna causalmente una zona futura al instante del pico. El registro diagnóstico guarda la asociación conocida al detectar y permite estudiar una historia pasada accesible entonces.

Si el filtro en confirmación resulta demasiado escaso, comparar un conjunto PEQUEÑO y escrito de alternativas de observación/ventana por frecuencia, cobertura, duplicación y geometría humana, sin retornos. Sólo después congelar feature/evento y justificar muestra. No aflojar detector, cherry-pickear días o aumentar celdas para encontrar ganancia.

## 3. Gate de potencia para la fase financiera (por fijar con Nico)

- Definir estimando: mejora neta sobre baseline con los mismos costos/ejecución, unidad de análisis y mínima mejora económicamente útil delta en ticks/R.
- Fijar potencia objetivo 80 % y error familiar 5 %, pocas hipótesis; documentar corrección prevista (max-T u otra ratificada), reparto y evaluación única.
- El número mínimo NO se conoce sólo a partir de detecciones: depende de delta, variabilidad, dependencia por sesión, proporción retenida y controles. No inventar hoy un N universal.
- Con conteos target-free podemos estimar factibilidad/attrition, NO varianza de retornos. Usar varianza conservadora de una referencia ya autorizada y comparable si existe; de lo contrario reservar pilot de desarrollo para outcomes con manifiesto + OK, sin consumir confirmación ni elegir parámetros con su resultado.
- Calcular N de sesiones/clusters y MDE mediante simulación o resampling por sesión/episodio, preservando dependencia y múltiples pruebas. Un cálculo iid por trade sólo ilustrativo, nunca el gate final.
- GO sólo si la muestra reservada permite detectar delta con potencia pactada. Si no: MÁS sesiones/datos, reducir hipótesis ANTES de medir o declarar inconcluso. Aumentar actividad no justifica rebajar el mínimo económico.
- Controles emparejados por hora/actividad y volatilidad observada entonces, sin selección por desenlace. Publicar soporte de ambos brazos, censuras y MDE; no usar estados HMM STOP como filtro.

## 4. GC como línea propia, sin trasladar MNQ

Pendiente: recuperar configuración visual que Nico eligió (familia, bar size, ancho de pico, escalón, retroceso, número de picos, duración y confirmación). Un indicador visual con bastantes marcas es un candidato, no edge ni paridad demostrada.

Adaptar en ticks GC y escala de geometría/actividad propia, no copia mecánica de ES×12,42/MNQ ni de dólares por tick. Comparar inicialmente frecuencia y observabilidad con parámetros confirmados. Probar identidad detector↔visor y prefijos causales antes de medir utilidad. Spread, comisiones, slippage, profundidad visible y reseteos propios GC.

Disponibles en nube dos ejemplos L1/L2 GC propios para mecánica. El smoke 9.000 grupos/7 velas/0 señales usa parámetros MNQ sólo para ejercitar el pipeline: NO es adaptación GC ni muestra representativa. Se requieren varias sesiones para densidad/distribución y muchas más para potencia. No mezclar episodios publicados en investigaciones GC previas con confirmación nueva; declarar exposición anterior y reservar evaluación según protocolo.

## Entregables y reglas

Acta de primer MNQ y V2 diagnóstico separados del detector V1 congelado. GC registrado como PENDIENTE DE CONFIGURACIÓN Y QA. Nada de nuevas ganancias, TP/SL, MFE/MAE, fills ni exploración forward oct+. Si se cambia semántica, opt-in explícito; manifiesto + OK antes de cualquier outcome.

## Aporte al referente

Se exige muestra suficiente de señales observables repartidas entre sesiones, no sólo muchas marcas. MNQ y GC seguirán geometría→información→economía con costos y validación propios.
