# PRED-005 — **Q2 REFUTADA en K=50.** La grilla de §2-ter no se puede correr completa

**Fecha:** 2026-08-08 · `BigTrap2.cs` v2.4 (`9b63959a62f08860…`)
**Preregistro:** `docs/predictions/PRED-005_atribucion_grilla_completa.json`,
commiteado **antes** de capturar.

---

## 1. Resultado

| K | barras procesadas | `FOOTPRINT_MISMATCH` | **tasa** | anclaje OK | ambiguo | resincro | zonas | veredicto |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | 30.992 | 0 | **0 %** | 4 | 0 | 0 | 102 | PASS *(PRED-004)* |
| 15 | 20.661 | 0 | **0 %** | 4 | 0 | 0 | 228 | **Q1 PASS** |
| 25 | 12.397 | 0 | **0 %** | 4 | 0 | 0 | 413 | PASS *(PRED-004)* |
| **50** | 6.198 | **790** | **12,75 %** | 4 | **0** | **2** | 229 | **Q2 REFUTADA** |
| 100 | 3.098 | 0 | **0 %** | 4 | 0 | 0 | 297 | **Q3 PASS** |

- **Q4 (P3, OHLCV 100 %)**: PASS en 15 y 100; **FAIL en 50** — 790 pares
  procesados sin igualdad.
- **Q5 (P4, ambigüedad)**: **PASS en las tres.** Cero violaciones.
- **Q6 (`BARRA_PROCESADA` presente)**: PASS en las tres. Denominadores reales.

> **Corrección de lectura, registrada.** `tasa_mismatch_total` es una
> **fracción**, no un porcentaje: `0.12746` = **12,75 %**. En la primera lectura
> se interpretó como 0,127 % y eso invertía la conclusión. El propio analizador
> lo dice sin ambigüedad: *«mismatch interior 12.7460% > umbral 1.00%»*.

## 2. El patrón no es monótono, y eso es lo raro

**Sólo K=50 falla.** Sus vecinos inmediatos —25 y 100— dan cero, igual que 10 y
15. No es una degradación por escala: si lo fuera, el error crecería o
decrecería con K.

## 3. Firma del defecto: jitter de frontera, no desalineación de bloque

De los 790 mismatches:

| | |
|---|---|
| **OHLC idéntico, sólo difiere el volumen** | **557 (70,5 %)** |
| algún componente OHLC distinto | 233 (29,5 %) |
| campo que difiere | `vol` 673 · `open` 135 · `close` 113 · `high` 43 · `low` 27 |
| delta de volumen (`blk − bar`) | −1: 156 · +1: 132 · +2: 91 · −2: 70 · −3: 37 · +3: 28 |

Todos declaran `n_eventos=50; k=50`: **el conteo es correcto**. Los deltas de
volumen son chicos y **simétricos alrededor de cero**, y en 7 de cada 10 casos
el OHLC coincide entero.

Eso es la firma de un **corrimiento de uno o dos eventos en el borde del
bloque**: se intercambian trades de la frontera, el volumen se mueve poco, y sólo
a veces cambia el `open` o el `close` —los precios de los extremos—. No es el
defecto de v2.2, donde el conteo mismo estaba mal.

## 4. Está confinado al arranque

Los 790 mismatches caen en las barras **2 a 1285** de 6.198. Distribución por
sextos del chart: `[619, 171, 0, 0, 0, 0]`.

**Después de la resincronización, K=50 corre limpio 4.900 barras seguidas.** Es
el mismo perfil que tenía K=25 con v2.2: falla en la primera sesión, se recupera
en la frontera.

## 4-bis. Reproducido byte por byte — no fue la captura

Nico recapturó K=50 con todo idéntico, 50 minutos después. v2.4 rotó a
`..._v24__Tick50_2.csv` sin pisar la primera.

