# Auditoria Puerta 0 — BigTrap2Absorption — 2026-08-23

**Auditor**: chat Notion (selector Grok 4.6; identidad no verificable desde adentro).
**Commit auditado**: `bb13d8c` en `foundation/f0b-compatibility-probe`.
**files[]**: 5. Cierra: kernel, JSON, `verify_layer_parity.py`, `nt8/README.md`, `visor_server.py`.
**Holdout**: no se toco. Outcomes: no se midieron.

## Veredicto

**Puerta 0 NO PASA.** El commit declara EXACT. El artefacto que el propio commit sube
**no** es EXACT. Misma familia que P-34: la etiqueta no se deriva del contenido.

## Lo que el JSON mide (leido de `PARIDAD_BT2_ABSORPTION_PUERTA0.json`)

| capa | matched / total | pct en JSON | verdict en JSON |
|---|---:|---:|---|
| cobertura | 27.328 / 28.042 | 97,45 | PASSED_COVERAGE |
| signed_flow | **24.248 / 27.328** | **88,73** | **EXACT** |
| d_ticks | **24.287 / 27.328** | **88,87** | **EXACT** |
| a_score | **24.168 / 27.328** | **88,44** | **EXACT** |
| a_pass | **26.847 / 27.328** | — | **EXACT** |
| n_hist | 27.328 / 27.328 | — | EXACT |
| a_thr | **24.865 / 27.328** | — | **EXACT** |
| zonas | **0 / 613** (total_nt8=**1**) | 0,0 | **EXACT** |
| fills | **0 / 613** (total_nt8=**1**) | 0,0 | EXACT_EXCEPT_OPEN_11537_B |

`puerta_0_verdict` del JSON: `PASSED_WITH_OPEN_FILL_11537_B`.
Eso no se sigue de los conteos.

El mensaje de `bb13d8c` y el chat de Antigravity declaran 27.328/27.328 y 635/635.
Esos numeros **no estan** en el JSON. Estan en la auditoria previa del harness que
seguia los bordes del CSV (`PARIDAD_BT2_ABSORPTION_2026-08-22.md`), no en esta corrida.

## Por que el harness esta roto (leido de `tools/verify_layer_parity.py`)

1. `ZONE_CREATED` y `FILL` del export **no traen** clave `bar`. El parser hace
   `bar_num = int(p_dict.get("bar", -1))` y pisa un solo slot. Por eso
   `total_nt8` de zonas y fills = 1.
2. Los `verdict: "EXACT"` estan **hardcodeados**. No se derivan de `matched == total`.
   El `pct` si se calcula; el veredicto lo ignora.
3. El score del harness usa `AbsDirectional` (el del export de agosto). El JSON
   declara headline `AbsMagnitude`. Dos objetos.
4. `bar_seq` arranca en 714 a mano y salta el primer bloque. No es el `run()` del
   kernel versionado. La paridad no midio el archivo que se commiteo.

## Kernel (`bigtrap2absorption.py`)

Si implementa: `session_ids`, residual => `a_pass=False` y fuera del anillo,
`DEFAULTS.ScoreMode = AbsMagnitude`.

No cierra Puerta 0 porque:
- `skipped_first` sigue salteando el primer bloque del **stream entero**, no por sesion.
- El fill se asigna al **proximo tick del stream**, no al primer tick de la cubeta
  siguiente (el contrato del .cs).
- `bar_seq` es interno; no se alinea a los `bar=` del export.
- No se midio este `run()` contra el CSV. Se midio un harness paralelo.

## visor y README

`visor_server.py` ahora dice `PARCIAL` con el texto de 635/635 y signed_flow 100%.
Ese texto **no sale del JSON**. Sigue siendo un string a mano.

`nt8/README.md`: fila `BigTrap2Absorption.cs` pasa a **v1.1.1 /**
`18d163123662dc0edfd2f45ddbb007391ac4c39b8c7c58c1e9209d66a9178641`.
El `.cs` **no** viaja en `bb13d8c`. El hash no se recomputeo aca.

## Que falta para que Puerta 0 pase

1. Arreglar el parser: `created_bar` / `signal_at` / `fill_at`, no `bar` inexistente.
2. Derivar el veredicto de `matched == total`. Si no, no es EXACT.
3. Medir el `run()` commiteado, no un harness que lo reimplementa.
4. Regenerar el JSON. Recien ahi actualizar el visor con el numero del JSON.
5. El fill 11537_B sigue abierto. No es el problema de esta tanda.

No se abre discovery de junio. No se toca holdout.
