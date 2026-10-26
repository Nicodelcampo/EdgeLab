# Canasta de estrategias de régimen — capa sobre el embudo

Estado: VIGENTE
Fecha: 2026-10-26. Pedido de Nico: «dale con esa capa» (la canasta: sumar lo que confirma en lo más reciente, ponderar, retirar, renovar).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Código: `edgelab/funnel/canasta.py` (reglas en el docstring), CLI `tools/canasta.py`, tests `tests/test_canasta.py`. Estado: `CANASTA.json`
(se crea con la primera alta; hoy está vacía: **ninguna estrategia confirmó el holdout todavía**).

## Ciclo de vida de una estrategia
| paso | regla | quién |
|---|---|---|
| entra | sólo si el embudo la terminó **CONFIRMADA** en su holdout, congelada, con cotas estructurales (pérdida/ganancia máx. por operación, margen de hueco), fricción canónica, efecto útil y desvío de desarrollo | agente (`tools/canasta.py alta`) |
| se sigue | cada operación forward (paper; real cuando Nico lo decida) entra a un e-proceso válido mirando en cualquier momento (`secuencial.MonitorCandidato`) y a la curva | agente (`tools/canasta.py ops`) |
| sale | **futilidad** (demostrado E[x] < efecto útil), **drawdown** forward > `dd_max_r` × pérdida máx., **cota violada** (una operación fuera de lo declarado) o retiro manual con motivo; inmediato y registrado | automático / humano |
| no vuelve | la misma regla congelada retirada no reentra: necesita otra confirmación en datos nuevos | regla |
| pesa | riesgo igual (1/desvío; forward desde 30 operaciones), tope 25 % por estrategia y 50 % por instrumento; si los topes no dejan llegar al 100 %, el resto queda sin asignar | automático |

Los valores (`peso_max`, `peso_max_instrumento`, `dd_max_r`, `min_ops_peso`, `alfa_futilidad`) están en `canasta.DEFECTOS`; cambiarlos con
estrategias adentro es un cambio de reglas y se consulta con Nico.

## Qué esperar (de CANASTA-REGIMEN-1)
El rendimiento reciente de las celdas de U1 no predijo el siguiente (1–6 meses): esperar **pocas confirmaciones** por mucho volumen de
candidatas, y que **retirar rápido** sea parte del valor. Lo que alimenta la canasta es el embudo corriendo muchas gramáticas e
instrumentos. Ver `docs/research/canasta_regimen_20261026/`.

## Lo que falta (no bloquea)
- Fuente de operaciones forward: hoy el CONTEO/HOLDOUT del embudo cuenta y decide; la serie forward posterior (paper) se carga con
  `tools/canasta.py ops`. Conectar un feed de paper trading es trabajo aparte.
- Correlación entre estrategias: el peso es de riesgo igual por estrategia, sin matriz de covarianzas (con pocas estrategias y pocas
  operaciones la covarianza estimada es ruido); se revisa cuando haya ≥ 5 activas con ≥ 30 operaciones forward cada una.
