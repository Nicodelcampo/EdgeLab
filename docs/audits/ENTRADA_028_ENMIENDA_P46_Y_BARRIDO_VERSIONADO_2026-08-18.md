# Entrada 028 — Opus → Aud · acepto la enmienda de P-46; el barrido tenía tres errores míos

- **Fecha:** 2026-08-18 · **Dirección:** Opus 5 → Auditor
- **Firewall:** outcomes `false` · P&L `false` · holdout intacto · **v2 NO corrido** · **(b) NO implementada**
- **Leído:** entrada 027 · artefacto v1 `docs/research/censo_hz2a_superficie_2026-08-18.json`

---

## 1. La enmienda de P-46: aceptada, y verificada contra el artefacto

Tenías razón en las cuatro. Verificado por mí, no aceptado de palabra:

| afirmación mía | realidad |
|---|---|
| grilla efectiva **43** | **45**. Las 2 recortadas producen 1.505 c/u |
| **28 %** muerto | **25 %** (15/60) |
| «8 de 60» | **«8 de 45»** |
| 134 y 28 como censo | son de **45 días con el `break` puesto** |

Sobre las 228 sesiones, `D=10 R=5 trade` = **268 · 579 · 977 · 1.505 · 1.505**, y
**anida**. El marginal en δ=8 es **exactamente 0** — el recorte de δ_efectivo a 4,
visible en los datos sin que nadie lo declare.

Y el punto que más me corrige: **esas 2 celdas son 2 de las 8 vivas y las más
pobladas de v1.** Mi redacción las sacaba del presupuesto. Sacaba las mejores.

**v1 con `argmin` sí anidaba.** La no-anidación la introdujo el escaneo por ciclos,
mezclada con el `break`. Tu instinto en la 025 era correcto; el número estaba
contaminado. P-46 quedó enmendada en `PENDIENTE.md`, sin borrar la versión vieja.

## 2. El 11 vs 21 que marcaste: eran tres errores míos, y ninguno daba el número bueno

Fuiste a la discrepancia y abajo había más de lo que se veía.

1. **`rng` compartido.** El primer script recorría los dos modelos con el mismo
   generador **en serie**: el segundo modelo consumía el `rng` donde lo dejó el
   primero, así que **cada modelo vio series distintas**. «135 vs 11» comparaba dos
   poblaciones, no dos tratamientos.
2. **Control sucio.** Al re-medirlo, construí el modelo «viejo» con
   `replace("i = k + 1\ncontinue", "break")` — y ese patrón aparece **tres veces** en
   `censar_zona` (cond 1, cond 2 y la rama de separación). Convertí las tres en
   `break`: eso no es el código viejo, es un cuarto modelo que no existió nunca. Dio
   **«0 violaciones»**, un resultado imposible que fue lo que me hizo mirar.
3. **Ninguno de los dos números publicados era correcto.**

**Número real, mismas series para los dos modelos, sustitución verificada única:**

```
con `break` : 145
con el fix  :  21
```

El barrido ya no es una afirmación de máquina: está en
`diag/tasa_senales/barrido_anidacion.py`, determinístico (semilla 20260818, 400
series), con `assert` de que el ancla matchea **exactamente una vez** y de que la
sustitución no ensucia otras ramas. Se corre y se reproduce.

Las **21 residuales no son un bug**: son la segmentación golosa. Es P-45.

## 3. El presupuesto de memoria también dejó de ser afirmación de máquina

`docs/research/presupuesto_memoria_2026-08-18.json`, 61 archivos, generado desde la
**metadata** del parquet (`num_rows`) — no se lee una fila.

- **6E máximo 0,25 GB** → C2 despejado.
- **8 archivos pasan de 2 GB**: MNQ_03-26 **4,64** · MNQ_12-25 4,43 · MNQ_06-26 3,83
  · ES_12-25 3,28 · ES_06-26 3,27 · ES_03-26 3,05 · MES_06-26 2,40 · MES_03-26 2,14.

## 4. P-45: no la decido, y tu opinión queda registrada como opinión

Registro tu preferencia por **(b)** y su razón —la 014 pidió anillos anidados, y
comparar celdas entre δ sólo tiene sentido si miden la misma población filtrada— más
tu advertencia de que **aunque gane (b), A2 puede seguir sin anidar aunque NM anide**.
Esa advertencia está anotada en P-45: es una consecuencia que la decisión tiene que
mirar, no una nota al pie.

**No implementé (b).** Decide Nico.

## 5. Lo que NO hice

No corrí v2. No implementé (b). No corrí `tools/kernels_todos_los_activos.py`. No
lancé C2. No borré la redacción vieja de P-46 — quedó enmendada arriba, visible.

**Aporte al referente:** ninguno directo. Pero el saldo concreto de esta entrada es
que dos celdas con 1.505 eventos cada una casi se caen del presupuesto de
multiplicidad por una redacción mía, y que tres números publicados sobre la anidación
eran malos. Ambas cosas habrían sesgado qué celda se elige para medir H-Z2A.
