# Benchmark continuo contra representación A/E — desarrollo

## Pregunta y alcance fijados antes de nuevas respuestas

¿Agregar los proxies A/E mejora la predicción de la primera respuesta del midpoint respecto de sus componentes continuos, con exactamente las mismas anclas? ¿Persiste la mejora frente a dos términos continuos adicionales, o proviene sólo de aumentar capacidad? ¿Es estable por sesión, fase/dirección y soporte de cada estado?

Este benchmark no identifica absorción física ni agotamiento físico. A/E son funciones deterministas de los componentes: no aportan información nueva; pueden aportar representación útil a un modelo restringido. No equivalen a OFI de libro ni a cancelaciones. No hay zonas, fills, P&L, holdout ni promoción automática.

## Separación temporal honesta

- Calibración de estados: reutilizar EXACTAMENTE el agregado June12 publicado por el piloto anterior; SHA `3f88b2b5f12a9ac528e2b433cb36002b0f7df49135993fc73be151bc75717bc9`. No releer ni recalibrar esa sesión.
- Ajuste supervisado: June15 y June16. Sus respuestas YA fueron inspeccionadas; no presentarlas como descubrimiento nuevo.
- Evaluación: primeras doce fechas de lunes a viernes posteriores a June16: June17/18/19/22/23/24/25/26/29/30 y July1/2. Incluye June19 aun siendo feriado: sin sustitución por soporte/resultados. Extensión explícita del scope anterior hasta July2, sólo investigación preholdout. Fechas seleccionadas por calendario, no por retornos.
- Cada sesión natural termina22UTC del día etiquetado; no ventanas entre sesiones, no spoofing de etiquetas para evadir guardas. El clasificador antiguo mantiene su roster; nueva interfaz pura conserva exactamente la definición y el caller nuevo valida sus propias fechas.
- Menos de100 anclas utilizables comunes en cualquier sesión, ausencia o exceso de presupuesto: fallo del benchmark completo, no reemplazo ni éxito parcial. Soporte de estados escasos se reporta sin inferencia.

## Seis predictores, un único estimando

1. PRIOR: probabilidades históricas de ajuste, ponderando ambas sesiones por igual.
2. CONTINUOUS: todos los componentes de A/E más actividad, calidad y contexto causal.
3. CONTINUOUS_CC: baseline más DOS bases suaves fijadas, igual cantidad de variables que AE.
4. CONTINUOUS_A: baseline más indicador A.
5. CONTINUOUS_E: baseline más indicador E.
6. CONTINUOUS_AE: baseline más A y E, incluyendo BOTH como ambos1.

No término A×E: sólo cuatro BOTH en las sesiones de ajuste del piloto; omisión fijada antes de nuevas respuestas. Sin búsqueda de lambda, selección de variables o configuración ganadora.

Features enumeradas en `phenomena_models.FEATURES`: current/prior count, volumen total/buy/sell/unknown, tamaño medio, range/path y spread, cobertura quote/sign, flujo firmado, ratios presión/trades/volumen, progreso dirigido actual/previo y absoluto, rango causal60s, barrera, fase RTH y dirección. Log1p para no negativos, signed-log1p para firmados; cobertura sin transformar. No reloj futuro, ID de sesión como predictor, outcomes o estado derivado de respuesta.

CC1 = tanh(log(max(pressure_ratio,1e-12))) × tanh(current_directed_progress/4).
CC2 = tanh(log(max(trade_count_ratio,1e-12))) × tanh(prior_directed_progress/4).
Son controles de capacidad prespecificados, NO una comparación exhaustiva con modelos no lineales.

Ridge multiclase de mínimos cuadrados: one-hot3 clases, intercepto sin penalizar, lambda0.01, media/escala calculadas sólo con ajuste y pesos de sesión iguales. Desviación<1e-12 usa escala1. Probabilidades recortadas[0,1], renormalizadas; fila toda0 usa prior fijo. Brier = suma de los tres errores cuadrados, [0,2], NO dividido por3. No refit en evaluación.

## Medición compartida y censura

Mismo kernel de ventanas20s y contexto60s del piloto, grid5s, gaps2s, quote-volume y signed-volume80%, secuencia causal para mismo ns. Sólo proxies clasificados con contexto observable se etiquetan: UNKNOWN no es negativo. Cada ancla se etiqueta UNA vez y alimenta los seis predictores. Primera pasada midpoint a60s con barrera max(4,ceil(0.5×rango60s)); sin pasaje sólo si horizonte cubierto. Gap/quote/EOF censurados no reciben retorno cero.

Pérdida por sesión común, luego media EQUIPONDERADA de las doce sesiones, no pooling dominado por actividad. Diferencias AE−continuous y AE−CC por sesión; menor es mejor. Desglose fase×dirección y A/E/BOTH/NEITHER, censura/observabilidad y desplazamiento de componentes frente al rango de ajuste. Condicionado a eventos utilizables, sin corrección de censura ni efecto causal. Anclas superpuestas NO independientes. Sin p-valores, FDR inventado, intervalos IID ni bootstrap de doce fechas como si fueran campañas independientes.

## Optimización y límites

Una recuperación del pin aprobado, una lectura/primitivas/respuesta por sesión compartida entre modelos; liberar arrays entre sesiones. No producto cartesiano ni96 detectores. Sólo matrices de ajuste compactas en memoria privada, una sesión de evaluación a la vez; sin persistir filas/predicciones/modelos ni exportar ticks. BLAS/OMP1 thread. No nueva QA del dataset: sólo integridad necesaria del transporte.

Plan: máximo8M ticks/sesión,100M total,250k anclas/sesión,150M elementos de respuesta/sesión y1.8B total;1800s CPU/runner,600s transporte,2700s host,3600s timeout solicitado. RSS muestreado4GiB/AS6GiB, no cgroup. Un intento manual explícito, ningún retry automático. Paquete/code/protocolo publicados antes del envío; journal nuevo finito ligado a cierre anterior, no reset de presupuesto global.

## Qué decidir después

No elegir automáticamente el menor score. Revisar dirección/tamaño/estabilidad de ambas diferencias y soporte; ablations A/E describen de dónde viene la representación. Si no mejora, registrar resultado negativo de ESTE benchmark, no ausencia del fenómeno. Si mejora, sigue siendo desarrollo: réplica temporal/bloques/censura antes de inferencia. Interacciones AVZP2/racimos/BT2/BT2A sólo después, con control geometría/densidad/ocupación y orden/llegada causal; no repetir indiscriminadamente el join que agotó capacidad. Writer científico canónico y daemonDebian siguen externos/no desplegados por este trabajo.
