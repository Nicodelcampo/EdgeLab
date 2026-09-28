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
| 6 | **Ciclo de vida** (escalón 2, riesgos competitivos) | **OBSOLETO desde 2026-09-08.** Midió 99,4 % `INVALIDATED` sobre 18.851 clusters del log real — pero el `.cs` v2.0.0 **eliminó esa transición**, así que la distribución de riesgos competitivos del motor actual **no está medida** | `docs/research/MOTOR_CLUSTERS_V2_DIVERGENCIA_2026-09-08.md` |
| 7 | **Decaimiento por consumo** (canal no direccional) | **SIN EFECTO DETECTADO, con cota.** 40 sesiones, 6.468 muestras, **MDE 0,067**. Ningún contraste lo supera; si hay efecto es < 7 pp y no es monótono | `docs/research/DECAIMIENTO_CLUSTERS_NQ_2026-09-07.md` |
| 8 | **H2 — rechazo en bordes** (canal direccional) | **ANULADO POR ESCALA (2026-09-08).** Corrió sobre **50** sesiones (no 65: el parquet de `NQ 06-26` termina el 18-jun), 1.026.840 contactos, 71.641 en borde. El umbral de desenlace (4 ticks) es un tercio del rango mediano de barra (12); el 25 % de los desenlaces los decide un desempate fijo hacia `cruza`; el «borde» de ±1 tick es una astilla de un objeto de 60 ticks. **Ni el +0,035 ni el −0,011 son evidencia** | `docs/research/H2_VOID_POR_ESCALA_2026-09-08.md` |
| 10 | **Escalón 5 (intensidad + hold-out)** | **ANULADO junto con H2** — corre sobre el mismo desenlace. Además su −0,011 **no supera su propio MDE** (0,0296) y se publicó sin estratificar, que es lo único que el propio estimador prohíbe. La descomposición correcta (fresco vs rancio) existe ahora en `cr.contraste_lag` | `docs/research/H2_VOID_POR_ESCALA_2026-09-08.md` |
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
| **`desenlace` desempata siempre hacia `cruza`** cuando la barra abarca los dos umbrales — 25 % de los casos. Si se resolvieran al revés la tasa de rechazo pasa de 0,323 a 0,573 | medido 2026-09-08, **sin corregir** |
| **`agregado` llama «sin borde» a libre + interior**: su control está contaminado y su contraste no es comparable con el de `tabla`. Se agregó `agregado_limpio` aparte | corregido por adición |
| **`HFTClusterZonesNQ.cs` no dibujaba nada**: `DibujarZonasIndividuales=false`, `RenderZonasDx` recorría sólo las últimas ~120 zonas con culling roto, y había carrera entre el hilo de datos y el de render | corregido por Antigravity 2026-09-08 (`syncLock` + culling + flag). Mi diagnóstico previo —`OcultarInvalidados`— valía para el motor viejo y es irrelevante para el actual |
| **`InvalidationTicks` es un parámetro muerto en v2.0.0**: se declara, se documenta y se escribe en el `# params` del CSV, y ninguna línea lo lee | verificado en fuente 2026-09-08 |
| **Los runners entregan la zona al motor de clusters en la barra de INICIO, y el `.cs` lo hace en la de FINAL.** Medido sobre 836 zonas: **el 98,2 % se adelanta**, mediana 2 barras, cola hasta 9. Como los datos de la zona (volumen, CVD, bordes) recién están completos al final del streak, el cluster de la barra `i` usa información de ticks posteriores a `i`: es **look-ahead**, chico pero real | medido 2026-09-08, **sin corregir en los runners**; el arnés de paridad ya usa el orden correcto |
| **Ningún runner filtra sesiones por liquidez**: 3 de las 50 sesiones de H2 tenían 14-27 % del volumen mediano (un feriado y dos post-roll del `06-26`, que vence el 19-jun) | medido 2026-09-08, **sin corregir** — hace falta una compuerta de sesión reutilizable |
| **El objeto histórico y el objeto en vivo no son el mismo objeto**: el camino de consumo por barra se saltea en `Realtime` pero no en histórico, donde la sub-serie de ticks también corre. En histórico el volumen se cuenta **dos veces** | verificado en fuente 2026-09-08, **sin corregir — decisión de Nico** |

---

## NO MEDIDO

| # | Qué falta | Por qué importa | Bloqueo |
| :-- | :-- | :-- | :-- |
| 1 | **H1 completa**: probabilidad de tocar contra el nulo browniano `2(1−Φ(d/(σ√h)))` condicional a σ local | Es el escalón 1 y el que replicó la muerte del 6E. El módulo de decaimiento cubre el contraste contra placebo, **no** contra el nulo analítico | ninguno, falta implementarlo |
| 2 | **H2 a la escala del objeto** | El estimador midió a 4 ticks un objeto de 60 y una barra de 12. Hace falta re-pre-registrar la escala con justificación target-free y barrerla publicando el landscape completo | resolver el desenlace sobre ticks primero |
| 3 | **Escalón 3**: sensibilidad a la vigencia | Todas las mediciones fijaron `max_age_bars=500` sin barrerlo. Herramienta escrita (`tools/vigencia_clusters_nq.py`), no corrida hasta el final | ninguno |
| 4 | **CIF Fine-Gray** del ciclo de vida | El 99,4 % de invalidación se midió por conteo, no con incidencia acumulada ni riesgos competitivos formales | ninguno |
| 5 | **Escalón 5**: condicionamiento por intensidad y hold-out | Implementado y corrido, pero sobre el desenlace anulado. Se rehace con el estimador nuevo | H2 re-escalada |
| 6 | **Escalón 6**: Ripley 1-D sobre POCs | Diagnóstico transversal | ninguno |
| 7 | Paridad de la **capa de clusters** | Sólo la capa de zonas está certificada. `hft_clusters` tiene 47.875 filas y **todas caen fuera de los ticks disponibles** (oráculo 28-ago→8-sep; parquet de NQ hasta 28-jul). No hay ni una fila de ES | **Nico exporta el oráculo**: `NQ 06-26`, 3→11 jun, `SoloLogEnVivo=false`. Cierra también el item 8. Espejo ya en v2.0 |
| 8 | Paridad sobre **NQ** | El certificado es sobre ES 09-26. El oráculo viejo de NQ era de ago-sep y el parquet llega al 28-jul | **resuelto por la misma corrida del item 7**: NT8 tiene ticks de `NQ 06-26` del 31-mar al 18-jun, pre-holdout |
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
