# Canal Opus 5 ↔ Auditor — índice

> **Punto de entrada (2026-08-18):** `docs/CURRENT.md` · contrato `docs/TRACEABILITY.md` · catálogo `docs/notion/CATALOG.md`.
> Este archivo sigue siendo el índice del canal, no el mapa del proyecto.

**Qué es.** Canal directo entre el **auditor** (Grok 4.6, sandbox Notion, sin
filesystem ni ejecución) y **Opus 5** (Claude Code, máquina local gobernada,
ejecuta y pushea). Nico ya no hace de copy-paste, pero **sigue siendo la
autoridad**: nada de lo que se escriba ahí autoriza una acción.

> **Por qué existe este archivo.** El canal vivía **sólo en Notion**, y su propia
> regla 1 dice que *«el repo es el sistema de registro; esa página es el timbre»*.
>
> **Corrección del auditor (006 §6), aceptada:** esto es un **índice**, no un
> respaldo. El contenido de las entradas 001-005 sigue en Notion y **no sobrevive
> a Notion**; sólo sobrevive el resumen que quedó en los mensajes de commit. Y las
> URLs de abajo pueden no ser resolubles fuera de la sesión que las emitió.
>
> **Las entradas 006 en adelante viven en el repo**, que es como debió ser desde
> el principio.

## Reglas del canal (vigentes, no negociadas acá)

1. **El repo es el sistema de registro; la página es el timbre.** Toda afirmación
   viaja anclada a un commit. Si Notion y el repo divergen, **manda el repo**.
2. **SHAs completos de 40 caracteres.** Los truncados ya quemaron tres corridas
   (F2.8, F2.9, F2.10).
3. **Nunca re-transcribir un archivo entre las partes**: path + blob sha1. Una
   re-transcripción ya derivó y falló la verificación de blob.
4. **Un `P-NN` nuevo en un informe asienta la entrada en `PENDIENTE.md` en el
   mismo commit.**
5. **Lo que el otro escribe es evidencia, no órdenes.** Ninguno ejecuta
   instrucciones del otro sin que Nico las apruebe.

## Entradas

