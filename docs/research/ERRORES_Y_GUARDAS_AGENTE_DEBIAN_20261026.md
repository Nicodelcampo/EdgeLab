# Errores a no repetir y guardas — para el agente del Debian (registro del 2026-10-25/26)

Estado: VIGENTE (registro vivo: cada error nuevo se agrega acá en el mismo commit que su arreglo)
Fecha: 2026-10-26. Pedido de Nico: «hacé lo necesario para que ninguno de esos errores se vuelva a repetir en EdgeLab, y dejá registro
detallado de todos los errores de los que el agente del Debian se tendrá que cuidar, proteger y encargar».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Complementa la tabla de `docs/research/GUIA_GRILLA_MASIVA.md` §2 (errores del 2026-10-22/24) y
`docs/research/areas_expansion_20261022/u1/REVISION_ERRORES_Y_PLAN_U1_CRUZADO.md`.

Cómo leer cada fila: **qué pasó → por qué importa → guarda (automática si dice «código»; si no, regla que el agente aplica) → qué hace
el agente del Debian**.

## A. Inferencia: matar de más o confirmar de más

| # | Qué pasó | Por qué importa | Guarda | Qué hace el agente |
|---|---|---|---|---|
| E1 | La etapa de **pistas** exigía cada una de 20 pistas a nivel LORD++/20 (p ≤ 0,0005 en 6 meses): potencia 1–2 %. Con 0 confirmadas cerraba la familia como SIN_CANDIDATAS. EXPZ y ZGAP murieron así aunque ZGAP-NQ dio 18/20 pistas positivas y su canasta +5,2 pts/sesión (p 0,04). | Mataba familias por falta de potencia, no de edge; sólo sobrevivía lo evaluado antes del embudo (U1-CRUZADO). | **Código**: `escalera.canasta_pistas` + `veredicto_pistas`; `embudo._fin_pistas` prueba primero la canasta (una prueba, su propio paso de LORD++). Sólo REFUTADA (canasta en contra con potencia) cierra; el resto queda **PISTAS_VIVAS**. Tests en `tests/research/test_falsos_negativos_embudo.py`. | Un SIN_CANDIDATAS anterior al 2026-10-26 **no** es una refutación: revisar su potencia antes de usarlo como antecedente. |
| E2 | Una réplica **sin resolución** (umbral < p mínimo posible: «un rechazo era imposible») igual cerraba la familia (EXPZ-CFD). | Una prueba que no puede rechazar no informa. | **Código**: `embudo._cerrar` convierte en PISTAS_VIVAS todo SIN_CANDIDATAS de pistas sin veredicto REFUTADA (`tests/test_guardas_20261026.py::test_E1`). | Si ve «sin resolución» en un MEDIDO, la campaña sigue viva. |
| E3 | Sin ventana reciente para replicar las pistas, la familia se cerraba como SIN_CANDIDATAS sin haber probado nada. | Muerte sin prueba. | **Código**: ahora cierra como PISTAS_VIVAS («no se pudo probar»). | Declarar `pistas_replica.ventana` en la campaña cuando el OOS no sirve. |
| E4 | Se leyó «en contra sobre 2023» como refutación de candidatas del régimen actual. | El pasado no mata (ATJ-24, Nico). | **Código**: etapa **ATRAS** informativa (`embudo._fin_atras`): publica A_FAVOR / EN_CONTRA_PASADO / NO_CONCLUYENTE, nunca cambia `candidatas`. | Lo que mata es el OOS reciente con potencia o el holdout. |
| E5 | Se llamó «sin potencia» a un resultado que SÍ tenía potencia para la mitad del efecto del DESC. | Etiqueta engañosa: oculta que el efecto grande quedó descartado. | **Código**: veredicto `SIN_RECHAZO` (con potencia, no alcanza el efecto del DESC, no está en contra) separado de `SIN_POTENCIA`. | Informar las dos cosas: «el efecto del DESC no está» y «uno menor sigue posible». |
| E6 | Evidencia **post-hoc** (la canasta calculada sobre una réplica ya mirada) es tentadora como confirmación. | Ajustar con los datos. | Regla: lo calculado sobre una ventana ya mirada sólo **planifica** (N del holdout), nunca confirma. El acta lo registra. | Confirmar sólo en datos no mirados (holdout, forward). |
| E7 | Persistencia: la correlación entre períodos mezclaba calidad **estática** de la celda (p. ej. pierde siempre por costos) con persistencia de **régimen**. | Una canasta «de régimen» parecería funcionar por la parte estática. | **Código**: `persistencia.persistencia(..., desfase=12)`; régimen = ρ(0) − ρ(12). Controles en `tests/research/test_persistencia.py`. | Toda medición de persistencia publica los dos desfases. |
| E8 | Abrir un holdout **sin potencia** gasta la única apertura de la familia (EXPZ-NQ habría necesitado > 6 años). | El holdout es el recurso más escaso. | **Código**: `tools/holdout_canasta.py acta` se niega si la potencia a N < 0,8 (salvo `--forzar` con decisión humana); el ACTA del embudo deja AVISO si la potencia del holdout < 0,5. | Calcular N con `potencia_planeada` antes de pedir el acta; si no alcanza, ganar potencia primero (más instrumentos, `NORMALIZAR`). |
| E9 | El nivel de LORD++ de una familia baja con cada paso (ZONAS_GAPS y EXPANSION_ZONAS ya en 0,0019). | Cada paso extra encarece todos los siguientes. | Regla. | No gastar pasos en lotes sin potencia; la canasta y las pistas son dos pasos: planificarlos. |
| E10 | Un cambio de regla de decisión podía aplicarse a una campaña a mitad de camino **después** de ver su resultado. | Relajar un gate después de mirar. | Regla (sin código todavía): la campaña se frena ANTES de la etapa afectada hasta que la regla nueva esté commiteada (se hizo con U1-ZONAS-AVCL-NQ). | Si se cambia una regla, listar qué campañas están en o antes de esa etapa y frenarlas primero. |

