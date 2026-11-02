# Pre-registro: U1-CRUZADO en PAPEL y seguimiento/promoción POR CANASTA (2026-11-02)

Estado: VIGENTE (pre-registro; nada de la ventana forward se miró). Aprobado por Nico en la sesión en la nube: «sí, dalo de alta» y
«sí, agregá el seguimiento por canasta y la promoción». Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF5 (seguimiento forward). Marco: `docs/CARTERA_VIVA.md`.

## 1. U1-CRUZADO en papel
**Regla congelada**, sin cambios desde el acta del holdout exploratorio
(`docs/research/areas_expansion_20261022/u1/ACTA_HOLDOUT_EXPLORATORIO_U1_CRUZADO.md`):
- Señal U1 sobre USATECH (Dukascopy): N ≥ 3 zonas LUX-IMB en 40 pts, A/H ≥ 8, regreso al 75 %.
- Ejecución en NQ, base trasladada, entrada E1A. Objetivo T3, stop S3 con tope de 3× la distancia al objetivo. Fricción canónica de NQ.

**Motor.** `edgelab/research/u1_cruzado_papel.py`, etapa `OPERAR`. Llama a `u1_cruzado.operar` con el mismo código del descubrimiento.
- **Paridad verificada** (kernel `nicolasbuttaro/embudo-u1-cruzado-papel-paridad-operar-20250805`,
  `u1_cruzado/paridad_resultado.json`): n = 52 igual que la referencia. 50 de las 52 operaciones son idénticas. Las otras dos salen
  0,25 y 0,75 pts peor porque el stop se llena al precio real del primer tick que lo cruza (corrección conservadora del error 27 del
  simulador, posterior a esa medición). Media +21,24 contra +21,26.
- Paridad: el kernel sobre DESC 2025-08-05 → 2026-03-31 tiene que reproducir n = 52 y media +21,26. La referencia es
  `u1/topes/U1_TOPES_NQ_20250805_20260331_operaciones.csv` (mult:3, E1A/T3/S3).
- El alta en papel se hace sólo si la paridad da; si no da, se informa y no hay alta.

**Ventana.**
- Sesiones ≥ 2026-11-02.
- La familia `AREAS_EXP_1_CRUZADO` tiene consumidas las sesiones 2026-10-01 → 2026-10-22, por la mirada exploratoria. Su reuso
  autorizado es sólo con e-proceso; acá no se reusa nada.
- Las sesiones 2026-10-23 → 2026-10-31 quedan sin usar en este seguimiento. Siguen disponibles para la confirmación a N fijo del
  embudo.

**Monitor de la ficha.** Una observación por operación.
| Parámetro | Valor | Origen |
|---|---|---|
| Cotas declaradas | −655 / +735 pts | 3 × peor (−218,3) y mejor (+245,0) operación de desarrollo, DESC + réplica abr–sep, 144 operaciones |
| `mu_util` | 10,63 | 0,5 × min(media DESC 21,26; media réplica 27,34) |
| `sd_desarrollo` | 61,25 | por operación |

Retiro por futilidad, por drawdown mayor a 8 × la pérdida máxima declarada, o por violar una cota. Promoción individual por
e-proceso, según las reglas de la cartera.

**Datos.** Necesita, cada día, USATECH sellado (Dukascopy) y NQ sellado (logger de NT8). Si falta uno, la ficha no suma sesiones y
espera. El USATECH diario todavía no tiene fuente operativa: la descarga de Dukascopy en SV1 está caída.

**Cómo podría refutarse.** Futilidad del e-proceso o media forward ≤ 0. Ya se sabe que la regla no funcionaba en 2023–2024, así que
puede ser un edge de régimen que ya se apagó.

## 2. Seguimiento y promoción por canasta (`edgelab/cartera/canasta.py`)
**Serie.** Por sesión, la media del resultado de cada ficha miembro dividido por su desvío de desarrollo, en unidades de riesgo
igual.
- Una ficha sin operación esa sesión aporta 0.
- Sólo entran sesiones ya evaluadas por todas las fichas activas y con al menos una operación.
- Entrada a la canasta: una ficha entra cuando la evalúan por primera vez, desde la sesión siguiente a la última ya contada. Así
  nunca se reescribe una sesión ya mirada. Una ficha que no se puede evaluar no entra y no frena a las demás. Hoy es el caso de
  PRERANGE-ZONAS, que no tiene almacén de zonas forward, y de U1-CRUZADO hasta que exista el CFD diario.
- Miembros: fichas que ya entraron y siguen activas (o se retiraron después de esa sesión).

**Monitor.**
- Cotas: 3 × el peor y el mejor valor de la misma serie armada con las operaciones de desarrollo de las fichas. Se fijan una vez y
  sólo se ensanchan si entra una ficha nueva, con registro en la bitácora.
- `mu_util`: mediana de mu_util / sd de las fichas.
- `alfa_real`, `alfa_futilidad` y `min_ops_real`: los de la cartera.

**Promoción.** Con e-proceso de edge ≥ 1/alfa_real y al menos `min_ops_real` sesiones, todas las fichas activas en PAPEL pasan a
REAL ("promovida por canasta"). **REAL no habilita dinero**: las cuentas reales las habilita una persona. La futilidad o la cota
violada de la canasta generan una alerta, no un retiro: cada ficha conserva su propia regla.

**Por qué es válido mirarlo todos los días.** La composición de cada sesión se decide antes de esa sesión, y el e-proceso conserva
la garantía de Ville.

**Lo que no hace.**
- No corrige el sesgo de selección de cada estrategia: diversificar baja la varianza, no el sesgo. Por eso la futilidad individual
  sigue retirando rápido.
- No trata como independientes a estrategias correlacionadas: el valor de la canasta es una sola serie.

**Cambio de semántica.** La promoción por canasta es una regla nueva de promoción. La decidió Nico el 2026-11-02 en la sesión en
la nube.
