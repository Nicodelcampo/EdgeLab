# Contextos implementables en análisis — contrato v0

**Estado:** join y features target-free implementados; HMM todavía no entrenado.  
**Modelo reservado:** `gate_gc_l1_hmm3_forward_v0`.  
**Outcomes:** no abiertos.  
**NORTH STAR:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`.

## Qué queda operativo

`edgelab.context` aporta dos piezas reutilizables:

1. `build_l1_minute_features`: RV, actividad, spread, tape imbalance y efficiency
   ratio con disponibilidad al cierre del minuto.
2. `attach_context_at_event_time`: join backward por instrumento, contrato y sesión
   CME, con edad máxima de un minuto y salida fail-closed por evento.

La capa sirve para BigTrap2Absorption, BigTrap2 u otros análisis porque no conoce
zonas, fills ni outcomes. Consume un ledger de eventos y una tabla de estados.

## Contrato temporal

```text
data_window_end <= feature_available_at <= event_time
```

La clave completa es:

```text
(instrument, contract, cme_session, feature_available_at)
```

Nunca se cruza instrumento, contrato o sesión. Una feature futura, stale o ausente no
se imputa: `context_as_of_ok=false` y se declara la causa.

## Estados

```text
calm / normal / volatile
```

`toxic` queda prohibido. El módulo viejo que llamaba OFI al signed tape y VPIN a una
media temporal no se reutiliza. Las features se llaman por lo que realmente miden.

## Uso dentro de análisis

El análisis principal se mantiene sin contexto. La extensión preregistrada puede usar:

```text
estimando_principal + contexto + estimando_principal×contexto
```

No se permite buscar el único subgrupo favorable después de mirar outcomes. Antes de
la corrida formal deben congelarse estimandos por estado, Holm, MDE y potencia por
celda. Las filas `context_as_of_ok=false` no entran silenciosamente.

## Lo que todavía no afirma este commit

- No existe checkpoint HMM entrenado.
- No existe normalización train-only congelada.
- No hay labels formales sobre GC ni crypto.
- No se declara que GATE mejora BigTrap2Absorption.
- El antiguo Transformer y su `model_id` quedan fuera de esta ruta.

## Event-space y población

- Eventos posibles: creación, aproximación, primer toque, toque n-ésimo,
  invalidación, expiración, confluencia y estado continuo.
- Este módulo no elige una familia. El manifiesto de cada campaña debe enumerarlas y
  congelar cuál analiza antes de outcomes.
- Cada evento se etiqueta sólo con el último contexto disponible en su propio t0.

## Justificación económica

Un contexto causal puede separar condiciones de liquidez y volatilidad donde una
señal conserva expectativa neta de aquellas donde los costos o el ruido la destruyen.
El valor sólo existe si la interacción es incremental, estable y ejecutable.

## Cómo podría refutarse

Se refuta como módulo útil si los estados no aportan información incremental, el join
no logra cobertura sin imputación, las celdas quedan sin potencia, aparece look-ahead o
la mejora no sobrevive preregistro, multiplicidad, OOS y costos.
