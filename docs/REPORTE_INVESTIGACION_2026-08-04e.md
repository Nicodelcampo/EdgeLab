# Reporte de investigación (5) — 2026-08-04 · autoridad canónica G2

## Hallazgo

La reconstrucción canónica agregada en `b574d6c` vivía en
`g2_decision.validate_decision_dict()`, pero `PromotionRegistry` todavía no la
invocaba. `_validate_g2()` aceptaba una forma superficial con `passed=true`,
cinco nombres de gates y hashes bien formados, sin reconstruir el IC primario ni
recalcular la decisión.

Por lo tanto, el criterio #6 de la enmienda G2 no estaba completamente cerrado.
La allowlist vacía contenía el riesgo actual, pero abrirla en el futuro habría
reactivado el bypass.

## Corrección

Commit:

```
d92fa8a801623caed3a6f2ad5b5685e0333ff4e5
fix(research): require canonical G2 decision for promotion
```

`promotion.py` ahora:

- importa la única definición de `G2_REQUIRED_GATES` desde `g2_decision`;
- reconstruye toda decisión con `validate_decision_dict()`;
- no confía en `passed` ni `evidence_digest` recibidos;
- exige el IC primario canónico y su cota inferior positiva;
- exige que los cinco gates resulten PASS después de reconstrucción;
- exige coincidencia de `campaign_id`, `run_id` y `config_id` entre la fila del
  registry y la decisión;
- conserva la allowlist contractual vacía.

Regresiones agregadas contra:

- `passed` falsificado;
- `evidence_digest` adulterado;
- IC ausente;
- cota inferior del IC igual a cero;
- gate DSR fallido;
- identidad cruzada de campaign/run/config;
- forma superficial anterior.

## Verificación

El sandbox no tiene pytest instalado. Se ejecutaron:

```
py_compile: PASS
PROMOTION_CANONICAL_G2_HARNESS_PASS
```

El harness ejercitó una promoción canónica válida, todos los bypasses anteriores
y la secuencia append-only completa. Esto no sustituye pytest canónico.

## Handoff a la máquina operativa

Claude debe hacer fetch de `d92fa8a...` y ejecutar:

```bash
python -m pytest tests/research/test_promotion.py tests/research/test_g2_decision.py --basetemp=C:/t -q
python -m pytest --basetemp=C:/t -q
```

Debe reportar cualquier regresión sin abrir allowlists ni modificar la enmienda.

**Aporte al referente:** se cerró la distancia entre una decisión G2 serializada
y la única autoridad capaz de promocionarla. Una fila superficial ya no puede
materializar `statistically_supported`, incluso después de una futura apertura
de allowlist.