```
BigTrap2_tick50_6E_0926_v24__Tick50.csv     sha256 481251ea6c1d2862...  1.035.358 B
BigTrap2_tick50_6E_0926_v24__Tick50_2.csv   sha256 481251ea6c1d2862...  1.035.358 B
```

**Los dos archivos son idénticos byte por byte.** El analizador sobre la
recaptura devuelve lo mismo: 790 mismatches, 6.198 barras, 12,75 %, `p3` FAIL,
`p4` PASS.

Descarta tres explicaciones alternativas de una sola vez:

- **no es aleatoriedad de captura** — sería imposible reproducir el sha256;
- **no es que NT8 haya bajado datos distintos** — un tick de más o de menos
  cambiaría el archivo;
- **no es contaminación ni append** — la rotación creó el `_2` limpio, con su
  propio `# meta` y su `seq` desde cero.

El defecto es **determinista**. Lo que queda por clasificar es la causa, no si
existe.

## 5. Lo que NO falló, y conviene no perderlo de vista

**`ANCLAJE_AMBIGUO` = 0.** El ancla nunca se abstuvo: encontró candidato único en
las cuatro fronteras. El defecto **no está en anclar, está en mantener** la
alineación dentro de la sesión.

**El fail-closed funcionó.** Detectó, marcó la sesión no confiable, suprimió
zonas y resincronizó (2 `SESION_RESINCRONIZADA`). Las 229 zonas de K=50 salieron
de tramos verificados. **No hay contaminación silenciosa** — que es exactamente
lo que el verificador existe para impedir.

## 6. Consecuencia, según lo que el preregistro ya declaraba

> *«si alguna resolución supera 1 %, la grilla de §2-ter NO puede correrse
> completa con este `.cs`. Habría que recortarla ANTES de medir economía y
> declararlo, nunca después de ver resultados.»*

Se cumple el antecedente. **La grilla queda `10, 15, 25, 100`** — cuatro
resoluciones, no cinco. `50` sale hasta que se clasifique y repare la causa.

Impacto en §2-ter, que hay que evaluar **antes** de correr nada económico:

- La regla de muerte de H1 exige **banda contigua de ≥3 resoluciones
  adyacentes**. Con `50` fuera, la grilla queda `10, 15, 25` contigua y `100`
  aislada. **`100` ya no tiene vecino inferior**, así que no puede evaluarse
  bajo la regla de banda.
- El costo de multiplicidad se declaró para 5 resoluciones + control. Correr 4
  no lo aumenta —es conservador— pero conviene declararlo.

**Ninguna de esas decisiones se toma acá.** Son de Nico y del auditor.

## 7. Qué sigue, en orden

1. **Clasificar la causa** del jitter en K=50 antes de tocar código. Es la misma
   disciplina de TICKBAR-001 §6 que evitó tres parches equivocados: primero por
   qué sólo 50, después el fix con predicción falsable.
   Pregunta abierta concreta: por qué 25 y 100 sobreviven y 50 no.
2. **Decidir §2-ter** con la grilla recortada, o esperar la reparación.
3. Lo demás sigue igual: **D3**, el censo de primeros toques y el pin de
   `sha256` del `.cs`.

## 8. Procedencia

`oracles/*.csv` gitignoreado; identidad en `docs/oraculos_manifiesto.json`
(**11 archivos**, «todo coincide»). Ventana pre-holdout `2026-06-14`→`06-18`,
`6E 09-26`, defaults, `Maximum bars look back` 256 — idénticos a PRED-004.
**Holdout no tocado.**

| corrida | `resultado_sha256` |
|---|---|
| K=15 | `96857d73fbacf51ec59a0a83cf56d2a39b7e87e112d838aad8cee159d51ca65c` |
| K=50 | `27bc4d741444157bd891c09031cdb308aaf4e725e229059351b280609863dbe1` |
| K=100 | `21ef6deb6875832eaad834ecc94721a2fde9e554124d4f028f8fae8088aa6b7c` |
