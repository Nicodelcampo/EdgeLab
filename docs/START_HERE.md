# Cómo entrar y trabajar en EdgeLab

## 1. Identificar el clon

```bash
git status --short
git branch --show-current
git rev-parse HEAD
python tools/edgelab_catalog.py check
```

No instalar dependencias ni ejecutar todos los scripts para «ver si funciona». El chequeo de navegación es sin red y sin datos.

## 2. Elegir una tarea

| Necesito… | Componente y siguiente paso |
|---|---|
| Entender lo que existe | `list`, después `show <id>`; [mapa](COMPONENTS.md) |
| Proponer una estrategia | `engine` y `validation`; [contrato](../CONTRATO_LLM.md) |
| Revisar datos o builders | `data` y `builders`; [matriz de lectores](DATA_CONSUMER_MATRIX.md), gate y autorización antes de leer |
| Screening CPU/GPU | `funnel`; [contrato CPU](COMPONENT_FUNNEL.md), split original y aprobación; GPU end-to-end bloqueado |
| Consultar/persistir evidencia | `memory`; especificar ledger, anchors y permiso |
| Papers SSRN | `bibliography`; PR 67 fuera de esta base |
| Ejecutar en Kaggle/agregados | `kaggle-execution`; [contrato local](COMPONENT_KAGGLE.md), QA y guard; dataset actual bloqueado para research causal |
| Ver indicadores | `bridge` + `viewer`; paridad específica y bundle aprobado |
| Ordenar investigación histórica | `campaigns` + `history`; conservar negativos |

`entrypoint` del registro es una referencia de uso, **no** una instrucción para autoejecutar. Las ayudas de herramientas de research pueden necesitar dependencias; no las importa el catálogo.

## 3. Establecer autoridad y permisos

- Specs/manifests aprobados gobiernan su objeto; el contrato de ejecución gobierna fills y señales.
- El registro gobierna navegación y ubicación, no veredictos económicos.
- Una política de holdout debe provenir de la enmienda aprobada y del manifiesto de campaña; no seleccionar una fecha por mayoría de documentos.
- Los docs de agosto/septiembre en otras ramas son fuentes históricas hasta reconciliar su vigencia. En particular hay diferencias entre el umbral antiguo de julio y HOLDOUT-A3 de octubre. Esta organización no abre ni amplía permisos.

## 4. Environments

El catálogo requiere sólo stdlib Python 3.10+. Eso no significa que el motor ni bridge soporten ese rango. `requirements-funnel.txt` y `requirements-funnel-gpu.txt` pertenecen al funnel; los locks de foundation pertenecen a otra base. El [entorno de esta base](ENVIRONMENT.md) define Python 3.12, lock CPU e instalación del wheel. La reconciliación de dependencias/suite con foundation sigue pendiente.

## 5. Reportar trabajo

Siempre: módulo, rama/commit, entradas, outputs, tests, permisos usados y límites. Si algo falta, registrar bloqueo con el dataset/dependencia/decisión concreta; no fabricar resultados ni reparar silenciosamente.
