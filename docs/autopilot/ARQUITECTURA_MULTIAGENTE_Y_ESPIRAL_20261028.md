# Auditoría Integral del Agente Debian (`SV1`), Sistema Multi-Agente (`2 Opus + 1 Sonnet`) y Arquitectura en Espiral de EdgeLab

**Fecha:** 28 de octubre de 2026  
**Rama troncal de referencia:** `foundation/f0b-compatibility-probe` (`faad4600`)  
**Alcance:** Cosecha completa del embudo (`Ola 1` a `Ola 5`), diagnóstico de desincronización y fallas del agente del servidor Debian (`SV1`), diseño del sistema multi-agente óptimo, protocolo de auditoría automática de alineación (`auditor_alineacion.py`), sincronización automática de ramas (`auto_sync_code.sh`) y taxonomía modular en espiral (`docs/MODULES.md` + `APRENDIZAJES_ESPIRAL.md`).

## 1. Cosecha Completa del Embudo (`Ola 1` a `Ola 5` — 28 de Octubre de 2026)

Se ejecutaron y cosecharon las 5 olas de corridas en Kaggle a través del puente `EdgeLab_Bridge`, completando el recorrido pre-holdout de **`CORREDOR-VOL-GAPS` v2** (`edgelab.research.corredor_vol_gaps`, acoplando `EmaCorridorTrendVolW2.cs` con `ZonasDeGaps.cs` en futuros CME y CFDs Dukascopy) y destrabando las campañas de zonas y racimos **`U1-RACIMOS-GRILLA-NQ`** y **`U1-ZONAS-GRILLA-YM`**.

| Campaña | Módulo / Par | `DESC` (`FDR q≤0,10`) | `INDAGA` | `INTEGRIDAD` (Placebo y Latencia 1v) | `OOS` (`2026-04..2026-09`) | `TOPES` | Estado Final Hoy |
|---|---|---|---|---|---|---|---|
| **`CVGAP-NQ`** | `corredor_vol_gaps` (`NQ->NQ`) | `83.052` eval. / **`297` FDR** (`RW 4,21`) | `3` candidatas | **`3/3` pasan** (`c1`: `+$14,64/op`, plac. `-$3,13`, lat1v `+$15,47`) | **`+$19,13/op`** (`n=88`, `58` ses., `IC90 [+$4,51, +$33,21]`, `p=0,0153`, `meseta=True`, `4/4` econ., `86,6%` cons.) | Elegido `['mult', 4.0]` (`puntaje=2,825`, `peor=-$221,80`) | **`CONTEO` (`ACTA` pre-holdout registrada, `n=150`, `α=0,00361`)** |
| **`U1-RACIMOS-GRILLA-NQ`** | `u1_racimos_grilla` (`NQ->NQ`) | `955` eval. / **`77` FDR** (`RW 3,44`) | `3` candidatas | **`3/3` pasan** (`+$25,67`, `+$24,24`, `+$23,72/op`; lat1v `+$27,85`, `+$22,19`, `+$23,43`) | **`3/3` positivas**: `+$32,83/op` (`IC90 [+$15,93, +$52,34]`, `p=0,0044`), `+$19,78/op`, `+$5,74/op` | Elegida `c1` `[1,0,0,9,1,0]` con `['pts', 100.0]` (`puntaje=9,156`, `peor=-$70,80`, ambas mitades `p≤0,004`) | **`CONTEO` (`ACTA` pre-holdout registrada, `n=150`, `α=0,00361`)** |
| **`CVGAP-CFD-NQ`** | `corredor_vol_gaps` (`USATECH->NQ`) | `71.792` eval. / **`80` FDR** (`RW 4,31`) | `3` candidatas | **`3/3` pasan** (`+$17,56`, `+$17,19`, `+$13,27/op`; lat1v `+$16,45`, `+$16,39`, `+$12,25`) | **`3/3` positivas**: `c0` y `c1` **`+$10,50/op`** (`n=110`, `69` ses., `p=0,085`, `meseta=True`, `4/4` econ., `69,6%` cons.), `c2` `+$7,41/op` | Elegida `c0` `[0,1,0,0,2,3,2,1,2,0,10]` con `['pts', 50.0]` (`puntaje=11,321`, `peor=-$74,80`, `+$17,84/op` `p=0,0010`) | **`CONTEO` (`ACTA` pre-holdout registrada, `n=150`, `α=0,00361`)** |
| **`U1-ZONAS-GRILLA-YM`** | `u1_zonas_grilla` (`YM->YM`) | `932` eval. / `1` cand. (`RW 3,27`) | `1` candidata | **`1/1` pasa** (`+$12,78/op`, plac. `-$5,90`, lat1v `+$17,10`, lat2v `+$19,81`) | **`+$3,65/op`** (`n=32`, `22` ses., `meseta=True`, `100%` cons.) | Sin tope dio `+$12,78/op` (`p=0,0020`), pero ningún tope sostuvo ambas mitades (`pts:150` `1ª mitad -$2,81/op`) | **`FIN / SIN_REGLA_OPERABLE`** |
| **`CVGAP-ES`** | `corredor_vol_gaps` (`ES->ES`) | `55.664` eval. / `0` FDR (`20` pistas) | `20` pistas a réplica | — | Canasta de 20 pistas: **`+$5,99/op`** (`p=0,180`); pista `p3` **`+$24,47/op`** (`n=60`, `p=0,0049`) | — | **`FIN / PISTAS_VIVAS`** (señal viva por sub-régimen horario `ORIG100`) |
| **`CVGAP-CFD-ES`** | `corredor_vol_gaps` (`USA500->ES`) | `46.506` eval. / `0` FDR (`20` pistas) | `20` pistas a réplica | — | Pista `p0` positiva (`+$4,15/op`, `n=94`, `61` ses.); canasta agregada `-$5,55/op` (`potencia=0,50 < 0,80`) | — | **`FIN / PISTAS_VIVAS`** (`SIN_POTENCIA`) |

