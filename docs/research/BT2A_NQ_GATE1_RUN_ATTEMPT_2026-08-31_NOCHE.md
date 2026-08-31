# BT2A NQ Gate 1 — intento de corrida nocturna 2026-08-31, acta completa

**Rama:** `research/bt2a-nq-gate1-runner-impl-v1-20260831`.
**Autorización:** Token 3 y Token 4 ya otorgados por escrito (`DECISION_NICO_IMPLEMENT_Y_RUN_BT2A_NQ_GATE1_2026-08-31.md`). Opción de riesgo aceptado sobre el gap de autorización self-serve: elegida por Nico ("2") — ver `PENDIENTE.md` P-58.
**Resultado de esta noche: el kernel de Gate 1 NO se lanzó.** Se avanzó todo lo que se podía avanzar sin tocar un spec congelado, y se encontró un blocker real que exige una decisión de Nico, no una corrección mecánica.

## Lo que quedó cerrado y verificado esta noche (no hay que rehacer nada de esto)

1. **Fix del runner post-auditoría** (commits `7f99d30`/`8fabfa29`/`f2299a9`, de Notion AI): verificado por mí de forma independiente, no solo leído — hashes de blob confirmados contra remoto (`f0d8f750`, `ce8baadc`, `f0f60e71`, `5c45f3c9`), demo de efecto plantado reproducida a mano (8 ticks → 16/16 celdas `SUPPORTED`; nulo → 0/16), suite acotada 62/62 PASS. Real, no un "verde" reportado.
2. **Gap de autorización self-serve encontrado y registrado** (`PENDIENTE.md` P-58): el token de ejecución es una constante hardcodeada, misma clase que P2B. Nico eligió aceptar el riesgo y correr igual; fix diferido, no bloqueante.
3. **Coordenadas K_BT2 (`tick_25_IMB30_VOL10`) exportadas por primera vez** (commits `596b1d5`/`32356da`): el sweep V2 original nunca persistió las filas de zona, solo agregados. Escribí `tools/export_bt2_v2_coords_parquet.py` con 7 tests sintéticos, lo corrí de verdad en Kaggle (kernel `bt2-v2-coords-export`, COMPLETE en ~7,6 min) y **coincide exacto con lo congelado**: 516.971 eventos / 234 sesiones, hash del resultado V2 verificado (`e162a0e0...`). Subido como dataset `nicolasbuttaro/edgelab-bt2-v2-nq-artifacts`.
4. **Bug de plomería encontrado y corregido en el lanzador** (commit pendiente de push, ver abajo): `bt2a_nq_gate1_16cell_runner.py` buscaba un dataset "coordinates" y otro "package" que **no existen con esos nombres** en la cuenta real de Kaggle — nunca se probó contra datos reales (Token 4 nunca se había gastado). Verificado con `kaggle datasets list`, `kaggle kernels pull -m` sobre los kernels reales que efectivamente produjeron cada artefacto. Corregido: `package_dir = ticks_dir` (el manifest del paquete vive dentro de `edgelab-ticks-nq-preholdout`, ya verificado por el propio kernel de export de coordenadas), y el event store se busca en un dataset nuevo (`event-store` como substring), no en "coordinates".

## El blocker real: el manifest del event store no calza con el hash congelado — y el propio spec ya lo advertía

Bajé el output del kernel `bt2a-nq-event-store-rebuild-v2` (ya `COMPLETE`, corrido antes de esta noche). Su propio `hash_verification_result.json`:

```json
{
  "manifest_sha256_actual": "1e45c43fa60327b67aeb618d00b4137b82cc6c44ad43f348fc5bca8250ef90ea",
  "manifest_sha256_expected_frozen": "b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544",
  "manifest_sha256_match": false,
  "parquet_sha256_actual": "96281e880d7949f9dfcf3364091d9ce7696f778e59e6f2e2243995becdd38808",
  "parquet_sha256_expected_frozen": "96281e880d7949f9dfcf3364091d9ce7696f778e59e6f2e2243995becdd38808",
  "parquet_sha256_match": true
}
```

