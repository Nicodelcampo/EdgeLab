# Manifiesto — AREAS-EXP-1, corrida de descubrimiento con desenlaces (DESC)

Estado: VIGENTE — OK de Nico el 2026-10-22 («ya te doy el OK»). Réplica decidida antes de mirar el DESC (sección Réplica).

- **Spec:** `SPEC_AREAS_EXPANSION_V1.md` (v1.1). **Código:** commit `3b077192`. El kernel autocontenido lleva sus SHA embebidos.
- **Referente:** `docs/NORTH_STAR.md` (cuerpo `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`).
- **Etapa del embudo:** EF2 (tamiz) → E2 (sobrevivientes) → hasta 3 celdas por fuente a réplica pre-registrada (EF5).

## Qué se corre
Dos kernels de Kaggle, uno por fuente, en modo `DESC`:

| Fuente | Datos | Período |
|---|---|---|
| Futuro NQ | release `liquid_tick_v1`, ticks reales con volumen | 2025-08-05 → 2026-03-31 (descubrimiento HOLDOUT-A3) |
| Índice USATECH | Dukascopy, ticks; volumen cotizado | mismo período |

## Corrida descartada (v1.2) — NO SE MIRA
- El kernel `edgelab-areas-desc-usatech` (versión 1) se lanzó con el código v1.2.
- La revisión posterior encontró errores que afectan desenlaces: entrada a mercado sólo al cierre, v_rel faltante en el tercio «bajo» y condiciones del manifiesto sin aplicar.
- **Sus resultados no se descargan ni se miran.** Las pruebas siguen contadas (`areas_exp_1/desc_*`).
- Se relanza con v1.3.

## Número de pruebas (contador global, antes de correr)
- **v1.3: 995.328 celdas por fuente.** Se registran como `areas_exp_1_v13/desc_nq` y `areas_exp_1_v13/desc_usatech`, sumadas a las de v1.2. Contar de más es conservador.
- 746.496 celdas por fuente, **1.492.992 en total**.
- Las celdas están anidadas: los umbrales «≥» y «≤» comparten operaciones. El número efectivo se estima sobre las sobrevivientes, y el recorte de Harvey-Liu se cobra con ese N_eff.
- Se registran en `TRIAL_REGISTRY_GLOBAL.jsonl` como `areas_exp_1/desc_nq` y `areas_exp_1/desc_usatech`.

## Regla de decisión (fija)
- **Tamiz:** FDR BH-Storey a q = 0,10 sobre todas las celdas. Las que tienen menos de 30 operaciones cuentan con p = 1.
- **E2, por celda nominada** (hasta 1.000, por t), tienen que pasar las tres condiciones:
  - IC 90 % por sesiones con cota inferior > 0 neta de fricción canónica (1,545 pts por viaje);
  - meseta: ≥ 2/3 de los vecinos ±1 en x, A/H, comercio y stop positivos, con mediana ≥ 50 %;
  - económico: sin las 5 mejores, ningún mes > 80 %, sin colapso con +0,5 pts de costo.
- **A réplica:** hasta 3 celdas por fuente, por cota inferior del IC (no por P&L máximo).
- **Si no pasa ninguna:** se informa el MDE por zona de la grilla. La familia no se declara muerta si es un nulo sin potencia.

## Réplica (decidida antes de mirar el DESC)
- **(a) USATECH 2023-01 → 2025-07.** Nunca mirado y con mucha potencia. Sirve sólo para la fuente índice.
- **(b) NQ abr–sep 2026.** Es la única apertura de la familia. Esos meses ya se vieron en el visor para otras preguntas LUX-IMB, así que la réplica no es limpia para esta familia.
- **(c) ES u otro índice como réplica entre activos.**