### Hallazgos Empíricos Clave que Alimentan la Espiral
1. **Tres nuevas reglas con `ACTA` pre-holdout registrada antes de mirar (`CVGAP-NQ`, `CVGAP-CFD-NQ` y `U1-RACIMOS-GRILLA-NQ`)**:
   - En `CVGAP-NQ`, la celda `[0, 0, 1, 2, 2, 2, 3, 2, 0, 2, 11]` (`50T`, caja amarilla `W2=200%`, percentil `P80`, excursión `>= 2,0x H_amarilla` en dirección del impulso, regreso al borde de la caja amarilla `R_CAJA`, target `50%` del impulso `T50`, stop en el extremo de la caja `S_CAJA`, `G_TOM >= 1` gap barrido en la excursión, ventana `SIG`, franja `ORIG100`) mantuvo el `86,58%` de su efecto fuera de muestra (`+$19,13/op` en OOS sobre `88` operaciones y `58` sesiones) y aprobó `TOPES` con `['mult', 4.0]`.
   - En `U1-RACIMOS-GRILLA-NQ`, la celda `[1, 0, 0, 9, 1, 0]` aprobó `INTEGRIDAD` (`+$24,24/op`, latencia 1 vela `+$22,19/op`), sostuvo OOS positivo (`+$19,78/op`, acompañada por `[1, 0, 0, 9, 2, 1]` con `+$32,83/op` y `p=0,0044`) y coronó `TOPES` con `['pts', 100.0]` (`puntaje = 9,1561`, `1ª mitad +$26,44/op p=0,0005`, `2ª mitad +$22,03/op p=0,0040`, `peor = -$70,80`).
