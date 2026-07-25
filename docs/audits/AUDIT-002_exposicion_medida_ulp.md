# AUDIT-002 — Exposición MEDIDA a la familia de 1 ULP

**Fecha:** 2026-07-25 · **Alcance:** los 5 kernels · **Estado:** SOLO REPORTE.
Herramienta: `tools/ulp_exposure.py` · artefacto:
`runs/nt8_bridge/audit002_ulp_exposure.json`.

## Por qué existe: AUDIT-001 falló

`AUDIT-001` se hizo **leyendo código**. Marcó como riesgo **NULO** las
comparaciones de borde de zona razonando que "ambos operandos son precios de
grilla construidos igual en los dos lados" — y esa resultó ser **la causa raíz**
de los 82 `FEATURE_DIFF` de HFTZones2. Leer código tiene ese modo de falla.

AUDIT-002 mide en vez de leer, y se **calibra contra la verdad conocida** antes
de creerle cualquier otra cosa.

## Qué se mide

NT8 construye los precios desde el `double` que manda el feed (un decimal
parseado); el kernel Python desde `price_ticks × tick_size`. Representan el
mismo precio y **no son el mismo `double`** — difieren en 1 ULP en el 24,3 % de
los niveles del 6E, siempre con el feed por debajo.

Para cada umbral se evalúa el **caso decisivo** —el precio cae exactamente sobre
el umbral— con las dos representaciones, y se cuenta cuántas veces la decisión
**cambia de lado**. Si el umbral vive a medio tick, ningún precio negociable
puede caer ahí y la exposición es **cero por construcción**.

## Calibración contra el caso conocido ✅

| | predicho por el modelo | medido sobre el oráculo real |
|---|---:|---:|
| HFTZones2 `close_through` (lado inferior) | **9,90 %** | **9,0 %** (188 de 2.078 zonas) |

El modelo reproduce la verdad conocida, así que sus otras predicciones son
creíbles. **Sin esta calibración el reporte no valdría nada.**

## Resultados

| kernel | umbral | exposición |
|---|---|---:|
| **Gaps2** | `bottom < price`, `price >= top` | 0,00 % |
| **Gaps2** | `price <= bottom − 2·ts` (`inverse`) | **0,00 %** |
| **HFTZones2** | `price >= lower`, `price <= upper` | 0,00 % |
| **HFTZones2** | `price <= lower − pen·ts` | **9,90 %** ⚠ |
| **HFTZones2** | `price >= upper + pen·ts` | **48,59 %** ⚠ |
| **BigTrap2** | los 3 umbrales | 0 % *(medio tick, por construcción)* |
| **VolTicksPOC2** (`price_mark_ticks=1`) | ambos | 0 % *(medio tick)* |
| **VolTicksPOC2** (`price_mark_ticks=2`) | ambos | 0,00 % |
| **aVolCellPOI2** | ambos | 0 % *(medio tick, por construcción)* |

### Gaps2 es inmune de verdad, no por suerte

Su umbral expuesto **está fuertemente ejercitado**: de las 97.458 zonas de
desarrollo, **46.239 (47,4 %)** mueren por `inverse`. Con 0 % de exposición sobre
un camino usado casi en la mitad de los casos, el **PASS 1316/1316 está ganado**,
no es una ventana afortunada. Es la confirmación que hacía falta para seguir
usándolo como referencia.

### El hallazgo que importa para diseñar el fix

| expresión | offset neto | exposición |
|---|---|---:|
| `(e − ts) − ts` — HFTZones2 (`lower` ya restado, y se le resta otra vez) | −2 ticks | **9,90 %** |
| `e − 2·ts` — Gaps2 (una sola resta desde el precio negociado) | −2 ticks | **0,00 %** |

**Misma distancia matemática, distinta secuencia de operaciones, y una está
expuesta y la otra no.** El redondeo del paso intermedio es lo que introduce la
divergencia.

Consecuencia práctica: **no existe una regla simple del tipo "una operación es
segura y dos no"** — `upper + pen·ts` es una sola suma y da 48,59 %. La
exposición **hay que medirla por expresión**. Ésa es la razón de ser de esta
herramienta y la lección que AUDIT-001 no podía dar.

## Qué NO se hizo

- **No se aplicó ningún fix.** Los umbrales expuestos de HFTZones2 son los
  mismos que ya tienen causa raíz documentada y **esperan la decisión de Nico**,
  igual que los dos casos anteriores de la familia.
- No se tocó Gaps2 — y ahora hay evidencia de que **no hace falta**.
- No se cambió ninguna tolerancia ni semántica de gate.

## Recomendación de método (para la próxima vez)

Correr `python tools/ulp_exposure.py` **antes** de gastar un oráculo en un
kernel nuevo o en un parámetro no probado. Cuesta segundos y ya evitó dos
diagnósticos equivocados: el mío por lectura, y el primer modelo de esta misma
herramienta —que dio 0 % donde los datos reales daban 9 %— hasta que se le
corrigió la secuencia de operaciones.
