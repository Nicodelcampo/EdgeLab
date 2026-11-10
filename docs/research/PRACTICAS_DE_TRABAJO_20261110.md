# Prácticas de trabajo: qué se hizo, qué salió bien y qué salió mal (sesión 8 al 10 de noviembre de 2026)

Estado: VIGENTE. Va en el núcleo de contexto de todos los roles (`edgelab/autopilot/contexto.py::NUCLEO_FUENTES`). Es un registro de
una sesión concreta, con sus errores incluidos: sirve como lista de cosas a verificar, no como autoridad. Si una práctica de acá
choca con una regla de `CLAUDE.md` o con un resultado medido, manda la regla o el resultado.

## Prácticas que funcionaron
1. **Leer la evidencia antes de asentar una lección.** Al armar el registro de factores se iba a cargar «stop ancho, horario 9:30–12
   e imán: confirmados» porque así lo decía `APRENDIZAJES_ESPIRAL.md`. Leer el resultado posterior (`RESULTADO_BRUTO_NETO.md`) mostró
   que eran fricción. Regla: una lección escrita se contrasta con el resultado más nuevo sobre el mismo tema antes de repetirla.
2. **Achicar la pregunta antes de correr.** La grilla de 20.736 celdas se cambió por: E0 sin retornos → una hipótesis contra placebo
   → P&L sólo si pasa. Menos cómputo, menos selección y un resultado que se puede interpretar aunque sea negativo.
3. **Decidir con una regla escrita antes de ver el dato.** La definición de cluster se elige por una regla mecánica pre-registrada;
   cuando el E0 mostró que la regla original no servía (apuntaba a «2 por sesión»), se cambió por enmienda fechada ANTES de ver el
   paso con retornos, y se informa igual el resultado de la definición vieja.
4. **Poner el costo dentro del criterio.** `borde detectable = 2,49/√N + fricción en R` junta potencia y fricción en un número;
   evitó elegir «muchos clusters angostos» (no pagan) o «pocos anchos» (no se pueden medir).
5. **Separar hipótesis que parecen la misma.** Rebote (después del toque) e imán (antes del toque) se miden aparte: un nivel puede
   atraer y no frenar. Cada una con su control que comparte la condición del evento real.
6. **Test de causalidad por prefijo para todo detector:** correr sobre los ticks hasta N y hasta M > N y exigir que lo anterior a N
   no cambie. Encontró que el diseño era causal y dejó escrita la guarda.
7. **Dejar el error como archivo de salida** (`ERROR_KERNEL.txt`): el segundo fallo de kernel se diagnosticó en un paso; el primero,
   sin eso, se había relanzado a ciegas.
8. **Una sola fuente para cada cosa que estaba repetida** (modelos de los agentes, factores, familias) con un test que falla si
   alguien la duplica o si el documento generado queda viejo.
9. **Decir qué no se verificó.** Cada informe separa lo probado con datos reales, lo probado con datos sintéticos y lo no probado
   (p. ej. el indicador de NinjaTrader nunca se compiló acá; la autoprueba del Debian no corrió en el servidor).
10. **Chequeos agendados de una sola pasada** en vez de consultar seguido: menos gasto y el trabajo sigue aunque nadie mire.

## Lo que salió mal (y la guarda que quedó)
1. **Medir mal la primera vez.** ORB+EMA20 se lanzó con la EMA sembrada a las 09:30 (no era la del gráfico) y contando el objetivo
   en la vela de entrada. Lo detectó una pregunta de Nico, no un test. Guarda: enmienda antes de ver resultados y relanzar; revisar
   el indicador contra «cómo lo ve quien lo usa» antes de lanzar.
2. **Dos kernels caídos por bordes no probados:** un día sin velas tras la ruptura y un evento en el último tick. Guarda: probar todo
   detector por eventos con el evento en el primer y en el último tick (O18).
3. **Funciones copiadas y documentos sin encabezado** que rompieron tests que no se habían corrido: se corría sólo el test del
   archivo tocado. Guarda: antes de commitear, correr también `test_existente`, `test_product_registry` y `test_current_md`.
