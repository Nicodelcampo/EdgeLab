# aVolClusterPOI — resolución de barra (GC): resultado del experimento mínimo

- **Fecha**: 2026-08-26 · **Estado**: `MEASURED_COMMITTED`, target-free, `CAMPAIGN_OUTCOMES_OPENED=false`
- **Protocolo**: `docs/research/AVOLCLUSTER_POI_RESOLUTION_PROTOCOL_2026-08-26.md` §4 (experimento mínimo, aprobado por Nico)
- **Universo**: `specs/avolclusterpoi_resolution_split_v1.json` — 152 sesiones (GC 02-26/04-26/06-26/08-26), split `S`=133 / `C`=19, intersección 0. `C` no fue tocado por esta campaña.
- Este documento **consolida** tres artefactos ya commiteados por separado; no mide nada nuevo.

---

## 0. La pregunta

Nico preguntó si preferiría las zonas de otra resolución de ticks en vez de la M1 nativa del indicador. Antigravity propuso 5 métricas estructurales para comparar sin mirar P&L. `AVOLCLUSTER_POI_RESOLUTION_PROTOCOL_2026-08-26.md` las auditó (con research bibliográfico real) y encontró que apuntaban bien pero les faltaba nulo, split S/C, y un criterio para decidir tiempo-vs-ticks antes de barrer tamaño de bloque. Este documento es el resultado de correr ese protocolo corregido.

## 1. Paso 0 — cuánta actividad hay por minuto

`diag/tasa_senales/avolcluster_bar_type_paso0.py` · `docs/research/avolcluster_bar_type_paso0.json`

Sobre una submuestra determinística de 19 sesiones de `S` (cada 7ma, sin semilla): **mediana 61 ticks/minuto**, con dispersión grande (p10=16, p90=208 — más de 10× entre sesión lenta y sesión activa). De acá salieron los candidatos de ticks para el eje A (61→60, 183→185, 305→305, redondeados a múltiplo de 5), no elegidos a mano.

## 2. Eje A — tiempo vs. ticks

`diag/tasa_senales/avolcluster_bar_type_decision.py` · `docs/research/avolcluster_bar_type_decision.json`

Sobre las mismas 19 sesiones, comparando autocorrelación lag-1 y homocedasticidad de la serie de volumen del bloque de 10 barras (el mismo bloque que usa el indicador, no el score del kernel — eso sería circular):

| Candidato | Autocorrelación (↓ mejor) | Homocedasticidad (→1,0 mejor) |
|---|---:|---:|
| 1m | 0,616 | 0,103 |
| 3m | 0,574 | 0,081 |
| 5m | 0,576 | 0,104 |
| **60t** | **0,232** | **0,990** |
| 185t | 0,332 | 1,103 |
| 305t | 0,267 | 1,056 |

**Ganador: 60 ticks.** Los tres candidatos de tiempo son consistentemente malos en las dos métricas (no es un capricho de un minuto en particular); los de ticks ganan claro, y 60t gana en las dos métricas a la vez contra los otros dos candidatos de ticks propios.

## 3. Eje B — meseta de tamaño de bloque + placebo

`diag/tasa_senales/avolcluster_plateau_placebo.py` · `docs/research/avolcluster_plateau_placebo.json`

Corrido sobre **`S` completo (133 sesiones)**. Grilla declarada de antemano (no el producto cartesiano 5×3×3 completo — ver docstring del script para el alcance exacto): 5 tamaños de bloque {40,50,60,70,80}t a (percentil=98, multiplicador=2,0) + 4 combinaciones de (percentil, multiplicador) a bloque fijo 60t.

### 3.1 Placebo — resultado limpio

Permutación de volumen intra-bloque (K=50, preserva ticks activos y multiset de volumen exacto), sobre 30.138 bloques evaluados en la config ganadora (60t/98%/2,0):

- **Tasa de paso real: 2,38 %**
- **Tasa de paso placebo: 0,043 %**
- **Excedente: ~55×**

La estructura de volumen detectada no es ruido con forma de zona.

### 3.2 Meseta — resultado honesto, no un "sí" limpio

Con la vara declarada antes de correr (±15 % simultáneo en espesor, frecuencia normalizada y aislamiento respecto del vecino), **ningún vecino pasa las tres a la vez**. Pero el eje de tamaño de bloque muestra un **gradiente monótono y suave**, no un pico aislado:

| Bloque | Espesor mediana (ticks) | Aislamiento mediana (ticks) | Zonas |
|---:|---:|---:|---:|
| 40t | 13,0 | 62,0 | 672 |
| 50t | 15,0 | 71,0 | 458 |
| **60t** | **17,0** | **87,0** | **435** |
| 70t | 19,0 | 114,5 | 397 |
| 80t | 21,0 | 103,0 | 337 |

Cada paso cambia un poco, en la misma dirección — no hay salto brusco alrededor de 60t. Falla la vara estricta declarada (el motivo exacto por metrica y por vecino está en el JSON), pero no de la forma que preocuparía (una singularidad frágil).

El eje percentil/multiplicador confirma que el test funciona: bajar el percentil de detección (95 % en vez de 98 %) dispara la frecuencia +123 % — correcto y esperado, es un umbral, no una escala fina, y el chequeo lo marcó sensible como corresponde.

## 4. Qué significa esto para seguir

**60 ticks queda como candidato defendible**: gana claro el eje tiempo-vs-ticks (la pregunta más cara), tiene señal real contra el placebo, y su entorno inmediato se mueve suave, no erráticamente. No es una confirmación perfecta de meseta plana.

**Paridad**: en paralelo, Nico/Antigravity exportaron el oráculo NT8 sobre 60 ticks (`GC 04-26`, `E:\DatosNT8\avolcluster_gc0426_60t_oracle.csv`, 630 eventos: 180 `ZONE_CREATED`, 177 `FIRST_TOUCH`, 174 `ZONE_INVALIDATED`, 99 `AT_PRICE_CREATED`) y están corriendo el test de paridad 1 a 1 contra el kernel Python. Ese resultado es aparte de este documento.

**Pendiente, no hecho todavía**:
- Confirmación en `C` (las 19 sesiones apartadas) — sólo re-chequeo pass/fail de los gates para 60t, nunca re-optimizar ahí.
- El producto cartesiano completo de la grilla 2-D (5×3×3), si esta primera pasada no alcanza para decidir.
- Ciclo de vida más allá de creación (invalidación/touches) — el kernel de investigación en Python no lo implementa todavía; el `.cs` sí, y el oráculo recién exportado trae `FIRST_TOUCH`/`ZONE_INVALIDATED` que el kernel Python no puede reproducir aún.

## Aporte al referente

No mide edge todavía — es selección de instrumento, target-free, sin outcomes ni holdout tocado. El aporte es que la próxima medición formal sobre `aVolClusterPOI` (segunda familia viva del proyecto) parte de una resolución de barra elegida con criterio y verificada contra ruido, no heredada sin examinar de la configuración M1 por defecto del `.cs`.
