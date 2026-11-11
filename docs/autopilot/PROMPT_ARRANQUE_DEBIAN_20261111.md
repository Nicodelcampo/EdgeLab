# Prompt de arranque para el agente del Debian (SV1) — 2026-11-11

Estado: VIGENTE (2026-11-11, pedido de Nico: «que ya empiece a trabajar, reportar fallas, asignar roles, probar que funcionen los
roles, sin tiempos muertos entre llamadas y midiendo el uso»). Se pega tal cual en la sesión de Claude Code de SV1.

---

Sos el operador del agente autónomo de EdgeLab en SV1. Nico autorizó arrancar. Trabajás desde `foundation/f0b-compatibility-probe`
al día (incluye el paquete `docs/autopilot/PAQUETE_DEBIAN_20261110.md`: leelo primero) y seguís `CLAUDE.md`, `config/autopilot/DIRECTIVAS.md`
y `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`. Lo que no puedas hacer sin root lo dejás listo para Gonza, con los
comandos exactos. Nunca imprimas credenciales. Respondé en castellano rioplatense y cerrá cada informe con «Aporte al referente: …».

## 1. Antes de arrancar (en este orden; si algo falla, frená y reportalo)
1. `git fetch && git status`, `.venv/bin/python tools/estado.py`, `.venv/bin/python tools/autopilot_protect.py check` (OK).
2. `bash deploy/debian/update.sh <punta de foundation>` siguiendo O20–O24 (libro LORD, TRIAL_REGISTRY, aperturas, manifiestos):
   verificá después que el LORD del clon y el del estado tengan el mismo sha256 y que esté la reserva `HFT_RUPTURA::rep_no_defiende_20261110`
   (ya resuelta).
3. Tests: `.venv/bin/python -m pytest tests/autopilot tests/research/test_banco_eventos.py tests/research/test_factores.py
   tests/research/test_fill_pasivo.py -q`.
4. Datos de Kaggle por cuenta: para cada cuenta de `EDGELAB_KAGGLE_CUENTAS` y para `nicolasbutta`, `datasets/view` de los 12 datasets.
   Si `edgelab-zonas-hft` ya da 200 en `nicobuttaro` y `nicolasbutta` (Nico lo está compartiendo), sumá `nicolasbutta` a
   `EDGELAB_KAGGLE_CUENTAS` (cambio de `/etc/edgelab/autopilot.env`: paso de Gonza). Si no, seguí con las dos de hoy.

## 2. Roles: asignar y PROBAR que funcionan
1. Fuente única: `config/autopilot/AGENTES.json` (arquitecto = proponente, abogado, meta_analista; ingeniero = programador; juez =
   revisor; auditor = revisor2, auditor; escribas = lector, bibliotecario, cronista; capataz determinista). No inventes roles.
2. `.venv/bin/python tools/agentes.py --write` y la autoprueba de conectividad (`tools/agentes.py`, función `probar`): cada modelo
   tiene que responder `ok=true`. Un modelo que falla se reporta con su detalle; el rol usa el `respaldo` declarado.
3. Prueba funcional de cada rol (no sólo conectividad): una llamada real y barata por rol con su entrada mínima válida (p. ej. el
   revisor sobre un borrador ya existente, el meta-analista sobre `RESULTADO_OP1_DESARROLLO.md`, el lector sobre una ficha corta). Para
   cada uno, registrá: salida válida contra su esquema, núcleo de contexto completo (sin recortes; `contexto.con_nucleo` no debe
   fallar por presupuesto), modelo usado, tokens y duración. Resultado en `docs/autopilot/PRUEBA_ROLES_<fecha>.md`.
4. Si un rol falla dos veces seguidas por la misma causa, no lo reintentes a ciegas: causa raíz, arreglo con test, y recién ahí reintento.

## 3. Arrancar el trabajo
1. Quitá `PAUSE` y poné `embudo.activo: true` **sólo después** de 1 y 2 en verde, con estas reglas para lo que quedó colgado:
   - U1-ORO-GRILLA: no relanzar hasta que haya ticks de GC sellados en `edgelab-holdout-sellado` (error O15). Marcala en espera de datos.
   - U1-ZONAS-AVCL-NQ y U1-ZONAS-BT2-NQ: relanzar con el código actual sólo en una cuenta que vea `edgelab-zonas-hft`; si ninguna lo
     ve, en espera de datos.
   - Los 4 slugs de la ventana 20261023: se rigen por la frontera vigente (`desde 20261001`); si su ventana no coincide, se relanzan.
   - Toda apertura de holdout sigue el protocolo (`edgelab/autopilot/holdout_apertura.py`), una por familia, registrada antes de lanzar.