4. **Siete iteraciones del indicador visual sin compilar.** Sin compilador de C#, cada error se descubrió en la máquina de Nico.
   Además los umbrales se ajustaron mirando gráficos del período de holdout. Guarda: declararlo (K9) y no usar esos umbrales en
   ninguna prueba; pedir de entrada una definición por escrito antes de iterar sobre capturas.
5. **Definiciones equivocadas de «expansión» tres veces** (huecos de precio, regiones de grilla, zigzag) antes de entender que era
   «lo recorrido entre dos zonas». Guarda: reformular la definición en una frase y confirmarla antes de programar.
6. **Una estimación dicha como dato:** «300 barras de 5 ticks son 1 a 3 minutos» era una cuenta propia; el E0 no la midió. Guarda:
   lo estimado se rotula como estimado y se mide en el paso sin retornos.
7. **Supuesto que el dato desmintió:** se pre-registró apuntar a ~2 clusters por sesión y hay 20 a 70. No fue grave porque el E0
   iba antes que todo; lo habría sido si se hubiera ido directo a retornos.
8. **Trabajo en una rama mientras el agente del Debian lee otra:** 32 commits que el agente no veía. Guarda: integrar a
   `foundation` el mismo día.
9. **Suite completa de 28 minutos corrida mientras se editaba el árbol:** dio fallos falsos. Guarda: dejar que la corra el CI
   sobre el commit y correr local sólo lo afectado.

## Lecciones de la tarde del 10/11 (clusters HFT → niveles de la sesión)
1. **El control también es un hallazgo.** La cuerda más sólida del día salió de mirar el CONTROL (un nivel cualquiera rebota) y no
   el objeto (el cluster): «real − control» se lee en sus dos partes. Guarda: todo resultado informa el control por sí solo.
2. **Lo que muere al derecho puede vivir al revés.** Ninguna de las 7 definiciones de rebote en zonas sobrevivió, pero el signo
   contrario fue estable en casi todas: se miden siempre los dos canales con estabilidad (`banco_eventos.estabilidad`).
3. **Con efectos chicos, estabilidad antes que «sin potencia».** 5 sub-bloques de sesiones y nulo de inversión de signo; una pista
   elegida entre muchas se juzga repitiendo la selección (`nulo_de_seleccion`): el retroceso pasó de p 0,002 a p 0,24.
4. **Confirmar barato en datos independientes:** una pista de NQ/ES se prueba como hipótesis previa en otros activos sobre toda la
   tabla, sin gastar la réplica; y una re-lectura de tablas viejas con la medición nueva (sin datos nuevos) sumó evidencia.
5. **El kernel que alimenta al banco no calcula nada con desenlaces** (sólo tabla, conteos y estratos): si no, la tabla ya está
   mirada. Y dos familias que comparten ventana declaran el ORDEN en que se miran.
6. **El análisis de una confirmación se escribe y se commitea antes de que exista la tabla** (`tools/confirmar_no_defiende.py`,
   `tools/op1_niveles.py`), con el α de LORD++ reservado antes de mirar.
7. **Una carrera desde el borde no es una operación.** Con orden límite y fills realistas, en una caminata al azar se pierde ≈ 0,07 R
   en bruto por selección adversa (`edgelab/research/fill_pasivo.py`): el efecto tiene que superar fricción + selección adversa.
8. **El presupuesto de datos se gasta rápido:** en una tarde se consumió abr–sep para una familia. Antes de lanzar, escribir qué
   ventana/activo queda sin mirar para cada familia y qué la va a confirmar después.

## Orden de trabajo que resume lo anterior
1. ¿Ya está medido? (`FACTORES_CON_VENTAJA.md`, `FAMILIAS.md`, `tools/existente.py buscar`).
2. Escribir la población, la hipótesis, el control y la regla de decisión; contar las pruebas.
3. Paso sin retornos primero; elegir por regla mecánica.
4. Tests con casos de borde y de causalidad; kernel probado de punta a punta con datos sintéticos.
5. Lanzar; al volver, escribir el resultado con lo que no se pudo verificar, asentar el factor y corregir cualquier lección vieja
   que el resultado contradiga, todo en el mismo commit.
