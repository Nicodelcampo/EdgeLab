# Leer antes de cada corrida — índice obligatorio (v5, 2026-11-28)

Estado: VIGENTE — pedido de Nico: «un documento que sea obligatorio leer para cada corrida, que sea un índice de todos los otros
documentos que se deberían leer». La v3 responde a su segundo pedido: «asegurate que la cadena estándar no te permita cometerlos […] no
debe ser falta de información, seguramente es falta de gobernabilidad, estandarización y acceso a los datos».
North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

**Cómo se cumple:**
- **Línea obligatoria:** todo pre-registro nuevo lleva «Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — …», diciendo qué secciones
  aplican.
- **Quién la exige:** `edgelab/research/preflight.py::validar_preregistro`. Sin ella, `tools/registro_global.py preregistrado` no
  cuenta la corrida y el CI la rechaza.
- **Versiones:** este índice se versiona; si cambia, sube la versión.
- **Principio de la v3:** lo que se puede impedir en código se impide (§6, columna «guarda»). Este documento queda para lo que no se
  puede.

## 0. Dónde estamos (siempre)
- `CLAUDE.md` (estado vigente y rituales) y `docs/research/VEREDICTO_M1_20261117.md` (qué regla está viva, refutada o sin medir).
- `docs/research/FACTORES_CON_VENTAJA.md`: lo que hay que indagar primero y la lista NO_REPETIR.
- `docs/research/FAMILIAS.md` y `docs/research/LINAJES.jsonl`: de qué familia deriva la idea y qué ya usó.
- `python tools/antecedentes.py "<idea>"`: su línea va al pre-registro.

## 1. Antes de diseñar
- **Cadena estándar:** `docs/research/CADENA_DE_CORRIDA.md`. Un módulo con el contrato de `tablas`, motor único y comandos fijos; nada
  de simuladores, kernels ni análisis propios.
- **Reutilizar:** `python tools/existente.py buscar "<qué>"`, `docs/MODULES.md`, `docs/HERRAMIENTAS.md`.
- **Según el tipo de corrida:**
  - grilla grande: `docs/research/GUIA_GRILLA_MASIVA.md` (K4: más de 500 celdas con retornos exige un E0 antes);
  - muchas ideas sobre los mismos eventos: `docs/research/BANCO_DE_EVENTOS.md`;
  - régimen: `docs/research/GUIA_REGIMEN_PARA_AGENTE_20261107.md`;
  - estrategia de afuera: medir la regla exacta primero (ritual del visor, CLAUDE.md).
- **Población y espacio de eventos declarados** (CLAUDE.md, reglas permanentes).
- **Causalidad:** todo lo que decide en la vela k usa velas ≤ k COMPLETAS. Una vela de 5 min «armada» con los minutos que hay todavía
  no cerró. `tools/tablas.py preflight` lo prueba sobre datos reales (disparos y cortes arbitrarios).

## 2. Datos, holdout y ventanas
**Acceso a datos (estándar desde la v3):**

| Dato | Cómo se obtiene | Dónde queda | Lector |
|---|---|---|---|
| M1 de futuros de NT8 (NQ, ES, YM, GC, EMD, RTY; 2006/2008 → hoy) | `python tools/datos.py traer M1NT8` (o `importar` de una copia que coincida con el origen) | `data/m1nt8/` con `PROCEDENCIA.json` (sha256 y tamaño por archivo) | `fuentes_ticks.bloques_m1nt8` (corta en la frontera) |
| Ticks del release y CFD | Kaggle, dentro del kernel (`tools/tablas.py lanzar`) | `/kaggle/input` | `fuentes_ticks.resolver` |
| Costos | `edgelab/costos.py` (`config/costos/costos_canonicos.json`) | — | `embudo_runners.friccion` |

- `python tools/datos.py estado` dice qué está local y si coincide con el origen.
- Las herramientas leen `datos.ruta("M1NT8")` por defecto; una carpeta bajada a mano ya no hace falta ni se acepta como evidencia.
- **Holdout:**
  - frontera única y partición A5: `edgelab/holdout.py`, `docs/incidents/AMENDMENT_HOLDOUT-A4_2026-10-22.md` y
    `docs/incidents/AMENDMENT_HOLDOUT-A5_2026-11-17.md`;
  - ventanas ya consumidas por la familia o su linaje: `docs/research/HOLDOUT_VENTANAS.jsonl`.
