# BT2A NQ Event Store — verificación de reproducibilidad (2026-08-30)

Orden 3a del auditor Notion AI (canal `EdgeLab — canal Notion AI ↔ Claude`,
2026-08-30 14:05 ART): relanzar el build del Event Store de creación NQ como
kernel nuevo en Kaggle y verificar contra los hashes congelados el
2026-08-30 01:15 ART. Target-free en todo momento (firewall de outcomes
intacto, ver manifiestos abajo).

## Kernel

- Slug: `nicolasbuttaro/bt2a-nq-event-store-rebuild-v2`
- Versión que dio PASS: **3** (v1 y v2 fallaron por bugs del launcher, ver
  abajo; corregidos antes de v3).
- Commit de código usado (`--expected-commit`): `a6bfcb08590c3f20f1863cabd9e5f5916e4b3b04`
  (tip de `research/bt2a-nq-v2-sweep-v1-20260829` al momento de la corrida).
- Launcher: [`notebooks/kaggle/12_nq_event_store_rebuild_v2_runner.py`](../../notebooks/kaggle/12_nq_event_store_rebuild_v2_runner.py)
  (sha256 `f6043c61eff46a5f1d3b71dd15129794411be75c415c61f7bf932447b01a5460`),
  kernel-metadata en el archivo hermano en el mismo directorio.

## Bugs encontrados y corregidos en el launcher (antes de v3)

1. **v1**: asumía que el dataset de entrada se montaba en
   `/kaggle/input/edgelab-nq-informal-all5-coordinates`. Kaggle lo monta en
   `/kaggle/input/datasets/nicolasbuttaro/edgelab-nq-informal-all5-coordinates`.
   `FileNotFoundError` inmediato.
2. **v2**: usaba el `--spec` por defecto de la herramienta
   (`specs/bt2a_nq_creation_event_store_v1.draft.json`, sigue en
   `DRAFT_PREAUTHORIZATION`) en vez del spec realmente congelado
   (`specs/bt2a_nq_creation_event_store_informal_v1.draft.json`,
   `FROZEN_PREFLIGHT_READY`). Preflight correcto: `NOT_READY`, no fue un
   fallo silencioso.

Corregido en el propio `tools/build_bt2a_nq_creation_event_store.py`: el
default fail-open (`DEFAULT_SPEC`) fue eliminado, `--spec` ahora es
obligatorio (`required=True`). Regresión fijada en
`tests/research/test_bt2a_nq_event_store_builder.py::test_spec_argument_has_no_fail_open_default`.

## Resultado del rebuild (v3)

```
preflight: PASS_READY_FOR_FREEZE_OR_BUILD
build:     READY_CREATION_EVENT_STORE
validate:  PASS_READY_CREATION_EVENT_STORE
rows: 152695, sessions_with_events: 234, contracts: 5 (NQ 03-26/06-26/09-25/09-26/12-25)
```

## Verificación de hash contra el registro congelado (2026-08-30 01:15 ART)

| Artefacto | Hash de esta corrida | Hash congelado | Coincide |
|---|---|---|---|
| `bt2a_nq_creation_events.parquet` | `96281e880d7949f9dfcf3364091d9ce7696f778e59e6f2e2243995becdd38808` | `96281e880d7949f9dfcf3364091d9ce7696f778e59e6f2e2243995becdd38808` | **Sí, exacto** |
| `bt2a_nq_creation_event_store_manifest.json` (archivo) | `1e45c43fa60327b67aeb618d00b4137b82cc6c44ad43f348fc5bca8250ef90ea` | `b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544` | No, directo |
| `payload_sha256` del manifest | `95ac5f3b5efc61d0937b58d5f7d4eb8646a20cb16e3e4a2e4eabdfd13bd7d667` | `983d54a0519fc476c2ae51a34a54e71033793dfdce2bdd359f03ecbabd2489a7` | No, directo |

El parquet es byte-idéntico. El manifest no lo es en bruto porque embebe
`frozen_commit` (el commit de código con el que corrió cada build), y las dos
corridas usaron commits distintos (`5aba599e...` el 2026-08-30 01:15 ART,
`a6bfcb08...` esta corrida).

## Test de sustitución (pedido por el auditor, 2026-08-30 14:37 ART)

Reconstrucción determinista desde el JSON impreso en el log del kernel
(`api.kernels_logs_cli`, no `kaggle kernels output` — ver nota de límite de
herramienta abajo), usando el mismo serializador que
`edgelab/kaggle/execution.py::canonical_sha256` /
`atomic_write_json` (`json.dumps(..., sort_keys=True, separators=(",", ":"))`
para el payload; `indent=2, sort_keys=True` + `"\n"` final para el archivo).
Las 22 claves de nivel superior del manifest se sustituyeron sólo en
`frozen_commit` → `5aba599e5e5dbd74a3650f995325a3d51becac15`, se recalculó
`payload_sha256`, y se recalculó el hash del archivo resultante:

```
payload_sha256 recalculado: 983d54a0519fc476c2ae51a34a54e71033793dfdce2bdd359f03ecbabd2489a7  -> MATCH exacto
file sha256 recalculado:    b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544  -> MATCH exacto
```

**Las dos igualdades cierran.** No hay una segunda discrepancia real (en
particular, `spec_file_sha256` es idéntico entre ambas corridas pese al bug
2 del launcher: el spec correcto, una vez usado, tiene el mismo contenido en
ambos commits). La única diferencia entre las dos corridas del Event Store
es, en efecto, `frozen_commit` — la cadena está sana.

Script del test: `.kaggle_kernel_v2/substitution_test.py` (no versionado,
scratch de verificación; el resultado queda registrado acá).

## Límite de herramienta descubierto (no de datos)

`kaggle kernels output` no devolvió nunca los artefactos reales de
`/kaggle/working/edgelab-output/` — 4/4 intentos contra 2 kernels distintos
(incluida esta corrida exitosa) se cortan en el mismo punto: 26 archivos de
documentación de nivel superior del clon de git, nada más. No es timeout
(probado con 180-300s explícitos). El rodeo que sí funciona:
`kaggle.api.kaggle_api_extended.KaggleApi.kernels_logs_cli()` (librería
Python, no el CLI) devuelve el log completo de stdout/stderr, que es de
donde salió el JSON del manifest usado en este documento.

Consecuencia: el parquet real (el binario) no está disponible en disco local
todavía, sólo su hash verificado. La solución estructural pendiente (pedida
por el auditor, no ejecutada aún): encadenar kernels vía `kernel_sources` en
`kernel-metadata.json` para que el runner de Gate 1 consuma el parquet
directo del kernel que lo produce, sin pasar por el CLI de descarga; y/o
publicar el output como dataset privado versionado desde adentro del kernel
(token como Kaggle Secret + `kaggle datasets version`).

## Estado

Punto 2 del orden del auditor (2026-08-30 14:37 ART) cerrado: "la cadena
está sana" confirmado con evidencia reproducible, no por plausibilidad.
Sigue pendiente: publicar el parquet real en un dataset durable (3a no
cerrado del todo), y el punto 7 del auditor (`bt2_v2_result_file_sha256`
sigue `null`, mismo defecto en el resultado del sweep V2).
