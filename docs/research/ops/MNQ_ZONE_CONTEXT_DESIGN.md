# Componentes continuos + contexto AVZP2/racimos — piloto de desarrollo

Estado: protocolo fijo y runner implementado; sin envío ni resultados de mercado nuevos en este checkpoint. Plan `MNQ_ZONE_CONTEXT_PLAN.json`. No confundir preparación, ejecución y cierre.

## Pregunta que sí responde

¿Ubicación relativa de zonas y aproximación del precio añaden capacidad predictiva sobre componentes continuos y controles de densidad/ocupación, en los mismos instantes y respuestas? No selección de parámetros, primera llegada física, causalidad de absorción, edge o desempeño de trading.

El benchmark anterior favoreció componentes continuos frente al prior pero no añadir estados A/E. Su cierre v4 se preserva: no otra auditoría de datasets, recalibración A/E, rerun ni parámetros elegidos por sus respuestas.

## Perfil elegido antes de nuevas respuestas

Un AVOLZONEPOI2 del roster existente, índice2/hash `1ccfeaf809b3912b7c4405bb5be9ded88b7cbd606486601d4a2dbb0f01b07bb8`: tick25, ventana5, multiplicador1.25, gap2, cluster mínimo2, scoreSuma, percentil70. El resto del perfil nativo permanece igual, incluido lookback20sesiones y min_samples20. Racimo derivado único del roster, índice0: mínimo3, ventana250barras y altura20ticks. Elección por parámetros/propuesta densa histórica, no una garantía de cantidad observada ni el ganador de un grid.

BT2/BT2A y otros perfiles quedan fuera de este piloto. Se agregarán en un protocolo posterior si corresponde; no se certifica paridad NT8 cercana al100% como cifra medida.

## Calendario y población

- Lectura continua única desde el comienzo de warmup ya usado por el piloto de confluencias; se preservan calibración, footprint NT8, tick-rule y pertenencia racimo entre sesiones. No acortar historia ni resetear racimo para aumentar coincidencias.
- Ajuste June15/16; las12fechas siguientes originales de investigación para scoring. Vacías se publican como EMPTY y no se sustituyen. Al menos6 disponibles; entrenamiento completo obligatorio.
- Mismas anclas5s, ventanas20/60s, cobertura80%, gap máximo2s, labels first-passage60s y barrera causal del benchmark v4. UNKNOWN no es NONE ni respuesta negativa. La función de labels se reutiliza, sin segunda pasada ni labels especiales para zonas.
- **Respuestas de estas fechas YA inspeccionadas.** Este es desarrollo pareado, no confirmación ni muestra virgen. El siguiente split disjunto y su rango deben fijarse antes de abrirlo; holdout desde2026-10-01 permanece cerrado.
- Población reloj completa común, no sólo toques, coincidencias o A/E. Todos los modelos usan idénticas filas y respuestas. No IID, p-values ni selección automática del mejor modelo.

## Qué significa una zona aquí

Snapshot inmutable disponible por `(timestamp_ns, sequence)`, nunca el objeto final ni una clasificación posterior trasladada al nacimiento. Exposición primaria = nacida y reconocida en la sesión actual. RACIMO exige también todos sus miembros de esa sesión; revisión mixta retira la exposición sin resurrección. Historia nativa de carry se conserva, aunque no entra en esta exposición primaria.

Se mide **geometría reconocida a la fecha dentro de sesión**, NO liveness nativa de AVZ ni zonas certificadas vigentes. CLASSIFY se cuenta, no cambia retrospectivamente la población. Cero significa sin snapshot primario reconocido, no ausencia física de absorción ni detector calibrado negativamente. Las exclusiones de carry y soporte se publican.

## Siete representaciones y controles

Mismo ridge multiclase lambda0.01, estandarización sólo train y peso igual por sesión. Brier = suma de tres errores cuadráticos, media equiponderada de sesiones, menor mejor.

1. PRIOR: frecuencias de train.
2. CONTINUOUS: componentes exactos del v4.
3. DENSITY: continuous +8variables de contexto.
4. GEOMETRY_CC: density +4bases suaves fijas de componentes continuos.
5. GEOMETRY: density +4variables geométricas.
6. ARRIVAL_CC: geometry +4otras bases suaves continuas fijas.
7. ARRIVAL: geometry +4variables de aproximación/observabilidad.

