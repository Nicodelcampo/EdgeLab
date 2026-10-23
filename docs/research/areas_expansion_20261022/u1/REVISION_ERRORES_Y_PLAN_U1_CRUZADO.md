# Revisión de errores (AREAS-EXP-1 → U1-CRUZADO) y plan antes del holdout (2026-10-23)

Estado: VIGENTE — pedido de Nico: «repasá todos los errores, inferí qué errores se podrían cometer en el análisis siguiente y
determiná si abrir el holdout es el paso correcto o conviene iterar antes».

## 1. Errores cometidos, por familia

**A. Definición y diseño**
1. El «área» se definió al principio como zonas pegadas, no como «X zonas en X área»; daba 0,35 áreas por día.
2. Cortes de comercio fijos (0, 1, 3) cuando la mediana real era 10: la perilla no filtraba.
3. Entrada «en la apertura siguiente» asumida como regla universal: el llenado es decisión de cada análisis.
4. BE muerto: el objetivo quedaba antes de 1R y 48 de 96 ejecuciones eran copias que inflaban las pruebas.
5. La regla de selección de U1 pedía datos (cada candidata en la otra fuente) que el kernel no producía.

**B. Estadística e inferencia**

6. El manifiesto exigía el MDE si no pasaba ninguna celda, y el código no lo calculaba: hubo que relanzar.
7. El tamiz trataba como independientes celdas anidadas y contaba las no probables; la t por operación ignoraba la sesión.
8. La regla «ningún período > 80 %» mataba edges recientes (contra el principio de edges actuales).
9. LORD++ aplicado de a una a réplicas simultáneas, dos veces: en la réplica manual de v1.4 y dentro del ciclo autónomo.
10. Cotas del e-proceso de U1-B sacadas del peor caso observado (69 operaciones). Una pérdida nueva las superó: LIMITE_VIOLADO.
11. Maldición del ganador subestimada: U1-B pasó de +7,3 en la selección a −0,18 en datos nuevos. Lo mejor de millones de celdas
    chicas siempre baja.

**C. Código e infraestructura**

12. Clave float combinada en numba (pérdida de precisión).
13. NaN mandado a un nivel real.
14. Defaults fijados al definir la función: `GRILLA` no cambiaba NS ni XS.
15. `estadisticas` y `romano_wolf` se caían sin celdas evaluables.
16. Control de ruido sin celdas evaluables: no tenía con qué fallar.
17. Réplica con `n = 0` en celdas chicas.
18. Familias nuevas sin `result_files`: nunca cerraban.
19. Experimentos del programador sin camino a corrida.
20. Registro de indicadores fuera del perímetro del agente.
21. Saltos de línea literales en ediciones mías (dos veces).
22. Leí el código de salida de `tail` como si fuera el de pytest.
23. Una corrida lanzada con código que después se corrigió (v1.2): se descartó sin mirar.

**D. Afirmaciones**

24. Dije que el release no estaba aprobado y no era cierto (corregido en el acta).
25. Propuse «sin código» para el agente cuando debía poder programar.

**Patrón común:** casi todos los errores son una condición escrita sin su línea de código y su test, o un supuesto que nadie
verificó contra los datos (cortes, cotas, independencia, horarios).

## 2. Errores que se pueden cometer en el análisis siguiente (U1-CRUZADO forward)

| riesgo | por qué es probable acá | cómo se evita |
|---|---|---|
| Look-ahead por desfasaje de relojes entre Dukascopy y NQ | la señal sale de un feed y la ejecución de otro | verificado al minuto (desvío de la base dentro de la sesión: 0,9 pts). **Falta al segundo:** correlación cruzada de retornos por segundo; el pico debe estar en 0 o con el CFD atrasado |
| Que el edge sea del feed de Dukascopy y no se reproduzca en vivo | la señal está en las zonas del CFD y otro broker cotiza distinto | antes de operar: que el feed en vivo reproduzca las zonas de Dukascopy (paridad de zonas entre feeds). **Pedido humano** |
| Gastar la única apertura del holdout con una regla que después se cambia | todavía falta decidir el tope de stop, T1 o T3, y el tamaño | congelar todo antes: tope, objetivos (lote de 2), N fijo, fecha y α |
| Pérdida sin tope | peor operación −218 pts (≈ 4.400 USD por NQ) | regla con pérdida máxima estructural, medida en desarrollo |
| Incompatible con las reglas de una prop firm | un solo día peor −157 pts | medir drawdown diario y total contra los límites de las cuentas (MNQ en lugar de NQ si hace falta) |
| Cambio de contrato de NQ en diciembre | la base salta en cada vencimiento | la base se toma por minuto de señal; verificar que no haya señales cruzando el vencimiento |
| Mirar el forward muchas veces con una prueba clásica | los datos llegan por semana | prueba única a N fijo, o e-proceso con cotas estructurales; nunca «mirar y decidir» |
| Elegir T1 o T3 después de ver el forward | los dos se ven bien | lote de 2 congelado (Simes + BH) |
| Huecos de datos (7–8 de octubre, Dukascopy de octubre) | ya pasó con NQ | auditar la cobertura antes de abrir; los huecos se documentan, no se rellenan |
| Que el régimen cambie | P1 +17 contra P2 +21; 3 de 13 meses negativos | no se usa para elegir; se reporta por mes |

