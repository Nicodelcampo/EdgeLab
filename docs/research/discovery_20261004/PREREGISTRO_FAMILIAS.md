# Barrido de familias (GC, ZB, FX = 6E + 6J) — pre-registro (2026-10-04)

Estado: escrito ANTES de barrer. Exploratorio. Solo datos **previos al holdout** (corte estricto `< 2026-06-30T22:00Z`, agosto de 2025 a junio de 2026); no se lee nada de julio en adelante (los tramos posteriores quedan para confirmación). Los datasets de GC, ZB, 6E y 6J son «partial contract-month slices»: EF0 los marca no elegibles, así que ningún resultado de este barrido es confirmatorio.

## Qué se decide y por qué así (decisiones de diseño, compute frente a aporte)
- **Cinco familias** con una historia económica cada una, cada una con su propia rejilla y su propio nulo de máximo (evita el producto cartesiano): momentum, VWAP, flujo y absorción, régimen (rango y spread como filtro) y medias (EMA como filtro de régimen).
- **Las 96 franjas de 15 minutos del día completo** y holdings de 15, 30, 60 y 120 minutos. No se acota el día: el cómputo no limita (unos segundos por activo y familia) y acotarlo bajaría el umbral de evidencia de ≈ 4,1 a ≈ 4,0 a cambio de una decisión tomada mirando datos. Las franjas sin mercado quedan inválidas solas.
- **Pares acotados dentro de cada familia** (no todos contra todos): suben el umbral de evidencia de ≈ 4,1 a ≈ 4,4 y aportan lo pedido sobre absorción y flujo.
- **Grupos de activos fijados de antemano:** GC solo, ZB solo y **FX = 6E + 6J** (mismo mercado de divisas; se suman por sesión; 1 tick = USD 6,25 en ambos). No se agrupan oro, bonos ni divisas entre sí.
- **CPU como referencia** (≈ 70.000 celdas por activo en total). La GPU está verificada (paridad PASS en una T4) pero no hace falta a esta escala.

## Familias (historia económica, parámetros libres, ablaciones)
Cada propuesta tiene ≤ 3 parámetros libres: **franja**, **holding** y **condición**. Variables causales con ventana W en minutos (15, 30, 60): `mom` (cierre − cierre de hace W), `vwapdev` (cierre − VWAP de la ventana), `imb` (desequilibrio comprador/vendedor por agresor), `absorb` (volumen / recorrido), `effort` (volumen / |movimiento neto|), `rng` (máximo − mínimo), `spread`, `emadev` (cierre − EMA de W barras, W = 20, 50, 200). Los z-scores son causales (60 sesiones previas de la misma franja, mínimo 20).

| Familia | Historia económica | Ablación pre-registrada |
|---|---|---|
| f1_momentum | tras un movimiento reciente el precio continúa o revierte según la franja | celda sin condición en la misma franja y holding |
| f2_vwap | el precio tiende a volver hacia (o alejarse de) el valor intradía | celda sin condición y con `mom` en lugar de VWAP |
| f3_flujo_absorcion | un volumen grande con poco recorrido o un desequilibrio contra el precio anticipa giro o continuación | misma celda con solo `imb` o solo `mom` |
| f4_regimen | el efecto de momentum y VWAP depende de si el rango o el spread están altos o bajos | celda base sin filtro de régimen |
| f5_medias | la posición frente a una EMA lenta modula el momentum | celda base sin EMA |

## Rejillas (hash = SHA-256 del JSON de la especificación; archivos en `config/discovery/families/`)
| Familia | Condiciones simples | Pares | Celdas por activo | Hash |
|---|---:|---:|---:|---|
| f1_momentum | 12 | 0 | 4.992 | `45ba0dd55b0191d80bd1bfce14b10b863e86a12fe58b48cad86a4f0119ef8fcc` |
| f2_vwap | 12 | 0 | 4.992 | `ddaaefbb59b52518fd324a7aee77e3266ae8eb9e077302a62d774f51800f147c` |
| f3_flujo_absorcion | 30 | 30 | 23.424 | `63134cbf49887a09db8e3593a476b349ec4f15c4cf4f7e22a10771716e4b35da` |
| f4_regimen | 21 | 30 | 19.968 | `e13dd2d2ca3e85f4312331eb9b089fa725165678080716273757229a5ee9cc59` |
| f5_medias | 18 | 24 | 16.512 | `6d82ec1435d2b883211bba52557442fefa5498c5090ea7061366c858d61028d9` |

Total: **69,888 celdas por activo**. Tres grupos (GC, ZB, FX): **209,664 pruebas** a registrar en el contador (`trial_registry.jsonl` de esta carpeta), una campaña por familia y grupo.