Densidad8 = por familia: log cantidad reconocida, log suma de anchuras (con multiplicidad), fracción de unión local y log cantidad local. Dominio local = midquote±barrera causal. Ocupación exacta en coordenadas **half-tick enteras cerradas**, incluidos puntos; no se confunde con longitud continua.

Geometría4 = distancia firmada a zona más cercana por familia, fracción de intersección de las uniones AVZ/racimo dentro del dominio, y presencia interior en ambas familias. Cercanía/empates se resuelven por distancia, anchura e identidad, nunca respuesta. Racimo no es un voto independiente: deriva de AVZ.

Aproximación4 = reducción de distancia absoluta a esa misma zona por familia y dos flags de snapshot sin revisión ya disponible en el origen. Origen = primer registro observado después de t−20s, igual que el inicio del componente continuo actual. Si la zona nació o se revisó después, delta0 y flag0 (no adjudicar movimiento previo a geometría futura). Es aproximación de **endpoints midquote**, NO primer toque, camino recorrido, no-touch ni paso por el interior.

Comparaciones primarias: GEOMETRY−GEOMETRY_CC y ARRIVAL−ARRIVAL_CC, capacidad igualada4vs4. Secundarias: density−continuous, geometry−density y arrival−geometry; contienen diferencia de capacidad y no deben venderse como prueba de especificidad. Publicar por sesión/fase/dirección/estado con censos, no elegir subconjuntos ganadores.

**No incluye aún null de zonas ficticias con geometría/exposición igualadas.** Ni una mejora de este piloto autoriza atribución específica a los indicadores: ese control y réplica disjunta son requisitos del siguiente protocolo. Un null no cierra ausencia de efecto o potencia; pocos racimos/zonas comparables limitan la conclusión.

## Optimización que realmente está implementada

Una lectura continua, un bar spec compartido, un AVZStream y un RacimoTape nativos persistentes. Sin96detectores, matriz cartesiana, SQLite de capturas ni grafo de todos los pares/triples. Snapshots privados acotados por sesión; interval-treap para consulta local, endpoints ordenados para más cercano y unión/intersección por segmentos, sin materializar pares globales. La feature sólo se calcula en población común utilizable; features/labels continuos se reutilizan.

Los endpoints usan listas Python con movimiento O(N) al insertar/borrar: NO claim falso de update O(logN) ni speedup Kaggle no medido. Las primitivas existentes siguen construyendo footprint agresivo además del TOTAL: oportunidad de optimización posterior, no un cambio no probado ahora. No poda silenciosa de historia/candidatos ni prefix-result si se agotan recursos.

Máximos:100Mticks total/8Mpor sesión,20k snapshots activos,100k vistos/session y100k historia racimo,100k mutaciones/session,20khits/anchor,10Mhits/session,150Mhits total, runnerCPU/wall1800s, transporte600s, parent2700s y notebook3600s. RSS muestreado4GiB/AS6GiB; no cgroup ni cuota global. BLAS1thread. Publicar tiempos separados de warmup/detectores/fit y memoria; el total incluye historia que no requirió el benchmark v4, por lo que comparación directa de53s sería engañosa.

## Firewalls y lanzamiento

Mercado sólo Kaggle privado CPU, mismo dataset/version/sha aprobado. Únicamente boot/zone/failure JSON agregados, nunca ticks, SQLite, arrays, labels por fila, modelos o log privado. Paquete aislado con imports `--help` y tests negativos antes de enviar. Recibos concilian hashes, poblaciones y Brier; verificar contra prior/continuous v4 sin volver a auditar ticks.

Nuevo intento manual único con journals propios enlazados al último cierre terminal; no reutilizar/resetear batch v3/v4, ambiguo→no resend, reservas antes de status. No otra daemon, merge, deploy, canonical Brain writer ni autoridad autónoma. Guardar fuente/protocolo/paquete y pre-send en repo antes de ejecutar.

## Preguntas abiertas que se mantienen

Especificidad vs geometría genérica; soporte de racimos derivados/carry; formación/edad/revisión; dirección/velocidad/flujo de llegada y separación de aproximación/toque; estabilidad por sesiones/fases/contrato; absorción física vs proxy sin profundidad/cancelaciones; stationarity descriptiva vs edge. Este piloto sólo comienza por contexto/representación de endpoints. Priorizar contraste interpretable antes de expandir muchos escenarios.
