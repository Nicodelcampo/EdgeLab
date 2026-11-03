# Revisión de las 12 familias propuestas por Gemini

Estado: REVISIÓN — no autoriza lanzamientos; correcciones propuestas, no aplicadas. Fecha 2026-11-03. Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Alcance y conclusión

Revisión del código y manifiestos de `gemini/familias-20261103`, commit `c73bbb60`, frente al programa y los antecedentes del PR #189, HEAD `82e02f26`. Las 40 campañas están desactivadas. El conjunto usa 108 celdas por canal, R y piso de cuatro ticks; tener un piso no garantiza que la fricción sea económicamente aceptable. La certificación de causalidad de disparos comprueba casos muestreados, no toda ejecución ni todos los feeds. Se ejecutaron en esta revisión los tests `test_familias_nuevas_r.py`, `test_wm_fixing.py` y `test_absorcion_climax.py`: 10 pasan; otra ejecución anterior reportó 24, que no sustituye la validación de calendario, datos ni noticias.

**No lanzar las 40 como están.** Primero corregir y probar las guardas comunes; depurar solapamientos; después pre-registrar cualquier cambio de lógica y contabilizar pruebas y linaje. Que una idea sea prioritaria no implica que sea rentable.

## Arreglos transversales necesarios

1. **Noticias durante toda la operación.** `EXCLUIR_EVENTOS` en `grilla_generica.correr` sólo filtra cercanía al disparo, no el intervalo entrada–salida. ABSORCION es la única de las 12 que declara el filtro. MEDIODIA, PRIMERA-HORA y COMEX pueden permanecer abiertas a las 14:00 ET. Implementar una política causal previamente decidida: impedir entradas en la ventana prohibida y cerrar antes de la noticia conocida, con costo y ejecución reales; no eliminar ex post por su salida futura. Pruebas para antes/durante/después, ambos sentidos, entradas sin llenar, calendario incompleto fail-closed y cobertura en todas las campañas. Validar la política contra `edgelab/noticias.py` y la decisión humana del 25-oct; no sustituirla por ±15 min sin justificar.
2. **Relojes de la sede.** Tokio usa ET fijo, aunque Nakane 09:55 JST equivale a 19:55 ET en invierno de NY y 20:55 ET en verano. WM 16:00 Londres es 12:00 ET durante semanas de desajuste de DST y 11:00 la mayor parte del año. Londres y Europa-oro también requieren calendario local. Convertir por `Asia/Tokyo` o `Europe/London` y calendario de sesiones; pruebas en transiciones y cierre de barras, no un offset constante.
3. **Datos, instrumentos y costos.** TOKIO-FX-USDJPY opera `DK:USDJPY`; el resolver/costo de futuro correspondiente no está demostrado. Bloquear hasta verificar datos y costo canónico o diseñar explícitamente traducción inversa al 6J con unidades, dirección, base y fricción. WM EURUSD ejecuta 6E y COMEX XAU ejecuta GC: `embudo_runners` solicita fricción del instrumento de ejecución; igualmente probar traslado sensor/futuro, ticks, unidades, base y ejecución con datos reales antes de correr. Señal spot no equivale a fill en futuro.
4. **Celdas y potencia.** 108 por canal es espacio teórico, no prueba de >=30 operaciones reales por celda: hacer E0 target-free con cobertura, porcentaje de celdas evaluables, sesiones y costos relativos por stop antes de cualquier outcome. No sumar instrumentos como réplicas independientes: declarar multiplicidad y dependencia entre sensores, instrumentos, canales y ramas de dirección.
5. **Ejecución y causalidad.** Pruebas de siguiente tick, gaps y stops, ambigüedad intrabar, salida por hora y cierres anticipados; nivel de riesgo desde fill real, no cierre teórico. Tras cualquier cambio, regenerar certificados por huella, sin tratarlos como prueba de ausencia universal de lookahead.

## Mapa familia por familia

| Familia | Evaluación y reparación propuesta |
|---|---|
| WM-FIXING | Prioridad 1 tras corregir hora Londres y costeo/traducción. Fade y continuación son hipótesis distintas ya incluidas; contar ambas, no elegir tras mirar. |
| COMEX-CIERRE-ORO | Prioridad 1: revisar definición/horario exacto de settlement contra fuente oficial, cierres tempranos y noticias de 14:00. Fade y continuación cuentan juntas. |
| ABSORCION-CLIMAX | Prioridad 1: señal distinta de caja-ruptura; el filtro de noticias de entrada no basta. Verificar volumen relativo y densidad real sin prometer potencia. |
| ESTRUCTURA-HHLL | Prioridad 2: pivotes se confirman con retraso de cinco barras; probar empates, reinicio por sesión, precio real del fill y stop; noticias. |
| OVERNIGHT-INVENTARIO | Prioridad 2: cerca de apertura/gaps existentes; explicar mecanismo realmente distinto, validar límites de sesión y horarios. Ambas direcciones cuentan. |
| LONDRES-IMPULSO | Caja → ruptura ya ampliamente explorada; distinguir de RANGO-ASIA/PREAPERTURA y corregir horario Londres. Prioridad baja sin hipótesis incremental. |
| MEDIODIA-SUBASTA | Caja → ruptura; solapa gramática existente; corregir cobertura de noticias y demostrar diferencia antes de lanzar. |
| PRIMERA-HORA-CONT | Caja Initial Balance → ruptura de apertura: solapa ORB/OTR930 y criterio de no duplicación; noticias y mecanismo incremental antes de lanzar. |
| COMPRESION-NR | Ruptura de caja con selección NR; revisar solapamiento y justificar contribución del filtro de compresión, con multiplicidad heredada. |
| TOKIO-APERTURA-FX | Solapa Asia; corregir calendario JST y ejecución/costo USDJPY. No convertir a 6J como si cotizara igual. |
| APERTURA-EUROPA-ORO | Caja → ruptura; justificar novedad respecto de Londres y familia oro, corregir hora local y traslado XAU → GC. |
| IMPULSO-POST-MACRO | No se identifica evento real: la ventana 08:30 corre también en días sin anuncio. Definir calendario y control de día sin noticia, período de exclusión y grado de solapamiento. |

## Acciones antes de activar

Congelar un diseño revisado por familia, política de noticias, calendarios y multiplicidad; probar con sintéticos y E0 sin desenlaces; comprobar datos de desarrollo, costos, cuenta y hashes. Sólo después evaluar la autorización de corridas y el presupuesto. Ninguna de las reparaciones anteriores se presenta como aplicada o probada.
