# Impacto del filtro de noticias sobre operaciones ya publicadas (conteo target-free)

Estado: VIGENTE
Fecha: 2026-10-25
Familia / módulo: `costos` (`edgelab/noticias.py`); familias medidas: U1-CRUZADO y LUX-IMB (sólo tiempos)
Procedencia: `python tools/noticias_impacto_operaciones.py` → `IMPACTO_FILTRO_NOTICIAS.json` (este directorio), calendario
`config/noticias/calendario_usd_tier1.csv` (736 filas; fuentes en `config/noticias/FUENTES.md`).

## Qué se midió y qué no

**Sólo conteos de tiempo.** El script lee de los CSV las columnas de tiempo e identidad (`t`, `ses`, `ejecucion`, `motivo`,
`j_nq` en U1; `inst`, `dia`, `hora` en LUX-IMB). No lee `bruto`, `neto` ni ninguna columna de resultado. No se mira P&L con o
sin filtro, y por eso esto **no dice si el filtro mejora o empeora la regla**. Responde una sola pregunta: cuántas de
las operaciones ya publicadas no se podrían haber hecho bajo la regla de noticias. No toca el holdout: todo es anterior
a la sesión CME del 2026-10-01, y el script lo verifica con `edgelab.holdout`.

Ventana por defecto **±1 min** (LucidDaily fondeada: plano desde 1 minuto antes hasta 1 minuto después; ver el docstring de
`edgelab/noticias.py`). Para la fricción se agregan ±2 y ±5 como sensibilidad. `tier1` = lista mínima del pedido;
`tier1+tier2` suma las solicitudes semanales de subsidio.

**Justificación económica:** si una regla operable cae en ventanas de noticia, una cuenta de prop la pierde (hard breach en
LucidDaily) o paga una fricción que el backtest con costos medios no ve. Saber la proporción expuesta dice cuánto de la
muestra publicada no es ejecutable tal cual.
**Cómo podría refutarse:** si las salidas reales (no publicadas) de U1 cayeran todas antes de la ventana, la cota de
tenencia máxima sobrestima el cruce; si `hora` de LUX-IMB no fuera la hora de Nueva York del cierre de confirmación (lo es
según `tools/luximb_parity/luximb_m8_features.py:44-45`), el conteo de LUX-IMB no vale.

## U1-CRUZADO (`docs/research/areas_expansion_20261022/u1/`)

El CSV no trae la hora de salida, así que hay dos cotas. **Entrada:** el instante `t`, cierre de la vela de decisión; la orden
E1A se llena en el primer tick de la vela siguiente. **Tenencia máxima:** el intervalo [t, min(t + 241 min, 16:00 CT de `ses`)],
con el tope de 240 barras del simulador más la vela de llenado. El cruce real está entre las dos. Se cuentan sólo las
operaciones operadas (`motivo` vacío).

| Archivo | Ejecución | Operadas (sesiones) | Entrada en ventana ±1 | Tenencia máx. cruza ±1 (tier1) | ídem tier1+tier2 | ±2 / ±5 (tier1, tenencia máx.) |
|---|---|---|---|---|---|---|
| `U1_CRUZADO_20250805_20260331` | E1A/T1/S3 | 49 (37) | 0 (0,0 %) | 4 (8,2 %) | 5 (10,2 %) | 4 / 4 |
| `U1_CRUZADO_20250805_20260331` | E1A/T3/S3 | 52 (37) | 0 (0,0 %) | 4 (7,7 %) | 5 (9,6 %) | 4 / 4 |
| `U1_CRUZADO_20260401_20260930` | E1A/T1/S3 | 90 (44) | 1 (1,1 %) | 3 (3,3 %) | 4 (4,4 %) | 3 / 3 |
| `U1_CRUZADO_20260401_20260930` | E1A/T3/S3 | 92 (46) | 1 (1,1 %) | 3 (3,3 %) | 4 (4,3 %) | 3 / 3 |

La entrada en ventana no cambia con ±2 ni con ±5 (sigue en 0 y 1). Eventos tocados con la tenencia máxima y ±1 (tier1):
desarrollo → FOMC_MINUTES, PPI, ISM_MANUFACTURING_PMI y JOLTS (uno cada uno); réplica → CPI, PPI e ISM_MANUFACTURING_PMI.

Lectura: casi ninguna operación de U1 **entra** en una ventana (0 de 101 en desarrollo, 1 de 182 en réplica). Hasta un 8 %
podría estar **posicionada** durante una publicación si dura lo máximo. Ese tramo es el que la regla de LucidDaily
prohíbe. Hace falta la hora de salida para el número exacto (ver NO MEDIDO).

