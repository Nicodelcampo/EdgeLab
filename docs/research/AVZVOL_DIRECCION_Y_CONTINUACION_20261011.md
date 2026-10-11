# AVZVOL: dirección y continuación en desenlaces ya expuestos

## Conclusión para decidir en qué continuar

**No aparece una ventaja fuerte y uniforme de continuación tras la salida. Hay una asociación exploratoria con la tendencia previa, pero es heterogénea y sensible al soporte.** Merece una prueba causal acotada, no una señal direccional a promover ni una búsqueda de contratos/filtros ganadores.

Tres preguntas distintas:

1. **¿Hacia qué lado saldrá?** El export `dir` es el lado de la primera salida observada después del ancla: es futuro respecto de `t0`, no una predicción de la zona disponible al ancla. Usarlo como feature allí sería fuga de información.
2. **¿Continúa después de salir?** O2 ya exportado permite revisar un evento geométrico posterior a la salida. No aporta por sí mismo dirección antes de salir.
3. **¿La tendencia previa coincide con la salida?** Podemos revisar el signo de `close[t0] - close[t0-500]`, ya exportado como `trend`. Es una regla de tendencia conocida al ancla bajo la receta legacy, **no un predictor direccional específico de las zonas**, y su procedencia causal sigue sin certificar.

## 1. Continuación: O2 no muestra mejora uniforme

O2=1 si, desde las barras posteriores a la salida, la excursión alcanza una altura congelada `h=H-L+1` desde el borde por el que salió, antes de volver a cerrar dentro de `[L,H]`. El código considera hasta 2.000 barras posteriores de 25 trades dentro de la sesión, excluye la barra de salida y evalúa excursiones high/low y cierre; **no es una probabilidad de ganar una operación**, ni un horizonte fijo de reloj ni una simulación de fills/costos.

En las **31 celdas con soporte en los seis contratos**, con igual peso por sesión soportada, celda y contrato:

- Reales: **19.0870%** de continuación resuelta.
- Pseudo legacy: **19.4500%**.
- Diferencia: **-0.3630 puntos porcentuales**.

Cuatro contratos tienen diferencia negativa y dos positiva; 21 celdas comunes negativas y 10 positivas. No se eliminan las excepciones. Hay 34 celdas computables en algún contrato y dos sin soporte de contraste; las 36 quedan en el archivo completo.

## 2. Tendencia previa y dirección: asociación pequeña, no universal

Población distinta: ancla todavía dentro de la banda (`pos=0`), tendencia previa no nula y salida registrada. No se buscan otros lookbacks, umbrales o reglas después de ver sus resultados.

- Coincidencia tendencia–salida en reales: **56.6344%**.
- Coincidencia en pseudo: **54.1540%**.
- Diferencia: **+2.4804 puntos porcentuales**, 31 celdas comunes.

Cinco contratos son positivos y MNQ_06-26 es negativo (**−3,9844 pp**). Hay 23 celdas comunes positivas y 8 negativas. Los porcentajes no son tasas pooled de todas las filas ni precisión out-of-sample de una estrategia. Superar 50% no acredita una ventaja frente a la mezcla direccional del mercado; el contraste pertinente aquí es con el control disponible, aún no certificado como libre de zonas.

| Contrato | Continuación O2 real−pseudo (pp) | Coincidencia tendencia–salida real−pseudo (pp) |
|---|---:|---:|
| MNQ_09-25 | -2.8799 | +2.6915 |
| MNQ_12-25 | -1.3781 | +4.3956 |
| MNQ_03-26 | -0.6970 | +1.3809 |
| MNQ_06-26 | -1.1428 | -3.9844 |
| MNQ_09-26 | +1.7073 | +3.6205 |
| MNQ_12-26 | +2.2125 | +6.7786 |

## 3. Contexto: no confundir soporte distinto con efecto mejorado

Revisión descriptiva adicional dentro de estratos exactos **contrato/sesión/celda/franja horaria/signo de tendencia**, con igual peso a estratos soportados por sesión. No controla magnitud de tendencia, actividad, volatilidad, geometría completa ni ausencia de zonas en pseudo; no es emparejamiento causal acreditado.

- O2: **+1.1546 pp**, en **30** celdas comunes y 5.117 grupos sesión/celda soportados. En exactamente la misma población de filas con solapamiento, pero sin igualar el peso de los estratos horario/tendencia, el gap ya es **+1,1816 pp**. Por tanto, pasar del −0,3630 pp original al positivo no demuestra que el ajuste descubrió una ventaja: **la restricción de población ya cambia el signo**.
- Coincidencia tendencia–salida: **+0.7774 pp**, en **28** celdas comunes y 4.801 grupos sesión/celda. En exactamente esa población de solapamiento sin reponderar estratos es **+0,7484 pp**. No comparar el +2,4804 pp original con +0,7774 pp como si fueran idénticas poblaciones. Aquí MNQ_12-25 y MNQ_06-26 son negativos; este último **−6,9009 pp**. La mayor diferencia positiva es MNQ_12-26 **+7,5179 pp**, observada después de inspeccionar; **no se promueve como ganador**.