**Decisión (2026-10-22, delegada por Nico: «decidilo vos»; tomada antes de ver ningún resultado del DESC v1.3).** Criterio: priorizar datos nunca mirados y no gastar aperturas únicas sin necesidad.
1. **Celdas de USATECH → (a) USATECH 2023-01 → 2025-07.** Nunca mirado; réplica limpia, informativa (CFD, no operable).
2. **Celdas de NQ → (b) NQ abr–sep 2026, una sola vez.** Se publica con la advertencia de exposición visual previa (otras preguntas LUX-IMB). Se suma un chequeo informativo de esas mismas celdas en USATECH 2023–2025; ese chequeo no confirma por sí solo.
3. **Holdout (desde 2026-10-01) al final**, sólo para lo que pase la réplica y con seguimiento secuencial (`edgelab/funnel/secuencial.py`).
Celdas, VR_CORTES y COM_CORTES se congelan desde el DESC; el nivel de cada réplica lo asigna LORD++ (`escalera_v1`). (c) queda para una familia futura.

## Resultado DESC v1.3 (2026-10-22) — decisión fija
| fuente | operaciones | ambiguas M1 resueltas con ticks | celdas | evaluables | nominadas | π0 |
|---|---:|---:|---:|---:|---:|---:|
| NQ 2025-08-05 → 2026-03-31 | 7.652.794 | 1.871.443 | 995.328 | 351.888 | **0** | 1,0 |
| USATECH 2025-08-05 → 2026-03-31 | 6.181.816 | 1.436.467 | 995.328 | 315.654 | **0** | 1,0 |

Ninguna celda pasa el tamiz en ninguna de las dos fuentes, así que no hay E2 ni réplica. **Falta el MDE por zona de la grilla** que este manifiesto exigía «si no pasa ninguna»: la condición estaba escrita y el código no la implementaba (el mismo error de la tabla de la guía). Sin MDE el nulo no distingue ausencia de efecto de falta de potencia, así que la familia queda `SIN EFECTO DETECTADO, POTENCIA PENDIENTE`, no muerta.
**Relanzamiento v1.3b, sólo para el MDE:** mismo código de decisión, mismos datos y cortes; agrega `nulo` (`grilla_masiva.resumen_nulo`). No es una prueba nueva (no hay selección nueva: las nominadas ya quedaron en 0) y no suma al contador. Si v1.3b no reproduce exactamente operaciones, evaluables y nominadas de v1.3, es un fallo de determinismo y se investiga antes de interpretar nada.

## v1.3b (MDE, 2026-10-22)
Determinista: reproduce v1.3 exacto en las dos fuentes. t máximo NQ 4,59 · USATECH 4,29 (umbral del tamiz 5,20); el máximo esperado
de 351.888 normales independientes es ≈ 4,55, o sea lo observado es lo que daría el azar. No es falta de potencia: 32.994 (NQ) y
25.173 (USATECH) celdas habrían detectado +1 fricción neta (1,545 pts/op) en el tamiz. MDE de confirmación mínimo 0,05 / 0,06 pts, mediano 3,5 / 3,6 pts.

## Enmienda v1.4 (2026-10-22, OK de Nico en el chat: «las dos») — registrada ANTES de correr
Motivo: Nico señala que matar el 100 % puede ser artefacto del filtro, y aclara el principio de régimen («queremos edges actuales,
aunque en el pasado no hayan funcionado»). Se revisó el filtro y se encontraron tres sesgos reales, en las dos direcciones:
1. **Demasiado estricto:** el tamiz BH trata como independientes celdas anidadas que comparten operaciones, y cuenta en m las 643.000
   celdas que no se pudieron probar. → se agrega **Romano-Wolf step-down** (`grilla_masiva.romano_wolf`, 200 remuestreos de
   sesiones enteras, α = 0,10 FWER, sólo celdas evaluables): el umbral de máximo t se MIDE con la correlación real.
2. **Demasiado permisivo:** la t por operación ignora la dependencia dentro de la sesión. → la t de Romano-Wolf es la del remuestreo por sesiones.
3. **Contra el régimen:** un único promedio de 8 meses diluye un edge reciente, y la regla dura «ningún período > 80 %» mataba lo
   concentrado al final. → canal **`reciente`** (últimos 3 meses calendario del período, declarado ahora) con su propio tamiz y
   Romano-Wolf; y `escalera.economia` ya no mata la concentración en los períodos más recientes (la marca `regimen_reciente`);
   concentración en un período viejo sigue matando.
- **Pistas:** las 20 mejores celdas distintas entre sí por canal (difieren en ≥ 2 perillas; ≥ 20 sesiones; objetivo ≥ 3× fricción),
  ordenadas por cota inferior del IC. **No son hallazgos:** van a réplica; lo que sea azar muere ahí.