2. **Confirmación Cruzada CFD $	o$ Futuro (`CVGAP-CFD-NQ`)**:
   - Medir la caja amarilla y los gaps sobre el CFD Dukascopy (`DK:USATECHIDXUSD`) y ejecutar en el futuro `NQ` nominó `80` celdas por FDR (`q <= 0,10`), pasó `INTEGRIDAD` en las `3/3` candidatas (`+92%` a `+95%` conservado bajo latencia de 1 vela) y arrojó `3/3` medias positivas en OOS (`+$10,50/op` en `110` operaciones y `69` sesiones con `meseta=True` y `4/4` criterios económicos aprobados).

## 2. Diagnóstico del Agente del Debian (`SV1`): Planificado vs. Real

Contrastamos toda la documentación, planificación e infraestructura del agente del Debian (`config/autopilot/DIRECTIVAS.md`, `edgelab/autopilot/*`, `deploy/debian/*`, `docs/autopilot/ARQUITECTURA_MULTIAGENTE.md`, `docs/research/MENSAJES_AL_AGENTE_DEBIAN.md`, `docs/research/REPORTE_ALINEACION_AGENTE_DEBIAN_20261027.md`, `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` y `docs/research/agente/PLAYBOOK_CREATIVIDAD_Y_ESCALA_20261024.md`) contra su comportamiento real.

### 2.1. Por qué el Agente del Debian NO se actualiza automáticamente y queda aislado en su rama

Identificamos **cuatro causas técnicas exactas** en el código y en los scripts de despliegue:

1. **Pinning en `detached HEAD` sin bucle de actualización (`deploy/debian/install.sh` y `deploy/debian/update.sh`)**:
   - Tanto `install.sh` como `update.sh` ejecutan `git checkout -q --detach "$1"`. No existe ningún timer ni paso pre-ciclo en `edgelab/autopilot/__main__.py` que haga `git fetch origin foundation/f0b-compatibility-probe` y avance en fast-forward cuando el árbol está sano. Por diseño estático de `update.sh`, el servidor quedó congelado en commits antiguos (`6c54ca75` / `a0bfeb22`) mientras el desarrollo avanzaba a `faad4600`.
2. **Bloqueo por Árbol Sucio (`Dirty Worktree Deadlock`) causado por el propio Embudo**:
   - Según documentó el propio Debian en `REPORTE_ALINEACION_AGENTE_DEBIAN_20261027.md` (§C), durante cada ciclo del daemon, el embudo y los lanzadores escriben archivos de estado vivo directamente dentro del clon de código `/opt/edgelab/EdgeLab` (`CODE_DIR`): `docs/research/EVALUABLES.jsonl`, `docs/research/LIBRO_LORD.json`, `docs/research/autopilot_runs/account_launches.jsonl` y 17 archivos `docs/data_catalog/launches/*.json`.
   - Como esos 20 archivos quedan modificados o sin seguimiento en `/opt/edgelab/EdgeLab`, `tools/estado.py` devuelve código `1` (`dirty: true`) y cualquier intento de `git pull --ff-only` o `update.sh` aborta para no pisar archivos locales.
3. **Fragmentación Multi-Rama (`Split-Brain` entre 5 ramas distintas)**:
   - Las sesiones cloud comiteaban en ramas de sesión (`claude/vibrant-clarke-s9z6e2`); la rama troncal era `foundation/f0b-compatibility-probe`; `sync_state.sh` subía estado a `autopilot/state`; el programador subía código a `autopilot/codigo/<id>` y propuestas a `autopilot/propuesta/<id>`; y las promociones iban a `autopilot/prereg/<run_id>` sin que nadie integrara automáticamente las ramas validadas hacia la troncal.
4. **Aborto de `update.sh` ante commits locales de autorreparación**:
   - Cuando el agente local comitea un arreglo en `/opt/edgelab/EdgeLab` y aún no fue mergeado en `origin/foundation/f0b-compatibility-probe`, `update.sh` verifica `git branch -r --contains HEAD` o ancestría lineal y se niega a actualizar.

### 2.2. Contraste Punto por Punto: Funcionamiento Planificado vs. Funcionamiento Real en `SV1`