- **M1 como pseudo-ticks:**
  - **K40:** el stop sale en su nivel salvo hueco en la apertura (`ctx["m1_sintetico"]`, motor único y de grilla).
  - **K30:** M1 no ve saltos dentro de la vela. Toda familia en M1 se calibra contra ticks reales ANTES de correr: `a5_campana.py
    calibracion`, con el criterio único `a5.calibrar_por_sesion`.
  - No se usa para footprint, velas de ticks ni señal en un CFD.
- **Kaggle:**
  - un dataset privado se lanza con la cuenta dueña (`docs/research/atras_m1_20261117/FALLIDAS.jsonl`);
  - con el tope de cola o un 429, `tablas.py traer` relanza lo que quedó en cola: no lanzar a mano;
  - consultar cada ≥ 5 min.

## 3. Medición (dónde más nos equivocamos)
- **Medir en R** (`docs/research/MEDIR_EN_R_20261102.md`), con el riesgo INICIAL de la propia regla. Verificar en el código que la
  columna de riesgo sea el stop inicial.
- **K35–K37:** unidad de riesgo propia, parámetros en puntos fijos entre épocas y puntos entre años
  (`docs/research/m1_largo_20261117/AUDITORIA_Y_VIEJAS.md`).
- **Bruto y neto siempre juntos**, con la fricción en R por época. El «antes no, ahora sí» suele ser fricción relativa.
- **Neto con el mini y con el micro**, los dos, por instrumento (`a5.evaluar` acepta la fricción por fila `f_<ejec>`). El micro tiene
  más fricción por punto; una prop firm suele operar micros.
- **Un agregado que no cuadra con otra fuente:** antes de culpar al motor, comparar operación por operación y usar la MISMA función de
  agregación que la serie de referencia (K47).
- **Variables de régimen o contexto:** se declara a qué hora se conocen y se comparan con la hora de cada entrada (K48). «Del día» no
  alcanza: para una regla nocturna, el día empieza a las 18:00 del anterior.
- **Capas de entrada** (esperar, filtrar o confirmar un gatillo): el valor de no entrar es 0 y no paga fricción, así que el contraste
  neto contra la entrada inmediata favorece siempre al que menos entra. Se decide con el R absoluto por gatillo y contra un placebo
  de la misma espera.
- **Costos:** sólo de `edgelab/costos.py`. Los estimados, sólo dentro de `costos.estimados_permitidos(<pre-registro>)` (K33).
- **K39, unidad monetaria:** multiplicador del contrato que se opera de verdad.

