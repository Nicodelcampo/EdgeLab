# INC-P2B-AUTH-GAP · gate de autorización de P2B GC no vinculado al spec congelado; corrida completa sin rastro en git

- **Fecha:** 2026-08-30 · **Rama de registro:** `audit/notion-ai-sltp-p2b-provenance-20260830`
- **Rama donde vive el código auditado:** `research/bt2a-p2b-economic-gc-v1-20260827` @ `54ab1437fe8f5c7543b789ce6755b10ab55b5e85`
- **Detectado por:** Notion AI (auditoría de proveniencia, `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §3), causa raíz confirmada por Claude el mismo día
- **HEAD de registro:** ver commit de este archivo

> **Esto no es una retractación del resultado reportado.** El resultado de P2B
> (16 celdas, todas `supported: false`, efecto económico negativo en las dos
> escenas de costos) es real: se leyó directamente del log completo de un
> kernel de Kaggle ya `COMPLETE`, vía `kaggle.api.kaggle_api_extended.KaggleApi
> .kernels_logs_cli()` (el `kaggle kernels output` del CLI no devuelve estos
> artefactos — ver hallazgo separado de esta misma sesión). El dato existe. Lo
> que no existe es su autorización trazable en git.

---

## 1. Qué se encontró

Un mensaje de Claude en el canal Notion AI ↔ Claude (2026-08-30, sesión
posterior al cierre del canal en PDF) reportó un resultado completo de
`bt2a-gc-event-store-and-p2-b-economic-v1` en Kaggle: estado
`COMPLETE_P2B_AUTHORIZED_POST_OUTCOME_DIAGNOSTIC`, 16 celdas
(barreras `[5,9,18,30]` × horizontes `[25,50,100,250]`), todas
`p2a_positive_annotation`/`supported` en `false`, efecto neto en USD por señal
negativo en las dos escenas de fricción (`base` y `adverse`).

Verificado contra las fuentes congeladas en `research/bt2a-p2b-economic-gc-v1-20260827`:

| Campo | Valor en el spec/código congelado |
|---|---|
| `specs/bt2a_p2b_gc_economic_v1.json` (blob `5921e7a053a1c82633deb70ba6d2a395f6f94ebb`) | `status: FROZEN_PREAUTHORIZATION`, `P2B_RUN: false`, `authorization.execution_authorized: false` |
| Historial completo de ese archivo (`git log -p`) | `execution_authorized` **nunca** aparece como `true` en ningún commit |
| Ramas `results/bt2a-p2b-*` | **no existen** |

Es decir: el spec congelado que en teoría gobierna esta corrida dice, en cada
versión que jamás tuvo, que la ejecución NO está autorizada — y sin embargo
existe una corrida `COMPLETE` con resultados económicos reales en la cuenta de
Kaggle de Nico.

## 2. Causa raíz — el gate no está atado al campo que dice controlar

`tools/run_bt2a_p2b_gc_economic.py` (blob `c249d64d13b3e0dee6e0f98363058951f9a53325`):

```python
AUTH = "AUTHORIZE_BT2A_P2B_GC_ECONOMIC_V1"          # constante en texto plano en el .py

def require_authorization(token: str | None) -> None:
    if token != AUTH:
        raise SystemExit("ABSTAIN_MISSING_EXPLICIT_P2B_AUTHORIZATION")
```

Y en `frozen_checks()` (el preflight que corre antes):

```python
"authorization": spec.get("authorization", {}).get("execution_token") == AUTH,
```

**El preflight no verifica `authorization.execution_authorized`.** Verifica
`authorization.execution_token`, un campo que declara qué token *haría falta*,
no si fue *concedido*. Ese campo vale `"AUTHORIZE_BT2A_P2B_GC_ECONOMIC_V1"` en
el spec **desde que se congeló**, autorizado o no — no es un flag que alguien
active con un commit, es una constante descriptiva.

`require_authorization()`, a su vez, no lee nada del spec ni de git: sólo
compara el `--authorization-token` recibido por línea de comandos contra la
constante `AUTH` **hardcodeada en el mismo archivo que se está auditando**.

**Consecuencia medida:** cualquiera con acceso para correr este script en
Kaggle y capacidad de leer su código fuente (que contiene el token en texto
plano) puede pasar el gate completo sin que exista, en ningún momento, un
commit en git que diga "esta corrida está autorizada". El campo
`execution_authorized: false` del spec es **decorativo**: no lo lee ninguna
ruta de código de este runner.

Esto es distinto (y más débil) que el patrón usado en
`tools/build_bt2a_nq_creation_event_store.py::require_build_authorization()`,
que sí compara el token recibido contra `spec["authorization"]["active_token"]`
— un campo que sólo puede volverse verdadero mediante un commit que congele el
spec con ese valor.

## 3. Qué NO se pudo determinar desde este entorno

- **Quién lanzó la corrida ni bajo qué instrucción.** El canal Notion AI ↔
  Claude ya mencionaba este kernel como `RUNNING` el 2026-08-29 22:11–23:05
  ART, en un mensaje de una sesión de Claude anterior a la que detectó el
  resultado. No hay forma de reconstruir desde git ni desde el canal qué
  autorización humana (si la hubo) precedió ese lanzamiento.
- **Si el `--authorization-token` se pasó a mano, vía Kaggle Secret, o vía
  algún otro mecanismo** — el kernel de Kaggle no expone su script de entrada
  completo a este auditor (mismo problema de `kaggle kernels output` truncado
  documentado aparte).
- **Si hubo una autorización verbal de Nico no registrada.** No descartable,
  pero no verificable desde el repo.

## 4. Clasificación de exposición

| clasificación | valor |
|---|:-:|
| Outcomes de P2B (USD netos por señal, 16 celdas) | **ACCEDIDOS** |
| Origen de la autorización | **NO TRAZABLE EN GIT** |
| Holdout tocado | No relevante — P2B corre sobre pre-holdout GC, mismo dataset que Gate 1 GC (ya con outcomes abiertos por diseño) |
| Resultado usable para decisiones | **NO**, hasta que se resuelva la proveniencia — ver `docs/audits/AUDITORIA_SLTP_Y_PROVENIENCIA_P2B_2026-08-30.md` §3, que ya clasifica el reclamo como NO EVIDENCIA mientras esto no se cierre |

## 5. Remediación pendiente (no ejecutada por este registro)

1. **Cerrar la brecha de diseño**: `require_authorization()` debe verificar
   `spec["authorization"]["execution_authorized"] is True` y, si corresponde,
   un `active_token` bindeado al spec congelado — no solo comparar contra una
   constante del propio archivo. Mismo patrón que ya usa el Event Store de
   Gate 1 NQ.
2. **Reconstruir la procedencia de la corrida ya completada**: identificar el
   commit/branch/estado exacto de código que corrió en Kaggle (el kernel
   debería haber clonado un commit específico — verificar cuál), y si el
   `EVENT_PAYLOAD` usado coincide con el congelado.
3. **Decisión de Nico**: tratar el resultado ya obtenido como (a) exposición a
   descartar y re-ejecutar bajo un gate corregido con autorización trazable, o
   (b) autorización retroactiva explícita y registrada, dejando el resultado
   existente como válido. Ninguna de las dos opciones la toma este registro.

## Aporte al referente

Un gate de autorización que no lee el campo que dice controlar es
indistinguible de no tener gate. Esto se encontró auditando un reclamo
puntual (el resultado de P2B), no buscando fallas de autorización — lo cual
sugiere que vale la pena revisar si el mismo patrón (constante hardcodeada en
vez de verificación contra el spec) aparece en otros runners de outcomes del
proyecto. Ningún outcome nuevo se abrió al escribir este registro; el dato de
P2B ya estaba abierto antes de que este auditor lo viera.