| Dimensión | Funcionamiento Planificado (`DIRECTIVAS.md` + `PLAYBOOK`) | Funcionamiento Real Observado (`O1..O16`, `E1..E10`, `REPORTE_ALINEACION`) | Causa Raíz en la Infraestructura |
|---|---|---|---|
| **1. Autorreparación de campañas (`Directiva #1`)** | Detectar `BLOQUEADA` o errores en cada ciclo, leer el log real del kernel, corregir la causa raíz, testear, reabrir en la misma etapa y **verificar el primer kernel relanzado (`O16`)**. | Tras aplicar `6685c9a9` (`O13`), reabrió 5 campañas `U1-*` a las `02:18 UTC` **sin mirar el primer log relanzado**; las 5 volvieron a caer a las `03:12 UTC` con `KeyError: 'r_vol'` en `resumen_e0` y quedaron `BLOQUEADAS` 14 horas hasta `4e975fcb`. | No existe un estado transicional `VERIFICANDO_REAPERTURA` en el daemon que obligue a auditar el log del primer kernel tras reabrir, ni hay un rol `Doctor` con herramientas de edición conectado automáticamente a las alertas. |
| **2. Salud de servicios (`systemd`)** | Si un servicio auxiliar falla, el sistema debe detectarlo, recuperar la unidad y seguir operando. | `edgelab-autopilot-generate.service` quedó clavado en estado `failed` desde el 26-oct `21:44 UTC` (>20 horas, 5 alertas en `alertas.jsonl`) sin auto-recuperarse. | Ningún script ejecutaba `systemctl reset-failed` ni diagnosticaba el `journalctl` de servicios caídos antes del ciclo. |
| **3. Aprendizaje en Espiral (`Directiva #2`)** | Mantener `docs/research/APRENDIZAJES_ESPIRAL.md` actualizado después de cada tanda y consultar `tools/metaanalisis_embudo.py` antes de proponer. | `APRENDIZAJES_ESPIRAL.md` **no existía** en el repositorio. `metaanalisis_embudo.py` y `analizar_embudo.py` existen en `tools/`, pero ningún paso automático los invocaba. | Falta el gancho post-cosecha en `daemon.py` / `autopilot_generate.py` que actualice `RESUMEN.json`, corra `metaanalisis_embudo.py` y refresque `APRENDIZAJES_ESPIRAL.md`. |
| **4. Investigación en Internet (`Directiva #3`)** | Buscar literatura cuantitativa, blogs de practitioners y discusiones técnicas en la web para inspirar nuevas hipótesis y combinaciones. | El proponente (`roles.py`) jamás buscó en Internet. | `edgelab/autopilot/roles.py` invoca `claude -p` sin herramientas (`WebSearch`/`WebFetch` deshabilitados) y con timeout corto de 240s. |
| **5. Programación Autónoma (`Directiva #5`)** | Cuando una hipótesis requiere un módulo nuevo (`edgelab/research/agente/<slug>.py`), el proponente emite `pedido_codigo` y `programador.py` lo escribe, pasa los 4 controles y lanza la campaña. | **`programador.activo` estaba en `false`** en `autopilot.json` y `edgelab-autopilot-programador.timer` estaba apagado (`inactive/disabled`). Los `pedido_codigo` quedaban sin ejecutar. | Configuración desactivada en `SV1` y desconexión entre la cola de `pedidos_codigo` y el ciclo principal. |
| **6. Contexto Amplio y Rápido** | El agente que propone debe ver todas las fichas de código (`tools/existente.py`), el mapa de vacíos (`par × familia × escala`), las cartas de `gramatica.py` y las lecciones previas. | `contexto.py` fija `max_chars = 12000` y aplica un bucle `while len(...) > max_chars: pop()` que **elimina silenciosamente `fichas`, `vacios` y `cartas_gramatica`** en cuanto el estado del embudo crece. | Truncamiento destructivo de diccionario completo en lugar de un resumen jerárquico indexado con presupuesto de `64.000`–`120.000` caracteres. |
| **7. Velocidad vs. Cuidado del Diseño** | Equilibrar exploración rápida con rigor de paridad C# y factibilidad computacional en Kaggle (`< 90 min`, `E0 >= 30 ops`). | Se lanzaron campañas con filtros rígidos vacíos (`O1`..`O9`) o barridos por celda `O(N_barras)` que daban timeout o 0 evaluables. | Falta una compuerta de **Pre-Vuelo Cuantitativo (`Preflight Densidad & Complejidad`)** que mida en una muestra local de 10 sesiones el tiempo por celda y el conteo `E0` antes de enviar a Kaggle. |
| **8. Escala Kaggle (8 slots en 2 cuentas)** | Repartir hasta 8 kernels concurrentes entre `nicolasbuttaro` y `nicobuttaro` (`"cuenta_kaggle": "auto"`). | Varias campañas tenían `"cuenta_kaggle"` fijo en una sola cuenta o chocaban con el tope de 5 sesiones CPU por cuenta de Kaggle. | El balanceador de `KaggleRunner` requiere que todas las campañas usen `"cuenta_kaggle": "auto"` y verifique cupo real por cuenta antes de elegir owner. |

