# GC presión local — C2 y espejo50%, preparación antes de nueva medición

Solicitud: continuar presión cerca del precio; escalonadas con al menos4 zonas
por día. Se selecciona C2 EXACT4_DENSAS existente, no se ajusta por retorno.
Cuatro miembros disjuntos; w1,gap23,step49,pull19,confirmaciónprecio28ticks;
dmax1M,totalMin0,stepMin0. No reemplazar el perfil en el visor ni barrer una grilla.

## Frecuencia: criterio y excepción visible

Umbral solicitado=4 por ID de sesión. Recontar C2 de todo el censo privado
febrero, incluyendo IDs con cero del reporte (no inferir población sólo de los
eventos), y conservar excepciones. GCfeb es sólo evidencia geométrica, sin L2/
publicación. May31 es una captura parcial con L2, no varias sesiones ni garantía
de cuatro en cada día futuro. No mezclar frecuencia mensual con cobertura L2.
La completitud/calendario de cada sesión debe certificarse antes de un gate
operativo de densidad; cero no se elimina por ser cero ni se atribuye a falta
de datos sin evidencia. Si no pasa, registrar FAIL/UNKNOWN, no fabricar señales.

## Panel de presión, sin labels futuros

Fuentes ya verificadas: eventosL2 May31, receipts de TODOS los intentos de espejo,
L1 raw del mismo feed. Sólo C2 y cruces50% prospectivos existentes; preservar
exclusiones/tardíos y receipts. No cambiar detectorA/B, porcentaje o horizonte.
Features primarias: QI_touch orientado al evento y OFI endpoint10s normalizado
por profundidadtouch y orientado. No sumar un score, no microprice duplicado.

Gate de investigación propuesto y fijado antes del nuevo conteo: snapshot
con publicación estrictamente previa y edad≤1.000ms, integridadPASS,
ventana10s completa y features finitas. Es un criterio conservador candidato,
NO umbral óptimo/latencia garantizada. No relajarlo para llegar a4; reportar
frecuencia bruta y soporteL2 elegible por separado. Mantener filas excluidas.

Adjuntar baseline histórico: movimiento neto y recorrido absoluto de precio
en10s, volumen/prints en10s, spread y distancia al nivel conocido. Sólo trades
con fila≤decisión y timestamp≤decisión; no destinos. La clasificación por signos
(ambas a favor/ambas en contra/divergentes/alguna neutral) es descriptiva,
no entrada/veto ni predicción. No elegir thresholds usando resultados.

Pruebas: igualdadtiempo y futuroraw excluidos; null nozero; staleness1000ms;
ventanaincompleta; signos y orientaciones; preciohistórico sinfila futura.
QA independiente de baseline y conteos. Datasets/precios/eventos privados.

## STOP

No y_true, accuracy, llegadasposteriores aA, TP/SL, estimador/P&L o costos.
Para predicción faltan más sesiones certificadas, manifiesto completo y OK.
Frecuencia≥4 no implica4 casosL2 usables ni potencia independiente.
GCJun15ABSTAIN y holdout siguen intactos.