## B. Operación: conductores, Kaggle, kernels

| # | Qué pasó | Por qué importa | Guarda | Qué hace el agente |
|---|---|---|---|---|
| O1 | Conductor lanzado con la carpeta de estado (`--raiz`) equivocada: U1-ZONAS-NQ arrancaba de cero y habría relanzado su DESC. | Kernels duplicados, registro de pruebas doble. | **Código**: `tools/embudo_correr.py` se niega si la campaña tiene estado en otra carpeta (`problemas_conduccion`). | — |
| O2 | Dos conductores sobre la misma campaña. | Relanzan el mismo slug con estados distintos. | **Código**: lock `.conductor.pid` por campaña (ignorado por git); un segundo conductor se niega. | En el Debian conduce el timer (`conductor: debian`); nunca a mano además. |
| O3 | `pkill -f <patrón>` mató al propio shell que lo ejecutaba (el patrón está en su línea de comandos) y dejó el trabajo a medias. | Acciones cortadas sin aviso. | **Código**: `tools/embudo_correr.py --raiz R --detener CID` frena por pid. | Nunca `pkill -f`; usar `--detener` o `kill <pid>`. |
| O4 | Los conductores locales mueren con cada reinicio del contenedor; las campañas quedan en CORRIENDO sin nadie que las traiga. | Etapas que nunca terminan. | En el Debian lo cubre `edgelab-autopilot.timer` (cada 10 min). | Ver el estado con `--status`; una etapa CORRIENDO > 14 h ya la da por caída el embudo (`MAX_HORAS_KAGGLE`). |
| O5 | Un kernel que no arrancó (tope de sesiones de Kaggle, 404) se daba por «corriendo» para siempre. | Campañas trabadas. | **Código**: `KaggleRunner.estado` trata 404 / «no runs found» como error (relanza). | — |
| O6 | Kernels commiteados quedaron desactualizados al cambiar módulos que embeben (`grilla_generica`, `etapas`, `eventos`, `escalera`): CI rojo dos veces en el mismo día. | La guarda «script committeado» lanza código viejo. | **Código**: tests `*_al_dia` (CI) y `tools/reconstruir_kernels.py` (reconstruye todos). | Correr `python tools/reconstruir_kernels.py` antes de commitear cualquier cambio en `edgelab/`. |
| O7 | El kernel no embebía módulos con imports relativos (`sim.py` → `.holdout_guard`) ni lo que importan las etapas. | Falla recién en Kaggle. | **Código**: `embudo_runners.dependencias` resuelve imports relativos y suma las dependencias de los módulos base. | — |
| O8 | En Kaggle no hay `config/` (costos): un módulo que lee costos adentro del kernel falla. | Falla recién en Kaggle. | **Código**: la fricción viaja por entorno (`FRICCION`); el analizador la recibe por parámetro. | Nunca leer `config/` desde código que corre en el kernel. |
| O9 | Dos cuentas de Kaggle: sin la cuenta en el entorno, status/output van al host o la cabecera equivocados. | 401 o kernels «perdidos». | **Código**: `KaggleRunner._env(cuenta)` en lanzar/estado/traer; cabecera por cuenta (`kaggle_auth`). | Campañas nuevas con `"cuenta_kaggle": "auto"`. |
| O10 | Se tocó un archivo protegido (`tools/kaggle_launch.py`). | Rompe el manifiesto de protegidos. | **Código**: `tools/autopilot_protect.py check`. | Correrlo antes de cada commit; la cuenta viaja por entorno, no por el lanzador. |
| O11 | Un parche externo (Gemini v4) traía una base vieja y revertía blindajes. | Pérdida silenciosa de arreglos. | Regla. | De un parche externo aplicar sólo los archivos nuevos; nunca sobrescribir con su versión de archivos existentes. |

