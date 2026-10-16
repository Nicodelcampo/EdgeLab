# Censo sin retornos: impulsos del corredor × zonas HFT (ES, 100T) — resultados

Estado: MEDIDO (censo; sin desenlaces ni retornos)
Fecha: 2026-10-16
Familia / módulo: EXP-CORREDOR-HFT (confluencia; a registrar antes de medir desenlaces)
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)
Procedencia: kernel Kaggle `nicolasbuttaro/edgelab-corredor-hft-census-v1` (id 139053926; ~6 min, CPU); código `tools/corridor_hft_census/` (Pasada 2 sha256 `10e8fa9f…` + `DET_NT8` + port Python de `HFTZonesESPureV2Flat`, parámetros por defecto, sin absorb). Salidas: `docs/research/corredor_hft_census_20261016/`. Definición: `DEFINICION_INICIAL_CORREDOR_X_HFT_20261016.md`.

## Alcance
ES, descubrimiento HOLDOUT-A3 (2025-07-18 a 2026-03-31): **178 sesiones**. Impulsos = zonas del corredor `DET_NT8` en barras 100T estrictas por sesión. Ventana W = primera mitad de la longitud conocida al confirmar (`origin_bar … origin_bar + floor((conf_bar − origin_bar)/2)`; decisión en `conf_bar`). **Tocada** = el rango de alguna barra de W intersecta un rectángulo HFT activo (creado después de su `end_ts` y antes de W, dentro de su extensión). Barras donde la zona se crea no cuentan. Sin desenlaces posteriores a `conf_bar`.

## Resultados
Zonas HFT (sin absorb): **7.841** en 178 sesiones (**44,1 por sesión**).

**Preset 1 (5.312 impulsos, 30 por sesión, 177 sesiones con impulsos)**
| extensión | activa | **tocada** | n tocada | control sin toque | activa sin toque | W termina dentro |
|---|---|---|---|---|---|---|
| fija 300 | 56,4 % | 45,6 % | 2.422 | 2.890 | 573 | 455 |
| **fija 600** | 72,8 % | **54,5 %** | **2.897** | **2.415** | 970 | 675 |
| fija 1200 | 86,1 % | 63,6 % | 3.377 | 1.935 | 1.195 | 939 |
| dinámica (hasta mitigar) | 94,9 % | 74,0 % | 3.932 | 1.380 | 1.110 | 1.615 |
| dinámica (hasta 1.er toque) | 96,2 % | 79,8 % | 4.241 | 1.071 | 868 | 1.891 |

**Preset 2 (7.360 impulsos, 41,6 por sesión):** mismo patrón; fija 600: tocada 52,7 % (3.881 vs control 3.479).

**Potencia aproximada** (diferencia de proporciones, 80 %, α = 5 %, efecto de diseño 2 por clustering **supuesto**, no medido): MDE ≈ **4,4–5,3 pp** (preset 1, fija 600) y 3,7–4,5 pp (preset 2); crece a 5–6,6 pp con las dinámicas (control chico).

## Lectura
1. **La definición discrimina:** con 600 barras fijas, ~55 % de los impulsos tienen una zona HFT tocada en su primera mitad y ~45 % no; el control es de buen tamaño (≈ 2.400). Con las extensiones dinámicas el control cae a 1.100–1.400 y la presencia casi no separa, como se anticipó.
2. **Sólo coexistir no es tocar:** 970 impulsos (18 %) tienen una zona activa sin toque con fija 600; es un estrato aparte útil.
3. **Variante primaria sugerida:** preset 1, fija 600, "tocada en W"; sensibilidades: 300 y 1200 fijas, preset 2.
4. **Potencia:** una diferencia de ~4–5 pp en P(llegar)/P(atravesar) es detectable en la comparación global; las superficies condicionadas (edad, volumen, virginidad, distancia) tendrán MDE mayor y requerirán rejilla chica.

