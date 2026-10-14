# Próxima prueba de desarrollo: retorno AVZ25 denso × BigTrap2 tick200 en GC

## Congelado antes de nuevos resultados
La pista fue elegida **después de inspeccionar** la campaña anterior: 4.308 anclas / 12 sesiones, llegada frente a control mejor en 10/12 sesiones. No es una selección ciega ni una confirmación. En el modelo completo la densidad sola ya explicaba casi toda la mejora: solamente 1/18 pares completos superaba densidad. Por eso no se agregan miles de configuraciones antes de comprobar si esta pista se sostiene.

- GC_12-26, tick 0,1; mismas versiones, fuente y parámetros nativos publicados.
- Solo AVOLZONEPOI2 tick25 denso y BigTrap2 tick200 (par SHA `fc63696a0c15f4c0e9aad9987e360da0502eb5870f54ef02fbc024e2ddf752ec`). Dos perfiles, un par, diez representaciones con los controles originales.
- Misma calibración sin resultados del 31 de julio y mismas seis sesiones de entrenamiento del 3–10 de agosto. Historia AVZ20 sesiones y todo el prefijo nativo conservados.
- Diez fechas pedidas: 27–28 y 31 de agosto, 1–4 y 7–9 de septiembre. Esta campaña no había evaluado sus resultados. No se afirma que ningún otro agente las haya visto.
- 28 de agosto ya figura vacío en el manifiesto; 7 de septiembre es feriado. Ambos quedan en el calendario: sin sustituciones ni exclusiones guiadas por resultados. Mínimo seis sesiones evaluables; soporte del corte se informa aparte.
- Hueco observable máximo explícito de 10s tanto en ventanas previas como respuesta: no equivale a trayectoria continua ni ejecución de órdenes.

## Pregunta principal y medidas
Corte principal fijo `INSIDE_BOTH_AND_BOTH_RETURN`: ambas exposiciones presentes, precio dentro de ambas y retorno observado tras salir de cada exposición actual más cercana. No se presenta como primer toque físico ni episodio identificado por zona.

Se exportan exclusivamente agregados por sesión y del complemento NO RETURN, positivos y negativos: llegada frente a base continua, control de igual capacidad y densidad; completo frente a base, densidad y espejo. Se separan media por sesión y promedio ponderado por anclas. Intervalo bootstrap descriptivo de medias por sesión (2.000 remuestreos, semilla19413), no inferencia confirmatoria. Sensibilidad temporal: primera ancla común y siguientes separadas al menos60s **antes de aplicar el corte**; no garantiza independencia ni identidad de episodios.

Los 17 cortes anteriores se conservan para diagnóstico, no para reemplazar al primario si falla. Soporte2000 anclas/6 sesiones no es validación de edge. Holdout desde1 de octubre cerrado; sin P&L, ganadores automáticos ni escritura canónica del cerebro.

## Optimización medida, no prometida
La corrida científica omite siete perfiles y17 pares irrelevantes, sin recortar historia o controles del par elegido. Prueba sintética exige tensor del par exactamente igual a la grilla original.

Segundo job separado: tres BigTrap2Absorption nativos sobre **la misma sesión GC del3 de agosto**, estados iniciales nuevos en cada pase y mínimos nativos intactos. Orden ABBA: procesamiento perfil-secuencial en bloques100k vs intercalado en bloques1k. Compara SHA de capturas, logs nativos, tamaños de estado, conteos y residuos EOF. Solo si todo coincide se calcula aceleración del subpaso. No certifica NT8, calentamiento multis sesión ni velocidad de todo el pipeline; no modifica automáticamente el runner de producción.

## Custodia y presupuesto
Dos nuevas intenciones explícitas, máximo dos jobs pendientes y seis consultas de estado por job. Journals nuevos vinculados al plan nuevo; journals anteriores se conservan terminales y nunca se reinician. Antes de enviar se guarda intención SEND_STARTED y checkpoint público. ACK solamente tras comparar fuente remota, versión, privacidad CPU y Docker. Ante envío ambiguo no reenviar; ante fallo registrar y no cambiar umbrales automáticamente.
