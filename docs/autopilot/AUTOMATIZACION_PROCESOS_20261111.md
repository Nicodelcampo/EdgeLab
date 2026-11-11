# Procesos de una corrida que se pueden automatizar o estandarizar (relevamiento del 2026-11-11)

Estado: PROPUESTA (pedido de Nico, 2026-11-11: «repasá todos los pasos de la corrida de recién… cuáles se pueden automatizar,
estandarizar o simplificar para que el agente del Debian ahorre tiempo y tokens, se equivoque menos y lance más y mejores
corridas»). Sin implementar: Nico pide la implementación después.
Fuente: lo que hubo que hacer a mano en LUXIMB-HVN (`docs/research/luximb_hvn_20261111/`), en OP-2 y en la apertura del holdout de
HFT_RUPTURA (`docs/research/hft_clusters_u1_20261110/`), las tres del 2026-11-11.

Prioridad: **A** = ahorra mucho o evita errores ya cometidos; **B** = ahorra tokens o tiempo; **C** = comodidad.

## 0. Contexto: qué hizo el Debian anoche
- Corrió **sólo lo que no depende del ciclo**: la prueba de conectividad de modelos (01:09 UTC, 4/4 ok), el proponente diario
  (09:30 UTC, una propuesta y un pedido de código: `tools/orb_ema20_bruto_neto.py`) y la promoción mecánica.
- **El ciclo principal no corre**: `PAUSE` existe desde hace más de 24 h y el watchdog avisa «último ciclo hace ≈ 17.600 min»
  (≈ 12 días). Ningún embudo ni kernel se lanzó.
- **Las 11 promociones de anoche se rechazaron mecánicamente por lo mismo**: el instrumento de la propuesta es una etiqueta
  (`MULTI`, `DATA`, `BLOCKED`, `GC_ES`, `NQ_YM`) y la guarda de fricción no encuentra costo medido. Es un error de formato del
  proponente, no de la idea (ver P1).

## 1. Razonar la corrida (diseño)
| # | Paso hecho a mano | Costo o riesgo observado | Propuesta | Prio |
|---|---|---|---|---|
| R1 | Buscar los antecedentes de la idea: docs, familias, factores, holdout consumido, código existente (≈ 15 grep y lecturas) | muchos tokens; riesgo de no ver un antecedente (la regla del visor estaba en 4 carpetas) | `tools/antecedentes.py "<idea>"`: con `existente.buscar` + FAMILIAS + FACTORES + LINAJES + HOLDOUT_VENTANAS, una ficha de una página: familias parecidas, últimos desenlaces, NO_REPETIR, código reutilizable y ventanas ya gastadas | A |
| R2 | Calcular qué datos quedan sin mirar para el linaje (DESC/REP gastados; USATECH 2023–25 limpio; holdout desde 23-oct) | razonamiento largo y propenso a error (O15, K19) | `presupuesto_datos(familia, instrumentos)`: por instrumento y fuente, ventanas consumidas, limpias, holdout disponible y aperturas usadas, contra el catálogo de datos | A |
| R3 | Enumerar el espacio de eventos, separar evento y estado, elegir control | regla de CLAUDE.md, se escribe a mano cada vez | plantilla del pre-registro con las secciones obligatorias que `validar_prereg` exige (espacio de eventos, control, justificación, refutación, EF, hash del North Star, conteo, datos por uso) | A |
| R4 | Decidir ejecuciones (stop, objetivo, parcial, BE, entrada en la vuelta) | se reinventa por familia (op2 `_op`, `fill_pasivo`, `areas_expansion.simular`, `luximb_hvn._e0_nb/_ext_nb`) | **biblioteca de ejecuciones declarativas** (§2-I3): el diseño elige de un menú (`E0`, `EXT`, `LIMITE`, `CONT`) con parámetros | A |
| R5 | Escribir hipótesis previas y contar pruebas | conteo hecho a mano (27.600) | el conteo sale solo de la especificación (definiciones × ejecuciones × filtros) | B |