## 3. Evaluación del Sistema de Agentes: ¿Por qué NO un solo agente y qué combinación usar?

Concentrar en un único agente LLM la exploración creativa, la lectura de literatura externa, la programación de módulos Numba/C# con paridad de ticks, la reparación de tracebacks del embudo y la auditoría estadística produce tres fallas estructurales:
1. **Sesgo de autoconfirmación**: El mismo agente que inventa una hipótesis escribe un test laxo o relaja un umbral para que su idea pase.
2. **Contaminación y truncamiento de contexto**: El contexto necesario para diseñar una cartera de campañas (`RESUMEN.json`, `APRENDIZAJES_ESPIRAL.md`, matriz de vacíos `par × familia`, literatura web) es completamente distinto del contexto necesario para depurar un kernel de Numba (`corredor_vol_gaps.py`, `EmaCorridorTrendVolW2.cs`, traceback de Kaggle).
3. **Bloqueo de cola**: Si una sesión de codificación o reparación tarda 12 minutos iterando con `pytest`, bloquea el avance determinista del embudo y la cosecha de Kaggle.

### Comparativa de Arquitecturas Multi-Agente Evaluadas

| Arquitectura Candidata | Ventajas | Limitaciones Críticas | Veredicto |
|---|---|---|---|
| **A. Un solo Agente monolítico (`1 Opus`)** | Simple de invocar. | Sufre sesgo de autoconfirmación, agota contexto rápido y mezcla decisiones estratégicas con parches de código. | **Descartada** |
| **B. `1 Opus (Proponente/Programador) + 1 Sonnet (Revisor)`** | Reduce costo en la revisión. | Si el único Opus hace a la vez de Arquitecto e Ingeniero, sigue siendo juez y parte de sus propios módulos y satura su ventana de contexto. | **Insuficiente para código + diseño** |
| **C. `2 Opus` puros sin separador rápido** | Alta capacidad en diseño y en código. | Usar Opus para tareas de alta frecuencia (auditoría de invariantes cada ciclo, filtro adversario rápido y crónica de sala) encarece y enlentece el loop operativo. | **Subóptima en latencia/costo** |
| **D. Sistema Triádico Asimétrico sobre Capa 0 Determinista: `Capataz Determinista (Python)` + `2 Agentes Claude Opus 4.6` + `1 Agente Claude Sonnet 4.6`** | Separa creación estratégica (`Opus 1`), ingeniería/autorreparación con tests (`Opus 2`) y auditoría adversaria + alineación + crónica (`Sonnet 3`), manteniendo el embudo 100% determinista en Python. | Requiere contratos JSON explícitos entre los 3 agentes (ya soportados por `STATE_DIR`). | **ÓPTIMA — Seleccionada** |

