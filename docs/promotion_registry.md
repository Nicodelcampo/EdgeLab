# Promotion Registry — control ejecutable de estados

> Referente: `docs/NORTH_STAR.md`. Incidente de origen:
> `docs/incidents/INC-007_autoridades_estadisticas_incompatibles.md`.

## Propósito

`edgelab/research/promotion.py` es la única superficie sancionada para
materializar estados de candidatos. Un reporte Markdown, un print de gauntlet o
un booleano suelto no promueven nada.

El ledger canónico vive en `docs/promotion_registry.jsonl` cuando exista la
primera entrada. Es append-only y cada fila queda encadenada por SHA-256.
Alterar, borrar o reordenar una fila invalida el ledger completo y bloquea
nuevas promociones.

## Cadena

```text
external_candidate | idea
  -> technically_valid
  -> exploratory_candidate
  -> statistically_supported
  -> economically_viable
  -> holdout_confirmed
  -> paper_validated
  -> live_candidate
```

`failed` y `retired` son terminales. No se permiten regresiones ni saltos de
gate. Un candidato nuevo sólo puede entrar como `external_candidate` o `idea`.

## Regla fail-closed G2

Todo estado igual o posterior a `statistically_supported` exige:

- `campaign_id`;
- `run_id`;
- `config_id`;
- `validation_decision.gate = G2`;
- `validation_decision.passed = true`;
- SHA-256 completo del contrato;
- digest completo de la evidencia;
- lista explícita de gates requeridos;
- resultado `passed=true` para cada gate, sin faltantes ni extras.

El registro no decide qué significa MCPT, PBO, DSR o walk-forward. Exige que la
decisión cite el contrato versionado que sí lo define. Esto permite enmendar G2
sin volver permisivo el ledger.

## Ejemplo mínimo

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

Los campos `previous_digest` y `record_digest` los genera el módulo. El caller
no puede proporcionarlos.

## Alcance actual

Este control impide promociones estadísticas inválidas. Todavía no valida los
requisitos específicos de G0, G1, G3, G4 o G5; esos validadores se agregan sin
relajar la regla G2. Hasta entonces, llegar a estados posteriores exige conservar
la decisión G2, pero no implica que los demás gates ya tengan enforcement
completo.

## Pruebas

`tests/research/test_promotion.py` cubre:

- identidad obligatoria para G2;
- gates completos y todos en PASS;
- DSR/MCPT/PBO faltantes bloqueados por estructura;
- secuencia sin saltos ni regresiones;
- estados terminales;
- append-only;
- duplicados;
- timestamps UTC;
- alteración, borrado y ruptura de la cadena de hashes.

**Aporte al referente:** un candidato no puede avanzar hacia despliegue por una
etiqueta narrativa; debe dejar evidencia ligada a una campaña y una decisión
reproducible.
