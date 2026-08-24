# CURRENT — estado de la rama crypto/contexto

> Este archivo describe la rama de módulo. La continuidad e integración siguen en
> `foundation/f0b-compatibility-probe`; este branch no reemplaza ese punto de entrada.

**Rama viva:** `foundation/f0b-compatibility-probe`  
**Rama de módulo:** `work/crypto-context-foundation-20260824`  
**Fecha:** 2026-08-24  
**Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Qué está vivo acá

**Piloto Binance USD-M para BigTrap2/BigTrap2Absorption, todavía target-free.**

- Ingesta `trades + bookTicker` con join estricto
  `bookTicker.transaction_time < trade.time`.
- `tick_size` y unidad base de cantidad son obligatorios; no se heredan de CME y no
  tienen default económico.
- Identidad y orden causal explícitos por timestamp más secuencia/ID.
- Contrato de sensibilidad de unidad congelado en
  `specs/crypto_bt2_target_free_v1.json`.
- Censo sin respuestas y validadores en `edgelab/crypto/target_free.py`.
- Materializador reproducible en `tools/binance_bt2_pilot.py`, con hashes de inputs y
  outputs y procedencia HEAD/dirty de inicio y fin.
- Join de contexto point-in-time estrictamente anterior en
  `edgelab/context/point_in_time.py`; igualdad sin secuencia falla cerrado.
- Tests focalizados de crypto y contexto pasaron en ambos eventos de CI del commit
  diagnóstico; la suite histórica completa conserva fallas heredadas en shards ajenos y
  sigue bajo aislamiento. No leer el PR como mergeable hasta cerrarlas.

## Firewall

```text
TARGET_FREE                   = true
CAMPAIGN_OUTCOMES_OPENED      = false
RETURNS_ACCESSED              = false
PNL_ACCESSED                  = false
HOLDOUT_ACCESSED              = false
EDGE_DECLARED                 = false
```

No interpretar cantidad de zonas, acuerdo maker/quote, actividad, spread ni estabilidad
como expectativa económica.

## Próximo input permitido

Parquets u oráculos de `trades` y `bookTicker`, acompañados por símbolo, fuente, rango,
`tick_size`, unidad base propuesta y hashes si ya existen. El orden de trabajo es:

1. verificar tamaño, hash y schema;
2. congelar unidad/metadata;
3. auditar IDs, gaps, timestamps, cobertura y join causal;
4. ejecutar sólo censos y sensibilidad target-free;
5. detenerse antes de cualquier columna de respuesta.

## No tocar desde esta rama

- outcomes, retornos, P&L, MAE/MFE o holdout;
- specs/splits congelados de campañas vigentes;
- la rama primaria durante el sweep activo;
- merge del PR #14 antes de CI completa y auditoría de base.

## Aporte al referente

La rama queda preparada para recibir datos crypto reales sin inventar unidades ni abrir
respuestas. El progreso actual reduce riesgo de look-ahead y de procedencia; todavía no
aporta evidencia de edge.