- **Pruebas:** se registran 995.328 más por fuente y canal (`areas_exp_1_v14/total_*` y `/reciente_*`). Contar el procedimiento nuevo
  sobre las mismas celdas como pruebas nuevas es conservador.
- **Réplica (reemplaza la decisión anterior por el principio de régimen):** lo más reciente sin usar primero. Celdas de NQ y de USATECH
  → **2026-04-01 → 2026-09-30** en su fuente (advertencia: jul–sep ya se miró para otras preguntas LUX-IMB, no estas celdas). Después,
  **holdout forward** con seguimiento secuencial: es la única prueba limpia de «funciona ahora». USATECH 2023–2025 pasa a ser
  **informativo** («¿funcionaba antes?»): fallar ahí no mata una celda que funciona ahora. El nivel de cada réplica lo asigna LORD++.

## Resultado v1.4 (2026-10-22)
| fuente · canal | evaluables | FDR | umbral RW (90 %) | t máx | p RW del máximo | rechazadas RW |
|---|---:|---:|---:|---:|---:|---:|
| NQ · total (2025-08 → 2026-03) | 351.888 | 0 | 5,46 | 4,65 | 0,44 | 0 |
| NQ · reciente (2026-01 → 03) | 244.254 | 0 | 5,43 | 4,44 | 0,50 | 0 |
| USATECH · total | 315.654 | 0 | 5,48 | 4,05 | 0,89 | 0 |
| USATECH · reciente | 182.118 | **4** | 5,60 | **5,45** | **0,12** | 0 |

- El umbral medido con la correlación real (5,4–5,6) es **más alto** que el teórico (5,2), no más bajo: las celdas chicas (30–50 operaciones) dan t con colas gruesas al agrupar por sesión. El filtro no era demasiado estricto por la correlación.
- Lo más cerca de pasar es el canal reciente de USATECH (FDR nomina 4; RW p = 0,12).
- Las pistas tienen medias de +15 a +55 pts/op con 30–100 operaciones: es la forma típica de la maldición del ganador (lo mejor de cientos de miles de celdas chicas). Se concentran en pocas regiones (NQ: N ≥ 8, W = 40, HACIA T3, E1C/E1A, S2): son pocas ideas, no 40.
- **Réplica congelada** (`v14/REP_CONGELADO_v14.json`, antes de correr): 40 celdas por fuente (pistas de los dos canales, sin repetir), cortes v_rel y comercio del DESC, período **2026-04-01 → 2026-09-30** en la misma fuente. Confirma una celda: p por sesiones bajo su nivel LORD++ (orden: el del archivo), media neta > 0 y económico. Registro: `areas_exp_1_v14/rep_nq` y `/rep_usatech`, 40 cada uno.

## Riesgos y datos faltantes
- **USATECH es un CFD:** no tiene costo canónico (se usa el de NQ como referencia) y su volumen es cotizado, no negociado. **Nada de USATECH es operable tal cual.**
- **Huecos de NQ:** ES y NQ terminan el 25-sep. Afecta sólo a la réplica (b).
- **La definición de área es una elección:** W, G y los ciclos están congelados en v1.1.
- **Ejecución:** la ambigüedad de M1 se resuelve con ticks, pero los límites suponen que no hay cola (se exige atravesar el nivel por 1 tick).

## E0 (target-free, ya corrido)
**USATECH (kernel `edgelab-areas-e0-usatech`):**
- 4.766 áreas y 59.754 disparos en 169 sesiones, unas 28 áreas por día.
- La configuración más escasa (N ≥ 8, W = 40) tiene unos 450 disparos.
- A/H: p10 1,1 y p90 6,7. p_vol: mediana 0,35.

**Corrección v1.2, decidida sin desenlaces:**
- El comercio real tiene mediana de 9,7 visitas por zona y p10 = 4, así que los cortes fijos 0/1/3 dejaban la perilla sin efecto.
- Ahora los cortes son los **cuartiles del E0 de cada fuente**, como en v_rel. Se guardan en el resultado.
- Control de ruido: sigue en 0 nominadas.

**NQ:** se completa cuando termine el kernel `edgelab-areas-e0-nq`.
