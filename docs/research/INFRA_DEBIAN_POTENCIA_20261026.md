# Infraestructura del Debian para correr más y concluir más — lo agregado el 2026-10-26

Estado: VIGENTE
Fecha: 2026-10-26. Pedido de Nico: «implementá todas las propuestas dejándolas listas para correr en el Debian», con un cuidado
explícito: **no descartar estrategias que funcionan en el régimen actual aunque no hayan funcionado en el pasado**.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Corrección de la lectura del 2026-10-26
Se había escrito «el DESC nomina cientos de celdas que no se sostienen en otros años; hay que filtrar antes y con más datos». Nico lo
corrige: que una regla no funcione en 2023 **no** la refuta para hoy (ATJ-24: el pasado no mata; la confirmación es en lo más
reciente sin usar y forward). Por eso la etapa nueva «hacia atrás» es **informativa**: publica, nunca mata. Las seis candidatas de
U1-ES/YM que dieron en contra sobre 2023 siguen vivas en su embudo; ese resultado dice que, si el edge existe, es del régimen actual.

## Qué se agregó (todo con tests; ninguno relaja un gate)
| # | qué | dónde | cómo se activa | efecto en la decisión |
|---|---|---|---|---|
| 1 | etapa **ATRAS**: candidatas congeladas sobre años anteriores al DESC no usados | `edgelab/research/embudo.py` (`_fin_atras`) | `"atras": [d0, d1]` en la campaña (anterior al DESC; lo verifica el PREFLIGHT) | ninguno: A_FAVOR / EN_CONTRA_PASADO / NO_CONCLUYENTE al acta |
| 2 | **potencia prevista**: MDE de DESC/OOS/holdout antes de correr, y por candidata al final del DESC | `edgelab/research/potencia_previa.py` | `"potencia_previa": {"ops_mes", "sd_op", "efecto_util"}` (opcional); la de candidatas es automática | ninguno: se publica en MEDIDO y en el estado |
| 3 | **P&L normalizado** por el rango de la sesión anterior (causal) | `grilla_generica.escala_ops` | `NORMALIZAR = "rango_sesion_previa"` en el módulo del experimento | cambia el estadístico: se declara en el módulo, antes de correr |
| 4 | **meta-análisis** entre instrumentos de una regla congelada (fijo, aleatorio DerSimonian-Laird, I²) | `edgelab/funnel/metaanalisis.py`, `tools/metaanalisis_embudo.py` | a mano sobre estados del embudo | un paso de LORD++ sólo si se declara en un acta; hoy es diagnóstico |
| 5 | **calendario de eventos** CPI/NFP/FOMC as-of, filtro y diagnóstico | `edgelab/research/eventos.py` sobre el calendario de `edgelab/noticias.py` (`tools/eventos_desde_noticias.py`; corregido el 2026-10-26: el primer calendario duplicaba `noticias.py`) | `EXCLUIR_EVENTOS = dict(...)` en el módulo; el diagnóstico sale en toda réplica | filtro: declarado antes; diagnóstico: informativo |
| 6 | **reparto entre las dos cuentas de Kaggle** según kernels corriendo | `embudo_runners.KaggleRunner.elegir_cuenta`, `tools/kaggle_auth.py` (cabecera por cuenta) | `"cuenta_kaggle": "auto"`; en el Debian, credencial y variables del paso 3a de `deploy/debian/LEEME.md` | ninguno (ventanas, LORD++ y registro son por familia) |
| 7 | conductores que sobreviven reinicios | ya lo hace el timer del Debian (`edgelab-autopilot.timer`, cada 10 min, `avanzar_todas`) | pasar la campaña a `"conductor": "debian"` (traspaso de `DECISIONES_20261025_SV1.md` §3) | — |

Fuente del calendario: `config/noticias/calendario_usd_tier1.csv` de `edgelab/noticias.py` (fuente por fila). El 2026-10-26 se había armado un calendario propio desde ALFRED y la Fed sin buscar antes: duplicaba ese módulo y se reemplazó.

## Para el agente del Debian (orden sugerido en campañas nuevas)
1. Declarar `potencia_previa` con la frecuencia y el desvío de una familia vecina: si los meses necesarios superan la historia, ampliar
   instrumentos o años antes de lanzar (o lanzar sabiendo que el resultado esperable es NO_CONCLUYENTE).
2. Reglas con objetivo/stop en puntos y días muy distintos: `NORMALIZAR`.
3. `atras` con los años de Dukascopy no usados: información sobre si el edge es de régimen o general.
4. Mirar `eventos` en las réplicas antes del acta; si el P&L vive cerca de los eventos, declarar `EXCLUIR_EVENTOS` en una campaña nueva.
5. `"cuenta_kaggle": "auto"` en todas las campañas nuevas.

## Cómo podría refutarse que esto ayuda
Si las campañas con `potencia_previa` siguen terminando NO_CONCLUYENTE en la misma proporción, o la normalización no achica el IC
de las réplicas frente al P&L en puntos de las mismas celdas, no aporta y se retira.