## 2. Implementación
| # | Paso hecho a mano | Costo o riesgo observado | Propuesta | Prio |
|---|---|---|---|---|
| I1 | Escribir el módulo de eventos (`eventos(ctx)`, rasgos, `desenlaces(E, ctx)`) | ≈ 220 líneas por familia | **contrato «tabla de eventos»**: el experimento sólo declara `eventos(ctx)` y `rasgos`; los desenlaces y su convención de columnas (`r_<ej>`, `k_<ej>`, definiciones booleanas) los pone el motor común | A |
| I2 | Parametrizar un módulo existente (definición del impulso) | **error real**: los valores por defecto atados a constantes al importar rompieron el oráculo (los tests cambian las constantes con monkeypatch) | regla de lint + test: parámetros nuevos con `None` y resolución en la llamada; el chequeo corre en `tests/test_existente.py` | B |
| I3 | Simulador tick a tick propio | **error real**: acreditar el stop en su nivel infla ≈ +0,3 R en una caminata con saltos | un solo motor de ejecuciones (`edgelab/research/ejecucion.py`) con la convención fija: stop a mercado al tick que cruza; objetivo/parcial límite en su nivel; tope por velas, sesión y hueco; fills pasivos con «atraviesa» | A |
| I4 | Rasgos de volumen (perfil por franjas) | escrito de cero | biblioteca de rasgos causales (`rasgos_comunes.py`): perfil de volumen por franjas relativas, régimen, hora, distancia a zonas/clusters HFT; cada uno con su test de prefijo | B |
| I5 | Lista de módulos del kernel a mano (12 rutas) | olvidar un import = kernel roto en Kaggle | `construir_kernel` resuelve las dependencias por el grafo de imports de `edgelab` | A |
| I6 | `main` del kernel (fuente, ventana, ctx, CSV + JSON con sha del código) | repetido en cada familia | un kernel genérico `tabla_main.py` que recibe `MODULO` y `FUNCION`; los lectores, el sellado y el JSON de procedencia van incluidos | A |
| I7 | `tools/<familia>.py lanzar/traer` (slug, datasets, needs, chequeo de push) | repetido; errores O19 (slug con «_»), push silencioso | un lanzador genérico `tools/tablas.py lanzar <modulo> <fuente> <ventana>` + `traer` con verificación de código vigente, y lanzamiento por lote con una sola orden | A |
| I8 | Dependencia ausente (`scipy`) en el análisis, descubierta al correrlo | falló justo en el análisis congelado del holdout | test que prohíbe en `tools/` y `edgelab/` imports fuera del lock; utilidades estadísticas comunes (Fisher, BH, Stouffer) en un módulo | A |
| I9 | Curva de capital en SVG a mano (sin matplotlib) | 60 líneas | `tools/curva_r.py`: curva IS / OOS / holdout desde cualquier tabla con `r_`/`k_` | C |