2. Prioridades de investigación (núcleo `factores_con_ventaja` y `PAQUETE_DEBIAN_20261110.md` §5):
   a. Lente `remedir`: primera candidata de `REMEDICIONES_CANDIDATAS.md`, verificada en su carpeta.
   b. OP-2: continuación en el primer regreso a un cluster HFT grande (la pista viva `F-HFT-CLUSTER-GRANDE-NO-DEFIENDE-C`), con
      geometría fija, fills por stop y su nulo; pre-registro antes de medir. NO uses abr–sep de NQ/ES/RTY/YM/GC para elegir nada:
      ya está gastado para esta línea.
   c. OP-3: veto HFT en fades de otras familias (en bruto, K2).
   d. Lo que la rotación de lentes proponga, con banco de eventos cuando haya tabla.
3. NO decidas por tu cuenta la apertura del holdout de `HFT_RUPTURA` en modo exploratorio: prepará el acta (probabilidades de azar
   de desarrollo: 0,088 DESC independiente, 0,052 réplica) y dejala para Nico.

## 3b. Herramientas nuevas del 11/11 (usarlas siempre; están en el núcleo como `cadena_de_corrida`)
- Diseño: `python tools/antecedentes.py "<idea>" --familia F` antes de escribir un pre-registro.
- Una familia de reglas sobre eventos = UN módulo con el contrato de `edgelab/research/tablas.py` (plantilla
  `edgelab/research/plantilla_tabla.py`) y `python tools/tablas.py preflight|lanzar|traer|explorar|curva|congelar|confirmar|holdout`.
  Nada de simuladores, kernels ni análisis propios (el revisor los mata).
- Cierre: `python tools/cierre.py` antes de cada commit. Activar `"tablas": {"activo": true}` en `/etc/edgelab/autopilot.json`
  (paso de Gonza) para que el ciclo traiga solo las tablas terminadas.
- Guía corta: `docs/research/CADENA_DE_CORRIDA.md`; origen y pendientes: `docs/autopilot/AUTOMATIZACION_PROCESOS_20261111.md`.

## 4. Sin tiempos muertos entre llamadas
Hoy hay huecos de diseño: `edgelab-autopilot.timer` espera 10 min entre ciclos (`OnUnitInactiveSec=10min`); el proponente corre
una vez por día (06:17) y el programador una vez por día (07:41).
1. Medí primero: con el libro de llamadas (`llm_calls` en el SQLite de `RoleRunner`, `edgelab/autopilot/roles.py`) y los logs de
   `journalctl`, calculá por día el tiempo entre el fin de una llamada y el comienzo de la siguiente, y cuánto de ese tiempo hubo trabajo
   pendiente (cola de propuestas, revisiones, kernels por traer). Ese «hueco con cola» es el tiempo muerto a eliminar.
2. Proponé por PR (los timers los instala Gonza con root): ciclo con `OnUnitInactiveSec=1min` y salida inmediata si no hay trabajo;
   proponente y programador disparados por el ciclo cuando su cola tiene trabajo (no por hora fija), respetando los topes de la
   suscripción (`governor`) y el paralelismo de 8; un kernel terminado se trae en el ciclo siguiente.
3. Objetivo medible: hueco con cola < 2 min de mediana. Reportalo antes y después del cambio.

## 5. Medir el uso (siempre)
Reutilizá antes de construir (`tools/existente.py buscar "uso tokens costo por rol"`). Si no existe, `tools/uso_agente.py` con test:
- **LLM:** por día y por rol y modelo: llamadas, éxito/error, tokens de entrada y salida, costo informado, duración, reintentos.
- **Kaggle:** por cuenta: kernels lanzados, terminados, en error, horas de CPU/GPU, cola (de `account_launches.jsonl` y `kaggle_kernel.py`).
- **Tiempo muerto:** el hueco con cola de §4.
- **Producción:** propuestas, revisiones (PROMOTE/DERIVE/KILL), corridas, resultados, factores asentados.
Publicalo cada día en `docs/autopilot/USO_<fecha>.md` (y un resumen de una línea en la sala).

## 6. Reportar fallas
- Toda falla (rol, kernel, sincronización, test, dato faltante) va a `docs/research/REPORTE_ALINEACION_AGENTE_DEBIAN_20261027.md`
  con causa raíz; si es un error nuevo, fila nueva en `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` con su guarda en código y test.
- Lo que necesita a Nico o a Gonza (datos por sellar, permisos, root, holdout) va en una lista corta «Para humanos» al principio del
  reporte, con el comando o el link exacto.
- Cambios de código: rama propia + PR a foundation, tests verdes; nunca push directo a foundation.

## 7. Pendientes humanos conocidos (no los resuelvas vos)
Rotar el token de `nicolasbutta`; compartir `edgelab-zonas-hft` (https://www.kaggle.com/datasets/nicolasbuttaro/edgelab-zonas-hft)
con nicobuttaro y nicolasbutta; sellar GC (y ES/NQ que falten) en `edgelab-holdout-sellado`; instalar los timers nuevos.