Esta dependencia del soporte es precisamente el motivo para definir censo y comparabilidad antes del siguiente resultado. No se eligió este corte por tener mayor efecto: horario y tendencia son dimensiones de comparabilidad declaradas en el diseño existente. El diagnóstico de tendencia en esos estratos y la descomposición de población se añadieron tras la primera corrida expuesta; no se presentan como confirmación ciega.

## Faltantes, duplicados y semántica

- Universo: **544.531 filas evento×celda**, 96.755 reales y 447.776 pseudo; no eventos independientes.
- Sin salida registrada: **287** (85 reales, 202 pseudo). No se cuentan como dirección correcta/incorrecta ni como fracaso de continuación.
- O2 no resuelto después de salida: **177** (18 reales, 159 pseudo). La falta de resolución puede corresponder a fin de ventana, sesión o archivo; el export no identifica cada motivo. Se conservan, no se imputan.
- O2 conocido: **544.067**; éxitos 16.234 reales y 83.540 pseudo, retornos antes del umbral 80.418 reales y 363.875 pseudo. Son conteos, no las tasas reponderadas anteriores.
- Acuerdo tendencia–salida elegible: **74.158** reales y **343.292** pseudo. No se extrapola a anclas fuera de banda, tendencia nula o sin salida.
- Sensibilidad adversarial a O2 no resuelto, sobre exactamente los grupos que soportan el contraste primario e incluyendo todas sus salidas observadas: gap entre **-0.4015 y -0.3326 pp**. No son intervalos de confianza ni resuelven sesgos upstream/no salida. Sólo extremos algebraicos según cómo se resolvieran los códigos −1.
- Se conservan duplicados pseudo por muestreo con reemplazo, celdas sin soporte y filas solapadas. No independencia inferencial, p-valores, intervalos ni potencia. Perfil técnico Arrow: todos los códigos/nulls/identidades validados después de preflight de los seis archivos; no lecturas de precios crudos.

## Recomendación operativa de investigación — no trading

**Continuar con la pregunta de P2: si la zona añade información a una regla previa simple de tendencia y consolidación.** Fijar el censo as-of, los controles zone-free, la señal conocida al ancla, la comparabilidad y el soporte antes de nuevos desenlaces. No usar `dir` futuro como predictor, no elegir ahora MNQ_12-26 ni celdas positivas, ni optimizar el lookback 500.

P1 permanece prerrequisito de calidad/procedencia. P3 deberá separar dirección de salida, continuación tras salida, horizonte de reloj y censura; no intercambiar estos endpoints. P4 económico sigue bloqueado; no estrategias, P&L, entradas, costos, stops ni holdout calculados.

**Lectura simple:** la evidencia disponible es más compatible con un contexto que modifica algunas probabilidades que con una flecha direccional fuerte y estable. Esa lectura es exploratoria; no demuestra el mecanismo ni información incremental causal.

## Evidencia y reproducción

- [Plan](avzvol_exposed_direction_20261011/analysis-plan.json), [evidencia completa](avzvol_exposed_direction_20261011/evidence.json), [las 36 celdas de cada contraste](avzvol_exposed_direction_20261011/all_cells.csv).
- [Receta opt-in](../../tools/review_avzvol_exposed_direction.py): inventario privado de seis exports, `--historical-stage-source`, `--out-dir` nuevo, `--allow-exposed-direction-review`. Verifica SHA y footers de todos antes del payload; fija plan antes de leerlo. Sólo lee columnas de outcomes/covariables ya exportadas. Etapa histórica SHA `889d9b23cf2428167c93e18bfc45436b9efb48f67dd44d5a43c00654aa5c365c`; auditoría SHA `1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e`.
- Medias y conteos recomputados de forma independiente por listas/contadores; bounds recomprobados algebraicamente. Diferencia máxima de grupos 2,22e−16 en los diagnósticos de contexto. La receta no importa ni ejecuta el runner legacy.
- [Mapa candidato y decisión previa](AVZVOL_MAPA_Y_DECISION_20261011.md): la exclusión de 27 cruces de O5 no era una prueba direccional y no valida el horizonte de O2.
- Especs de gráficos agregados incluidos; el builder canónico pasó preflight, pero la carga del HTML al chat falló sin devolver un archivo válido. No se inventa URI ni se sustituye por una figura de otra ruta.
