# HP-007 — Contrato de medición causal de corredores v1

**Estado:** preregistro de infraestructura; no certifica resultados.  
**Holdout:** sellado desde `2026-07-01`; estas herramientas rechazan señales de desarrollo en o después de esa fecha.  
**Principio:** el efecto primario es el **delta neto del corredor contra un control emparejado**, no la expectativa absoluta del corredor.

## Qué corrige

Los scripts exploratorios anteriores mezclan eventos dependientes, usan controles aleatorios no comparables, permiten decisiones con OHLC ambiguo, prueban muchas variantes sin ledger completo y aplican tests por evento como si cada observación fuera independiente. También contienen rutas locales y afirmaciones más fuertes que la evidencia.

La nueva capa es aditiva: no borra ni reescribe resultados históricos. Los resultados anteriores quedan como evidencia exploratoria, no como certificación.

## Contrato obligatorio

1. **Point-in-time:** cada feature lleva `created_ns`, `available_ns` y `decision_ns`; debe cumplirse `created <= available <= decision`.
2. **Ejecución:** entrada en el primer tick ejecutable estrictamente posterior a la decisión. Nunca se llena en la barra/tick que genera la señal.
3. **Identidad:** cada evento fija `root`, contrato real, `trade_date`, `regime_id` y `session_id`. Se aborta si la trayectoria cruza contrato, sesión de trading o régimen.
4. **First passage:** target y stop se resuelven en secuencia de ticks. OHLC solo puede usarse como análisis acotado: las barras que tocan ambos niveles se reportan como ambiguas y deben calcularse en escenario pesimista y optimista; nunca con target-first implícito.
5. **Independencia:** se admite una señal por episodio predefinido mediante cooldown causal. La inferencia reagrupa por sesión; no usa el número bruto de eventos como N independiente.
6. **Control:** matching 1:1 sin reemplazo dentro de estratos congelados: contrato, dirección, bucket horario, volatilidad, impulso y distancia. Un caliper fallido produce abstención, no un match forzado.
7. **Estimando primario:** `mean(net_R_corridor - net_R_control)` por sesión. Si el control iguala o supera al corredor, no existe edge incremental aunque ambos sean positivos.
8. **Fricción:** reportar ideal, base, adversa y severa usando la fuente única `edgelab/research/costs.py`. Ideal jamás decide.
9. **Inferencia:** bootstrap y permutación al nivel de sesión. Para G2, reutilizar la implementación canónica `stationary_bootstrap_t`, PBO, DSR, walk-forward y sensibilidad del contrato G0–G5; este módulo no crea una ruta alternativa de promoción.
10. **Multiplicidad:** toda variante corrida cuenta en `N_eff`; Holm se reporta para la familia de contrastes. No se agregan variantes después de mirar resultados dentro de la misma campaña.
11. **Walk-forward:** folds naturales por contrato; el ganador se vuelve a seleccionar usando solo contratos anteriores. Nunca partir un único flujo de barras a la mitad y llamarlo validación externa.
12. **Provenance:** cada salida incluye hash canónico del manifiesto y hash del input. Manifiesto, adapter y dataset deben identificar sus hashes.
13. **Lenguaje:** hasta aprobar G3, usar `PROMISING_EXPLORATORY_CANDIDATE`; no afirmar mecanismo L2, causalidad institucional ni universalidad.

## Archivos

- `edgelab/research/liquidity_corridors.py`: contrato causal, first-passage tick a tick, deduplicación, matching, inferencia pareada, Holm y auditoría.
- `tools/measure_liquidity_corridors.py`: runner portable JSONL con hashes; no descubre rutas ni abre datasets.
- `tests/research/test_liquidity_corridors.py`: verdad conocida para look-ahead, holdout, orden de ticks, cambio de régimen, matching, dependencia por sesión, multiplicidad y placebo superior.

## Esquema de entrada del runner

El manifiesto JSON fija antes de correr:

```json
{
  "campaign_id": "HP007-CAMP-001",
  "definition": {
    "forward_density_max": 0.28,
    "backstop_density_min": 0.70,
    "min_width_ticks": 4,
    "max_width_ticks": 7
  },
  "target_ticks": 10,
  "stop_ticks": 3,
  "horizon_ns": 3600000000000,
  "cooldown_ns": 60000000000,
  "friction_ticks_round_turn": 2.768,
  "n_eff_declared": 1
}
```

Cada línea JSONL contiene:

```json
{"signal": {"event_id": "...", "root": "6E", "contract": "6EM6", "trade_date": "2026-06-15", "regime_id": "...", "session_id": "...", "direction": 1, "created_ns": 1, "available_ns": 2, "decision_ns": 2, "reference_tick": 22000, "forward_density": 0.2, "backstop_density": 0.8, "width_ticks": 6, "time_bucket": "RTH_OPEN", "volatility_bin": "V2", "impulse_bin": "I1"}, "ticks": [{"ts_ns": 3, "price_tick": 22000, "contract": "6EM6", "trade_date": "2026-06-15", "regime_id": "...", "sequence": 0}]}
```

El adapter local debe construirse desde datos certificados y as-of. No se versionan payloads, outcomes ni datos del holdout.

## Gates de esta capa

- cero violaciones as-of;
- cero cruces de identidad;
- cero fills en la decisión;
- 100% de variantes en el ledger;
- matching con balance documentado y tasa de match;
- al menos 20 sesiones para que la inferencia preliminar deje de abstenerse; G2 conserva el mínimo canónico de 160 sesiones;
- CI pareado inferior > 0 y control emparejado inferior al candidato;
- resultado neto positivo en costo base y sin colapso bajo adverso;
- sensibilidad sin acantilado y walk-forward por contrato positivo.

Si cualquier requisito de datos falta, el estado correcto es `ABSTAIN`, no `PASS`.