### Especificación de la Arquitectura Seleccionada (`Capataz Python + 2 Opus 4.6 + 1 Sonnet 4.6`)

1. **Capa 0 — Capataz Determinista y Guardián de Sincronía (`Python puro, sin LLM, cada 10 min`)**:
   - Ejecuta `deploy/debian/auto_sync_code.sh` (limpia escrituras vivas hacia `STATE_DIR`, hace `fetch` + fast-forward a `origin/foundation/f0b-compatibility-probe` y resetea servicios `failed`).
   - Corre `Embudo.avanzar()` sobre todas las campañas activas, cosecha kernels de Kaggle repartiendo hasta 8 slots entre `nicolasbuttaro` y `nicobuttaro`, actualiza `RESUMEN.json` y ejecuta `edgelab/autopilot/auditor_alineacion.py` (`SLI-01` a `SLI-08`).
   - Si detecta una campaña `BLOQUEADA` o un desvío en `SLI-01..SLI-08`, abre un ticket inmediato en `STATE_DIR/tickets_doctor.jsonl` y despierta al **Agente 2 (`Ingeniero/Doctor Opus 4.6`)**.
2. **Agente 1 — Arquitecto Cuantitativo, Meta-Analista e Investigador (`Claude Opus 4.6`, ventana `64k–120k` chars + `WebSearch`/`WebFetch`)**:
   - **Rol**: Ejecuta los pasos 1 a 4 de la espiral (`Medir -> Aprender -> Investigar afuera -> Proponer`).
   - **Entradas**: Paquete jerárquico amplio (`contexto.py` v2 sin `pop()` destructivo) con `RESUMEN.json`, salida de `tools/metaanalisis_embudo.py`, `docs/research/APRENDIZAJES_ESPIRAL.md`, `docs/MODULES.md`, catálogo completo de `tools/existente.py` y matriz de vacíos (`instrumento × familia × escala`).
   - **Criterio Velocidad vs. Cuidado**: Clasifica cada propuesta en **Vía Rápida (`Fast-Grid`)** —combinación de primitivas `L1/L2` ya probadas en `gramatica.py`, lanzamiento inmediato— o **Vía Cuidada (`Deep-Parity`)** —nuevo detector o acoplamiento microestructural que exige a `Opus 2` test de paridad C#, pre-cómputo `@njit` en 2 pasadas y prueba de densidad `E0 >= 30 ops` antes de ir a Kaggle.
   - **Salidas**: Actualización de `APRENDIZAJES_ESPIRAL.md`, especificaciones de campañas y `pedidos_codigo` detallados.
3. **Agente 2 — Ingeniero de Módulos, Optimizador Numba y Doctor Autorreparador (`Claude Opus 4.6` con `Read/Write/Edit/Bash` en `git worktree` aislada)**:
   - **Rol**: Tiene prohibido inventar campañas comerciales por su cuenta; su misión exclusiva es **construir y reparar código con rigor matemático y computacional**.
   - **Modo Constructor (`programador.py`)**: Toma los `pedidos_codigo` del Agente 1, reutiliza las primitivas de `L1/L2` (`docs/MODULES.md`), escribe `edgelab/research/agente/<slug>.py`, ejecuta los 4 controles obligatorios (`ruido`, `plantado`, `oráculo`, `causalidad`) + benchmark de memoria/tiempo, y promueve bloques probados al catálogo compartido.
   - **Modo Doctor (`autorreparación + guarda O16`)**: Cuando el Capataz detecta una campaña `BLOQUEADA` o un fallo de infraestructura, `Opus 2` lee el log real de Kaggle, reproduce el fallo con un test en `tests/`, corrige el código en una worktree limpia, ejecuta `tools/reconstruir_kernels.py` para regenerar el bundle con el código nuevo, reabre la campaña en la misma etapa y **queda en estado `VERIFICANDO_O16` hasta comprobar que el primer kernel relanzado completó sin error**.
