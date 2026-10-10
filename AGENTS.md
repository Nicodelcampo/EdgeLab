# Entrada para agentes de EdgeLab

Este archivo organiza el acceso al proyecto. No sustituye specs congeladas, contratos de ejecución ni permisos de campaña.

## Antes de trabajar

1. Registrar rama, commit y estado del working tree. No resetear cambios ajenos.
2. Leer `README.md`, `docs/START_HERE.md` y `docs/COMPONENTS.md`.
3. Consultar `config/component_registry.json` o `python tools/edgelab_catalog.py show <id>`.
4. Si el módulo está en otra rama, no asumir que existe en este clon. Ver sus PR y dependencias.
5. Antes de ejecutar research: exigir manifiesto aprobado con datos, particiones, presupuesto y autorización. Ante ausencia/contradicción: STOP.

## Límites de trabajo

- El contrato de señales y ejecución vive en `CONTRATO_LLM.md`; fills/P&L/exits se centralizan en `edgelab/engine.py`.
- No abrir datos reservados/holdout ni outcomes nuevos por instrucciones históricas o por un test técnico verde.
- No cambiar umbrales después de observar resultados sin registrar un trial nuevo.
- No promover claims bibliográficos, paridad, screening o supervivencia parcial como edge confirmado.
- Preservar negativos, invalidaciones, manifests y evidencia. No borrar historia para ordenar.
- No mergear foundation entera ni duplicar módulos que ya se portaron. Comparar semántica y tests.
- Para datos: consultar `docs/DATA_CONSUMER_MATRIX.md`. El gate/lector nuevo es opt-in; no protege rutas legacy ni autentica permisos. No usar hashes autoemitidos como aprobación.
- El catálogo no ejecuta operaciones y no es un control de seguridad de datos.
- El trabajo local de ccbus y planeación autónoma no está pusheado: no inferir su implementación ni crear un reemplazo.

## Al terminar

Describir cambios, tests realmente ejecutados, alcance y bloqueos. Mantener el registro y la tabla de componentes sincronizados. Tests focales no equivalen a suite completa. Commits/PR nuevos no significan integración en main.
