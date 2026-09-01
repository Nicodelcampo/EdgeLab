# EdgeLab CME Futures Tick Dataset — legacy private custody

> **NO USAR DIRECTAMENTE PARA RESEARCH.** Este inventario histórico contiene Parquets crudos que alcanzan el holdout sellado.

Estado:

```text
CLASSIFICATION              = RAW_CUSTODY_LEGACY
KAGGLE_VISIBILITY           = private_only
PRIVATE_CLOUD_CUSTODY       = approved
RESEARCH_INPUT_ELIGIBLE     = false
HOLDOUT_PHYSICALLY_ABSENT   = false
PUBLIC_REDISTRIBUTION       = forbidden
```

La metadata histórica que declaraba `CC0-1.0` fue retirada: EdgeLab no puede dedicar al dominio público datos de mercado de terceros. La directiva del propietario del 2026-08-28 habilita custodia y cómputo privados, no publicación ni redistribución.

Para próximas corridas, usar exclusivamente:

1. `tools/prepare_kaggle_research_dataset.py` para verificar fuentes y construir un paquete físicamente pre-holdout;
2. un spec de campaña derivado de `specs/kaggle_frozen_execution_v1.template.json`;
3. `notebooks/kaggle/10_frozen_job_runner.py` para preflight y ejecución congelada;
4. el protocolo `docs/research/KAGGLE_FROZEN_EXECUTION_PROTOCOL_V1_2026-08-28.md`.

El packager no sube datos. La construcción del paquete requiere su token operativo y cada corrida requiere además freeze y autorización propios.