## 3. Lanzamiento y operación
| # | Paso hecho a mano | Costo o riesgo observado | Propuesta | Prio |
|---|---|---|---|---|
| L1 | Prueba local del kernel con fuente sintética | se hizo a mano, 3 intentos (fecha mal puesta) | `preflight` ejecuta el kernel generado con `FUENTE=SINT` antes de todo lanzamiento | A |
| L2 | Agendar «traer cuando termine» y volver a mirar | turnos y tokens gastados en esperar | el ciclo del Debian trae solo las tablas terminadas (cola de kernels con su `traer`), sin intervención | A |
| L3 | Registro de lanzamientos y estado (account_launches, launches/*.json) quedaban sin commitear | aviso del hook | el lanzador commitea su propio registro | C |
| L4 | Promociones rechazadas por instrumento = etiqueta (`MULTI`, `DATA`) | 11/11 rechazadas anoche | el proponente emite una lista de instrumentos reales; la guarda de fricción toma el peor costo de la lista; una propuesta sin instrumentos reales vuelve al proponente con el motivo | A |
| L5 | `PAUSE` olvidado más de 24 h | 12 días sin ciclo | además de la alerta: la sala recibe una sola vez por día el motivo y el paso que falta para quitarlo | B |

## 4. Validación
| # | Paso hecho a mano | Costo o riesgo observado | Propuesta | Prio |
|---|---|---|---|---|
| V1 | Tests a mano del simulador (objetivo, stop, parcial, BE, cancelación) | se escriben por familia | con el motor único (I3), los tests son del motor, una vez | A |
| V2 | Test de causalidad por prefijo | escrito a mano | test genérico para cualquier `eventos(ctx)`: cortar el contexto y comparar rasgos (ya existe `preflight.certificar_causalidad` para grillas: extenderlo a tablas) | A |
| V3 | **Calibración del motor con eventos al azar en una caminata sin deriva** (así apareció el sesgo del stop) | fue una sospecha mía, no un chequeo | chequeo automático del preflight: entradas al azar en sintético con y sin saltos → R medio ≈ 0 con su error; si no, no se lanza | A |
| V4 | Pasar una tabla sintética por el análisis y ver que el mejor resultado cae dentro del nulo | hecho a mano | parte del preflight del análisis: falla si con datos sin efecto declara algo | A |

## 5. Filtrado, embudo y robustez
| # | Paso hecho a mano | Costo o riesgo observado | Propuesta | Prio |
|---|---|---|---|---|
| F1 | Script de análisis por familia (cortes fuente × período, R neto con costos, fricción en R, estabilidad, top) | ≈ 160 líneas | **analizador genérico de tablas** (`banco_eventos` ampliado): lee la convención `r_`/`k_`, aplica costos de `edgelab/costos.py` por fuente, informa DESC/REP por separado, la guarda de fricción ≤ 0,08 R y el nulo de la búsqueda completa | A |
| F2 | Estabilidad con permutaciones en todas las celdas (demasiado lento) | corrida cortada por tiempo | estadístico barato para todas y permutaciones sólo para las de arriba (ya en el script; pasa al genérico) | B |
| F3 | Nulo de la búsqueda (mejor t por azar con todas las celdas) | lo escribí aparte | parte del analizador genérico; toda tabla de exploración lo muestra arriba | A |
| F4 | Congelar hipótesis, registrar k, generar la tabla de confirmación y probar una vez | hoy a mano y con riesgo de mirar antes | `tools/congelar.py`: escribe el archivo de hipótesis con su hash, registra pruebas y LORD/BH, y recién ahí lanza la tabla de confirmación; el análisis de confirmación queda congelado por el hash | A |
| F5 | Apertura del holdout (acta, `registrar_apertura`, modo sellado del kernel, Fisher con p de desarrollo, una sola corrida) | ≈ 1 h de trabajo y un error (scipy) | `holdout_exploratorio.abrir(familia, generador, hipotesis)` que hace todo el protocolo con el kernel genérico (I6) | A |
| F6 | Merge de PR con el catálogo de herramientas desactualizado (dos PR lo regeneran por separado) | CI rojo dos veces | regenerar los archivos generados en el merge (acción de CI que commitea) o un test que compare contra la regeneración en vez del archivo | B |

## 6. Interpretación y cierre
| # | Paso hecho a mano | Costo o riesgo observado | Propuesta | Prio |
|---|---|---|---|---|
| C1 | Escribir RESULTADO_*.md (tabla, veredicto, MDE, lectura) | tokens; riesgo de maquillar | informe generado del JSON con plantilla fija: veredicto por regla (A_FAVOR / EN_CONTRA / NO_CONCLUYENTE / SIN_POTENCIA), MDE y potencia siempre, sin texto libre en el veredicto | A |
| C2 | Entradas de FACTORES, MEDIDO/NO MEDIDO, LINAJES, TRIAL_REGISTRY | 5 archivos a mano por resultado | `tools/asentar.py <resultado.json>`: propone la entrada de FACTORES (con `reemplaza`), la fila de MEDIDO y el conteo | B |
| C3 | Regenerar índices (catálogo, docs_index, familias, factores, remediciones) y correr sus tests antes de commitear | olvidado más de una vez (CI rojo) | `tools/cierre.py`: regenera todo, corre los tests de índices y deja el commit listo; gancho de pre-commit | A |

## 7. Orden de implementación sugerido
1. **Motor único de ejecuciones + calibración automática** (I3, V1, V3): ya evitó un sesgo; todo lo demás lo usa.
2. **Contrato de tabla de eventos + kernel y lanzador genéricos con preflight sintético** (I1, I5–I7, L1, V2): una familia nueva
   pasa a ser un módulo de `eventos(ctx)` y una especificación.
3. **Analizador genérico + congelar + holdout** (F1–F5, C1): la cadena exploración → congelado → confirmación sin código propio.
4. **Antecedentes y presupuesto de datos** (R1, R2): ahorran el mayor gasto de tokens del diseño.
5. Operación (L2, L4, L5) y cierre (C2, C3, F6, I8, I9).

Estimación: con 1–3, la corrida de LUXIMB-HVN habría sido una especificación de ≈ 60 líneas más el módulo de eventos, en vez de
≈ 700 líneas nuevas y cinco errores encontrados durante el trabajo.