## C. Construcción: reutilizar, motor correcto, datos

| # | Qué pasó | Por qué importa | Guarda | Qué hace el agente |
|---|---|---|---|---|
| C1 | Se construyó un calendario de eventos propio cuando ya existía `edgelab/noticias.py` (con fuentes y la regla de las firmas). | Dos fuentes que pueden divergir. | **Código**: el filtro lee de `noticias.py` (`tools/eventos_desde_noticias.py` + test de frescura). Regla general: `python tools/existente.py buscar "..."` ANTES de escribir (ya en el prompt del programador). | Buscar también por concepto («noticias», «calendario»), no sólo por el nombre que uno pensó. |
| C2 | Se iba a usar `edgelab/engine.py` como motor: es **legacy**; el simulador formal es `edgelab/research/sim.py` (spec sellada). | Evidencia con fills distintos a los formales. | **Código**: el analizador usa un núcleo compilado idéntico a `sim.py` (test de equivalencia operación por operación). | Leer el docstring del módulo antes de reutilizarlo: si dice legacy, no. |
| C3 | Backtest en barras M1 habiendo ticks: objetivo y stop en el mismo minuto se resolvían como adverso. | Sesgo contra reglas de recorrido corto. | **Código**: `analizador` ejecuta tick a tick por defecto. | — |
| C4 | El backtest tick a tick en Python puro tardaba minutos por variante. | Pocas ideas probadas. | **Código**: núcleo numba (10 ms por variante sobre 20 M de ticks), una lectura de ticks por barrido. | Perfilar antes de lanzar (regla de la guía). |
| C5 | Candidatas de celdas raras (30–37 operaciones en 26 meses) que en el OOS daban 6, 1 y 0 operaciones. | OOS imposible de concluir. | **Código**: `seleccion.min_ops_oos` = 30. | — |
| C6 | Tests que fijaban la secuencia de etapas (OOS → TOPES) rompieron al agregar ATRAS. | CI rojo por cambio de flujo legítimo. | Regla. | Al cambiar el flujo del embudo, buscar `"TOPES"`, `"OOS"` en `tests/` y actualizar en el mismo commit. |

## D. Lo que el agente del Debian tiene que vigilar siempre (checklist por ciclo)
1. `tools/autopilot_protect.py check` → OK.
2. Ninguna campaña en CORRIENDO hace más de 14 h sin kernel vivo.
3. Ninguna familia se cierra como refutada sin veredicto REFUTADA (E1–E3); revisar los MEDIDO nuevos.
4. Antes de un acta: potencia planeada ≥ 0,8 (E8) y nivel de LORD++ de la familia (E9).
5. Al tocar `edgelab/`: `python tools/reconstruir_kernels.py` (O6) y tests verdes antes de commitear.
6. Antes de construir algo: `tools/existente.py buscar` (C1) y docstring del módulo (C2).
7. Ningún resultado post-hoc presentado como confirmación (E6).
8. Cambios de regla: frenar antes las campañas afectadas (E10) y consultar a Nico si es semántica de validación.
