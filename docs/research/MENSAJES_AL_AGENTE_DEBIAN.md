# Mensajes al agente del Debian

Estado: VIGENTE. Canal escrito desde la sesión en la nube de Nico (el agente del Debian no es alcanzable por mensajes entre sesiones).
Cada mensaje lleva fecha, remitente y origen. Lo más nuevo, arriba.

## 2026-10-27 (17:30 UTC) — de Nico (redactado por la sesión en la nube): el arreglo O13 no alcanzó; ya está corregido

**Qué pasó.** Las 5 campañas U1 (U1-ES, U1-YM, U1-ORO, U1-ZONAS-ES, U1-ZONAS-NQ) volvieron a quedar BLOQUEADA en CONTEO después de
la reapertura de las 02:18 UTC. El log del kernel `nicolasbuttaro/embudo-u1-ym-grilla-holdout-conteo-20261001` sigue diciendo
`KeyError: 'r_vol'` en `grilla_generica.resumen_e0` (línea 330): O13 arregló el índice `k`, pero con 0 disparos el DataFrame vacío
de U1 tampoco trae las columnas de las variables, y si no trae `k`, la línea del `ses` rompe igual. El test de O13 no lo cazaba
porque su DataFrame vacío traía las columnas.

**Arreglo (este commit):** `resumen_e0` trata la columna faltante como vacía, y `correr` no lee `D.k` si no existe. Dos tests nuevos
en `tests/research/test_guardas_20261027.py` reproducen exactamente el caso del kernel. Kernels reconstruidos.

**Qué te toca:**
1. `update.sh` a este commit (con pausa), y **reabrir las 5 a CONTEO** igual que hiciste con O13 (crash de infraestructura, el acta
   sigue vigente, nada del holdout se miró).
2. **Lección para tu checklist:** después de reabrir por un arreglo, mirá el log del primer kernel relanzado antes de dar el arreglo
   por bueno. Esta vez se bloquearon de nuevo a las 03:12 y nadie lo vio en 14 horas. Agregalo como guarda (O16) en
   `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`: una reapertura que vuelve a fallar igual dispara alerta, no un tercer reintento mudo.
3. **El generador:** el estado de `mandate.json` no frena la generación en el código (sólo es un WARN del doctor), así que el mandato
   en BORRADOR no explica por qué no propone. `edgelab-autopilot-generate.service` aparece fallido en `alertas.jsonl` (5 veces entre el
   26 y el 27): buscá la causa raíz en `journalctl -u edgelab-autopilot-generate.service` y arreglala, o decí qué falta.
4. U1-ZONAS-NQ: `kernels.get` sobre `nicobuttaro/…` sigue dando 403 desde afuera de esa cuenta. Es esperable (kernel privado de la otra
   cuenta), pero confirmá que vos lo leés con la cabecera de `nicobuttaro`.
5. **Tus dos preguntas abiertas** (3 vs 4 en paralelo; cómo viaja el estado del clon) siguen esperando a Nico; mientras tanto, dejá 4
   y el estado sólo por `autopilot/state`.

## 2026-10-27 — de Nico (redactado por la sesión en la nube): usá las dos cuentas de Kaggle + directivas en tu contexto

**Pedido de Nico:** si podés, **aprovechá las dos cuentas de Kaggle** (`nicolasbuttaro` y `nicobuttaro`) para las corridas: repartí
los kernels entre ambas (`"cuenta_kaggle": "auto"`), y si una rechaza por tope de kernels simultáneos o cuota, reintentá en la otra.
Reportá en el estado cuántas corridas fueron a cada cuenta.

Desde este commit, las directivas vigentes de Nico (autorreparación, pensar fuera del molde, espiral, dos cuentas, estructura que no
se rompe) viven en **`config/autopilot/DIRECTIVAS.md`** y entran en el paquete de contexto de cada rol en cada ciclo
(`directivas_de_nico`, nunca se recorta). Leelo primero.

## 2026-10-27 (05:25 UTC) — de Nico (redactado por la sesión en la nube): espiral de automejora con datos + Internet

**Directiva permanente (Nico):** trabajá en **espiral**: cada vuelta aprende de los datos y de lo que ya se midió, y la siguiente arranca
mejor. Sumado a pensar fuera del molde y a **investigar en Internet**.

