# EdgeLab

Herramientas para investigar edges y regímenes de mercado con contratos de datos, ejecución compartida y evidencia verificable. Un indicador, un backtest positivo o un PASS técnico **no** confirman un edge.

## Empezar aquí

1. [Entrada para humanos y agentes](docs/START_HERE.md).
2. [Mapa de componentes](docs/COMPONENTS.md): qué hace cada parte, dónde vive y qué falta integrar.
3. [Entorno e instalación](docs/ENVIRONMENT.md).
4. [Plan de integración](docs/INTEGRATION_PLAN.md).
5. [Contrato de señales y ejecución](CONTRATO_LLM.md), antes de proponer estrategias.

### Consultar el repo sin datos ni credenciales

Requiere Python 3.10+ **sólo para este catálogo**; no fija el entorno del motor.

```bash
python tools/edgelab_catalog.py list
python tools/edgelab_catalog.py show memory
python tools/edgelab_catalog.py check --json
```

Estos comandos usan sólo el registro y rutas del repo. No importan el motor, leen ticks, ejecutan campañas ni conectan servicios. `check` valida **el mapa**, no certifica EdgeLab ni habilita research.

### Datos Kaggle

[Entrada única y versiones fijadas para agentes](docs/KAGGLE_START_HERE.md).
El inventario distingue QA de research; el release actual NO está listo para research.

## Estado de integración

La base de organización/núcleo ya se integró mediante [PR 69](https://github.com/Nicodelcampo/EdgeLab/pull/69). Para screening, consultar el [contrato CPU del funnel](docs/COMPONENT_FUNNEL.md); no tratarlo como una plataforma confirmatoria completa.


Esta base contiene motor, bridge, contratos de datos, validación, memoria, funnel e [infraestructura técnica Kaggle](docs/COMPONENT_KAGGLE.md). El dataset agregado actual sigue bloqueado para research causal hasta resolver calidad/liquidez. Otras capacidades viven en ramas/PR separados. `foundation/f0b-compatibility-probe` y `main` divergen: no son intercambiables y no se propone un merge masivo. Consulte el registro, no asuma disponibilidad por una descripción histórica.

## Flujo y límites

**Datos autorizados → hipótesis/preregistro → ejecución → validación → evidencia → memoria → consulta/visor.**

- Screening no es confirmación; paridad técnica no es rentabilidad.
- Datos privados, dependencias y permisos son explícitos por componente.
- Una fecha de holdout en un documento viejo no autoriza lectura. Use el manifiesto aprobado de la campaña; si falta o contradice otra fuente, deténgase.
- Investigación y evidencia histórica permanecen preservadas; no son la API estable.
- Agentes/ccbus serán consumidores de estos contratos. El trabajo local de coordinación y autonomía no se implementa en esta fase.
