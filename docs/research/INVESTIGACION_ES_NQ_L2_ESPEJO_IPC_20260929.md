# ES/NQ L2 y espejo × IPC — diagnóstico y diseño para revisión humana

Estado: DIAGNÓSTICO TARGET-FREE HECHO / DISEÑO PROPUESTO / SIN NUEVOS OUTCOMES.
Solicitud: Nico, captura aportada en este chat. Fuente revisada: foundation/f0b-compatibility-probe, HEAD 3804c276b00a3a610aae76fc486c098a76cccf41.

## Hallazgos verificados

### ES: separar HMM base de overlay de estrés
El STOP de cuatro climas queda intacto. `seed_labels` compara argmax del filtro HMM base, antes del sticky y del overlay; no compara las etiquetas finales de cuatro estados. El acuerdo reportado no es una prueba de estabilidad de toxic.
`toxic` se calcula aparte, sobre cinco variables desestacionalizadas: |OFI normalizado|, |desequilibrio de trades|, spread, tasa de eliminaciones L2 y agotamiento de profundidad.
Calibración sólo en entrenamiento: mediana/IQR por variable, z positivo recortado 0..4, promedio de las tres mayores; entrada q90 con dos minutos de confirmación, salida bajo q75 con tres minutos. No depende de la semilla HMM.
Identidad entre semillas con el mismo overlay NO es validación temporal: la calibración, feed y umbrales aún pueden ser frágiles.
Calm NO equivale a no-toxic: normal y volatile también forman parte del complemento. No se construye una pareja calm/toxic descartando silenciosamente otros estados.

Se descargaron y auditaron 1.509 intervalos: 48 sesiones, 65.134 minutos; sin duplicados ni solapamientos. Evaluación: 32 sesiones, 43.238 minutos. Toxic: 402 rachas, 4.666 minutos, presente en las 32 sesiones. Siete huecos internos conservados. Cruce independiente CSV-module/pandas/reporte: PASS.
El 100 % es etiquetado sobre minutos elegibles, NO cobertura de toda la sesión: el acta declara grabaciones incompletas 11/08 y 12/08. No se rellenan.
`fin_ct`, duración total de racha y su máximo son retrospectivos: nunca usarlos para decidir en vivo.

Próximo test propuesto, sin retornos: overlay toxic vs no-toxic con calibración congelada; estabilidad al remuestrear sesiones de entrenamiento, sensibilidad a límites de archivo, hora, gaps y extremos de features. Requiere features por minuto y checkpoint, no sólo etiquetas.
Después, en protocolo distinto: si estrés predice costo, slippage o no-llenado adicional a spread/hora/volumen/QI. No autoriza a filtrar por las etiquetas ES STOP actuales ni demuestra edge.

### NQ: una clasificación reproducible no equivale a un filtro útil
Acta de contextos: PASS; entrenamiento 20 sesiones, evaluación 40. Auditoría posterior del cruce25: 35 sesiones con ticks; 0/12 max-T. Ese resultado cierra esa combinación de señal/entrada/control, no todos los usos de L2.
No seleccionar toxic por su +7..9 pp exploratorio ni rescatar el estudio original. Prioridad: costo/ejecución y riesgo condicionado a una señal definida sin L2, contra baseline de spread, horario y actividad. Usar climas o features continuas como modelos rivales con presupuesto explícito, no barrer hasta ganar.
Deriva tras roll: revisar 09-26 y 12-26, sin recortar retrospectivamente por performance. Oct+ sigue sellado; ningún nuevo outcome leído.

## Nueva idea de Nico — distinta de la del 27/09
Vieja idea: zona MÁS ALLÁ DE B y siguiente intento tras espejo.
Nueva captura: picos previos al impulso, cerca de A o más allá de A en la dirección de la vuelta; entrada durante la vuelta hacia A, al completar el espejo o antes.
La captura no tiene eje de precio/tiempo ni activo identificable: no inferir ticks, fechas, W ni causalidad del detector desde píxeles.
Esquema inicial sometido a confirmación: A bajo → B alto → vuelta bajista hacia picos previos próximos/debajo de A; simétrico para compras. Confirmar si «antes de A» es temporal, espacial o ambos.

