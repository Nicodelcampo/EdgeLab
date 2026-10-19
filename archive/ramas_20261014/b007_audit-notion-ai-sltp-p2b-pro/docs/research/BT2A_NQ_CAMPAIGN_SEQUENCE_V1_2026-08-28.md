# BigTrap2 / BigTrap2Absorption NQ — secuencia operativa v1

- **Fecha:** 2026-08-28
- **Plataforma:** `KAGGLE_ONLY`
- **Ejecución pesada local:** prohibida
- **Holdout:** cerrado desde la sesión CME `20260701`
- **North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Estado corregido

P2-B económico de BigTrap2Absorption sobre GC ya fue ejecutado y fue negativo después de costos. No se programa una repetición. La publicación hash-bound del resultado continúa pendiente porque PR #18 todavía conserva el contrato preautorización.

```text
P2B_GC_SCIENTIFIC_STATUS       = COMPLETE_NEGATIVE_COST_DOMINATED
P2B_GC_RERUN_REQUIRED          = false
P2B_GC_RESULT_PUBLICATION      = PENDING
```

## Orden obligatorio

1. Construir el paquete NQ privado físicamente pre-holdout.
2. Verificar y subir el paquete como dataset privado; la subida requiere una autorización distinta del build.
3. Completar los bindings y congelar el rerun BigTrap2 clásico NQ V2 de 112 configuraciones.
4. Ejecutar BigTrap2 clásico NQ V2 en Kaggle. V1 se preserva como expuesta y no puede seleccionar nada.
5. Completar bindings y congelar la selección estructural target-free de BigTrap2Absorption NQ.
6. Ejecutar la selección target-free en Kaggle y producir coordenadas Parquet para cada configuración.
7. Aplicar la regla estructural preregistrada o emitir `ABSTAIN_NO_STABLE_NQ_CONFIGURATION`.
8. Consolidar el Event Store BT2A NQ creation-only desde las coordenadas seleccionadas, sin releer futuros paths.
9. Validar el Event Store y congelar Gate 1 BT2A NQ.
10. Ejecutar Gate 1 exclusivamente en Kaggle sobre las 16 celdas completas.
11. Mantener AVol Gate 1B, join AVol+BT2A, L2 y cualquier protocolo económico NQ en HOLD hasta una autorización posterior.

## Distinciones metodológicas

- El sweep BigTrap2 clásico NQ V2 y la selección BigTrap2Absorption NQ son campañas distintas.
- Las 16 celdas `4 barreras × 4 horizontes` pertenecen a outcomes de Gate 1; no son configuraciones del indicador.
- Una configuración BT2A se elige sólo mediante creación, cobertura, balance, concentración, estabilidad de vecindad y replay determinista.
- Maximizar cantidad de eventos, first passage, `d_hat`, MFE, MAE, retornos o PnL para elegir configuración está prohibido.
- `N≥400` y 40 sesiones son mínimos de cobertura, no prueba suficiente de potencia.

## Estado de autorizaciones

```text
AUTHORIZE_BUILD_KAGGLE_RESEARCH_DATASET_V1 = ISSUED
KAGGLE_DATASET_UPLOAD_AUTHORIZED            = false
AUTHORIZE_BT2_NQ_TICKFRAMES_SWEEP_V2        = NOT_ISSUED
AUTHORIZE_RUN_BT2A_NQ_TARGET_FREE_SELECTION_V1 = NOT_ISSUED
AUTHORIZE_BUILD_BT2A_NQ_CREATION_EVENT_STORE_V1 = NOT_ISSUED
AUTHORIZE_RUN_BT2A_NQ_GATE1_V1              = NOT_ISSUED
HOLDOUT_AUTHORIZED                          = false
OUTCOMES_AUTHORIZED                         = false
```

## Salidas exigidas por campaña

Cada campaña debe emitir identidad del commit y spec, hashes de inputs, checkpoints reanudables, manifest físico y lógico, attestation de firewalls, cobertura por contrato/sesión y clasificación explícita. Un binding ausente o inconsistente produce `ABSTAIN`; nunca un resultado parcial presentado como completo.
