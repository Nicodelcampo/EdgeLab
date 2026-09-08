# Clusters HFT sobre NQ — registro vivo de qué está MEDIDO y qué NO

> Familia `H-CLUSTER-NQ`. Se actualiza **en el mismo commit** que cualquier resultado
> nuevo — no en un commit aparte, no "después".
> Pre-registro: `docs/research/PREREGISTRO_H-CLUSTER-NQ_2026-09-07.md`.
> Holdout 2026-07-01 → 2026-12-31: **intacto**. Las herramientas lo rechazan por
> construcción.

---

## MEDIDO

| # | Qué | Resultado | Dónde |
| :-- | :-- | :-- | :-- |
| 1 | **Paridad del motor de zonas** NT8 ↔ Python | **EXACT.** 7.494/7.494 zonas, 20 campos, 149.880 comparaciones, 0 diferencias | `docs/parity_coverage/HFTZonesNQ.md` |
| 2 | Censo de zonas y sensibilidad de umbrales | `min_total_volume` mueve la población **tres órdenes de magnitud** (0 → ~12.000 zonas; 50 → ~600; 200 → ~8). `min_sweep_ticks` de 1 a 16 la mueve en **3 zonas** | `docs/research/CENSO_ZONAS_NQ_2026-09-07.md` |
| 3 | Estabilidad del cluster (contrato del repo: ±1 de volumen en 2/3 de los ticks, turnover < 5 %) | **Zonas: 32–38 %, no pasan.** Clusters: 6 de 36 celdas pasan en las 3 sesiones, todas con umbral de zona 10 | `docs/research/estabilidad_clusters/` |
| 4 | Peso continuo vs conteo binario | `volume` ≤ `log_volume` ≤ `count` en fragilidad, en todas las celdas. Con umbral 25 y densidad 8: 53 % → 24 % | `docs/research/estabilidad_clusters/pesos_vs_count.json` |
| 5 | Degeneración del peso continuo | Real pero acotada: 8,7 % de clusters de una sola zona en modo `volume`, 0 % en `count`. **Con `min_contributing_zones=3` el turnover no cambia** (0,6 % → 0,6 %): la mejora no era degeneración | commit `c35362e` |
| 6 | **Ciclo de vida** (escalón 2, riesgos competitivos) | **99,4 % muere INVALIDATED.** 0,4 % agotado, 0,1 % expirado, 4,6 % llega a tocar su POC. 18.851 creados | log real `hft_cluster_events.csv` |
| 7 | **Decaimiento por consumo** (canal no direccional) | **SIN EFECTO DETECTADO, con cota.** 40 sesiones, 6.468 muestras, **MDE 0,067**. Ningún contraste lo supera; si hay efecto es < 7 pp y no es monótono | `docs/research/DECAIMIENTO_CLUSTERS_NQ_2026-09-07.md` |
| 8 | **H2 — rechazo en bordes** (canal direccional) | **SIN EFECTO DETECTADO, residuo positivo consistente.** 15 sesiones, 160.759 contactos, 11.318 en borde. Contraste **+0,024 / +0,032** en los dos estratos grandes, MDE 0,053 | `docs/research/RECHAZO_CLUSTERS_NQ_2026-09-07.md` |
| 9 | **Co-locación del cluster con el precio** | **74 %** de los contactos de nivel caen dentro de un cluster vivo, aunque los clusters cubren sólo 4–9 % del rango. Es la endogeneidad que hace obligatorio el escalón 5 | ídem |

### Defectos del instrumento, medidos