## 3. ¿Abrir el holdout ahora? No todavía

Hay iteraciones que **no gastan el holdout** y lo pueden ahorrar. Se hacen antes, en este orden:

1. **Integridad (target-free, barata).**
   - Alineación al segundo entre los ticks de USATECH y de NQ.
   - Placebo: la misma cantidad de señales en momentos al azar y dirección al azar, ejecutadas igual en NQ. Debe dar ≈ −fricción.
   - Latencia: la misma regla entrando 1, 2 y 5 minutos tarde. Debe degradarse suave; si muere con 1 minuto, depende del feed o
     de la latencia.

   Si algo falla acá, el holdout se habría gastado en un artefacto.
2. **Prueba fuera de muestra limpia y con potencia, sin tocar el holdout: USATECH 2023-01 → 2025-07.**
   - Nunca se usó para nada de esta familia.
   - El traslado a NQ ya se verificó: el P&L en NQ es ≈ el del CFD. Por eso el P&L en el CFD es un buen sustituto, y hay unos
     dos años y medio (≈ 300–400 operaciones).
   - Regla U1 congelada tal cual, T1 y T3 como lote.
   - Por el principio de edges actuales, que falle ahí no mata la idea. Pero si funciona, es la evidencia más fuerte que podemos
     conseguir antes del holdout, y da la historia larga de pérdidas para fijar un tope de stop estructural.
3. **Diseño de riesgo, en desarrollo.** Variantes con tope de stop (por ejemplo, el stop original con un máximo en puntos o en
   múltiplos de la distancia al objetivo) y medición contra los límites de drawdown de las cuentas. Se registran como pruebas.
   La variante elegida se congela antes del holdout.
4. **Recién entonces, el holdout:**
   - regla congelada, con el tope y T1 y T3 como lote;
   - N fijo (≈ 95–150 operaciones) o e-proceso con cotas estructurales;
   - α de LORD++ (paso 3: ≈ 0,0019);
   - ticks de USATECH de octubre en adelante (pedido de descarga) y NQ sellado.

**Lo que no se hace:** ninguna variante nueva se elige con los datos de 2023–2025 y se prueba en esos mismos datos.

## 4. Corrección y mitigación automática (2026-10-23, pedido de Nico: «corregí todos los errores y que queden mitigados automáticamente»)

| errores | corrección | mitigación automática (dónde) |
|---|---|---|
| 1, 2, 13, 16 | definiciones y cortes corregidos | preflight: el objeto aparece, cortes por cuantiles ≥ 10 % por nivel, faltantes fuera de nivel, control con potencia |
| 3 | llenado declarado por operación | interfaz `niveles` (el experimento declara el llenado) |
| 4 | `ejecuciones_equivalentes` | preflight: perillas muertas frenan el lanzamiento |
| 5, 6 | REP cruzado planeado; MDE en toda grilla | campaña: cada condición con su test (`verificar_campana`); `resumen_nulo` en toda corrida |
| 7, 8 | Romano-Wolf por sesiones; canal reciente; regla del 80 % consciente del régimen | en el conductor genérico, para todo experimento |
| 9 | `escalera.probar_lote` | en el núcleo y en `confirmacion.decidir` del ciclo autónomo |
| 10 | — | `MonitorCandidato.desde_regla` (cotas estructurales); campaña con seguimiento sin pérdida máxima = error de preflight |
| 11 | — | `media_esperada_fuera` en toda pista y réplica (recorte de Harvey-Liu con las celdas miradas) |
| 12, 14, 15, 17 | corregidos con test | tests de regresión; preflight corre el DESC completo sobre sintéticos |
| 18, 19, 20 | `STUDY_RESULTS.json` por defecto; campañas como datos; registro del agente | tests del ciclo autónomo |
| 21, 23 | — | `test_todo_python_trackeado_parsea`; `preflight.codigo_vigente(resultado)` |
| 22 | — | la suite se corre capturando su propio código de salida (no el de `tail`) |
| 24, 25 | corregidas en su momento | regla «fuente antes que recuerdo» (CLAUDE.md) |
| **26 (nuevo)** | el generador sintético reiniciaba el precio cada día (el «ruido» tenía reversión plantada) | `test_ruido_sintetico_es_martingala`; lo encontró el preflight |

**Dónde corre:** el programador corre el preflight dinámico antes de aplicar un experimento (`FALLA_PREFLIGHT`). `generate.campanas_grilla`
corre `verificar_campana` sobre cada JSON. Una persona corre `python -m edgelab.research.preflight <módulo>`.
