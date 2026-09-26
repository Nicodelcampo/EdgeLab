# Canal 034 — infraestructura Kaggle EF0 para aVolClusterPOI

**Fecha:** 2026-09-01  
**Pedido de Nico:** continuar la infraestructura de análisis en forma de
embudo, donde los primeros análisis sugieren cuáles deben ejecutarse después.

## Decisión de arquitectura

Se implementó únicamente EF0 target-free. EF0 consume el trace completo ya
generado y no repite la corrida de 34.203.535 ticks. Produce un perfil amplio y
cinco tarjetas de preguntas. Ninguna tarjeta puede iniciar EF1.

No se reutilizó `edgelab/research/kaggle_multiverse_sweep.py`: ese script abre
P&L y rankea por profit factor, fuera del alcance autorizado.

## Commit A — núcleo revisable

`4b0e5b3c6cf359447b2b81dcb9a1f4f873fcca97`

Incluye:

- `edgelab/research/avolclusterpoi_funnel.py`;
- cinco pruebas sintéticas;
- contrato JSON Schema de EF1;
- documento de arquitectura.

Barreras:

- rechaza outcomes, retornos, P&L, MFE/MAE y precio futuro;
- valida scope y commit del trace;
- valida conteos, decisiones e identidad de bloque;
- valida referencias de zonas;
- separa 658 candidatos `CREATE` en 414 zonas `OFF_PRICE` y 244 candidatos
  `AT_PRICE`;
- etiqueta el perfil `PROVISIONAL_UNPARITIED_FOR_FORMAL_SELECTION` porque el
  gate end-to-end continúa `FAIL`;
- no rankea ni excluye configuraciones.

Las cinco preguntas son historia/buckets, presión del threshold, geometría,
materialización AT_PRICE/OFF_PRICE y estabilidad por sesión.

## Commit B — launcher fijado

`58496ad6d69f9335e684f55a9d5e8672819e5299`

El launcher Kaggle:

- ejecuta exactamente el código EF0 de `4b0e5b3`;
- acepta la carpeta del output previo o su ZIP;
- fija hashes de `all_blocks`, `zones`, `summary` y manifest;
- publica perfil, integridad, tarjetas, status, manifest y ZIP;
- termina con EF1 bloqueado;
- no abre datos crudos, holdout ni outcomes.

## Pruebas

`py_compile` verde. Aserciones directas verdes:

1. hash canónico independiente del orden de claves;
2. perfil y preguntas sin transición automática;
3. rechazo de identidad de bloque duplicada;
4. rechazo de campo `pnl`;
5. descomposición correcta de candidatos y zonas.

La corrida real EF0 no se efectuó desde este entorno porque no posee acceso al
output Kaggle privado. Su ejecución queda separada del commit de código.

## Estado

```text
EF0_CODE = READY
EF0_RUN = NOT_RUN_HERE
EF1_PLAN = BLOCKED_PENDING_EF0_OUTPUT
OUTCOMES = CLOSED
HOLDOUT = CLOSED
PARITY_END_TO_END = FAIL
```

**Aporte al referente:** transforma el trace ya pagado en un embudo auditable y
barato, haciendo que la próxima inversión de CPU responda a una pregunta
observada en EF0 en vez de ampliar de antemano el espacio de búsqueda.