Una vuelta de la espiral (proponé tu propio ritmo; como referencia, una por día):
1. **Medir:** qué terminó desde la vuelta anterior (embudos, analizador, ATRAS, holdout), con sus potencias y MDE.
2. **Aprender:** meta-análisis (`tools/metaanalisis_embudo.py`) y lectura de los resultados: qué mecanismos, instrumentos, horarios,
   perillas y ejecuciones se repiten en lo que vive y en lo que muere; qué se cerró sin potencia. Escribilo en un archivo vivo
   `docs/research/APRENDIZAJES_ESPIRAL.md` (vuelta, evidencia con rutas, lo que cambia en la próxima) — es la memoria de la espiral.
3. **Investigar afuera:** buscá en Internet papers, notas de microestructura, blogs serios de practitioners, foros de prop firms y
   documentación de exchanges sobre los mecanismos que viven o sobre huecos que no cubrimos. Sumá lo útil al corpus (CerebroSSRN /
   biblioteca) con la fuente citada. Lo de Internet es **inspiración, nunca evidencia**: sólo cuenta lo que pase el embudo con nuestros datos.
4. **Proponer:** hipótesis nuevas o refinadas (incluidas las fuera del molde), cada una con justificación económica, cómo podría
   refutarse, linaje y cuánta potencia tendría con los datos que hay. Priorizá por valor esperado / costo de cómputo.
5. **Correr:** pre-registro, contador global, embudo. Nada se elige mirando el holdout.
6. **Mejorarte:** una mejora concreta de la herramienta o del proceso por vuelta (velocidad, robustez, una guarda nueva, un control
   que faltaba), con test.
7. **Contar:** resumen corto en la sala al cerrar la vuelta: qué aprendiste, qué cambiaste, qué corre, qué falta.

Para no autoengañarse (la espiral no puede convertirse en buscar hasta encontrar): toda vuelta suma sus pruebas al contador global y a
LORD++; lo aprendido de una familia no se usa para «rescatar» esa misma familia con los mismos datos; lo que se refina con datos ya
mirados se confirma sólo con datos nuevos (réplica no mirada u holdout a N fijo).

## 2026-10-27 (05:15 UTC) — de Nico (redactado por la sesión en la nube): pensá fuera del molde

**Directiva permanente (Nico):** no te limites a hacer lo que se te pide. Pensá, proponé y mejorá — a vos mismo y a los análisis — de
forma creativa, autónoma y proactiva, **sin romper la estructura** (embudo, pre-registro, contador global, LORD++, firewall del holdout,
costos canónicos, CLAUDE.md).

Qué significa en la práctica (ideas, no una lista cerrada; inventá las tuyas):
- **Sobre los análisis:** leé el registro MEDIDO/NO MEDIDO, los resultados del embudo y el corpus de papers, y buscá huecos: familias que
  nadie probó, cruces entre instrumentos, variables de régimen, ejecuciones distintas, datos que existen y nadie usa. Diseñá barridos
  propios con `grilla_generica` (guía §6) sobre indicadores PASS o causales propios, con su pre-registro. Que cada idea tenga
  justificación económica y cómo podría refutarse.
- **Sobre lo que ya se midió:** meta-análisis de tus propias campañas (`tools/metaanalisis_embudo.py`): qué tipos de hipótesis mueren y
  por qué, dónde falta potencia, qué perillas nunca importan; usalo para que la próxima campaña sea mejor y más barata.
- **Sobre vos mismo:** medí tu rendimiento (ciclos, kernels por día, fallas, tiempo muerto por cupo de Kaggle, tokens) y atacá el cuello
  de botella; automatizá lo que hoy se hace a mano; agregá guardas y tests a partir de cada error (registro de errores).
- **Sobre la infraestructura:** si una herramienta es lenta, frágil o duplica otra, mejorala (reutilizar antes de construir:
  `tools/existente.py`).
- **Proponé en la sala** lo que no puedas o no debas hacer solo, con una recomendación concreta.

Límites que siguen (la estructura): nada se elige mirando el holdout; todo resultado pasa por el embudo y se registra antes de correr;
nunca se relaja un criterio después de ver resultados; cambiar gates/FDR/mandato/archivos protegidos sigue lo que dice CLAUDE.md; no se
opera con dinero real. Dejá constancia de cada iniciativa propia (qué, por qué, resultado) en `docs/research/` o en la sala.

## 2026-10-27 (04:30 UTC) — de Nico (redactado por la sesión en la nube): arreglate solo; primer caso, el CONTEO del holdout

**Directiva permanente (Nico):** el Debian se arregla a sí mismo. Tené un monitoreo global del proyecto y de vos mismo: en cada ciclo,
mirá tu propio estado y actuá sin esperar a nadie. Como mínimo:
- campañas en `BLOQUEADA` o con `fallas > 0` → bajá el log del kernel (`kernels/output`), encontrá la causa raíz, arreglá el código,
  tests, commit con la causa, y desbloqueá la campaña para que reintente **la misma etapa** (sin rehacer etapas ya hechas ni reabrir
  ventanas del holdout);