4. **Agente 3 — Auditor Adversario, Guardián de Alineación y Cronista (`Claude Sonnet 4.6`, baja latencia, independiente)**:
   - **Rol**: Control cruzado independiente en cada ciclo.
   - **Funciones**:
     1. **Abogado del Diablo (`revisor2`)**: Audita cada propuesta del Agente 1 y cada módulo nuevo del Agente 2 antes de gastar cuota de Kaggle, verificando que no haya `look-ahead`, que los umbrales sean invariantes a la escala del instrumento (`ES` vs `NQ` vs `YM` vs `CFD`), que el linaje de multiplicidad (`LibroLord`) esté bien declarado y que la potencia prevista supere `0,80` en holdout.
     2. **Auditor de Alineación (`auditor_alineacion.py`)**: Verifica el cumplimiento de `DIRECTIVAS.md` y de las guardas `O1..O16` / `E1..E10`, bloqueando promociones si algún invariante crítico (`SLI-01`, `SLI-02`, `SLI-07`) está en rojo.
     3. **Cronista de la Sala (`sala.py`)**: Publica el resumen claro y verificable de cada transición de etapa, aprendizaje de la espiral y estado de la canasta pre-holdout.

## 4. Soluciones de Infraestructura Implementadas en este Parche

Para que estas mejoras no queden solo en papel, hemos implementado y testeado en el árbol del repositorio los siguientes componentes listos para aplicar sobre `faad4600`:

1. **`deploy/debian/auto_sync_code.sh` (Solución definitiva al problema de la rama aislada y el árbol sucio)**:
   - Evacúa automáticamente cualquier modificación viva en `EVALUABLES.jsonl`, `LIBRO_LORD.json`, `LINAJES.jsonl`, `account_launches.jsonl` y `docs/data_catalog/launches/*.json` hacia `/var/lib/edgelab-autopilot/state/` y restaura el árbol limpio de `/opt/edgelab/EdgeLab`.
   - Hace `git fetch origin foundation/f0b-compatibility-probe` y ejecuta `git checkout -q --detach "$REMOTE_SHA"` en fast-forward automático siempre que el árbol esté limpio.
   - Ejecuta `systemctl reset-failed` sobre `edgelab-autopilot-generate.service` y `edgelab-autopilot-programador.service` si alguno cayó en `failed`.
2. **`edgelab/autopilot/auditor_alineacion.py` + `tests/autopilot/test_auditor_alineacion.py` (Auditoría continua alineada con la planificación)**:
   - Evalúa en cada ciclo los 8 indicadores operativos (`SLI-01` Sincronía Git, `SLI-02` Árbol limpio `CODE_DIR` vs `STATE_DIR`, `SLI-03` Programador Opus activo, `SLI-04` Presupuesto 8 slots en 2 cuentas Kaggle, `SLI-05` Unidades systemd sanas, `SLI-06` `APRENDIZAJES_ESPIRAL.md` al día, `SLI-07` Autorreparación y guarda `O16`, `SLI-08` Contexto amplio `>= 64k` chars).
   - Calcula un puntaje ponderado de salud (`0%` a `100%`), genera reporte Markdown/JSON y emite acciones correctivas automáticas.
3. **`docs/MODULES.md` y `docs/research/APRENDIZAJES_ESPIRAL.md` (Clasificación modular `L0..L5` y Memoria en Espiral)**:
   - Clasifica todos los módulos de EdgeLab en 6 capas (`L0` a `L5`), establece la vía formal de promoción en 4 etapas (`Experimento -> Primitiva @njit -> Carta de Gramática -> Eje de Canasta`) e inicializa `APRENDIZAJES_ESPIRAL.md` con todos los resultados empíricos de hoy (`CVGAP-NQ`, `CVGAP-CFD-NQ`, `CVGAP-ES`, `CVGAP-CFD-ES`, `U1-RACIMOS-GRILLA-NQ`, `U1-ZONAS-GRILLA-YM`).