## 4. Inferencia, confirmación y decisión
- **Errores y guardas:** `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (A, E2, E3, E5 y E6) y
  `docs/research_funnel_playbook.md` (ATJ).
- **Potencia antes de abrir:** `python tools/potencia_previa.py <ops>` (K27), y la potencia calculada **al nivel LORD++ reservado**,
  no a 0,05 (K42).
- **BH:** las pruebas con n < 30 quedan fuera (K29). Todo nulo publica su MDE.
- **Decisiones de validación:** `docs/research/revision_20261024/DECISIONES_VALIDACION_20261024.md` (el OOS mata sólo con potencia;
  FDR; LORD++).
- **K38:** la regla de un tercero se prueba fuera de lo que su autor pudo usar.
- **Selección:** lo elegido entre muchas variantes con poca historia arranca con media ≈ 0. ORB O1 lo volvió a mostrar: el «+0,16 neto
  en NQ 2020–25» de DESC+REP dio −0,03 bruto en el holdout.
- **Árbol para confirmar algo nominado** (en este orden; el forward es lo último, no lo primero):
  1. **Réplica** (meses REP de A5), con su nivel LORD++.
  2. **Holdout A5 del instrumento** (meses HOLDOUT, apertura única por familia), si la potencia al nivel reservado llega a 0,8.
  3. **Instrumentos que la familia nunca usó** (EMD, RTY, GC… con M1 de NT8), sumados al 2 en una sola lectura si hace falta
     potencia.
  4. **Forward desde la frontera terminal**: vigila y da tamaño; no reemplaza a 2–3.
- **Canastas y prop firms:** una simulación de cuenta sólo usa reglas confirmadas o las marca SIN CONFIRMAR en la misma tabla. Un
  subgrupo de DESC+REP (instrumento × época) no es una regla confirmada.

## 5. Proceso (K32) y cierre
`antecedentes.py` → `potencia_previa.py` → pre-registro con «Antecedentes:», «Potencia previa:» y «Lectura previa:» → commit →
`python tools/registro_global.py preregistrado …` → **commit de `TRIAL_REGISTRY_GLOBAL.jsonl`** → correr → resultado con su entrada en FACTORES y su línea MEDIDO en el mismo commit →
`python tools/cierre.py` sin tubos → `git show --stat` → push.

**Corrida con código que después se corrigió:**
- se aparta (`descartada_vN/`, `*.NO_VIGENTE.*`) y se relanza;
- su documento se marca DESCARTADA;
- lo que la citaba (FACTORES, VEREDICTO, CLAUDE.md, carteras) se actualiza en el mismo commit.

## 6. Errores de la etapa 15–18 nov y su guarda
Columna «guarda»: **código** = la cadena no deja pasar el error; **guía** = depende de leer esto.

| Error | Qué pasó | Guarda | Dónde |
|---|---|---|---|
| Stop de M1 al extremo de la vela (K40) | LuxImb no calibró (12/12); el «atrás» del 17-nov y papel M1 del 15-nov sesgados (−0,16 R) | código | `ejecucion._stop_m1`, `areas_expansion.simular_cierre_m1`, tests de `test_ejecucion`; simulador registrado (K28) |
| Velas de 5 min incompletas (IB, ORB) | decidía en el minuto 2 con un «cierre» que no era tal | código | `tablas.py preflight` (causalidad sobre datos reales); certificado por huella en `config/causalidad_certificados.json` |
| Controles y requisitos que miraban el futuro (ESCALONADAS) | el placebo se ubicaba según eventos posteriores; k+1 sin cerrar | código | el mismo preflight; control por hash del minuto |
| Tabla de ticks de código viejo (K41) | la calibración de ESCALONADAS comparó tablas viejas; `traer` salteaba lo ya bajado | código | `tablas.traer`/`_tablas`, `a5_campana._ticks` |
| Contraste perdido en `a5.evaluar` | el control que no era definición no se evaluaba | código | test `test_a5_evalua_contraste_…` |
| Veredicto de calibración a mano (K43) | ASIA se aprobó con «≈ 1 ee» usando otro EE | código | `a5.calibrar_por_sesion`; `tools/papel_m1.py validacion` → JSON |
| Potencia a α 0,05 (K42) | se dijo 0,9; al nivel reservado 0,0036 era ≈ 0,5 | código | `holdout_ventanas._exigir_alfa_reservado` |
| Script que no compilaba (K44) | paréntesis de más en una herramienta sin test | código | `test_todo_el_codigo_compila` |
| Datos en una carpeta temporal pasada a mano | no reproducible, sin verificación contra el origen | código | `tools/datos.py` (ruta verificada por defecto) |
| Forward propuesto antes que el holdout disponible | se iba a esperar meses teniendo holdout A5 e índices sin usar | guía | §4 árbol; `CADENA_DE_CORRIDA.md` |
| Neto sólo con micro | la fricción «alta» era la del micro | guía | §3; los resultados nuevos reportan mini y micro |
| Subgrupo sin confirmar en una canasta de prop firm | ORB5 en Lucid por el neto de NQ 2020–25 | guía | §4 canastas; aviso en `SENALES_ESTABLES_LUCID_20261118.md` |
| Lanzamientos que no salieron (cola de Kaggle, 429) | ORB YM y filtro ES/YM quedaron sin lanzar | código | `tablas.reintentar_cola` (dentro de `traer`) |
| Columnas de identidad perdidas en OPS (K45) | el análisis pareado del filtro de picos no podía emparejar gatillos | código | `a5_campana.columnas_ops` |
| Factor vivo apoyado en evidencia descartada (K46) | ASIA «noche movida» siguió viva citando un largo DESCARTADO | código | `test_ningun_factor_vivo_se_apoya_en_evidencia_descartada` |
| Agregaciones distintas en una validación (K47) | ASIA «duplicaba» a los ticks; se culpó al motor M1, que coincidía operación por operación | código | `papel_m1.validacion` con `canasta_por_sesion` y su test |
| Variable de régimen conocida después de la entrada (K48) | la «noche movida» de ASIA usaba el rango de la misma noche en que opera | código | `papel_regimen.CONOCIDA_H`, `mapa`/`encendido` con `t_entradas` |
| K48 en el atlas de FundedSync | noche/gap/orb15 con módulos que entran de noche: 7 «elegidas» falsas | código | `fundedsync_mecanismos.CONOCIDA_EJE` |
| Gastar REP en una prueba sin potencia (K49) | GEX: la etiqueta binaria se probó en REP con potencia ≈ 0,3; la variable útil salió después y no quedó dato limpio | código + guía | `a5.plan_lectura` / `exigir_potencia` (días, nivel LORD), `a5_campana rep`; cadena completa pre-registrada antes de REP |
| Registro .jsonl malformado (K50) | 19-nov: LINAJES.jsonl con una línea vacía y dos objetos pegados; `antecedentes.py` se cayó y el alta siguiente quedó pegada | código | `tests/test_gobernanza_20261118.py::test_jsonl_de_registros_parsean_linea_por_linea`; los registros se escriben con su herramienta o con `json.dumps(...)+"\n"` |
| Correr sin estar contada (K51) | 19-nov: `preregistrado` se negó (faltaba la justificación) y la corrida de FRICCION-RQ arrancó igual porque la cadena de comandos seguía tras un `;` | código | `registro_global.exigir_contada(prereg)` al inicio de toda herramienta ad hoc que mida desenlaces; nunca encadenar el lanzamiento con `;` después del conteo |
| Definición que nunca dispara en datos reales (K53) | 19-nov: FM6 de FLUJOS-MACRO no disparaba: la sesión CME empieza 18:00 del día previo y `mo >= 495` tomaba esa vela; el test sintético no cruza medianoche | código | `a5_campana.calibracion` frena si una definición no tiene disparos en la ventana de calibración; tests con M1 real cuando hay copia local |
| Insumo externo ausente en el kernel de ticks (K54) | 19-nov: FM7 de FLUJOS-MACRO coincidía en 42/209 sesiones entre ticks y M1: el kernel de Kaggle no tenía el parquet de CBOE y el módulo cayó en silencio a RV5/ATR (OPTION-ALPHA igual); ticks y M1 midieron reglas distintas | código | `a5_campana.insumos_distintos` frena la calibración si el M1 trae una columna de contexto que la tabla de ticks no; `tablas.insumos_externos` adjunta el dataset M1NT8 a todo módulo que lea CBOE o el calendario |
| Grilla de casi-copias o celdas vacías; promedio dominado por episodios (K55, K56) | 19-nov: la «variante rápida» de Z tenía 4 operaciones; A20 tiene 1,2 variantes efectivas de 81; el «apagado desde 2018» de IBS/Double Seven/pico de VIX lo hacían 3 meses de crisis | práctica | publicar operaciones por celda y número efectivo de variantes antes de leer meseta o PBO; descomponer por meses antes de declarar una regla apagada (`docs/research/MIRADA_HUMANA_20261119.md`) |
| Ranking móvil con huecos | `rolling(250)` dejaba sin estado medio año tras un feriado | código | ranking sobre sesiones con dato |
| Registro global sin commitear antes de correr | ASIA-NOCHE-PREVIA se contó antes, pero el registro entró recién después del resultado | guía | §5: commit del registro inmediatamente después de contar |
| Contraste neto con 0 al no entrar | el «neto» favorecía no entrar hasta con gatillos al azar | guía | decidir por R absoluto por gatillo y contra el placebo (§3) |
| `git add -A` en un commit de campaña | entraron resultados de otras campañas | guía | rutas explícitas y `git show --stat` |
| Presupuesto de contexto de los agentes | el cierre fallaba cuando FACTORES crecía y se compactaban entradas para entrar | humano + código | Nico lo elevó el 18-nov (juez y auditor 260.000, arquitecto 400.000, `config/autopilot/AGENTES.json`); `test_agentes` exige ≥ 25 % libre. No se achica contenido para entrar: se sube el tope |


## 7. Cómo se hace bien: el caso Z (v4, 2026-11-19 — K55/K56, obligatorio)
**Lo que salió mal.** La noche del 18 al 19-nov recomendé la «variante rápida» de Z (cubeta 10, EMA 10) porque los promedios marginales de la
grilla la favorecían. Tenía **4 operaciones en 18 años**. A20 se presentó con «81/81 variantes positivas» y tenía **1,2 variantes efectivas**
(3 de 4 perillas no cambiaban nada). La reversión corta se declaró «apagada desde 2018» cuando el signo lo hacían **3 meses de crisis**. Ningún
gate lo vio: lo encontró la pregunta de Nico («tiene una curva parecida a R, ¿por qué no entra?»).

**Lo que hay que hacer, en este orden, antes de leer cualquier grilla o veredicto por época:**
1. **Operaciones por celda** antes que su R: una celda con pocas operaciones no es una variante.
2. **Qué hace cada perilla en el mecanismo** (leer el código del módulo): en Z, cubeta y EMA mueven lo mismo (la severidad del filtro «ninguna
   cubeta toca la EMA»); en A20, tres perillas son inertes.
3. **Número efectivo de variantes** (participación de autovalores de las series mensuales): 81 casi-copias no son evidencia de meseta.
4. **Eje de severidad / dosis-respuesta:** correlación de rango entre operaciones y R. Si existe, la lectura correcta es la dosis-respuesta y
   la banda de configuraciones equivalentes, no «la mejor variante» (Z: la fábrica estaba en una meseta de 9 configuraciones).
5. **Episodios:** un promedio por época se descompone por meses antes de llamar «apagada» a una regla.

**Cómo se cumple (en código, no de memoria):**
- Pre-registro: línea obligatoria `Diagnóstico de mecanismo: …` (qué mueve cada perilla y cómo se va a leer la grilla, o «no aplica — motivo»).
  `preflight.validar_preregistro` la exige; sin ella `registro_global.py preregistrado` no cuenta y la corrida no arranca.
- Resultado: `python tools/diagnostico_grilla.py <ops> --variante … --valor R` imprime las líneas `Diagnóstico de grilla: …` y
  `Episodios: …`. `tests/test_diagnostico_obligatorio.py` hace fallar el CI si un RESULTADO nuevo lee meseta/PBO/«N/N variantes» sin la
  primera o declara una regla apagada sin la segunda.
- Ejemplo completo bien hecho: `docs/research/z_pico_20261119/RESULTADO_RAPIDA_Y_SEVERIDAD.md`; el error y su revisión:
  `docs/research/MIRADA_HUMANA_20261119.md`.


## 8. Errores del 26–27 nov y su guarda (v5, 2026-11-28)
Detalle de cada uno: `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (K58–K64).

