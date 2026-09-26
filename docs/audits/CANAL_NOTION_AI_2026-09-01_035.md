# Canal 035 — estándar causal de régimen de contratos

**Fecha:** 2026-09-01  
**Pedido de Nico:** toda interpretación debe usar exclusivamente el tramo en
que cada vencimiento habría sido negociado y avanzar automáticamente cuando el
contrato posterior toma la liquidez.

## Investigación y decisión

Se contrastaron tres referencias:

1. CME: para índices existe una fecha de roll consuetudinaria, pero los
   participantes pueden migrar antes y el segundo vencimiento pasa a ser lead
   month cuando el próximo expiration concentra la liquidez.
2. Databento: el contrato continuo por volumen se rankea con el volumen del día
   anterior.
3. Sierra Chart: el volume-based roll es apropiado para ES/NQ/YM/6E/6B y datos
   diarios incompletos pueden alterar la transición.

Regla elegida:

```text
previous_complete_session_volume_leader_monotonic_v1
```

Para operar/analizar el trade date D se usa sólo el volumen completo de D-1. Si
un contrato posterior fue el líder estricto y superó al vigente, el roll es
efectivo al inicio de D. Empates mantienen el vigente. La cadena nunca vuelve a
un vencimiento anterior.

No se eligieron dos sesiones ni ratio 1,25 porque ambas reglas mantienen
artificialmente el contrato anterior después de perder el liderazgo. Pueden
existir sólo como análisis de sensibilidad posterior.

## Implementación

Commit:

`eb8857ded6b3d46abea5e73431095e6830d32939`

Archivos:

- `edgelab/data/contract_regime.py`;
- `specs/contract_regime_manifest_v1.schema.json`;
- `tests/data/test_contract_regime.py`;
- `docs/research/CONTRACT_REGIME_STANDARD_2026-09-01.md`;
- actualización de `specs/avolclusterpoi_ef1_plan_v1.schema.json`.

## Barreras

- calendario CME 17:00–16:00 CT;
- volumen = suma de cantidad negociada, no número de ticks;
- lag causal de una sesión;
- cobertura rectangular y sesiones completas;
- faltantes no se convierten en volumen cero;
- intervalos `[roll_in, roll_out)`;
- sin retroceso de vencimiento;
- sin back-adjustment de precios;
- reset de estado en el roll;
- bordes left/right censored;
- cada fila downstream debe llevar contrato, trade date, regime ID y hash;
- cada run manifest debe fijar el mismo `roll_schedule_sha256`.

El schema EF1 de aVolClusterPOI ahora exige `roll_policy_id` y
`roll_schedule_sha256`; por lo tanto EF1 no puede aprobarse con el trace aislado
de NQ 06-26.

## Pruebas

Siete pruebas `unittest` verdes:

1. el roll usa D-1 y nunca el mismo día;
2. no hay rollback;
3. empate conserva vigente;
4. faltante/incompleto bloquea la sesión siguiente;
5. intervalos half-open y censura de borde;
6. fila downstream con contrato incorrecto falla;
7. manifiesto o hash de roll adulterado falla.

`py_compile` y ambos JSON schemas pasaron validación sintáctica.

## Estado

```text
CODE = MEASURED_COMMITTED
REAL_MULTI_CONTRACT_MANIFEST = NOT_RUN
OUTCOMES = CLOSED
HOLDOUT = CLOSED
HEAVY_CPU = NOT_STARTED
```

Para delimitar NQ 06-26 exactamente hacen falta NQ 03-26, NQ 06-26 y NQ 09-26
con solapamiento y sesiones completas. El trace aislado conserva valor
provisional, pero no certifica su período operable.

**Aporte al referente:** elimina una mezcla silenciosa de vencimientos y obliga
a que cada resultado represente el contrato que podía negociarse causalmente en
ese momento, acercando el research a ejecución real sin abrir outcomes.