## LUX-IMB (`docs/research/luximb_parity_20261020/`)

No hay CSV de **operaciones** con entrada y salida: los CSV de la familia son de eventos y resultados. Se cuentan los
**instantes de decisión** (cierre de la vela de confirmación, `dia` + `hora` de Nueva York) de los archivos de features
de M8/M10, que son descubrimiento hasta el 2026-03-31. No se usa `feat_NQ_ES.csv`, que es la unión de NQ y ES.

| Archivo | Inst. | Eventos | Rango | Decisión en ventana ±1 (tier1) | ±2 | ±5 | ±1 tier1+tier2 |
|---|---|---|---|---|---|---|---|
| `desc_m8/feat_ES.csv` | ES | 6.469 | 2025-07-25 → 2026-03-31 | 28 (0,43 %) | 44 (0,68 %) | 81 (1,25 %) | 29 (0,45 %) |
| `desc_m8/feat_NQ.csv` | NQ | 5.421 | 2025-08-12 → 2026-03-31 | 20 (0,37 %) | 34 (0,63 %) | 58 (1,07 %) | 20 (0,37 %) |
| `desc_m10/feat_6B.csv` | 6B | 6.283 | 2025-08-08 → 2026-03-13 | 32 (0,51 %) | 50 (0,80 %) | 86 (1,37 %) | 39 (0,62 %) |
| `desc_m10/feat_6E.csv` | 6E | 5.538 | 2025-08-11 → 2026-03-13 | 36 (0,65 %) | 55 (0,99 %) | 88 (1,59 %) | 45 (0,81 %) |
| `desc_m10/feat_6J.csv` | 6J | 5.223 | 2025-08-08 → 2026-03-13 | 33 (0,63 %) | 49 (0,94 %) | 81 (1,55 %) | 42 (0,80 %) |
| `desc_m10/feat_GC.csv` | GC | 5.097 | 2025-08-11 → 2026-03-27 | 28 (0,55 %) | 36 (0,71 %) | 52 (1,02 %) | 30 (0,59 %) |
| `desc_m10/feat_MBT.csv` | MBT | 3.884 | 2025-09-01 → 2026-03-27 | 18 (0,46 %) | 26 (0,67 %) | 53 (1,36 %) | 18 (0,46 %) |
| `desc_m10/feat_MYM.csv` | MYM | 4.828 | 2025-10-07 → 2026-03-16 | 13 (0,27 %) | 28 (0,58 %) | 53 (1,10 %) | 16 (0,33 %) |
| **Total** | | **42.743** | | **208 (0,49 %)** | **322 (0,75 %)** | **552 (1,29 %)** | **239 (0,56 %)** |

Estos son eventos de medición, no operaciones de una regla. Dicen con qué frecuencia el detector **decide** dentro de una
ventana, no cuánto tiempo quedaría posicionada una operación.

## MEDIDO / NO MEDIDO

- MEDIDO (2026-10-25): proporción de entradas de U1-CRUZADO en ventana ±1 (0 % desarrollo, 1,1 % réplica) y cota superior
  por tenencia máxima (≤ 8,2 % / ≤ 3,3 %); proporción de decisiones LUX-IMB en ventana (0,49 % con ±1, 1,29 % con ±5).
- NO MEDIDO: cruce **exacto** de U1 (falta la hora de salida en `U1_CRUZADO_*_operaciones.csv`; hay que agregar `j_salida` o
  `t_salida` al simulador y republicar); operaciones de la regla del visor de LUX-IMB (no hay CSV de operaciones); el
  efecto del filtro sobre el P&L (a propósito: se mide sólo con pre-registro, antes de mirar); noticias fuera de la lista
  tier1 que LucidDaily también bloquea (ADP, Flash PMI, UoM, etc.; ver `config/noticias/FUENTES.md`).

## Siguiente paso

1. Guardar la hora de salida en el CSV de operaciones de `edgelab/research/areas_expansion.simular` / `u1_cruzado.operar`
   para medir el cruce exacto.
2. Toda campaña nueva declara en su manifiesto si aplica `edgelab.noticias.cruza_noticia` (y con qué ventana) **antes** de
   correr: el filtro es una regla de ejecución, no un parámetro que se elige mirando el resultado.

Aporte al referente: ejecutabilidad real. El calendario y el filtro dejan medir y aplicar la regla de noticias de las
props antes de arriesgar una cuenta. Las operaciones publicadas de U1 casi no entran en ventana; hasta un 8 % podría estar
posicionada durante un dato.
