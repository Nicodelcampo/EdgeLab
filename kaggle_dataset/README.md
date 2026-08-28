# EdgeLab CME Futures Tick Dataset — legacy private custody

> **NO PUBLICAR NI ACTUALIZAR DESDE ESTA CARPETA.** Este inventario histórico contiene Parquets crudos que alcanzan el holdout sellado y el gate de licencia sigue `PENDING`.

Estado:

```text
CLASSIFICATION              = RAW_CUSTODY_LEGACY
KAGGLE_VISIBILITY           = private_only
RESEARCH_INPUT_ELIGIBLE     = false
DATA_LICENSE_APPROVED       = false
HOLDOUT_PHYSICALLY_ABSENT   = false
PUBLIC_REDISTRIBUTION       = forbidden
```

La metadata histórica que declaraba `CC0-1.0` fue retirada: EdgeLab no puede dedicar al dominio público datos de mercado de terceros.

Para próximas corridas, usar exclusivamente:

1. `tools/prepare_kaggle_research_dataset.py` para verificar fuentes y construir un paquete físicamente pre-holdout;
2. un spec de campaña derivado de `specs/kaggle_frozen_execution_v1.template.json`;
3. `notebooks/kaggle/10_frozen_job_runner.py` para preflight y ejecución congelada;
4. el protocolo `docs/research/KAGGLE_FROZEN_EXECUTION_PROTOCOL_V1_2026-08-28.md`.

El packager no sube datos y aborta mientras `docs/research/DATA_LICENSE_DECISION.md` no esté aprobado.
