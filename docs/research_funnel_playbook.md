# EdgeLab research funnel — CPU/GPU + Edge Brain

## Invariantes

- Una propuesta LLM es una hipótesis, nunca evidencia y nunca se auto-promueve.
- El generador y el revisor deben ser independientes.
- Negativos, falsaciones, fallas y reparaciones se conservan.
- Artefactos invalidados o stale no se reutilizan silenciosamente.
- El ledger es append-only y encadenado por SHA-256.
- El atlas y las propuestas usan `asserts_edge: false`.
- D2 está sellado: el runner exige el hash exacto del split para construir su máscara.
- Edge Brain gobierna custodia y promoción; no reemplaza costos, fills, PBO, DSR, MCPT ni SPA.

## Particiones

- **D0**: factibilidad y muerte barata.
- **D1**: réplica exploratoria, estabilidad y plateau de familia.
- **D2**: confirmación reservada; cerrado por defecto.

Las fechas son cronológicas y el manifiesto de split tiene hash. Abrir D2 no está permitido desde E0–E3.

## EF0–EF5

1. **EF0 — Elegibilidad**: custodia, cobertura, clock, roll, esquema, costos y datos necesarios.
2. **EF1 — Atlas target-free**: features/ubicaciones/triggers sin retornos futuros.
3. **EF2 — Cheap kill en D0**: outcomes independientes de señal, costos, controles y mínimos de muestra. Sirve para matar, no para confirmar.
4. **EF3 — Familias en D1**: evitar producto cartesiano; evaluar mesetas y congelar como máximo un headline por familia.
5. **EF4 — Multiplicidad**: matriz unidad temporal × candidato; PBO/DSR/BH y anti-dirección.
6. **EF5 — Confirmación D2**: kernel compartido tick-exact, preflight, MCPT, SPA y una sola apertura después del freeze.

## Contrato para propuestas LLM

Cada propuesta declara:

- historia económica;
- `location`, `regime`, `trigger`, `invalidate`;
- máximo tres parámetros libres;
- ablations y requisitos de datos;
- `asserts_edge: false`;
- prohibición de búsqueda continua de períodos.

EMA/SMA quedan preferentemente como `REGIME_GATE`. Los triggers prioritarios son eventos de auction/flujo y estructuras ya presentes en EdgeLab: VWAP/valor, HVN–LVN, absorción/exhaustión, HFTZones, BigTrap y aVolCluster/POI.

## Asignación de hardware

### CPU

- Arrow/Parquet, hashes, calendarios, splits y resets;
- EMA recursiva y features secuenciales;
- máquinas de estado, pullback/timeout/BE;
- fills bid/ask y replay tick-exact;
- finalistas y doble simulador.

### GPU

- máscaras y transformaciones masivas;
- matriz señal × configuración en EF2;
- first-passage de horizonte acotado, una hebra por señal/config;
- bootstrap/permutaciones grandes y ventanas para deep learning.

El kernel GPU es screening no confirmatorio. Los sobrevivientes vuelven al motor CPU tick-exact. TPU se reserva para entrenamiento tensorial; no aporta al replay divergente/path-dependent.

## API implementada

- `edgelab.funnel.device`: detección y dispatch fail-closed.
- `splits`: D0/D1/D2 cronológicos y token hash para D2.
- `features`: banco EMA CPU Numba y FeatureStore versionado.
- `screen`: mismo contrato CPU Numba / GPU CuPy RawKernel.
- `survivors`: Parquet ZSTD con provenance.
- `runner`: E1–E3, un headline estable por familia y cero apertura D2.
- `ledger`: eventos append-only sobre Edge Brain.
- `hypothesis`: contrato estructurado para LLM.

## Limitaciones actuales

El snapshot privado contenía el código central de Edge Brain pero no sus schemas JSON. Se integró sólo el subconjunto completo y ejecutable de memoria, ledger, invalidación, elegibilidad y promoción. El atlas schema-dependent debe incorporarse cuando aparezcan sus schemas originales; no se recrean post-hoc.

## Estado de implementación EF0–EF5 (2026-10-03)

| Etapa | Estado | Dónde |
|---|---|---|
| EF0 elegibilidad | Implementada: chequeos automáticos; UNKNOWN bloquea | `edgelab/funnel/eligibility.py` |
| EF1 atlas target-free | BLOQUEADA: faltan los schemas JSON originales de Edge Brain (no se recrean) | — |
| EF2 cheap kill D0 | Implementada (CPU Numba / GPU CuPy, mismo contrato) | `screen.py`, `runner.py` |
| EF3 familias D1 + plateau | Plateau implementado (regla fijada de antemano) | `multiplicity.plateau_report` |
| EF4 multiplicidad | Contador global encadenado + nulo de máximo con dirección aleatoria por sesión | `multiplicity.py`, `FunnelRunner.run_e4` |
| EF5 confirmación D2 | Sin implementar la apertura; existe guardia de holdout y registro de fechas ya vistas | `custody.py` |

Reglas nuevas:
- `forbid_holdout` se llama en el constructor del runner (`holdout_first_date`) y en todo script que lea precios.
- `SeenLedger` registra qué fechas tuvieron **resultados** examinados. Un D2 con contaminación > 0 no es confirmación limpia.
- El nulo de máximo evalúa el MEJOR de todo el grid (no una celda elegida a posteriori). `p_max > 0.05` o ausencia de meseta → `NOT_REJECTED_NO_DIRECTIONAL_EVIDENCE`.
- Cada corrida registra `kernel_id`, versión, backend, precisión y hash del código del kernel.

Revisión independiente (2026-10-03) corrigió antes de integrar: guardia de holdout que fallaba abierta (ahora obligatoria: `holdout_first_date`, o `allow_unguarded=True` sólo en tests sintéticos); contador de pruebas registrado ANTES de examinar resultados, idempotente, con bloqueo de archivo y detección de truncado por `head`; el contador ahora entra en la decisión (Bonferroni por número de campañas); nulo de máximo calculado con una pasada de kernel por partición y dirección (verificado contra fuerza bruta en tests); meseta que cuenta los vecinos sin muestra suficiente como no positivos; huella de kernel por partición; `SeenLedger` marcado por el runner. Gate abierto: la revisión humana.
