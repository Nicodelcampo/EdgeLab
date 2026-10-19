# Momentum más frecuente — censo target-free multi-activo

## Resultado y alcance

**Hay variantes con más oportunidades no solapadas; no se midió su rentabilidad.** Kaggle privado v2 COMPLETE. La primera versión falló por lector adaptado ante lote vacío; se preserva código/log y enmienda previa al reintento. La corrección agrega `if t.empty: continue`, patrón canónico ya existente. Manifest, fechas, variantes y criterios no cambiaron.

36perfiles = RTY/MNQ/YM × TF5/15min × umbral1/0,5TR20SMAprevia × permanencia120/60/30min. ROC60min, barras completadas, escala estrictamente previa, 600barraswarmup preservadas. Reservas H+60s, una posición por activo/perfil. La ventana también se amplía al acortarH:13:45/14:45/15:15ET últimasdecisiones. **No atribuir causalmente todo el aumento sólo aH.**

54fechas comunesOct–Dic2025 ya expuestas, noL2, no nuevos periodos ni holdout. Los contratos03-26 son vencimientos negociados en diciembre2025: NO se estudia marzo2026. Intenciones y quotes exportadas observables NO son fills/trades cerrados; no salidas, retornos, MFE/MAE, stops/targets ni selección por PnL.

## Frecuencia con umbral original1

| TF | Activo | H120: intents / mediana día | H60 | H30 | Fechas activas |
|---|---|---|---|---|---|
|5|RTY|108 / 2|243 / 4.5|440 / 8|54/54|
|5|MNQ|108 / 2|238 / 4|428 / 8|54/54|
|5|YM|107 / 2|245 / 5|438 / 8|54/54|
|15|RTY|86 / 2|146 / 3|216 / 4|48/54|
|15|MNQ|89 / 2|151 / 3|210 / 4|51/54|
|15|YM|95 / 2|154 / 3|227 / 4.5|51/54|

## Umbral más bajo0,5

| TF | Activo | H120: intents / mediana día | H60 | H30 |
|---|---|---|---|---|
|5|RTY|108 / 2|262 / 5|478 / 9|
|5|MNQ|108 / 2|267 / 5|475 / 9|
|5|YM|108 / 2|268 / 5|482 / 9|
|15|RTY|95 / 2|183 / 4|288 / 6|
|15|MNQ|100 / 2|191 / 4|302 / 6|
|15|YM|101 / 2|188 / 4|314 / 6|

Con5min/H120, bajar el umbral dejaRTY/MNQ108igual yYM107→108. Con15min/H30, mejoraRTY216→288,MNQ210→302,YM227→314: en esa escala sí aporta frecuencia. ATR/TR de cadaTF distinto: umbral1 no equivale a un mismo movimiento absoluto entre5/15min. Todas36celdas tienen quote de entrada observable para todas sus intenciones; nofill/edad dequote/salida certificada.

21/36cumplen meta diagnóstica predeclarada:mediana≥4intenciones/día incluyendo ceros,≥45fechasactivas,≥100intenciones. No es G1/G2 ni etiqueta de edge. No sumar estos perfiles solapados ni3índices correlacionados como muestras independientes. Tampoco1.000decisiones crudas son1.000trades mientras sigue abierta la primera posición.

## Revisión primero de herramientas EdgeLab

HEAD remoto de foundation verificado391314907dec889599493c4a38282171d94a2f25. Releídas entradas PROJECT_INDEX/AUDITOR_START_HERE/CURRENT y contrato de validación; instrucciones históricas se subordinan al protocolo del objeto.