### Confirmaciones del visor
1. A/B y límite causal de la decisión; completado por mecha o cierre; impulso y vuelta.
2. Qué visita/pico cuenta; familia acumulación de picos vs IPC-NIVEL con alejamiento entre visitas; cantidad, dispersión, pendiente, separación, vida, última penetración.
3. Que el objeto IPC ya existía con información disponible ANTES del impulso A; pivotes necesitan confirmación, no fecha retroactiva del extremo.
4. Entrada completa vs parcial. Un parcial nunca se etiqueta usando que después completó el espejo. Enumerar todos los intentos disparados online, incluidos los que no completan.
5. «Imbalance»: falta confirmar si es zona LUX/OG/VI de precio o desequilibrio del libro/QI/OFI. Se registran por separado, no sinónimos.
6. Geometría, unidades y condición operable de «justo antes»; distancia en ticks/W causal, no píxeles.

### Diseño posterior (no congelado)
Fases: revisión de captura → tanda real ciega en visor canónico → definición congelada → manifest/OK → información/economía.
Factores candidatos: configuración de posible espejo; entrada; IPC familia/configuración; imbalance presente/ausente. Primero factorial IPC sí/no × imbalance sí/no con controles emparejados, no eliminar controles negativos porque «no tienen motivo para ir».
No aceptar como hecho que sin IPC falla. Hipótesis rival: el movimiento es explicado por geometría, inercia o actividad, o IPC no agrega nada.
Comparar señal sola, +IPC, veto imbalance y ambos. Publicar decisiones descartadas, frecuencia/cobertura, ganancia perdida, fills, costos y efecto incremental. Dos canales: dirección y costo/riesgo. Bootstrap por sesión, multiplicidad real, mínimos y MDE antes.
Propuestas de fracción de vuelta son sólo alternativas de revisión; no se optimizan con outcomes. Entradas al primer tick ejecutable después de señal+latencia, no al extremo dibujado.
Ninguna apertura de reserva/holdout ni P&L en este trabajo.

## Visor de definición
El módulo HTML adjunto anota la captura suministrada, recortada a la izquierda del desenlace. La captura ya fue vista y no tiene timestamps ni desglose intrabar: NO es una tanda ciega certificada y no demuestra disponibilidad as-of. No es un segundo motor de mercado ni reemplaza `viewer/nt8_bridge/index.html`.
Permite marcar A/B/entrada y picos, elegir familia y definición de imbalance, y exportar el juicio JSON. Posiciones son coordenadas de imagen, NO precios/timestamps. No calcula detectores, ticks, P&L, TP/SL ni resultados.
Tanda real e integración al visor único PENDIENTES de las confirmaciones anteriores y datos elegidos por disponibilidad, no resultado. Debe cortar físicamente el bundle en cada instante de decisión; ocultar con CSS no basta.
En el repo se conserva la plantilla con `__IMAGE_DATA__`, sin versionar la captura privada. El HTML entregado en chat incluye el recorte y funciona sin red. El módulo exporta juicio, no confirma una spec del Brain.
Reproducir diagnóstico: guardar `intervals.csv` y `gate_report.json` en un directorio RAW; ejecutar `python tools/diagnose_es_context_intervals_20260929.py RAW OUT`. La salida `evidence.json` reconcilia CSV y reporte. Las conclusiones sobre código son auditoría estática, no un reentrenamiento ni una certificación de features.

## MEDIDO / NO MEDIDO de este trabajo
MEDIDO: reconciliación de intervalos ES y auditoría estática del overlay/HMM; revisión del alcance de los resultados NQ existentes.
NO MEDIDO: estabilidad temporal de overlay ES aislado, valor económico L2 ES/NQ en otras señales, nuevo espejo×IPC, efecto de imbalance, TP/SL y fills, potencia, replicación.
Para siguiente paso: ES features/checkpoint; NQ features/checkpoint/report y labels con available_at; sesiones/barras de la tanda real en el visor canónico. No se necesitan nuevos datos de holdout.

Aporte al referente: evita rescatar un HMM fallido, conserva una hipótesis independiente de estrés y convierte espejo×IPC en reglas causales revisables antes de outcomes.