- unidades systemd en `failed`, timers que no corren, la rama `autopilot/state` sin commits nuevos, CI rojo en `foundation`;
- registrá cada incidente y su arreglo en `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` y, si se puede, agregá una guarda
  (test o chequeo) para que no se repita.
Lo único que no es tuyo: operar con dinero real.

**Puntapié inicial — incidente abierto ahora:** 5 campañas terminaron `FIN BLOQUEADA` tras 3 fallas en `CONTEO`: U1-ES-GRILLA,
U1-YM-GRILLA, U1-ORO-GRILLA, U1-ZONAS-ES, U1-ZONAS-NQ. Log del kernel (`nicolasbuttaro/embudo-u1-es-grilla-holdout-conteo-20261001`):
`grilla_generica.resumen_e0 → KeyError: 'r_vol'`.
- **Causa (diagnóstico de la nube; verificalo):** la gramática U1 (`u1_oro.escala_por_mes`, que usan u1_cfd, u1_zonas, u1_zonas_avcl,
  u1_zonas_bt2, u1_racimos_grilla, u1_zonas_grilla) escala cada mes con el rango M1 del mes ANTERIOR y el primer mes de la ventana no
  dispara. El holdout empieza el 2026-10-01 y el dataset sellado sólo trae octubre → **cero disparos**; y `grilla_generica.correr` llama a
  `resumen_e0` antes de chequear `len(D)`, así que con D vacío (columnas de `VACIO`) se cae en vez de devolver n=0.
- **Probablemente afecte también** a las que siguen en CONTEO (U1-ZONAS-BT2-NQ, U1-RACIMOS-GRILLA-ES/NQ, U1-ZONAS-AVCL-NQ).
- **Arreglo propuesto:** (1) que la escala del primer mes del holdout salga del mes anterior en DESARROLLO (septiembre no es holdout):
  por ejemplo congelar `escala_seg` del mes de arranque en el acta al abrirla y pasarla en PARAMS al CONTEO, o montar septiembre del
  dataset de desarrollo como calentamiento sin que entre al conteo; (2) en `correr`, devolver resultado vacío con n=0 cuando `D` está
  vacío, antes de `resumen_e0`; (3) test que reproduzca el caso (ventana de un solo mes) y uno que verifique que el calentamiento no
  cuenta operaciones; (4) desbloquear las 5 con sus mismas actas (N y nivel de LORD++ ya reservados) — no se miró ninguna operación,
  así que no hay consumo nuevo del holdout.
- Avisá en la sala cuando esté resuelto, con el commit.

## 2026-10-27 (01:55 UTC) — de Nico (redactado por la sesión en la nube): generador caído y estado sin publicar

1. **`edgelab-autopilot-generate.service` en `failed` desde el 26-oct 06:19.** El bug conocido del paso `propose` (`TypeError: dict() got
   multiple values for keyword argument 'lente'`) está arreglado desde el PR #127 (mergeado el 25-oct), que SV1 ya tiene (está en
   `87b11b78` o posterior). Con el código actual `propose` corre bien (probado en la nube con `proponente: true`). Lo más probable es que
   el `failed` sea de una corrida con código viejo y la unidad quedó marcada. Hacé:
   `sudo systemctl reset-failed edgelab-autopilot-generate.service && sudo systemctl start edgelab-autopilot-generate.service`
   y mirá `journalctl -u edgelab-autopilot-generate -n 50`. Si vuelve a fallar con otro error, arreglalo vos (causa raíz en el commit).
2. **PR #141 (sync_state: heartbeat.json) mergeado.** Actualizá con `update.sh` (con pausa, sin corrida en curso) para que el estado
   empiece a publicarse en `autopilot/state`; confirmá en el próximo ciclo que la rama aparece en GitHub.
3. Avisá en la sala cuando los dos estén en verde.

## 2026-10-27 (01:45 UTC) — de Nico (redactado por la sesión en la nube): todo junto

1. **Actualizá el código del SV1 a foundation con `update.sh`, ya** (con pausa y sin corrida en curso, como siempre). Trae los kernels
   pre-armados reconstruidos (`tools/kaggle_grilla/kernel_*.py`): sin ellos algunas etapas fallan o quedan desalineadas.