- `universo_estudio.py`: puerta nativa, adaptador mecánico delcatálogo54fechas conservando fecha/archivo/n_ticks. Defaultsinholdout ni cuarentena; no cambiar alcance. Esto NO adjudica completitud canónica del Brain.
- `holdout_guard.py`: llamado antes de leer precios para rangoautorizado. Sellos/excepciones L2/ES/NQ no aplican a esta campaña.
- Productor causal previo: copiadas sólo funciones hash/scan/agregación/indicadores. No se empaquetó replay financiero ni evaluaciónPnl. Se conserva construcción original para comparar identidad.
- `bt2_absorption_power.py`: funciones genéricas puras `power_two_sided_ci`/`n_for_power`. NO se aplican SD ni conversiontick ni defaultsBT2 aRTY.
- `tools/sandbox/l3_power.py`: modelo ternario carrera/resolución, no usable directamente para retorno continuo momentum. No reasignar suN_eff a3índices.
- Bootstrap-t G2:54<160permanece bloqueado aun con478intenciones. No inventar potencia a partir del ganador previo.
- Simulador/nativefactory/NT8: sólo feed y paridadexacta futura permitirán llamar trades aestasreservas. Costos reales, quoteage, salidas y sizing siguen pendientes.

Tests nativos32PASS/1SKIP: omitida prueba con manifiesto de censo generado ausente en snapshotaislado. NO suite completa ni certificación universoBrain. Sintéticos9gruposPASS,18prefijos; regresiónlotesvacíos antes/después de batchreal. Dependencias pyarrow/pytest resueltas antes de ejecutartests; instruments.py añadido antes delprimerlanzamiento por dependencia nativa, no cambio método.

## Potencia: escenario, no estimación de esta estrategia

Con SD de estimando por sesión normalizada1 y alfa95% doscolas sin multiplicidad, efecto0,2SD requiere197sesiones para80%,0,3SD88,0,5SD32. A54sesiones potenciasaproximadas0,312/0,597/0,957. Son escenarios estandarizados ilustrativos, NO potenciaRTY estimada; dependencia y multiplicidad exigen diseño adicional. Y el mínimo formalG2160no se sustituye por esa aproximación.

## Auditoría y procedencia

Kaggle https://www.kaggle.com/code/nicolasbuttaro/edgelab-momentum-frequency-targetfree-20261001 v2 COMPLETE, privado. Manifest495a11a9d5ff73d5edfb2ac5880ac3f2b8b737bcb86d1d7831880f9d1f663c19 intacto. Scriptv1 328516ef81bfcfac50f96ea9943fa404706ad605081f43ee0f2e90bfa7703c0f; scriptv2 ccd2b9ba7f902cb5981936cd740e05bb25cfccbd8702ccb22d358c14aa142d7b. Preflight inspeccionado antes delcenso: código, productor, manifest ybaselineevents coincidenbytes,6parquetsSHA verificados porrunner. Transporte privadoembebido no publicado.

216comparaciones de prefijos PASS;593eventos delbaseline coinciden en identidad/dirección/U sin leerPnL en input. Todos36reconcilian contratos/meses/reservas/quotes. Comprobación independiente escalar sobreRTY12-25 confirma12conteos porcontrato, no reutiliza census.events; no se reclama auditoría independente de todoslosactivos. Ledgers originales se redujeron offline a camposdeevento antes detransportar, sinquotes/salidas/PnL. Repo publica agregados, no raw/URLsfirmadas ni ledgers privados.

## Continuidad propuesta

1. **RTY5min/H60/K1** es el siguiente contraste de mínima relajación deumbral:243intenciones,mediana4,5;H30/K1 tiene440/8 y mayorfricción. No elegir sólo por cantidad. ReplicaridénticasreglasMNQ/YM como contrastes; no presuponer queRTY anterior transfiere.
2. Conservar todas36variantes yregistrar selección/budget. H30 cambia horizonte yexposición: elresultadoeconómico anteriorH120 NOsetransfiere.
3. Antes decualquierretorno nuevo: congelar endpoints netos/control, costos explícitos, inferencia porfecha y multiplicidad delestudiocompleto, no mirar sólo el mejor. Operación exacta y quotesdesalida desconocidas debenbloquear, no excluirperdedores.
4. Si lafrecuencia alcanza peroelneto/estabilidadcontractualno, archivarlavariantenorescatarconhorario/stop. G2formal requiere mássesiones de desarrollo autorizadas/paridad; reservas intactas.

Aporte al referente: existe soporte para campañas más frecuentes, especialmente5min/H60oH30; frecuencia medible no esrentabilidadni potencia certificada.
