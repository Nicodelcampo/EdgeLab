# Promotion Registry — control ejecutable de estados

> Referente: `docs/NORTH_STAR.md`. Incidente:
> `docs/incidents/INC-007_autoridades_estadisticas_incompatibles.md`.

## Propósito

`edgelab/research/promotion.py` es la única superficie sancionada para
materializar estados. Un Markdown, un print de gauntlet o un booleano suelto no
promueven nada.

El ledger vive en `docs/promotion_registry.jsonl` cuando exista la primera
entrada. Cada fila se agrega sin reescribir y queda encadenada por SHA-256.

### Alcance honesto de integridad

La cadena detecta:
- alteración de contenido;
- reordenamiento;
- eliminación de una fila que tenga sucesora;
- ruptura de schema.

No detecta por sí sola la eliminación de la **última** fila: no existe un hash
posterior que la referencie. Ese truncado se detecta mediante el historial Git
del ledger. Tampoco se afirma seguridad frente a dos writers concurrentes; el
writer sancionado es local y de un solo proceso.

## Cadena de estados

```text
external_candidate | idea
        \              /
         technically_valid
           -> exploratory_candidate
           -> statistically_supported
           -> economically_viable
           -> holdout_confirmed
           -> paper_validated
           -> live_candidate
```

`external_candidate` e `idea` son entradas alternativas. Ambas pasan luego por
G0; convertir una externa en `idea` no permite esquivarlo. `failed` y `retired`
son terminales. No hay regresiones ni saltos.

## Contención vigente de INC-007

`APPROVED_G2_CONTRACT_SHA256S` está vacío a propósito. Mientras no exista una
enmienda G2 corregida y hasheada, **ningún candidato puede materializar
`statistically_supported`**, aunque presente un objeto con `passed=true`.

Cuando se apruebe la enmienda, su SHA-256 se agregará explícitamente. Cualquier
otro hash seguirá bloqueado.

## Regla fail-closed G2

Todo estado igual o posterior a `statistically_supported` exige:

- `campaign_id`, `run_id` y `config_id`;
- decisión `gate=G2`, `passed=true`;
- contrato en la allowlist aprobada;
- digest SHA-256 de evidencia;
- exactamente estos gates, en orden:
  - `mcpt`;
  - `pbo`;
  - `dsr`;
  - `walk_forward`;
  - `parameter_sensitivity`;
- un resultado `passed=true` para cada uno, sin faltantes ni extras.

El registro no decide la fórmula de los gates; exige el contrato versionado que
la define. La lista estructural cambia sólo junto con una enmienda.

## Uso mínimo

```python
from edgelab.research.promotion import append_record

append_record("docs/promotion_registry.jsonl", {
    "record_id": "PROM-0001",
    "candidate_id": "candidate-x",
    "status": "idea",
    "recorded_utc": "2026-08-03T21:00:00Z",
    "reason": "hipotesis registrada",
    "evidence_refs": ["docs/campaigns/CAMP-X.md"],
})
```

`previous_digest` y `record_digest` los genera el módulo.

## Alcance actual

Este commit impone secuencia y G2. Todavía no valida todos los campos específicos
de G0, G1, G3, G4 y G5; se agregarán sin relajar G2. Por eso el ledger queda
congelado antes de la primera promoción estadística hasta cerrar la enmienda.

## Tests escritos

`tests/research/test_promotion.py` cubre identidad, allowlist contractual, lista
exacta de gates, todos en PASS, entradas alternativa, secuencia, terminales,
append-only, duplicados, UTC y corrupción.

**Importante:** que los tests estén escritos no significa que hayan sido
ejecutados. Deben correrse en el entorno canónico antes del PR.

**Aporte al referente:** ninguna narrativa puede saltar directamente a evidencia
estadística; la promoción requiere identidad, contrato aprobado y evidencia
reproducible.