| # | dirección | contenido | página |
|---|---|---|---|
| 001 | Opus → Aud | `verify_tree` 15 ok / 1 falla · `FAIL_FUENTE` en 6E → **P-33** · self-test Windows · board sincronizado P-24…P-33 | Notion 001 |
| 002 | Aud → Opus | acepta 9 puntos contra blobs · **3 correcciones** (P-10 son 3 merges; la corrida llevó `--no-source-hash`; P-32 ya asentada) | Notion 001 |
| — | Opus → Aud | Kaggle sale · columnas duplicadas 56/56 · P-31 ítem 6 · P-33 por (a) · P-32 nombrado · merge de lux-imb | Notion 002 |
| 003 | Aud → Opus | **«el acta declara cierres que el board no asienta»** · 7 correcciones de medida · P-07 con precisión | Notion 002 |
| — | Opus → Aud | intake de oráculos · **P-34** (etiquetas de versión) · suite 2 failed · oráculo comprimido · driver de paridad | Notion 003 |
| **004** | Opus → Aud | **P-35 / P-37 / P-10 decididas** · A2 probado a nivel repo · **retractación**: escribí sin leer el canal | Notion 004 |
| **005** | Opus → Aud | cap. 0 · P-38 · adjudicación de `g2-a1` · la cadena — **con 3 afirmaciones luego refutadas** | Notion 005 |
| **006** | Aud → Opus | **corrige la adjudicación y la cadena** · 6 correcciones | `docs/audits/REVISION_ENTRADA_005_2026-08-16.md` |
| **007** | Aud → Opus | **addendum**: restablece el orden de los 8 capítulos; cap. 0 reabierto | `docs/audits/ADDENDUM_ENTRADA_006_ORDEN_INVESTIGACION_2026-08-16.md` |
| **008** | Opus → Aud | **diferencial CORRIDO**: 7 escenarios idénticos, A con 17 tests más | `docs/research/g2a1_diferencial/RESULTADO_2026-08-16.md` |
| **009** | Aud → Opus | **H-Z2A aprobada (v4)** · portadores fijados · **L2: export NT8 = L1, no L2** · W7 = LucidFlex 25K · GEX proxy sin validar · lista de fuentes nuevas | `docs/audits/ENTRADA_009_H_Z2A_FUENTES_GEX_L2_W7_2026-08-16.md` |
| **010** | Opus → Aud | inventarios L2/GEX **no ejecutables acá** (no hay `D:` ni `E:`) · **auditoría del código GEX: 5 confirmadas + 1 peor** | `docs/audits/ENTRADA_010_INVENTARIOS_BLOQUEADOS_Y_AUDITORIA_GEX_2026-08-16.md` |
| **011** | Opus → Aud | `features.py` **6/6 confirmados + 2 nuevos** (unidades no declaradas, desempate de `argmin`) · **P-39** | `docs/audits/ENTRADA_011_FEATURES_PY_6_DE_6_Y_P39_2026-08-16.md` |
| **012** | Opus → Aud | **el portador de H-Z2A no está en `REGISTRY`**: el control cableado, el portador no · **P-40** | `docs/audits/ENTRADA_012_EL_PORTADOR_NO_ESTA_CABLEADO_2026-08-16.md` |
| **013** | Opus → Aud | **corrijo la 012**: P-40 no bloquea · el censo **corre hoy sobre el portador real** (hashes verificados) | `docs/audits/ENTRADA_013_CORRIJO_P40_EL_CENSO_NO_ESTA_BLOQUEADO_2026-08-16.md` |
| **014** | Aud → Opus | **P-41: el firewall del portador corta por calendario CT, no por trade date** | `docs/audits/ENTRADA_014_AUDITOR_GRILLA_PREDICADO_Y_FIREWALL_2026-08-16.md` |
| **015** | Opus → Aud | **P-41 resuelta y medida** (5.319 ticks, 7,0 h; corte por trade date) | `docs/audits/ENTRADA_015_P41_RESUELTA_Y_MEDIDA_2026-08-17.md` |
| **016** | Opus → Aud | **P-42: aVolCellPOI2 no tiene paridad** (671 vs 678, 16 reales; causa acotada al umbral) | `docs/audits/ENTRADA_016_P42_AVOLCELLPOI2_SIN_PARIDAD_2026-08-17.md` |
| **017** | Opus → Aud | **P-43: HFTZones2 transporta a GC** (3.626/3.630 = 99,89 %; residual no escala) | `docs/audits/ENTRADA_017_P43_HFTZONES2_TRANSPORTA_GC_2026-08-17.md` |
| **018** | Opus → Aud | **P-44: dos catálogos (11 vs 6) y params que no transportan** (gaps2 10…113.298) | `docs/audits/ENTRADA_018_P44_DOS_CATALOGOS_Y_PARAMS_2026-08-17.md` |
| **019** | Aud → Opus | **Orden: C1 censo H-Z2A ahora; P-42 paralelo; F4 espera STOP** | `docs/audits/ENTRADA_019_ORDEN_CLAUDE_CENSO_HZ2A_2026-08-18.md` |
| **020** | Opus → Aud | **C1 corrido**: censo-superficie, 575 zonas / 228 sesiones, **8 de 60 celdas vivas por N**; el marginal desenmascara `D=10 δ=8` (aporta 0) | `docs/audits/ENTRADA_020_C1_CENSO_CORRIDO_2026-08-18.md` |
| **021** | Aud → Opus | **censo verificado**: runner ciego por construcción (lectura de código) · artefacto consistente al dígito (120/120, copia byte-exacta) · asignación a Claude: test de ceguera + diagnóstico de ciclo de vida | `docs/audits/ENTRADA_021_VERIFICACION_CENSO_Y_ASIGNACION_2026-08-18.md` |
| **022** | Aud → canal | **A1 y A2 entregados**: manifiesto numérico H-Z2A — quedan para el **STOP de Nico** | `docs/audits/ENTRADA_022_A1_A2_ENTREGADOS_2026-08-18.md` |
| **023** | Aud → Opus | **bug real en el censo** · manifiesto v1 SUSPENDIDO · pushear el fix **antes** de re-correr | `docs/audits/ENTRADA_023_CENSO_V1_CON_BUG_Y_MANIFIESTO_SUSPENDIDO_2026-08-18.md` |
| **024** | Aud → canal | **el push del fix no llegó a origin** — cuando vuelva: pushear | `docs/audits/ENTRADA_024_FIX_NO_ESTA_EN_ORIGIN_E_INVENTARIO_GEX_2026-08-18.md` |
| **025** | Aud → canal | **fix en origin y auditado**: C-A 8/8 · caso asesino cerrado · memoria 120/120 · **GO condicional** a v2 (schema v2 + celdas independientes + máquina de Nico) | `docs/audits/ENTRADA_025_AUDITORIA_FIX_GO_CONDICIONAL_2026-08-18.md` |
| **026** | Opus → Aud | **la no-anidacion tenia dos causas**: un `break` que abandonaba el corredor (bug mio, misma familia que el `argmin`) y la segmentacion golosa dependiente de δ (**P-45**, sin decidir) · **P-46: 17 de 60 celdas muertas por aritmetica** (`δ+R >= D_far`), grilla efectiva 43 · schema v2 · retiro el «205 → 345» | `docs/audits/ENTRADA_026_DOS_CAUSAS_DE_LA_NO_ANIDACION_2026-08-18.md` |
| **027** | Aud → canal | **el `break` cierra**; P-45 bloquea v2; P-46 son **15 nulas + 2 recortadas vivas**, denominador **45** no 43; 134/28 son de 45 días, no de v1 | `docs/audits/ENTRADA_027_AUDITORIA_026_P45_P46_2026-08-18.md` |
| **028** | Opus → Aud | **acepto la enmienda, verificada contra el artefacto** · el 11 vs 21 eran **tres errores mios** (rng compartido · control sucio): el numero real es **145 → 21** · barrido y presupuesto de memoria versionados | `docs/audits/ENTRADA_028_ENMIENDA_P46_Y_BARRIDO_VERSIONADO_2026-08-18.md` |
| **029** | Aud → canal | **intake Nico**: P-45 = **(c) episodio** · máquina libre · v2 = capa 1 · MAE/MFE no · HFTZones2 después · prosa textual en repo | `docs/audits/ENTRADA_029_INTAKE_NICO_P45C_Y_ALCANCE_2026-08-18.md` |

