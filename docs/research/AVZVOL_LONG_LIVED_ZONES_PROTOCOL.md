# Zonas longevas y revisitas: extensión exploratoria pendiente

Estado: hipótesis propuesta por el usuario durante la réplica fija. Este protocolo NO constituye resultados ni modifica las reglas de la réplica en ejecución. No es una prueba virgen sellada: ya existen investigaciones sobre este universo.

## Dos conceptos diferentes
- Ventana del racimo: retrospectiva usada para reunir zonas; probar por separado 1000, 2000 y 3000 barras.
- Antigüedad: barras desde el nacimiento observable de una zona/racimo de límites congelados. Antigüedad no demuestra que el mercado continúe interesado.

La unidad de barras de esta campaña es una barra causal cerrada de 25 registros Last ordenados por sequence; no equivale a 25 cambios de precio ni a una duración de reloj constante. Mostrar también tiempo transcurrido y sesiones.

## Hipótesis primaria de la nueva extensión
A igual antigüedad, distancia restante y contexto observado, las revisitas independientes y el volumen transado en la zona podrían modificar la probabilidad de retorno/cruce antes de una barrera opuesta equidistante. Examinar también rechazo/continuación; no asumir de antemano que mayor interés implica atracción.

## Diseño causal y frecuencia
- Congelar límites e identidad al nacimiento; no actualizar retrospectivamente una zona con volumen futuro.
- Tratar 2000 y 3000 barras como landmarks observables. Incluir TODAS las zonas que alcanzan cada landmark dentro del segmento autorizado, tengan o no revisitas. Las que no llegan por corte del segmento quedan explícitamente censuradas, no fallidas.
- No seleccionar zonas por su duración final, por futuros retornos o por un máximo futuro de excursión. Registrar estadísticas en el instante de cada señal.
- Edades predeclaradas: 0–249, 250–499, 500–999, 1000–1999, 2000–2999, 3000–4999 y 5000+ barras. Las bandas vecinas son sensibilidades, no rescate del mejor resultado.
- Revisita: nueva entrada a límites congelados tras salir. Sensibilidades de separación: una barra cerrada fuera, cinco barras fuera y separación de reloj; un tick repetido dentro no es una nueva visita.
- Medir visitas previas, volumen dentro/volumen total previo, duración de visitas, recencia, distancia máxima observada hasta la señal, velocidad y relación velocidad regreso/salida. Distinguir volumen total de flujo agresor: imbalance solo si una fuente auditada lo identifica; no inventarlo desde OHLC o dirección del Last.
- Deduplicar identidades superpuestas mediante regla congelada de solapamiento; publicar la sensibilidad a esa regla. Separar señales totales de episodios efectivos por zona y sesión; múltiples zonas pueden representar el mismo movimiento.

## Resultados y controles
- Mantener causal la secuencia salida → excursión mínima D → regreso q → carrera posterior. Comparar tocar borde, centro y cruzar el extremo opuesto como endpoints separados.
- Barrera contraria equidistante desde el precio observado de activación; no declarar ventaja por tasa de toque alta sin comparar geometría y contexto.
- Usar referencias de precio de igual antigüedad y geometría, y controles estratificados por sesión, volatilidad, distancia y hora; admitir falta de soporte común cuando corresponda. Referencias de ancho fijo sin emparejar no son un nulo causal exacto.
- Separar persistencia intrasesión de arrastre entre sesiones/segmentos. No unir huecos o contratos ni crear eventos en fechas excluidas. El warmup no produce señales.
- Informar resueltos, no resueltos, oportunidades por sesión y efectividad del filtrado; CIs por bloques de sesión y sensibilidad a agrupación por zona. Corregir multiplicidad o marcar todos los hallazgos como exploratorios.
- Elegir parámetros solo en desarrollo, luego congelarlos para replicar en otros segmentos autorizados. No elegir la mejor celda y llamarla validada. Los seis contratos de la réplica actual no pasan a ser un holdout virgen.

## Orden de ejecución
1. Terminar la réplica fija actual sin cambios.
2. Auditar identidad, antigüedad y revisitas con tests sintéticos de prefijo/futuro y tapes pequeños.
3. Ejecutar censo de frecuencia para evitar filtros con eventos escasos; reportar ceros y pérdidas de soporte.
4. Medir efectos de revisitas y antigüedad separadamente; después sus interacciones y variantes de ventana. Esto es una campaña adicional, aún no corrida.

Sin certificación de fuente, ejecución financiera ni rentabilidad neta demostrada. No eliminar ni reexportar los originales.