| Error | Qué pasó | Guarda | Dónde |
|---|---|---|---|
| Hora de una fuente externa distinta de la documentada (K58) | HistData: Nueva York con horario de verano, no «EST fijo»; T, R y Z no calibraban | código | `edgelab/research/alineacion_horaria.py::exigir_alineada`, en invierno y en verano, antes de medir |
| Costo en la escala de otro instrumento o época (K59) | puntos de NQ restados a índices europeos en la escala de 2010: 5–7 pb en vez de ≈ 1 | guía | costo en pb del destino; publicar fijo y proporcional (K34) |
| Cambiar la muestra después de ver el resultado (K60) | cripto 2019: se sacaron 3 meses en cero para pasar de t 1,64 a 1,73 y rotular CONFIRMA | guía + revisión cruzada | el veredicto sale de la muestra pre-registrada; lo demás es sensibilidad |
| Insumo exógeno de otro mercado al transferir (K61) | VBB con VIX de EE. UU. en Europa y Asia | guía | insumo local o regla excluida, decidido en el pre-registro |
| Recomendar una fuente de datos sin verificarla (K62) | TradingView no tiene intradía de bonos de BYMA | guía | verificar símbolo y temporalidad antes de recomendar una compra |
| `registro_global.py` sin argumentos consolidaba (K63) | se reescribió el registro global sin querer | código | ayuda sin argumentos; `consolidar` explícito; `tests/test_guardas_20261127.py` |
| Ventana móvil que cruza meses sellados (K64) | medias y desenlaces de BONOS-RATIOS tocaban meses HOLDOUT/EMBARGO | código (patrón) | máscara `limpio` de `tools/bonos_ratios.py::_serie` |
| `ESTADO_VIVO.md` sin regenerar tras tocar FACTORES | CI en rojo (5 tests) | código (CI) | `tools/contexto_vivo.py --write` en el mismo commit |

**Lo que salió bien y se reutiliza** (prácticas ATJ-28 a ATJ-31 de `docs/research_funnel_playbook.md`):
- confianza sin forward (otros mercados, período anterior, placebo, Sharpe deflactado parejo);
- compuerta de calibración del circuito de datos;
- auditoría cruzada entre agentes con revisión de admisibilidad;
- localizar un mecanismo por dónde no se transfiere.