## Protocolo estadístico (fijado)
- **Partición del embudo:** `make_splits` cronológica 50 / 25 / 25 sobre las fechas de trading (en FX, la unión de las fechas de 6E y 6J). **El barrido (nulo de máximo) corre solo en D0, la réplica en D1 y D2 permanece sellado** (no se abre aquí).
- **Estadístico y nulo:** retorno del tramo (medio-precio) menos la media de la sesión para ese holding; `z = Σ r~ / √V`, dos colas; nulo con el signo de cada sesión sorteado ±1, 20.000 sorteos, semillas `20261012` (f1), `20261013` (f2), `20261014` (f3), `20261015` (f4), `20261016` (f5); `p_max` = probabilidad de que el máximo del nulo iguale o supere el real. Celdas con ≥ 40 operaciones (escaladas por la fracción de sesiones de D0).
- **Réplica:** las 5 mejores celdas de D0 por |z|, con signo fijo, probadas en D1 (unilateral, 20.000 sorteos, semilla = semilla de la familia + 1), con Holm sobre las 5.
- **Titular por familia y meseta:** una celda por familia (la de mayor |z| de D0) con la fracción de celdas vecinas (franja ± 1, holding ± 1, misma condición) del mismo signo; meseta si ≥ 75 % de al menos 3 vecinas.
- **Costos:** ejecución de libro (largo al ask, corto al bid), comisión de ida y vuelta de USD 4,50 por contrato completo (GC 0,45 ticks; ZB 0,144; 6E y 6J 0,72), guarda de retraso de 120 s, elegibilidad por volumen ≥ 50 % de la mediana del contrato como líder.
- **Multiplicidad entre familias y grupos:** los 15 `p_max` (5 familias × 3 grupos) se corrigen con **Holm al 5 %**. BH sobre los p normales de las celdas se reporta solo como exploración.

## Regla de decisión (fijada antes)
Una (familia, grupo) **«pasa a confirmación»** solo si se cumplen **todas**: (i) `p_max` ajustado por Holm sobre los 15 contrastes ≤ 0,05; (ii) al menos una de las 5 celdas replicadas en D1 tiene p de Holm ≤ 0,05; (iii) el titular tiene media neta real > 0 tras costos en todas las sesiones; (iv) el titular tiene meseta. En cualquier otro caso: **sin estructura distinguible del azar** con estos datos. Pasar a confirmación solo habilita escribir un pre-registro de confirmación con datos posteriores; **ningún resultado de este barrido es un edge**.

## Expectativa registrada (antes de barrer)
Con ≈ 112 sesiones en D0, una rejilla de 5.000 a 23.000 celdas y un nulo de máximo, solo se detectan de forma fiable efectos de ≈ 0,5 desvíos por operación o más (ver calibración). Espero que **la mayoría de las 15 combinaciones salga sin nada** y que, si alguna pasa el punto (i), no replique en D1. La celda de GC de la etapa anterior (≈ 0,31 desvíos) probablemente quede por debajo de la potencia de esta rejilla en D0.

## Contador y custodia
- Cada (familia, grupo) suma su número de celdas al contador de pruebas encadenado; cada barrido se anota en el libro encadenado.
- No se lee el holdout formal (desde 2026-10-01), ni julio a septiembre de 2026 en estos activos, ni D2.
- Cualquier cambio de especificación después de ver resultados crea una especificación nueva con su propio hash y su propio pre-registro; no se reutiliza este.

## Calibración de las 5 familias sobre GC (antes del barrido real)
Método: tasa de falsos positivos con signos por sesión sorteados (40 repeticiones, nulo de 500 sorteos); potencia plantando un efecto en una celda al azar sobre una **base neutralizada** (cada repetición sortea un signo ±1 por sesión antes de plantar, para que la estructura real no contamine la curva). Archivos: `calibration_GC_<familia>_<hash10>.json` en esta carpeta.

| Familia | Celdas | Falsos positivos (de 40) | Detección a 0,1 / 0,2 / 0,3 / 0,5 desvíos por operación |
|---|---:|---:|---|
| f1_momentum | 4.992 | 0 | 0,00 / 0,10 / 0,15 / 0,85 |
| f2_vwap | 4.992 | 2 | 0,00 / 0,05 / 0,45 / 0,90 |
| f3_flujo_absorcion | 23.424 | 3 | 0,00 / 0,05 / 0,05 / 0,70 |
| f4_regimen | 19.968 | 3 | 0,10 / 0,00 / 0,30 / 0,80 |
| f5_medias | 16.512 | 1 | 0,00 / 0,00 / 0,15 / 0,90 |

Lectura: con 40 repeticiones la tasa de falsos positivos es compatible con el 5 % nominal (0 a 7,5 %; la repetición anterior con 300 repeticiones dio 5,0 % a 5,3 %). La potencia es baja por debajo de 0,3 desvíos y razonable recién en 0,5. Es la misma conclusión que ya figuraba en la expectativa.

## Declaración de una filtración parcial (se escribe antes de barrer)
La **primera pasada de calibración** de f1_momentum sobre GC usó la matriz real como base de la curva de potencia y detectó «efectos» plantados del 95 % ya desde 0,1 a 0,3 desvíos. Eso no podía ser potencia: indicaba estructura real en la base. En consecuencia, **ya sé, antes de barrer, que f1_momentum sobre GC (las 225 sesiones juntas) probablemente tiene un `p_max` cercano o inferior a 0,05**. Corregí el método (base neutralizada, con una prueba nueva) y repetí las cinco calibraciones; las tablas de arriba son las de la versión corregida.

Consecuencias fijadas:
1. El resultado de f1_momentum/GC **no es ciego**. Se corre igual y se reporta, pero su único valor probatorio es la réplica en D1 (datos que el barrido en D0 no usa) y la regla (i)–(iv).
2. No se modifica ninguna especificación ni el protocolo por esa información.
3. El resto de las 14 combinaciones no tuvo ninguna lectura previa.