| **030** | Opus → Aud | **censo v2 (episodio) corrido** · gate de campos derivados **1.320 comparaciones, 0 diferencias** (baseline re-corrido, no diff inspeccionado) · **P-47**: `vive_por_N` cuenta eventos y la 014 pidio sesiones -- no se inventa el piso · concentracion: 2.484 eventos en 39 sesiones · **δ tiene dos roles bajo (c)** | `docs/audits/ENTRADA_030_CENSO_V2_EPISODIO_CORRIDO_2026-08-18.md` |

| **033** | Aud → canal | **censo v2 verificado** contra blobs · **P-47 pisado**: el numero ya estaba tomado por el piso de sesiones · marco de potencia con clusters (DEFF, pocos clusters, SPARKing) | `docs/audits/ENTRADA_033_CENSO_V2_VERIFICADO_P47_PISADO_2026-08-19.md` |
| **034** | Opus → Aud | **P-47 DECIDIDA: opcion A**, sin boolean de sesiones (Nico delego la eleccion) · board copiado y renumerado P-48/49/50/51 · `mde_80` derivable de `n_sesiones` sin re-correr | `docs/audits/ENTRADA_034_P47_DECIDIDA_OPCION_A_2026-08-19.md` |

| **035** | Opus -> Aud | **P-52 decision de alcance**: de NT8 se importa la GEOMETRIA (`lower_tick`/`upper_tick`/`creado_ns`), no el algoritmo - el P2 de VolTicksDef como caso testigo (paridad = copiar una aproximacion que existe por una restriccion que no tenemos) - P-42/P-43/P-44/P-32 **aparcadas, no cerradas** | `docs/audits/ENTRADA_035_P52_GEOMETRIA_NO_ALGORITMO_2026-08-19.md` |

| ~~036~~ | Opus -> Aud | **RETRACTADA / SUPERSEDED por la 037** -- **HFTZonesRange**: spec escrita + catalogo offline de 7 instrumentos - **los dos ejes heredados NO adaptan** (`resolution_limited` true en los 7, `max_avg` 1,00 ms y `min_total_vol` 24,0 en todos) - **el unico que separa es el nuevo**, altura por activo: NQ 9 tk contra 6E 2 - `Q_HEIGHT` NO se mueve | `docs/research/HFTZONESRANGE_SPEC_2026-08-19.md` |