2. **El archivo de credencial lo revisa una persona, no vos** (tu clasificador lo bloquea y está bien que lo haga). Gonza o Nico
   corren en el SV1 estos dos comandos; ninguno imprime el token:
   ```
   sudo -u edgelab curl -sS -o /dev/null -w '%{http_code}\n' -H @/opt/edgelab/.kaggle_auth_header.nicobuttaro https://www.kaggle.com/api/v1/datasets/view/nicolasbuttaro/edgelab-holdout-sellado
   sudo awk '{print NR": "$1, $2, substr($3,1,5)"…", "largo="length($3)} END{print "lineas="NR}' /opt/edgelab/.kaggle_auth_header.nicobuttaro
   ```
   200 = resuelto. Si da 403 y la segunda no muestra exactamente una línea `Authorization: Bearer KGAT_…` (token nuevo) o
   `Authorization: Basic …` (clave vieja), hay que reescribir el archivo con ese formato.
3. **Vos sí podés** verificar (sin leer el archivo) que `EDGELAB_KAGGLE_OWNER=nicobuttaro` le llega al proceso que lanza los kernels de
   las tres campañas fijadas (U1-ZONAS-NQ, ZGAP-CFD, ZGAP-NQ): `embudo_runners.KaggleRunner._env`. Si no llega, arreglalo vos.
4. Cuando quede en 200, avisá en la sala y dejá que esas tres campañas se lancen con `nicobuttaro`.

## 2026-10-27 (01:35 UTC) — de Nico (redactado por la sesión en la nube): el 403 de `nicobuttaro` en `edgelab-holdout-sellado`

Nico dice que **el token de `nicobuttaro` está bien y lo tenés**. Y el dataset **ya está compartido**: desde la nube, con la credencial
de `nicobuttaro`, `datasets/view/nicolasbuttaro/edgelab-holdout-sellado` da **200** y la descarga da **302** (autorizada); lo mismo
`edgelab-zonas-u1` y `edgelab-liquid-ticks-20261014`. Lo más probable es que lo hayas probado antes de que Nico lo compartiera.

Qué hacer, en orden (sin preguntar; arreglá vos lo que encuentres):
1. **Repetí la prueba ahora**, con la cabecera de esa cuenta:
   `curl -sS -o /dev/null -w '%{http_code}\n' -H @/opt/edgelab/.kaggle_auth_header.nicobuttaro https://www.kaggle.com/api/v1/datasets/view/nicolasbuttaro/edgelab-holdout-sellado`
   Si da 200: listo, avisá en la sala y dejá que las campañas fijadas a `nicobuttaro` sigan su curso.
2. Si sigue en 403, revisá **el formato del archivo** (sin imprimir el token): tiene que ser exactamente una línea
   `Authorization: Bearer KGAT_...` (token nuevo) o `Authorization: Basic <base64 de usuario:clave>` (clave vieja), sin comillas ni
   saltos de línea extra. Un token KGAT con Basic, o usuario/clave con Bearer, falla.
3. Revisá **qué cabecera usa el servicio de verdad**: `tools/kaggle_auth.py` elige `<KAGGLE_AUTH_HEADER_FILE>.<EDGELAB_KAGGLE_OWNER>`
   sólo si `EDGELAB_KAGGLE_OWNER` llega al proceso (`embudo_runners._env`). Si la variable no llega, cae a la cabecera única (la de
   `nicolasbuttaro`) y un kernel de `nicobuttaro` se crea con la cuenta equivocada.
4. Si con todo eso sigue el 403, decilo en la sala con el código exacto y la URL (nunca el token).

## 2026-10-27 — de Nico (transcripto por la sesión en la nube)

> «Auto corregí tus propios errores, ya que estás en modo prueba.»

Alcance, tal como lo entiende la sesión que lo transcribe (si hay duda, preguntale a Nico en la sala):
- Si algo que **vos** hiciste falla (un CI rojo por tu PR, un kernel desactualizado, un conductor caído, una campaña que no arranca),
  arreglalo y pusheá sin esperar confirmación, con causa raíz en el commit.
- **Aclaración de Nico (2026-10-27): es todo autónomo.** Aprobar las corridas y abrir el holdout los decide el agente, con los
  protocolos en código (`edgelab/autopilot`, `edgelab/autopilot/holdout_apertura.py`), sin esperar a nadie. Lo único que CLAUDE.md
  deja fuera de eso es *modificar* esos protocolos y gates (FDR, mandato, archivos protegidos) y operar con dinero real.
- Errores conocidos a no repetir: `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (por ejemplo O6: tocar un módulo embebido
  obliga a `python tools/reconstruir_kernels.py`; O12: `python tools/docs_index.py --write` antes de commitear estado).
