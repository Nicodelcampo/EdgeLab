# AVZVOL: configuraciones con soporte y frecuencia primero

## Hallazgo medido
La ventana larga y el mínimo bajo ofrecen una base amplia para investigar. Entre las36configuraciones existentes, 4_1000_45 tiene el mayor conteo en cada uno de los6contratos. La alternativa estrecha 4_1000_20 conserva frecuencia sustancial: no hace falta descartar altura20ticks por falta de eventos. Esto elige poblaciones para investigar, NO una estrategia ni una ventaja predictiva.

## Comparadores prioritarios
Parámetros en orden: mínimo de zonas / ventana del racimo en barras / altura máxima en ticks. Primeras5configuraciones por conteo y comparador estrecho; no son categorías sumables.

| Configuración | Registros de formación | Por contrato-sesión representada | Sesiones con registros | Altura real mediana (ticks) |
|---|---:|---:|---:|---:|
| 4_1000_45 | 15,223 | 58.33 | 261/261 | 39 |
| 4_500_45 | 9,871 | 37.82 | 261/261 | 38 |
| 4_1000_30 | 9,836 | 37.69 | 260/261 | 26 |
| 5_1000_45 | 8,984 | 34.42 | 259/261 | 40 |
| 4_500_30 | 5,855 | 22.43 | 258/261 | 26 |
| 4_1000_20 | 4,919 | 18.85 | 255/261 | 18 |

Con mínimo4 y altura20, ampliar250→1000barras aumenta los registros1145→4919 (4.30×). La cobertura sube212/261→255/261contrato-sesiones. Ampliar la ventana aumenta los conteos en las12comparaciones que mantienen mínimo y altura; subir el mínimo los reduce en las9comparaciones que mantienen ventana y altura. Ampliar altura también aumenta conteos en las12comparaciones fijas de mínimo/ventana. No se extrapola monotonicidad a parámetros aún no probados.

## Frecuencia por contrato de los tres comparadores de ventana larga y mínimo4
Denominador: sesiones representadas en cualquier fila del export del contrato, incluyendo las sin registros de esa configuración. NO calendario completo ni frecuencia por hora.

| Contrato | Sesiones representadas | Altura20 | Altura30 | Altura45 |
|---|---:|---:|---:|---:|
| MNQ_09-25 | 29 | 16.90 | 33.45 | 47.45 |
| MNQ_12-25 | 62 | 16.03 | 31.03 | 47.03 |
| MNQ_03-26 | 57 | 15.14 | 30.79 | 50.98 |
| MNQ_06-26 | 57 | 15.88 | 34.09 | 55.56 |
| MNQ_09-26 | 46 | 29.30 | 58.11 | 88.78 |
| MNQ_12-26 | 10 | 31.90 | 57.10 | 77.40 |

Unidad de las3columnas de altura: registros por sesión representada. El nivel cambia considerablemente entre contratos; no llamar estable a la frecuencia absoluta. Los últimos contratos no son automáticamente réplicas independientes del mismo mercado.

## Qué NO conviene priorizar por frecuencia
8_250_20 contiene sólo1registro en el conjunto;8_250_30 contiene5 y8_500_20 contiene16. No perseguir porcentajes llamativos de esas muestras como candidatos principales. El ranking completo y todos los ceros por contrato se conservan en CSV.

## Campaña de cinco parámetros: propuesta, NO ejecutada
Los36exports sólo modificaron mínimo, ventana del racimo y altura. Percentil95 y window_bars10 permanecieron fijos. La configuración del ejemplo18/2000/20 tampoco está en este grid. No presentar los resultados anteriores como un barrido de5dimensiones.

La propuesta en campaign-proposed.json contiene1536combinaciones: mínimo4/5/6/8/12/18; ventana250/500/1000/2000; altura10/20/30/45; percentil80/90/95/97.5; window_bars5/10/20/40. Son valores exploratorios, no parámetros aprobados ni optimizados.

Orden:
1. Agregación de bloques e historial de puntuaciones una vez por window_bars. Reconstruir calibración histórica por ventana; no reutilizar una calibración equivocada.
2. Detectar zonas para cada par percentil/window_bars; reutilizar la cinta inmutable de zonas para las96ternas de racimo de ese par.
3. Antes de sustituir el agrupador, benchmark y paridad sintética con empates, asignación de miembros, geometría de creación y causalidad. NO se ha medido todavía una aceleración del motor.
4. Seleccionar candidatos por frecuencia/cobertura en entrenamiento SIN mirar resultados futuros. Contar nacimientos, no cada actualización del racimo; conservar configuración estrecha con soporte. No inventar un mínimo universal de potencia.
5. Medir efecto incremental respecto del mercado reciente: recorrido en ticks fijos y normalizado por altura, dirección frente a modelo sólo-contexto, memoria espacial del corredor, velocidad de salida, geometría de vuelta y picos confirmados disponibles a la decisión.
6. Validación temporal, dependencia por día/racimo y multiplicidad. Sin fills/costos, alcance no equivale a rentabilidad.

## Alcance y evidencia
Se leyeron los6exports ya expuestos y fijados por SHA256:544531filas,96755registros real repartidos en36configuraciones. Cada fila real procede de una formación histórica retornada por el agrupador, no de un snapshot regular. Hay0duplicados de(contract,session,t0,L,H) dentro de cada configuración y el mismo número de anclas distintas que filas; eso NO prueba independencia de eventos. Las configuraciones pueden representar el mismo episodio de mercado. El calendario completo y los días sin ninguna fila no están certificados.

No se recalcularon precios crudos, nuevas etiquetas de resultado ni P&L; no se tocaron gates, holdout ni configuración de ejecución. La campaña nueva permanece pendiente de datos/replay autorizado; este estudio aprovecha lo que ya está exportado.

Comprobaciones: conteos cuadran con96755real;36celdas y216celdas×contrato; líder verificado por filtro directo independiente de la tabla agregada; rerun portable produce ambosCSV idénticos. No afirmar CI ni optimización del detector por estas comprobaciones.

## Reproducción
```bash
python docs/research/avzvol_frequency_first_grid/analyze.py --raw-root <export-root> --out <derived-output> --repo-root .
```
Requiere pandas,numpy y motorParquet. Los rawfiles deben estar bajo k1/k2/k3. Los pins se toman del plan previo de entry_distance ya versionado. Los archivos plan.json,campaign-proposed.json,evidence.json y CSV conservan definiciones, resultados y estados.
