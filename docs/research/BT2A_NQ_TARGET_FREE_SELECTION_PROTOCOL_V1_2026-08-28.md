# BigTrap2Absorption NQ — selección estructural target-free v1

## Pregunta

¿Qué configuración produce una población de creaciones NQ reproducible, con cobertura suficiente y estable frente a perturbaciones cercanas, antes de mirar cualquier comportamiento posterior del precio?

## Universo

Cinco contratos NQ y 234 sesiones CME desde `20250804` hasta `20260630`. El dataset de research debe excluir físicamente todo timestamp igual o posterior a `1782856800000000000` ns.

## Diseño

El diseño incluye el ancla usada en GC, perturbaciones one-factor-at-a-time sobre los 16 parámetros de creación y 64 filas de interacciones discretas balanceadas. Parámetros de lifecycle y presentación permanecen fijos y no participan en la selección.

Cada configuración se ejecuta una sola vez por contrato. La partición segura es el contrato. El estado causal interno se conserva a través de las sesiones de cada contrato; no se puede paralelizar por sesión.

## Coordenadas permitidas

Se conservan únicamente identidad de configuración, contrato, sesión CME, timestamp disponible, fila fuente, dirección, precio de creación, score y umbral. No se inspecciona ningún tick posterior a la creación para generar métricas de selección.

## Elegibilidad

Una configuración debe tener al menos 400 eventos, 40 sesiones y cuatro contratos con eventos; HHI contractual no mayor que 0,55; ninguna sesión puede concentrar más del 10% de los eventos; y la mediana de Jaccard exacto con cuatro vecinos paramétricos debe ser al menos 0,25.

Estos umbrales son de estabilidad y cobertura. No demuestran potencia estadística ni rentabilidad.

## Selección

Entre configuraciones elegibles se maximiza un score congelado de estabilidad de vecindad, cobertura de sesiones, desconcentración contractual y estabilidad de conteo. Los desempates prefieren menor distancia normalizada al ancla GC y luego `config_id` ascendente.

Si ninguna configuración satisface todos los requisitos, el único resultado permitido es:

```text
ABSTAIN_NO_STABLE_NQ_CONFIGURATION
```

## Firewalls

```text
TARGET_FREE                  = true
LIFECYCLE_ACCESSED           = false
FIRST_TOUCH_ACCESSED         = false
FUTURE_PRICE_PATH_ACCESSED   = false
FIRST_PASSAGE_ACCESSED       = false
MFE_MAE_ACCESSED             = false
RETURNS_ACCESSED             = false
PNL_ACCESSED                 = false
HOLDOUT_ROWS_DECODED         = false
HOLDOUT_TOUCHED              = false
EDGE_DECLARED                = false
```

Planificar y validar contratos no autoriza ejecutar el kernel. La ejecución exige spec congelada, paquete físico hash-bound, commit exacto, runtime Kaggle y token separado.