**El parquet (los datos reales: 152.695 filas, 234 sesiones) coincide exacto.** Lo que no coincide es el archivo JSON del manifest completo — porque se auto-embebe su propio `frozen_commit` (`a6bfcb08...` en este run), y ese campo cambia en cada regeneración por definición (un commit no puede contener el hash de sí mismo). No es una discrepancia de datos: `event_rows_payload_sha256` (`93a70661...`, el hash de las filas mismas, sin metadata de commit) es la parte sustantiva y no depende de qué commit corrió.

**Esto ya estaba escrito en el propio spec congelado**, `specs/bt2a_nq_gate1_v1.draft.json` línea 45:

> `"bt2a_creation_event_store_manifest_sha256": "Bound to the frozen physical manifest. The 2026-08-30 rebuild reproduced it with only frozen_commit differing; if the rebuilt store is ever re-uploaded this binding must change."`

O sea: quien congeló el spec ya sabía que esto iba a pasar y dejó escrita la regla de qué hacer. Pero **actualizar ese binding significa editar un spec en estado `FROZEN_PREFLIGHT_READY`** — un archivo que el propio proyecto trata como inmutable salvo proceso explícito. No lo toqué. No es una corrección mecánica de plomería como la del punto 4 (buscar el dataset correcto): es modificar el valor congelado de una puerta científica, y ahí es donde freno según lo que prometí.

## Qué necesito de Nico para continuar

Una sola decisión, chica y acotada: **autorizar la actualización de `bt2a_creation_event_store_manifest_sha256` en `specs/bt2a_nq_gate1_v1.draft.json`** de `b3177b51...` a `1e45c43f...` (el hash real del manifest re-generado), con el `payload_sha256` del spec recalculado en consecuencia — exactamente la operación que la nota de procedencia del propio spec ya anticipó y prescribió. No cambia ningún dato: el parquet subyacente es byte-idéntico (152.695/234, hash `96281e88...` sin cambios).

Con ese OK, lo que queda es mecánico y ya está armado:
1. Actualizar el binding + recalcular `payload_sha256` del spec.
2. Subir el dataset `edgelab-bt2a-nq-event-store` (manifest + parquet ya descargados y verificados en `C:\kg\es_out\edgelab-output\`).
3. Commitear y pushear el fix del lanzador (ya editado localmente, no pusheado).
4. Lanzar `bt2a_nq_gate1_16cell_runner.py` en Kaggle — el preflight embebido (puerta 4) corre solo, y si algo más no calza, aborta fail-closed antes de tocar outcomes, como debe ser.

## Estado de archivos al cierre de esta sesión

- Pusheado: `596b1d5` (export tool + tests), `32356da` (launcher del export de coordenadas).
- **No pusheado todavía**: el fix del lanzador de Gate 1 (`notebooks/kaggle/bt2a_nq_gate1_16cell_runner.py`, discovery de datasets corregido) — lo dejo en el working tree de `C:\ProyectosQuant\EdgeLab-runner-impl`, listo para commitear en cuanto haya luz verde sobre el spec.
- Dataset ya en Kaggle: `nicolasbuttaro/edgelab-bt2-v2-nq-artifacts` (coords + resultado V2, verificado).
- Descargado localmente, no subido todavía: `C:\kg\es_out\edgelab-output\` (manifest + parquet del event store, esperando la decisión de rebind).

## Aporte al referente

Se cerró de verdad (no de nombre) la exportación de coordenadas K_BT2 que nunca existió, y se encontró un bug real de plomería en el lanzador antes de gastar el Token 4 a ciegas contra datasets que no existían. El blocker final no es ambigüedad ni pereza: es la diferencia exacta entre "dato que no coincide" (no ocurrió — el parquet es idéntico) y "un campo autorreferencial que el propio spec ya documentó que iba a cambiar" — y esa distinción es precisamente la que separa una corrección mecánica de una que necesita la firma de Nico.