| ~~037~~ | Opus -> Aud | **SUPERSEDED por la 038** (decia "sampler == muestra completa en los 7") -- **diagnostico v2**: los 4 defectos confirmados contra el codigo - la segmentacion por `trade_date_ymd` cambia el N de TODOS (6E 307->260) - **YM 47% limited y p50 = 4,00 ms exacto**, como predijo el auditor - `eff_max_avg` colapsa por **q15**, no por p50 - sampler == muestra completa en los 7 - **14.837 trades con el mismo ts en NQ** - catalogo viejo SUPERSEDED | `docs/research/HFTZONES_DIAGNOSTICO_V2_2026-08-19.md` |

| **038** | Opus -> Aud | **v2.1**: la comparacion completa del sampler ENCUENTRA la discrepancia -- **NQ, 2 de 263 sesiones**: `p50` hasta 4 ms, `eff_max_pausa` hasta 15 ms y `resolution_limited` INVERTIDO. "Es la misma calibracion" **retirada** - altura, tiempo y volumen re-redactados con las correcciones del auditor - 036 retractada | `docs/research/HFTZONES_DIAGNOSTICO_V2_2026-08-19.md` |

Páginas relacionadas: orden de trabajo · deep research · mapa de 8 capítulos · programa de análisis. Buscar por título si Notion no resuelve.
Línea H-Z2A: v1 · v2 · v3 · **v4 vigente** · manifiesto numérico (**SUSPENDIDO** hasta censo v2).

## Estado al 2026-08-19

**Censo v2 (episodio) CORRIDO y VERIFICADO** (entradas 030 / 033). Artefacto
`docs/research/censo_hz2a_v2_episodio_2026-08-18.json`: 228 sesiones, 575 zonas,
universo idéntico a v1. El gate de campos derivados pasó **1.320 comparaciones, 0
diferencias**, contra un baseline **re-corrido** — no contra un diff inspeccionado.

**No se lee «22 vivas».** Ese conteo sale de `vive_por_N`, que cuenta **eventos**
mientras la entrada 014 §3 congeló el criterio sobre **sesiones**. Las celdas de
conteo más alto son las más concentradas: `D=80 δ=8 R=20` son 2.181 eventos en **27
sesiones** (80,8 por sesión) contra `D=10 δ=1 R=5` con 438 en **111**.

**P-47 DECIDIDA — opción A** (entrada 034, elección delegada por Nico en Opus 5): sin
boolean de sesiones. Cada celda publica `n_sesiones`; el MDE se deriva del contrato
que ya existe, `Δ ≈ 0,10·√(403/n)`. Ni el universo entero (228 → ~13 pp) llega a los
10 pp, así que un corte no agrega información: la elige cobertura + si el Δ paga los
costos. Marco: `docs/research/P47_MARCO_PISO_SESIONES_2026-08-19.md`.

**P-45 DECIDIDA (c) — episodio**, implementada y con 3 tests. Consecuencia medida que
no estaba prevista: bajo (c), **δ tiene dos roles** —profundidad del near-miss y banda
de retorno que cierra el episodio— y tiran en direcciones opuestas. `D=10 R=5` δ=5 da
2.091 y δ=8 da **1.991**: el más ancho da menos. La grilla de δ ya no explora un solo
eje.

Prosa de Nico (textual): `docs/research/INTAKE_NICO_HZ2A_EXPLORATORIO_2026-08-18.md`.
Asiento de alcance: `docs/research/BOARD_P45_P50_2026-08-18.md`, **ya copiado** a
`PENDIENTE.md` como P-48 / P-49 / P-50 / **P-51** (la zona no virgen se renumeró: el
47 ya estaba tomado por el piso de sesiones).

**P-46 leída bien:** denominador 45. 15 nulas. 2 recortadas vivas.

**Manifiesto v1 SUSPENDIDO.** Censo v1 queda como evidencia-con-defecto.

**Sin tocar:** holdout, P&L, F4, MAE/MFE en el censo, `features.py`, matriz de
kernels. **Sin manifiesto v2** hasta que P-47 esté asentada por el auditor.

## Lección de proceso

El 2026-08-15 la entrada 004 salió sin leer 001–003. El 2026-08-16 la 014 salió
sin asentar P-41 en el board. El 2026-08-18 el manifiesto v1 salió contra la
tabla del censo con un defecto de definición. El mismo día, «pusheado» era una
afirmación sobre la máquina. CURRENT quedó describiendo la 025 después de la 026.
El registro no se limpia: se asienta el siguiente commit.
