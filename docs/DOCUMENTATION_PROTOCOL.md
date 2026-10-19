# Protocolo de documentación de EdgeLab

Estado: VIGENTE  
Fecha: 2026-10-14

> Versión 1 — 2026-10-14. Vale para personas y agentes. Objetivo: **que ninguna decisión, resultado o hallazgo se pierda, y que cualquier agente pueda continuar sin la conversación**. Si este protocolo y un documento histórico discrepan, manda este protocolo.

## 1. Regla madre
**Lo que decide algo vive en el repo, en Markdown, versionado.** Chat, Notion, Drive, `.gdoc` y memoria de agente son espejos o canales de trabajo, nunca la fuente. Un resultado que sólo existe en un chat no existe.

## 2. Dónde va cada cosa
| Tipo | Ruta | Nombre | Cuándo se escribe | Mutable |
|---|---|---|---|---|
| Referente y reglas | `docs/NORTH_STAR.md`, `CLAUDE.md`, `AGENTS.md` | fijo | sólo por decisión de Nico | no sin su OK (hash protegido) |
| Producto, roadmap, módulos | `docs/PRODUCT.md`, `config/modules.json` → `docs/MODULES.md` (generado) | fijo | al cambiar el producto o un módulo | sí, versionado |
| Manifiesto de campaña | `docs/research/<FAMILIA>_MANIFIESTO_<AAAAMMDD>.md` | `FAMILIA_MANIFIESTO_fecha` | **antes** de medir; commit propio | **no**: se enmienda con otro archivo |
| Acta de resultado | `docs/research/<FAMILIA>_RESULTADOS_<AAAAMMDD>.md` + carpeta de agregados `<familia>_<aaaammdd>/` (JSON) | `FAMILIA_RESULTADOS_fecha` | al medir; **mismo commit que el registro** | no (se corrige con enmienda) |
| Registro MEDIDO / NO MEDIDO | `docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` (y uno por familia nueva) | fijo por familia | mismo commit que cada resultado | sí, sólo se agrega |
| Edges promovidos | `EDGES_DISCOVERED.md` | fijo | sólo si una cadena completa lo permite | sí |
| Decisiones de Nico | `docs/DECISIONES_<AAAAMMDD>.md` | `DECISIONES_fecha` | el mismo día | no |
| Handoff de sesión | `docs/research/HANDOFF_<AAAA-MM-DD>_<tema>.md` | `HANDOFF_fecha_tema` | al cerrar una sesión larga | no (el siguiente lo supera) |
| Plan o referencia | `docs/research/PLAN_*`, `REFERENCIA_*` | prefijo + tema + fecha | cuando se necesite | sí, con fecha |
| Datos y release | `docs/infra/` | tema + fecha | al publicar o auditar datos | no |
| Incidentes | `docs/incidents/` | `INCIDENTE_*` / `RESOLUCION_*` | al ocurrir y al cerrar | no |
| Auditoría externa | `docs/audits/` (índice en `docs/audits/CANAL_AUDITOR.md`) | `ENTRADA_nnn_*` | por entrada | no |
| Contratos y especificaciones | `docs/*.md` (contratos), `specs/` (JSON congelados) | fijo | al cambiar semántica (consultar a Nico) | con enmienda |
| Resultados agregados de Kaggle | carpeta de agregados junto al acta | nombre del kernel | al terminar el kernel | no |
| Pendientes | `PENDIENTE.md` (P-NN) | fijo | cuando se abre o cierra una decisión | sí |

**Nunca al repo ni a Drive:** ticks, precios crudos, credenciales, tokens. Sólo agregados y recibos (política de licencia y custodia).

## 3. Encabezado obligatorio
Todo documento nuevo en `docs/` empieza con estas líneas (formato libre dentro de la primera pantalla):
- `Estado:` `VIGENTE` · `PROVISIONAL` · `PROPUESTA` · `SUPERADO por <ruta>` · `ARCHIVO`
- `Fecha:` AAAA-MM-DD
- `Familia / módulo:` la familia de indicador o el id de `config/modules.json`
- `North Star:` hash de `docs/NORTH_STAR.md` (obligatorio en manifiestos)
- `Procedencia:` commit, kernel y SHA de la release o del manifiesto usado
Las actas añaden, por plantilla: **justificación económica**, **cómo podría refutarse**, MDE, canal direccional y no direccional, y la frase del alcance de lo que se declara muerto.
`tools/docs_index.py --check` rechaza los documentos nuevos (desde 2026-10-14) sin `Estado:`.

## 4. Ciclo de vida
1. **Nace** `PROPUESTA` o `PROVISIONAL`.
2. **Se vuelve `VIGENTE`** cuando lo aprueba Nico, o cuando es un acta con datos verificados e integridad cerrada.
3. **Se supera**: el documento nuevo declara `Reemplaza: <ruta>` y el viejo recibe arriba `Estado: SUPERADO por <ruta>`. **No se borra nada**: la historia es parte de la evidencia.
4. **Se archiva** (`ARCHIVO`) sin moverse de lugar; el índice lo separa.

## 5. Evitar pérdida de información
- **Mismo commit:** resultado + registro MEDIDO/NO MEDIDO + (si cambia código) `config/modules.json`.
- **Recibo por corrida:** cada kernel de Kaggle guarda su recibo agregado en el repo con el SHA de la release y el commit del código. Estado COMPLETE de Kaggle no es un resultado.
- **Cada sesión larga termina con un handoff** y un puntero en `PROJECT_INDEX.md`/`CLAUDE.md`.
- **Decisión tomada en chat → archivo ese mismo día** (`DECISIONES_*` o enmienda). Lo que Nico responde en una pregunta abierta cierra o enmienda un P-NN.
- **Agentes externos** (Gemini, Notion): sus informes entran como `.md` revisables; sus parches viven en `patches_for_review/` hasta que alguien los revisa, y los informes con simulaciones sintéticas se retractan por escrito, no se borran.
- **Todo número que aparece en un documento** cita su fuente (acta, hash o recibo). Recordar no es verificar.

## 6. Cómo se encuentra todo
1. Entrada única: el `HANDOFF` más reciente, apuntado desde `README.md`, `PROJECT_INDEX.md` y `CLAUDE.md`.
2. `docs/PRODUCT.md` (qué es y a dónde va) → `docs/MODULES.md` (qué hace cada parte).
3. `docs/INDEX.md` + `docs/INDEX.csv`: generados con `python tools/docs_index.py --write`; por familia, con el último documento y su estado. No se editan a mano.
4. Lo vigente se distingue de lo superado por el campo `Estado:`.

## 7. Verificación automática
- `python tools/check_modules.py` — cada módulo existe, tiene función, documento, tests y dependencias válidas; ningún paquete queda sin dueño.
- `python tools/docs_index.py --check` — índice al día y encabezado presente en documentos nuevos.
Ambos corren en `tests/foundation/` y, por tanto, en CI.
