# EdgeLab — contrato Puerta 0.5 del runner económico

**Estado:** `SCAFFOLD_FAIL_CLOSED`  
**Outcomes:** cerrados  
**Holdout:** cerrado

## Propósito

Impedir que Puerta 1 se ejecute antes de congelar causalidad, datos, costes, fill, multiplicidad y autorización humana. Este componente no lee datos ni resultados; sólo valida el manifest de campaña.

## Gates obligatorios

1. Discovery y validation terminan estrictamente antes de `1782856800000000000`.
2. Todos los inputs tienen SHA-256 real.
3. `signal_semantics.status=CERTIFIED` y contiene `formation_spec` y `available_at_contract`.
4. Fill: `OBSERVED_FIRST_EXECUTABLE_TICK_OR_ABSTAIN`.
5. Costes: comisión, fees, spread, slippage base, estrés y latencia.
6. Familia y número efectivo de hipótesis congelados.
7. Outcomes habilitados explícitamente.
8. Autorización humana explícita.

## Separación temporal

`display_bar_key` no define la formación del indicador. Para BT2A actual la forma esperada, pendiente de certificación por PR #48, es:

```json
{"kind": "tick_count", "value": 25}
```

El adapter Factory→Brain exige:

```text
formation_start_ns <= formation_end_ns <= available_at_ns < observed_fill_ns
```

Si no hay fill observado, registra `NO_EXECUTABLE_FILL_AVAILABLE`; nunca inventa un timestamp.

## Estado YM/BT2A

El manifest `config/edge_factory/ym_bt2a_economic_campaign_blocked_20260920.json` queda intencionalmente bloqueado por:

- hashes de input todavía no congelados;
- semántica de señal no certificada;
- outcomes deshabilitados;
- autorización humana ausente.

Esto permite construir y probar el runner sin abrir evidencia económica prematuramente.

## Aporte al referente

Puerta 1 deja de ser una intención narrativa y adquiere un preflight ejecutable, fail-closed y compatible con el Brain, sin fabricar fills ni tocar el holdout.