| Defecto | Estado |
| :-- | :-- |
| `FallosTolerados` es un parámetro muerto (`fails` se escribe y nunca se lee) | verificado en fuente |
| Con `tick_resolution=1`, `MaxRangoTickPorVela` y `FiltroDireccionEstricto` son inertes | verificado |
| La envolvente de 3σ recorta el kernel antes de su corte de 3,5σ | test |
| El POC es el centro geométrico, **no** el nivel de más volumen | test |
| La invalidación exige capacidad no agotada (<80 %), lo que sesga su incidencia hacia abajo | verificado |
| Con >300 clusters se descarta el más viejo **en silencio** | verificado |
| **Canibalización**: el filtro de fusión excluye `DEPLETED` e `INVALIDATED` y **no** `EXPIRED`, así que un cluster que no muere crece sin techo | corregido con `merge_excluye_expirados`, apagado por default |
| `hftzones2.py` **no** sirve como espejo: le falta la compuerta de retroceso y sus umbrales son calibrados | verificado |
| El oráculo SQLite pierde zonas que arrancan en el mismo milisegundo (`UNIQUE` + `INSERT OR IGNORE`) | verificado, 36 de 7.530 |

---

## NO MEDIDO

| # | Qué falta | Por qué importa | Bloqueo |
| :-- | :-- | :-- | :-- |
| 1 | **H1 completa**: probabilidad de tocar contra el nulo browniano `2(1−Φ(d/(σ√h)))` condicional a σ local | Es el escalón 1 y el que replicó la muerte del 6E. El módulo de decaimiento cubre el contraste contra placebo, **no** contra el nulo analítico | ninguno, falta implementarlo |
| 2 | **H2 con potencia suficiente** | El residuo es +0,03 y el MDE 0,053. Para decidirlo hacen falta ~65 sesiones | ninguno |
| 3 | **Escalón 3**: sensibilidad a la vigencia | Todas las mediciones fijaron `max_age_bars=500` sin barrerlo. Herramienta escrita (`tools/vigencia_clusters_nq.py`), no corrida hasta el final | ninguno |
| 4 | **CIF Fine-Gray** del ciclo de vida | El 99,4 % de invalidación se midió por conteo, no con incidencia acumulada ni riesgos competitivos formales | ninguno |
| 5 | **Escalón 5**: condicionamiento por intensidad (Hawkes) y objeto hold-out | Es el que decide si hay información condicional o co-locación endógena | ninguno |
| 6 | **Escalón 6**: Ripley 1-D sobre POCs | Diagnóstico transversal | ninguno |
| 7 | Paridad de la **capa de clusters** | Sólo la capa de zonas está certificada. El cluster no tiene oráculo comparado | falta correr NT8 sobre una ventana con ticks disponibles |
| 8 | Paridad sobre **NQ** | El certificado es sobre ES 09-26. Las zonas de NQ en el oráculo son de agosto-septiembre y el parquet llega al 28 de julio | correr el indicador sobre NQ antes del 1 de julio |
| 9 | Cualquier medición de **P&L** | Ni entradas, ni salidas, ni costos | STOP del proyecto: exige manifiesto y presupuesto de hipótesis |

---

## Configuración congelada (enmienda P-72 aprobada el 2026-09-07)

La banda de no-degeneración del pre-registro estaba mal calibrada —decía 15–60 % de
cobertura as-of y las 108 mediciones dieron máximo 9,6 %, con lo que ninguna
configuración pasaba— y **Nico aprobó la enmienda**: *existe el objeto (≥ 20 clusters
por sesión) y no lo cubre todo (< 60 %)*. Acta:
`docs/research/ENMIENDA_P72_2026-09-07.md`. El criterio de estabilidad no se tocó.

Con eso la configuración de campaña deja de ser provisional:

| parámetro | valor |
| :-- | :-- |
| `min_total_volume` | 10 |
| `weight_mode` | volume |
| `halo_sigma_ticks` | 3 |
| `min_density` | 3 |
| `min_contributing_zones` | 3 |
| `merge_excluye_expirados` | True |
| `max_age_bars` | 500 — **congelado por omisión, no por medición** |

**La reserva sigue en pie:** `max_age_bars` nunca se barrió. El escalón 3 existe
(`tools/vigencia_clusters_nq.py`) y no se corrió hasta el final; el deep research lo
marca como crítico.

---

**Aporte al referente:** mantiene explícita la frontera entre lo medido y lo supuesto en
la única familia viva, que es lo que impide que un resultado provisional se cite después
como establecido.