## Reservas (verificar antes del manifiesto)
- **Densidad de zonas HFT — RESUELTA (2026-10-16):** el oráculo de NT8 de ES 03-26 (`runs/oraculo_espurev2flat_ES_snapshot.sqlite`, 9.486 zonas, 62 sesiones) se compone de **6.685 `Absorb` (70 %)**, **2.800 `Predator`** y **1 `Ultra`**. Sin absorb quedan **2.801 zonas ≈ 45,2 por sesión**, que coincide con las **44,1 por sesión** del censo (7.841 en 178 sesiones). La "mediana de 158 por sesión" incluía las zonas absorb. Queda por repetir, si se quiere, la comparación sesión por sesión sólo de las zonas no absorb.
- El efecto de diseño 2 del MDE es un supuesto; hay que medir el clustering por sesión.
- La extensión se midió en barras de 100T de la serie de este censo; el gráfico debe usar la misma serie.
- Impulsos con origen reubicado y confirmación tardía: W usa sólo lo conocido en `conf_bar` (causal); la versión retrospectiva (50 % de la extensión final) no se midió.
- Preset 1 y 2 se solapan (mismas zonas con distintos criterios): no son réplicas independientes.
- No se midieron desenlaces (llegar/atravesar) ni retornos; el holdout (≥ 2026-10-01) no se abrió.

## Siguiente paso propuesto
(1) (hecho: densidad verificada contra la composición del oráculo.) (2) Registrar la familia, congelar W, presencia (tocada), extensión primaria y la rejilla chica de variables, con número efectivo de hipótesis y MDE. (3) Con OK de Nico (STOP), medir los desenlaces en descubrimiento.

*Aporte al referente:* muestra que la definición de "zona HFT tocada en el 50 % inicial" separa los impulsos en dos grupos de tamaño suficiente (≈ 2.900 vs 2.400) con MDE ≈ 4–5 pp, antes de gastar presupuesto de hipótesis, y señala la discrepancia de densidad de zonas que hay que cerrar primero.

## Variante pedida por Nico: al menos 2 zonas HFT distintas tocadas en W
Se deriva del mismo censo (columna `*_n_touch` = zonas HFT distintas tocadas por el precio en W); no requirió volver a correr Kaggle. Tabla completa (k = 1, 2, 3) en `corredor_hft_census_20261016/CENSO_VARIANTE_K_ZONAS_TOCADAS.csv`.

| preset | extensión | n con ≥ 2 | n con < 2 (control amplio) | prevalencia | sesiones con ≥ 1 | MDE80 aprox. (p0 0,2 / 0,4) |
|---|---|---|---|---|---|---|
| 1 | fija 300 | 1.180 | 4.132 | 22,2 % | 159 | 5,2 / 6,4 pp |
| **1** | **fija 600** | **1.670** | **3.642** | **31,4 %** | **166** | **4,7 / 5,7 pp** |
| 1 | fija 1200 | 2.157 | 3.155 | 40,6 % | 170 | 4,4 / 5,4 pp |
| 1 | dinámica (hasta mitigar) | 2.781 | 2.531 | 52,4 % | 170 | 4,4 / 5,3 pp |
| 2 | fija 600 | 2.184 | 5.176 | 29,7 % | 169 | 4,0 / 4,9 pp |
Distribución de zonas tocadas (preset 1, fija 600): 0 zonas = 2.415; 1 zona = 1.227; 2 = 733; 3 = 354; 4 = 257; 5 = 116; ≥ 6 = 210. Entre los 1.670 con ≥ 2, 501 terminan W dentro de alguna zona (mediana de 3 zonas tocadas). Con ≥ 3: 937 impulsos (17,6 %), MDE 5,7–7,0 pp.

**Lectura:** el requisito de ≥ 2 zonas deja **1.670 impulsos (31 % del total)** en 166 sesiones con fija 600: tamaño suficiente (MDE ≈ 4,7–5,7 pp). Para contrastarlo hay tres controles posibles, a elegir antes de medir: (a) todos los de < 2 (3.642, mezcla ninguno + uno), (b) sólo los de **0 zonas** (2.415, contraste más limpio), (c) sólo los de **exactamente 1** (1.227, aísla el efecto de la segunda zona). Recomiendo declarar (b) como primario y (c) como secundario, y reportar la relación dosis-respuesta (0, 1, 2, ≥ 3 zonas).

