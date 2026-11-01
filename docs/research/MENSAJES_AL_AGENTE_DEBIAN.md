# Mensajes al agente del Debian

Estado: VIGENTE. Canal escrito desde la sesión en la nube de Nico (el agente del Debian no es alcanzable por mensajes entre sesiones).
Cada mensaje lleva fecha, remitente y origen. Lo más nuevo, arriba.

## 2026-11-01 (03:15 UTC) — de Nico (redactado por la sesión en la nube): estado, qué cambió y qué hacer al despertar

**Tu estado (leído de `autopilot/state`):** en PAUSE desde el 2026-10-30 01:09 (-03); último ciclo 2026-10-30 04:03 UTC; sólo publicás el
estado una vez por día. Seguís en `0f3a5466`; `foundation` va ~85 commits adelante. Nada se lanzó desde entonces.

**Lo primero: seguí `docs/research/RUNBOOK_SV1_ACTUALIZAR_Y_LANZAR_20261101.md`** (foto, respaldo de los libros append-only, unión con
los del repo, `update.sh` al último `foundation`, reconciliación de campañas con el estado del repo como fuente de verdad, unidades de la
cartera viva, doctor y tests). La pausa se levanta cuando Gonza o Nico lo confirmen (regla del handoff del 30-oct); hasta entonces
dejá todo listo y reportá en el reporte de alineación.

**Qué cambió mientras estabas pausado (todo en `foundation`):**
- Cartera viva: el centro de EdgeLab (`docs/CARTERA_VIVA.md`, directiva 8). Vos sos el dueño del ciclo diario.
- Criba maxT con alfa 0,05 por canal para campañas nuevas (PR #174); las congeladas conservan FDR.
- Auditoría de `t_ns` de AVZP2: **sin lookahead** en las reglas U1 (la canasta de 7 no cambia).
- Salida por tiempo de parada (τ) en el simulador; la variante τ de las 10 reglas con acta quedó **refutada** (0/30).
- Corridas cerradas (registro en `docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md`): la estrategia de las 8:12 sin zonas no tiene edge
  (PRERANGE-BASE en CFD 2023-25: ES/YM sin candidatas, NQ en contra); PRERANGE-ZONAS-ES en contra, -NQ viva sin potencia; TAU, EOD,
  PREAPERTURA, KALMAN-FADE y RANGO0100 sin candidatas o vivas sin potencia. **0 candidatos nuevos para el holdout.**
- Mejores pistas (equity IS+OOS en `docs/research/equity_pistas_20261101/`): RANGO0100-NQ (+13,7/sesión OOS), PRERANGE-ZONAS-NQ (+5,7),
  OTR930-NQ (+5,1), ASIA-NQ (+4,4; prueba forward pre-registrada desde la sesión del 2026-11-02).

**Al tomar la conducción:**
1. Las campañas que hoy conduce la nube (`conductor: local`): paquete del 31-oct (sólo RANGO0100-GC sigue corriendo), PRERANGE-ZONAS y
   PRERANGE-BASE (terminadas). Pasalas a `conductor: debian` en un commit **coordinado**: la nube deja de conducir en ese momento.
2. **Datasets de zonas sin compartir con `nicobuttaro`:** un kernel de PRERANGE-ZONAS lanzado desde esa cuenta falló y en
   `nicolasbuttaro` corrió bien. Compartí `nicolasbuttaro/edgelab-zonas-hft` y `edgelab-zonas-u1` con `nicobuttaro` (lectura) o
   forzá `cuenta_kaggle: nicolasbuttaro` en las campañas que los usan. Verificalo con un kernel chico.
3. Cartera viva: congelá los cortes de régimen (`tools/cartera_diaria.py cortes`) y dejá el timer listo; primeras altas en PAPEL cuando
   Nico apruebe RANGO0100-NQ, PRERANGE-ZONAS-NQ y OTR930-NQ (los pre-registros forward los escribe la sesión en la nube).
4. Bloqueante de datos para las zonas: hacen falta ticks de futuros 2023 → 2025-07 (export de NT8 con `EdgeLabTickLogger.cs`); sin eso
   las zonas sólo se miden sobre el período ya usado.

## 2026-10-31 (23:30 UTC) — de Nico (redactado por la sesión en la nube): la cartera viva pasa a ser el centro de EdgeLab

**Decisión de Nico:** «el agente del Debian tiene que ser quien mantenga nuestras canastas actualizadas al régimen». Leé
`docs/CARTERA_VIVA.md` entero y la directiva 8 de `config/autopilot/DIRECTIVAS.md`. Resumen:
- Todos los días después del cierre de CME: seguimiento forward, retiros inmediatos, régimen de mañana, afinidad, contratos por cuenta,
  cola de investigación con plazos y plan del día (`tools/cartera_diaria.py ciclo`). Si algo falla: MODO SEGURO (cero contratos) y alerta.
- La cola del plan manda: P0 en el día, P1 en 24 h.

**Qué te toca para ponerlo en marcha** (en este orden, todo con test y en tu worktree):
1. Después de reconciliar y actualizar SV1 (pendiente de Gonza), `install.sh` deja `edgelab-cartera.timer` y `/etc/edgelab/cartera.json`.
2. Congelá los cortes de régimen de NQ, ES, YM y GC sobre desarrollo (`cartera_diaria.py cortes`) y escribilos en `cortes_regimen`.
3. Verificá las rutas de `datos` contra lo que tiene SV1 y avisá qué instrumento no tiene datos del día (los futuros dependen del export
   de NT8: es el bloqueante número 1 del seguimiento diario).
4. Dalo de alta en PAPEL a medida que haya pre-registros: lo que confirme el embudo, la canasta forward de ASIA-NQ (20 fichas de una
   celda o ficha multicelda, con test) y las campañas del 31-oct (`docs/research/paquete_20261031/`).
5. No habilites cuentas reales ni cambies `reglas`: es de Nico.

## 2026-10-29 (05:10 UTC) — de Nico (redactado por la sesión en la nube): Infraestructura Multi-Agente Debian v2 (`sincronizador_ramas`, `catalogo_espiral`, `orquestador_multiagente`, `docs/MODULES.md`) + 3 Nuevas Familias en Espiral (Ola 10: `CONFLUENCIA-CVGAP-RACIMOS`, `TORI-TREND-TOQUE3`, `ASIA-BOS-GAPS`)

### 1. Cuatro módulos nuevos de infraestructura ya activos en el repositorio
1. **`edgelab/autopilot/sincronizador_ramas.py`** (y `deploy/debian/auto_sync_code.sh`):
   - Evacúa y fusiona sin pérdida los archivos de estado vivo (`EVALUABLES.jsonl`, `LINAJES.jsonl`, `HOLDOUT_VENTANAS.jsonl`, `LIBRO_LORD.json`, `launches/*.json`) desde `CODE_DIR` hacia `STATE_DIR`, y ejecuta `sincronizar_con_troncal()` hacia `origin/foundation/f0b-compatibility-probe` al inicio de cada ciclo (respaldando cualquier commit local en `autopilot/rescate/<ts>` si hubiera divergencia).
2. **`edgelab/research/catalogo_espiral.py` + `config/autopilot/CATALOGO_MODULOS_ESPIRAL.json` + `docs/MODULES.md`**:
   - Clasifica todos los módulos de EdgeLab en **6 capas (`L0..L5`)** y **7 categorías funcionales componibles**.
   - Antes de proponer o programar cualquier experimento nuevo, inyectar `catalogo_espiral.resumen_rapido_para_agente(max_chars=8000)` en el contexto del agente para reutilizar primitivas existentes.
3. **`edgelab/autopilot/orquestador_multiagente.py` + `config/autopilot/TOPOLOGIA_AGENTES_DEBIAN.json`**:
   - Formaliza la topología **`Capataz Python Determinista + 2 Agentes Claude Opus 4.6 (Arquitecto + Ingeniero/Doctor en worktree) + 1 Agente Claude Sonnet 4.6 (Auditor Adversario, Alineación 10-SLI y Cronista)`**.
   - Reemplaza el truncamiento destructivo (`pop()`) por `armar_contexto_amplio_espiral(max_chars=80000)`, aplica la compuerta objetiva **Velocidad vs. Cuidado** (`evaluar_velocidad_cuidado`: `VIA_RAPIDA_COMPOSICION` vs `VIA_CUIDADA_PARIDAD`), exige revisión adversaria pre-lanzamiento (`auditar_propuesta_sonnet`) y administra la **Guarda O16** (`registrar_reapertura_o16` / `verificar_cierre_o16`).
4. **`edgelab/autopilot/auditor_alineacion.py` (10 SLIs) + `tools/auditar_corridas_nube_20261029.py` (28 campañas y 6 módulos)**:
   - Audita ahora las **28 campañas** (16 de Olas 1–9 + 12 de Ola 10) y los **6 módulos experimentales nuevos**.

### 2. Doce nuevas campañas de la Ola 10 (3 familias nuevas en espiral)
- **Familia `CONFLUENCIA-CVGAP-RACIMOS` (`edgelab/research/confluencia_cvgap_racimos.py`, 314.928 celdas/canal)**:
  - Síntesis en espiral de las 6 campañas ganadoras de Olas 1–9 (`CVGAP-NQ/CFD`, `U1-RACIMOS-GRILLA-NQ/ES`, `U1-ZONAS-BT2-ES/NQ`) y `OTR930`, con cuantiles invariantes de escala para gaps (`g_tom_rel`, `g_cam_rel`) y densidad de racimo de absorción (`rac_dens`).
  - Campañas: `CONF-CVR-NQ` y `CONF-CVR-ES` (`DESC` ya corriendo en Kaggle), `CONF-CVR-CFD-NQ` y `CONF-CVR-CFD-ES` (`DESC / PENDIENTE` listas para lanzar).
- **Familia `TORI-TREND-TOQUE3` (`edgelab/research/tori_trend_toque3.py`, 1.119.744 celdas/canal)**:
  - Derivada del paper de Tori Trades (*Stopping-Time Theory of Swing Trading with Trendlines*) y Post #943 (`@ifriendlytrader`), acoplada con `ZONAS-GAPS` y `EmaCorridorTrendVolW2`.
  - Campañas: `TORI-NQ` (`DESC` corriendo en Kaggle), `TORI-ES`, `TORI-GC`, `TORI-CFD-NQ` (`DESC / PENDIENTE`).
- **Familia `ASIA-BOS-GAPS` (`edgelab/research/asia_bos_gaps.py`, 1.119.744 celdas/canal)**:
  - Derivada del catálogo scrapeado de Instagram (Posts #18/#23 `@alefx_ar` Rango Asia + BOS y Post #159 `@algo.jan` *Asian Session Glitch* / `IFVG`), acoplada con `ZONAS-GAPS` y `EmaCorridorTrendVolW2`.
  - Campañas: `ASIA-NQ` (`DESC` corriendo en Kaggle), `ASIA-ES`, `ASIA-GC`, `ASIA-CFD-NQ` (`DESC / PENDIENTE`).

## 2026-10-29 (03:50 UTC) — de Nico (redactado por la sesión en la nube): ORDEN DE AUDITORÍA PRIORITARIA de las 16 corridas y 3 módulos de las Olas 1–9 (`ba7c2351` + `de6c3ecf`)

### 1. Contexto y alcance de la auditoría encargada a los agentes del Debian (`SV1`)
En los commits `ba7c2351` y `de6c3ecf` se integraron al repositorio:
- **3 módulos experimentales nuevos** (100% causales y con paridad `niveles_lote == niveles`):
  1. `edgelab/research/corredor_vol_gaps.py` (`CORREDOR_VOL_GAPS_*`: `CVGAP-NQ`, `CVGAP-CFD-NQ`, `CVGAP-ES`, `CVGAP-CFD-ES`, 933.120 celdas/canal).
  2. `edgelab/research/otr_930_sweep.py` (`OTR_930_SWEEP_*`: `OTR930-NQ`, `OTR930-ES`, `OTR930-CFD-NQ`, `OTR930-CFD-ES`, 184.320 celdas/canal).
  3. `edgelab/research/oro_almuerzo_ruptura.py` (`ORO_ALMUERZO_RUPTURA_*`: `ORO-ALM-GC`, `ORO-ALM-CFD`, 92.160 celdas/canal).
- **16 campañas cosechadas de Kaggle (Olas 1 a 9):**
  - **6 campañas en `CONTEO` con `ACTA_HOLDOUT.json` congelada, apertura en `HOLDOUT_VENTANAS.jsonl` (`desde: 20261001`) y reserva en `LIBRO_LORD.json`:**
    `CVGAP-NQ`, `CVGAP-CFD-NQ`, `U1-RACIMOS-GRILLA-NQ`, `U1-ZONAS-BT2-ES`, `U1-ZONAS-BT2-NQ`, `U1-RACIMOS-GRILLA-ES`.
  - **9 campañas en `PISTAS_VIVAS` (`n_pistas_vivas = 20`) listas para `tools/holdout_canasta.py` y `tools/analizar_embudo.py`:**
    `CVGAP-ES`, `CVGAP-CFD-ES`, `OTR930-NQ`, `OTR930-ES`, `OTR930-CFD-NQ`, `OTR930-CFD-ES`, `ORO-ALM-GC`, `ORO-ALM-CFD`, `U1-6E-GRILLA`.
  - **1 campaña en `SIN_REGLA_OPERABLE` con candidata viva en desarrollo lista para `tools/analizar_embudo.py`:** `U1-ZONAS-GRILLA-YM`.

### 2. Herramienta y cola lista para ejecutar en el ciclo inmediato
Ya dejamos creado y verificado `tools/auditar_corridas_nube_20261029.py` junto con la cola estructurada en `docs/research/auditoria_corridas_20261029/COLA_AUDITORIA_DEBIAN_20261029.json` y el reporte base `docs/research/auditoria_corridas_20261029/REPORTE_PREAUDITORIA_20261029.md`.

### 3. Pasos obligatorios para los 3 roles del Debian (`Embudo`, `Programador`, `Auditor`)
1. **Rol Auditor (`auditor_alineacion.py` + `tools/auditar_corridas_nube_20261029.py`):**
   - Ejecutar `python3 tools/auditar_corridas_nube_20261029.py --dinamico` para re-verificar causalidad (`indicadores.causal`), paridad lote/escalar, multiplicidad (`LINAJES.jsonl`, `EVALUABLES.jsonl`), reservas LORD++ (`LIBRO_LORD.json`) y cumplimiento estricto de la Directiva #6 (`holdout.desde == 20261001`).
   - Auditar matemáticamente las etapas `DESC`, `INTEGRIDAD`, `OOS` y `TOPES` registradas en `estado.json` y `MEDIDO.md` de las 16 campañas.
2. **Rol Conductor de Embudo (`tools/embudo_correr.py` + `tools/holdout_canasta.py` + `tools/analizar_embudo.py`):**
   - Correr `tools/embudo_correr.py` (`CONTEO` / `HOLDOUT`) y evaluación de canasta de régimen sobre las **6 nuevas `ACTA_HOLDOUT.json`** (`CVGAP-NQ`, `CVGAP-CFD-NQ`, `U1-RACIMOS-GRILLA-NQ`, `U1-ZONAS-BT2-ES`, `U1-ZONAS-BT2-NQ`, `U1-RACIMOS-GRILLA-ES`) usando `edgelab-holdout-sellado` desde `20261001`.
   - Correr `tools/holdout_canasta.py` sobre las **9 campañas en `PISTAS_VIVAS`** (`CVGAP-ES`, `CVGAP-CFD-ES`, `OTR930-*`, `ORO-ALM-*`, `U1-6E-GRILLA`) y `python3 tools/analizar_embudo.py lanzar` / `traer` sobre las 16 campañas.
3. **Rol Programador (en worktree descartable):**
   - Inspeccionar la estabilidad de meseta paramétrica, descomposición por sub-ventana horaria y sensibilidad a costos/slippage de los 3 módulos nuevos (`corredor_vol_gaps.py`, `otr_930_sweep.py`, `oro_almuerzo_ruptura.py`) y publicar el dictamen consolidado en `docs/research/auditoria_corridas_20261029/DICTAMEN_AUDITORIA_DEBIAN_20261029.md`.

## 2026-10-28 (00:48 UTC) — de Nico (redactado por la sesión en la nube): frontera global del holdout desde el 30-sep (2026-10-01), evaluación de canasta de régimen en ventana corta, activos faltantes en el holdout y links/propuestas sobre griegas (0DTE / Gamma / Vanna / Charm)

### A. Directiva global de Nico sobre el Holdout (para todos los agentes, activos y campañas)
1. **El holdout empieza el 30 de septiembre (apertura `2026-09-30 22:00 UTC` = sesión CME `20261001`) para TODOS los agentes, TODOS los activos y TODO el proyecto:**
   - **No usar `holdout.desde = 20261023` en campañas que no consumieron octubre.** Las campañas cuyo `DESC` (`20250801..20260331`) y `OOS` (`20260401..20260930`) cerraron el **30 de septiembre de 2026** (`U1-ZONAS-ES`, `U1-ZONAS-AVCL-ES`, `U1-ZONAS-AVCL-NQ`, `U1-ZONAS-BT2-ES`, `U1-ZONAS-BT2-NQ`, `U1-ZONAS-BT2-YM`, `U1-ZONAS-GRILLA-YM`, `U1-RACIMOS-GRILLA-ES`, `U1-RACIMOS-GRILLA-NQ`, `U1-RACIMOS-GRILLA-YM`, `U1-ORO-GRILLA`) deben tener **`holdout.desde = 20261001`**, no `20261023`. Ponerles `20261023` desperdició 3 semanas enteras de octubre (`2026-10-01..2026-10-22`) que nunca fueron tocadas por esas familias.
   - Si en `HOLDOUT_VENTANAS.jsonl` una apertura fue registrada con `desde: 20261023` antes de mirar P&L (como ya se hizo el 26-oct con `U1-ES-GRILLA`, `U1-YM-GRILLA` y `U1-ZONAS-NQ`), corresponde anular y re-registrar con `desde: 20261001` antes de evaluar P&L.
2. **Cambio conceptual clave (canasta de estrategias de régimen vs. esperar `n_fijo = 150..450` durante años):**
   - **Criterio de Nico:** Si estas estrategias tienen edge real, probablemente sea un **edge de régimen**. Con una frecuencia de ~4 a 10 operaciones por mes por celda, exigir `n_fijo = 150..450` antes de confirmarlas implica esperar **1.5 a 4 años**, para cuando el régimen actual probablemente ya haya terminado.
   - **La idea de una canasta de estrategias de régimen** es que el riesgo se diversifica en la canasta justamente porque **no las probamos individualmente con un holdout de alta potencia a años vista**.
   - **Regla de confirmación para la canasta en periodo reducido de holdout:** estimar la distribución/desviación esperada del rendimiento de cada estrategia en la ventana corta disponible del holdout (desde el `2026-10-01` hasta hoy) a partir de su media y desvío (`se`) en desarrollo/OOS; **si el rendimiento observado en el período reducido de holdout está dentro de la desviación esperada (no cae por debajo de la banda inferior esperada para ese `n` reducido y mantiene consistencia con el régimen), puede ser confirmada para añadirse a la canasta**.
3. **Datos de activos que faltan descargar/sellar en `nicolasbuttaro/edgelab-holdout-sellado` (`v2`):**
   - **Lo que YA está en `edgelab-holdout-sellado` `v2`:**
     - Futuros CME (`2026-10-01` al `2026-10-27` parcial): `ES_12-26_ticks.parquet` (17 sesiones; faltan en servidor NT8 `2/7/8-oct`) y `NQ_12-26_ticks.parquet` (19 sesiones; falta `7-oct`).
     - Spots Dukascopy (`2026-10-01` al `2026-10-25`, 21 días): `USATECHIDXUSD`, `USA500IDXUSD`, `USA30IDXUSD`, `XAUUSD`, `EURUSD`, `GBPUSD`, `USDJPY`.
   - **Lo que FALTA descargar/subir al dataset sellado:**
     1. **Futuros CME usados como `sensor` o `ejecucion` en campañas activas:**
        - **`GC` (`GC_12-26_ticks.parquet`)**: bloquea la ejecución de `U1-ORO-GRILLA` (`sensor=DK:XAUUSD`, `ejecucion=GC`).
        - **`YM` (`YM_12-26_ticks.parquet`)**: necesario para las campañas en `YM` futuro (`U1-RACIMOS-GRILLA-YM`, `U1-ZONAS-BT2-YM`, `U1-ZONAS-GRILLA-YM`, y ejecución cruzada de `U1-YM-GRILLA`).
        - **`6E` y `6B` (`6E_12-26_ticks.parquet`, `6B_12-26_ticks.parquet`)**: necesarios para `U1-6E-FUT-GRILLA`, `U1-6B-FUT-GRILLA` y ejecuciones cruzadas de `U1-6E-*` / `U1-6B-*`.
     2. **Actualización de los 7 spots de Dukascopy (`2026-10-26` en adelante):** hoy cortan en `2026-10-25`.

---

### B. Material de referencia (5 documentos de la serie «Las griegas que mueven tu futuro») y propuestas para implementar en EdgeLab

Nico compartió estos 5 documentos para evaluar qué conceptos vale la pena, son posibles y tenemos recursos para sumar a EdgeLab:
- **Doc 1 (Cap. 6 — Las 0DTE):** https://docs.google.com/document/u/0/d/1t6rBaJtqRx6nm3tk1i0fyLctTx3uTxx8/mobilebasic
  - *Paper citado:* Adams, Dim, Eraker, Fontaine, Ornthanalai & Vilkov (2026), *"Do S&P 500 Options Increase Market Volatility? Evidence from 0DTEs"*.
  - *Mecanismo:* Los market makers están largos de gamma en 0DTE en el 88% de los tramos de 10 min; su cobertura con futuros `ES` va contra el movimiento (compran caídas y venden subidas), reduciendo la volatilidad intradía y haciendo que **los desequilibrios de órdenes en el E-mini reviertan durante ~30 minutos**. Con gamma neta baja, reaparece el momentum.
- **Doc 2 (Cap. 2 — El Delta):** https://docs.google.com/document/u/0/d/1PL8yCyAhbRWMfojgiR1_IpSoI-dHAeAG/mobilebasic
  - *Papers citados:* Gârleanu, Pedersen & Poteshman (2009, *RFS*); Ni, Pearson, Poteshman & White (2021, *RFS*); Baltussen, Da, Lammers & Martens (2021, *JFE*).
  - *Mecanismo:* El rebalanceo mecánico de delta de los dealers mete órdenes de futuros no informativas en el libro del `ES` que luego tienden a revertir si el flujo fue puramente mecánico.
- **Doc 3 (Cap. 5 — El Charm / OPEX):** https://docs.google.com/document/u/0/d/11MkXaNlbKzTfW2wWjK204VltOgxHcvC7/mobilebasic
  - *Paper citado:* Golez & Jackwerth (2012, *JFE*), *"Pinning in the S&P 500 futures"*.
  - *Mecanismo:* A medida que pasa el día (especialmente cerca de vencimientos / última hora de días tranquilos), el delta de las puts OTM decae hacia cero (*charm*), sobrando cobertura corta de futuros que los dealers recompran mecánicamente hacia el cierre (*drift* de última hora y *pinning* en días de OPEX).
- **Doc 4 (Cap. 4 — La Vanna y los anuncios macro):** https://docs.google.com/document/u/0/d/1dEIrfTtnLs3jm1GIQ7oFLnAypHGDhhET/mobilebasic
  - *Papers citados:* Savor & Wilson (2013, *JFQA*); Ederington & Lee (1996, *JFQA*).
  - *Mecanismo:* Antes de un anuncio macro programado (`CPI`, `NFP`, `FOMC`, `PPI`), la volatilidad implícita (IV) está inflada. Apenas sale el dato, la incertidumbre se resuelve y la IV cae (*IV crush*), encogiendo el delta de las puts OTM y obligando a los dealers a **recomprar futuros mecánicamente después del dato** (más del 60% de la prima de riesgo anual se gana en días de anuncio macro).
- **Doc 5 (Cap. 3 — El Gamma y el Gamma Flip):** https://docs.google.com/document/u/0/d/1Hx9AlGuppagwxY0RRG_pNJC2Fn-YkL7F/mobilebasic
  - *Papers citados:* Barbon & Buraschi (2020), *"Gamma Fragility"*; Baltussen et al. (2021, *JFE*).
  - *Mecanismo:* Gamma positivo = terreno en forma de valle (reversión a la media, falsas rupturas); Gamma negativo = terreno en forma de colina (las rupturas se amplifican, stops en cadena).

#### Propuestas concretas para que investigues e implementes con los recursos que YA tenemos en el repo:
1. **Propuesta 1 — Cruce/Filtro de Régimen GEX (`SqueezeMetrics`) sobre nuestras grillas de reversión `U1-*` (Docs 1, 2 y 5):**
   - *Recursos ya disponibles:* En `GEX-1` y `GEX-1b` (`docs/research/GEX_FUENTES_Y_EVIDENCIA_20261006.md` y `docs/research/GEX1B_RESULTADO_20261005.md`) ya verificamos con `Holm <= 0.022` sobre `SqueezeMetrics` (`2011–2026`, 100% causal con el OI del cierre previo) que con menor GEX ex-ante suben la amplitud (`I1a`), la volatilidad realizada (`I1b`) y la autocorrelación (`ac1`).
   - *Qué implementar:* Todas nuestras reglas `U1-*` son reversiones tras un impulso/barrido (el mecanismo de absorción de gamma positiva del Doc 1 y Doc 5). Agregá en `edgelab/research/analizador.py` (y como eje/filtro opcional en `grilla_generica`) la partición por el régimen de GEX ex-ante (p. ej. quintil inferior de GEX o GEX < 0 vs. GEX positivo) para verificar si los drawdowns de `U1-ES-GRILLA`, `U1-ZONAS-ES/NQ` y `U1-RACIMOS-GRILLA-ES/NQ` se concentran en días de gamma baja/negativa donde domina el momentum.
2. **Propuesta 2 — Familia / Estudio de Flujo Post-Macro por Vanna (`t + 10..90 min` tras `CPI`, `NFP`, `FOMC`, `PPI`) (Doc 4):**
   - *Recursos ya disponibles:* Ya tenemos `edgelab/research/eventos_datos.py` y `edgelab/research/eventos.py` con más de 700 timestamps exactos al segundo de anuncios `tier1`/`tier2` (`2023–2026`) y los ticks completos de `ES`, `NQ` y CFDs. Hoy sólo usamos `EVENTOS` para excluir (`EXCLUIR_EVENTOS`).
   - *Qué implementar:* Diseñar una familia pre-registrada que mida y opere la ventana **posterior** al anuncio (entrando `10 a 15 minutos después` del release, cuando ya pasó la ventana de `±1..2 min` prohibida por las prop firms y empieza el desarme mecánico de coberturas por *IV crush*), evaluando primero información *target-free* (asimetría de drift / absorción del latigazo inicial en los 60–90 min posteriores al dato) y luego el embudo.
3. **Propuesta 3 — Ventana RTH y horizonte de reversión de ~30 min por absorción 0DTE (Doc 1) y Drift de última hora / OPEX por Charm (Doc 3):**
   - *Recursos ya disponibles:* Módulos `edgelab/research/lux_imb.py`, `edgelab/research/u1_oro.py` y calendario de tercer viernes / fin de día RTH (`15:00–16:00 ET`).
   - *Qué implementar:* Testear en las familias de desequilibrio/absorción (`LUXIMB` / `U1`) la restricción al horario activo de 0DTE (`09:30–15:30 ET`) con salida temporal acotada a la ventana de reversión documentada por Adams et al. (~15 a 30 min), y medir en estudio separado el *drift* de desarme de coberturas en la última hora RTH (`15:00–16:00 ET`) en sesiones tranquilas vs. días de vencimiento.
   - *(Nota de alcance: descartar por ahora backtests que requieran cadena histórica intradía de strikes/walls antes de jul-2026 porque no hay fuente gratuita causal, y no repetir la prueba `I2n`/`I2d` de Baltussen aislada que ya dio nula en `GEX-1b`).*

## 2026-10-27 (23:55 UTC) — de Nico: `edgelab-holdout-sellado` v2 subido (ES + NQ hasta 26-oct), fixes de `HOLDOUT_CONTEO` (escala 202609, zonas selladas, calentamiento y slug <=49) y las 8 campañas lanzadas en Kaggle

1. **Holdout sellado v2 publicado en Kaggle (`nicolasbuttaro/edgelab-holdout-sellado`, v2):**
   - Ya incluye **`ES_12-26_ticks.parquet`** y **`NQ_12-26_ticks.parquet`** actualizados hasta el **2026-10-26** (además de los 7 spots de Dukascopy). La cuenta `nicobuttaro` ya tiene permiso `View` sobre `v2`.
   - Con esto, **`U1-ZONAS-ES`** ya tiene ticks sellados de `ES` futuro y **`U1-ZONAS-AVCL-NQ` / `U1-ZONAS-BT2-NQ` / `U1-RACIMOS-GRILLA-ES` / `U1-RACIMOS-GRILLA-NQ`** tienen sesiones `>= 2026-10-23`. *(Sólo `U1-ORO-GRILLA` sigue esperando ticks sellados de `GC` futuro).*
2. **Cuatro bugs de `HOLDOUT_CONTEO` corregidos y probados en este commit:**
   - **Slug >49 chars (`U1-RACIMOS-GRILLA-ES/NQ` y `AN_ANALIZAR_REGLA`):** `KaggleRunner.argumentos` recortaba a `<=50` pero `validate_push` exige `<=49`; ahora recorta a `[:49].rstrip("-")`.
   - **Escala causal de `202610` en `u1_oro.escala_por_mes`:** cuando la ventana arranca en `202610` (único mes del dataset sellado), `r.shift(1)` dejaba `202610` en `NaN` y todas las campañas `U1-*` daban `0` disparos en todo octubre. Ahora `u1_oro.py` fija `RANGO_M1_202609` (medido sobre los minutos activos de septiembre 2026 en desarrollo) y escala `202610` causalmente con `RANGO_M1_202609[sensor] / r_ref`.
   - **Zonas en `SELLADO=1` (`u1_zonas.py` y `u1_racimos_grilla.py`):** en el holdout sólo se monta `edgelab-holdout-sellado` (ticks crudos, sin `ZONAS_*.parquet`, lo que rompía `U1-ZONAS-NQ` con `FileNotFoundError`). Cuando `SELLADO=1` y no hay parquet de zonas, `u1_zonas` y `u1_racimos_grilla` calculan las zonas (`AVZP2`, `AVCL`, `BT2`, `AVZRG`) sobre las sesiones selladas `20261001..HASTA`.
   - **Calentamiento causal `20261001..desde-1` (`embudo_main.py` y `grilla_generica.correr`):** para campañas con `desde > 20261001` (`20261023`), el contexto se arma desde `20261001` para calentar el umbral de 20 bloques de `AVZP2`/`AVCL`, los racimos de `AVZRG` y `base_rate` de `u1_indaga`, y `grilla_generica.correr` filtra `D = D[D.ses >= ctx["desde_eval"]]` antes de `resumen_e0` y `simular_ops` para que el calentamiento nunca cuente disparos ni operaciones.
3. **Las 8 corridas de `HOLDOUT_CONTEO` ya se lanzaron y completaron (`8/8 complete`) en Kaggle con el código nuevo (`e1682e74`):**
   - `U1-ZONAS-NQ` (`nicobuttaro/embudo-u1-zonas-nq-holdout-conteo-20261001`, `[20261001, 20261026]`): **`conteo = [11]`** (de `n_fijo = 449`)
   - `U1-ES-GRILLA` (`nicolasbuttaro/embudo-u1-es-grilla-holdout-conteo-20261001`, `[20261001, 20261026]`): **`conteo = [6]`** (de `n_fijo = 169`)
   - `U1-YM-GRILLA` (`nicolasbuttaro/embudo-u1-ym-grilla-holdout-conteo-20261001`, `[20261001, 20261026]`): **`conteo = [2]`** (de `n_fijo = 450`)
   - `U1-ZONAS-BT2-NQ` (`nicolasbuttaro/embudo-u1-zonas-bt2-nq-holdout-conteo-20261023`, `[20261023, 20261026]`): **`conteo = [1]`** (de `n_fijo = 150`)
   - `U1-ZONAS-ES` (`nicolasbuttaro/embudo-u1-zonas-es-holdout-conteo-20261023`, `[20261023, 20261026]`): **`conteo = [0]`** (de `n_fijo = 150`; sólo 2 sesiones desde el 23-oct)
   - `U1-ZONAS-AVCL-NQ` (`nicolasbuttaro/embudo-u1-zonas-avcl-nq-holdout-conteo-20261023`, `[20261023, 20261026]`): **`conteo = [0]`** (de `n_fijo = 150`; sólo 2 sesiones desde el 23-oct)
   - `U1-RACIMOS-GRILLA-ES` (`nicolasbuttaro/embudo-u1-racimos-grilla-es-holdout-conteo-202610`, `[20261023, 20261026]`): **`conteo = [0]`** (de `n_fijo = 295`; sólo 2 sesiones desde el 23-oct)
   - `U1-RACIMOS-GRILLA-NQ` (`nicolasbuttaro/embudo-u1-racimos-grilla-nq-holdout-conteo-202610`, `[20261023, 20261026]`): **`conteo = [0]`** (de `n_fijo = 150`; sólo 2 sesiones desde el 23-oct)
4. **Acción inmediata en `SV1`:**
   - Ejecutá `update.sh` a la punta de `foundation/f0b-compatibility-probe`.
   - Reabrí a `CONTEO` (`fallas: 0`, `handle: null`, `ultimo_conteo: null`): **`U1-ZONAS-ES`**, **`U1-ES-GRILLA`**, **`U1-YM-GRILLA`** y **`U1-ZONAS-NQ`**, y poné **`"ultimo_conteo": null`** en **`U1-ZONAS-AVCL-NQ`** y **`U1-ZONAS-BT2-NQ`** para que `SV1` registre estos conteos en su `estado.json` y continúe el seguimiento semanal hasta alcanzar `n_fijo`.

## 2026-10-27 (18:40 UTC) — de Nico (redactado por la sesión en la nube): más corridas en paralelo con las dos cuentas

**Decisión de Nico:** con dos cuentas de Kaggle, el paralelo puede ser mayor que 4. El tope de kernels simultáneos es **por cuenta**, y
`KaggleRunner.elegir_cuenta` ya reparte con `"cuenta_kaggle": "auto"` (la que tenga menos kernels corriendo).
1. Subí `max_concurrent` a **8** (4 por cuenta) en `autopilot.json` y asegurate de que todas las campañas del embudo lancen con
   `"cuenta_kaggle": "auto"`.
2. Si Kaggle rechaza por tope en las dos cuentas, bajá de a 1 hasta que no haya rechazos y dejá en el reporte de alineación el número
   que quedó y por qué. Si no hay rechazos, podés probar 10.
3. Registrá en el estado cuántos kernels corren por cuenta (para que Nico lo vea en `autopilot/state`).

## 2026-10-27 (17:30 UTC) — de Nico (redactado por la sesión en la nube): el arreglo O13 no alcanzó; ya está corregido

**Qué pasó.** Las 5 campañas U1 (U1-ES, U1-YM, U1-ORO, U1-ZONAS-ES, U1-ZONAS-NQ) volvieron a quedar BLOQUEADA en CONTEO después de
la reapertura de las 02:18 UTC. El log del kernel `nicolasbuttaro/embudo-u1-ym-grilla-holdout-conteo-20261001` sigue diciendo
`KeyError: 'r_vol'` en `grilla_generica.resumen_e0` (línea 330): O13 arregló el índice `k`, pero con 0 disparos el DataFrame vacío
de U1 tampoco trae las columnas de las variables, y si no trae `k`, la línea del `ses` rompe igual. El test de O13 no lo cazaba
porque su DataFrame vacío traía las columnas.

**Arreglo (este commit):** `resumen_e0` trata la columna faltante como vacía, y `correr` no lee `D.k` si no existe. Dos tests nuevos
en `tests/research/test_guardas_20261027.py` reproducen exactamente el caso del kernel. Kernels reconstruidos.

**Qué te toca:**
1. `update.sh` a este commit (con pausa), y **reabrir las 5 a CONTEO** igual que hiciste con O13 (crash de infraestructura, el acta
   sigue vigente, nada del holdout se miró).
2. **Lección para tu checklist:** después de reabrir por un arreglo, mirá el log del primer kernel relanzado antes de dar el arreglo
   por bueno. Esta vez se bloquearon de nuevo a las 03:12 y nadie lo vio en 14 horas. Agregalo como guarda (O16) en
   `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`: una reapertura que vuelve a fallar igual dispara alerta, no un tercer reintento mudo.
3. **El generador:** el estado de `mandate.json` no frena la generación en el código (sólo es un WARN del doctor), así que el mandato
   en BORRADOR no explica por qué no propone. `edgelab-autopilot-generate.service` aparece fallido en `alertas.jsonl` (5 veces entre el
   26 y el 27): buscá la causa raíz en `journalctl -u edgelab-autopilot-generate.service` y arreglala, o decí qué falta.
4. U1-ZONAS-NQ: `kernels.get` sobre `nicobuttaro/…` sigue dando 403 desde afuera de esa cuenta. Es esperable (kernel privado de la otra
   cuenta), pero confirmá que vos lo leés con la cabecera de `nicobuttaro`.
5. **Tus dos preguntas abiertas** (3 vs 4 en paralelo; cómo viaja el estado del clon) siguen esperando a Nico; mientras tanto, dejá 4
   y el estado sólo por `autopilot/state`.

## 2026-10-27 — de Nico (redactado por la sesión en la nube): usá las dos cuentas de Kaggle + directivas en tu contexto

**Pedido de Nico:** si podés, **aprovechá las dos cuentas de Kaggle** (`nicolasbuttaro` y `nicobuttaro`) para las corridas: repartí
los kernels entre ambas (`"cuenta_kaggle": "auto"`), y si una rechaza por tope de kernels simultáneos o cuota, reintentá en la otra.
Reportá en el estado cuántas corridas fueron a cada cuenta.

Desde este commit, las directivas vigentes de Nico (autorreparación, pensar fuera del molde, espiral, dos cuentas, estructura que no
se rompe) viven en **`config/autopilot/DIRECTIVAS.md`** y entran en el paquete de contexto de cada rol en cada ciclo
(`directivas_de_nico`, nunca se recorta). Leelo primero.

## 2026-10-27 (05:25 UTC) — de Nico (redactado por la sesión en la nube): espiral de automejora con datos + Internet

**Directiva permanente (Nico):** trabajá en **espiral**: cada vuelta aprende de los datos y de lo que ya se midió, y la siguiente arranca
mejor. Sumado a pensar fuera del molde y a **investigar en Internet**.

Una vuelta de la espiral (proponé tu propio ritmo; como referencia, una por día):
1. **Medir:** qué terminó desde la vuelta anterior (embudos, analizador, ATRAS, holdout), con sus potencias y MDE.
2. **Aprender:** meta-análisis (`tools/metaanalisis_embudo.py`) y lectura de los resultados: qué mecanismos, instrumentos, horarios,
   perillas y ejecuciones se repiten en lo que vive y en lo que muere; qué se cerró sin potencia. Escribilo en un archivo vivo
   `docs/research/APRENDIZAJES_ESPIRAL.md` (vuelta, evidencia con rutas, lo que cambia en la próxima) — es la memoria de la espiral.
3. **Investigar afuera:** buscá en Internet papers, notas de microestructura, blogs serios de practitioners, foros de prop firms y
   documentación de exchanges sobre los mecanismos que viven o sobre huecos que no cubrimos. Sumá lo útil al corpus (CerebroSSRN /
   biblioteca) con la fuente citada. Lo de Internet es **inspiración, nunca evidencia**: sólo cuenta lo que pase el embudo con nuestros datos.
4. **Proponer:** hipótesis nuevas o refinadas (incluidas las fuera del molde), cada una con justificación económica, cómo podría
   refutarse, linaje y cuánta potencia tendría con los datos que hay. Priorizá por valor esperado / costo de cómputo.
5. **Correr:** pre-registro, contador global, embudo. Nada se elige mirando el holdout.
6. **Mejorarte:** una mejora concreta de la herramienta o del proceso por vuelta (velocidad, robustez, una guarda nueva, un control
   que faltaba), con test.
7. **Contar:** resumen corto en la sala al cerrar la vuelta: qué aprendiste, qué cambiaste, qué corre, qué falta.

Para no autoengañarse (la espiral no puede convertirse en buscar hasta encontrar): toda vuelta suma sus pruebas al contador global y a
LORD++; lo aprendido de una familia no se usa para «rescatar» esa misma familia con los mismos datos; lo que se refina con datos ya
mirados se confirma sólo con datos nuevos (réplica no mirada u holdout a N fijo).

## 2026-10-27 (05:15 UTC) — de Nico (redactado por la sesión en la nube): pensá fuera del molde

**Directiva permanente (Nico):** no te limites a hacer lo que se te pide. Pensá, proponé y mejorá — a vos mismo y a los análisis — de
forma creativa, autónoma y proactiva, **sin romper la estructura** (embudo, pre-registro, contador global, LORD++, firewall del holdout,
costos canónicos, CLAUDE.md).

Qué significa en la práctica (ideas, no una lista cerrada; inventá las tuyas):
- **Sobre los análisis:** leé el registro MEDIDO/NO MEDIDO, los resultados del embudo y el corpus de papers, y buscá huecos: familias que
  nadie probó, cruces entre instrumentos, variables de régimen, ejecuciones distintas, datos que existen y nadie usa. Diseñá barridos
  propios con `grilla_generica` (guía §6) sobre indicadores PASS o causales propios, con su pre-registro. Que cada idea tenga
  justificación económica y cómo podría refutarse.
- **Sobre lo que ya se midió:** meta-análisis de tus propias campañas (`tools/metaanalisis_embudo.py`): qué tipos de hipótesis mueren y
  por qué, dónde falta potencia, qué perillas nunca importan; usalo para que la próxima campaña sea mejor y más barata.
- **Sobre vos mismo:** medí tu rendimiento (ciclos, kernels por día, fallas, tiempo muerto por cupo de Kaggle, tokens) y atacá el cuello
  de botella; automatizá lo que hoy se hace a mano; agregá guardas y tests a partir de cada error (registro de errores).
- **Sobre la infraestructura:** si una herramienta es lenta, frágil o duplica otra, mejorala (reutilizar antes de construir:
  `tools/existente.py`).
- **Proponé en la sala** lo que no puedas o no debas hacer solo, con una recomendación concreta.

Límites que siguen (la estructura): nada se elige mirando el holdout; todo resultado pasa por el embudo y se registra antes de correr;
nunca se relaja un criterio después de ver resultados; cambiar gates/FDR/mandato/archivos protegidos sigue lo que dice CLAUDE.md; no se
opera con dinero real. Dejá constancia de cada iniciativa propia (qué, por qué, resultado) en `docs/research/` o en la sala.

## 2026-10-27 (04:30 UTC) — de Nico (redactado por la sesión en la nube): arreglate solo; primer caso, el CONTEO del holdout

**Directiva permanente (Nico):** el Debian se arregla a sí mismo. Tené un monitoreo global del proyecto y de vos mismo: en cada ciclo,
mirá tu propio estado y actuá sin esperar a nadie. Como mínimo:
- campañas en `BLOQUEADA` o con `fallas > 0` → bajá el log del kernel (`kernels/output`), encontrá la causa raíz, arreglá el código,
  tests, commit con la causa, y desbloqueá la campaña para que reintente **la misma etapa** (sin rehacer etapas ya hechas ni reabrir
  ventanas del holdout);
- unidades systemd en `failed`, timers que no corren, la rama `autopilot/state` sin commits nuevos, CI rojo en `foundation`;
- registrá cada incidente y su arreglo en `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` y, si se puede, agregá una guarda
  (test o chequeo) para que no se repita.
Lo único que no es tuyo: operar con dinero real.

**Puntapié inicial — incidente abierto ahora:** 5 campañas terminaron `FIN BLOQUEADA` tras 3 fallas en `CONTEO`: U1-ES-GRILLA,
U1-YM-GRILLA, U1-ORO-GRILLA, U1-ZONAS-ES, U1-ZONAS-NQ. Log del kernel (`nicolasbuttaro/embudo-u1-es-grilla-holdout-conteo-20261001`):
`grilla_generica.resumen_e0 → KeyError: 'r_vol'`.
- **Causa (diagnóstico de la nube; verificalo):** la gramática U1 (`u1_oro.escala_por_mes`, que usan u1_cfd, u1_zonas, u1_zonas_avcl,
  u1_zonas_bt2, u1_racimos_grilla, u1_zonas_grilla) escala cada mes con el rango M1 del mes ANTERIOR y el primer mes de la ventana no
  dispara. El holdout empieza el 2026-10-01 y el dataset sellado sólo trae octubre → **cero disparos**; y `grilla_generica.correr` llama a
  `resumen_e0` antes de chequear `len(D)`, así que con D vacío (columnas de `VACIO`) se cae en vez de devolver n=0.
- **Probablemente afecte también** a las que siguen en CONTEO (U1-ZONAS-BT2-NQ, U1-RACIMOS-GRILLA-ES/NQ, U1-ZONAS-AVCL-NQ).
- **Arreglo propuesto:** (1) que la escala del primer mes del holdout salga del mes anterior en DESARROLLO (septiembre no es holdout):
  por ejemplo congelar `escala_seg` del mes de arranque en el acta al abrirla y pasarla en PARAMS al CONTEO, o montar septiembre del
  dataset de desarrollo como calentamiento sin que entre al conteo; (2) en `correr`, devolver resultado vacío con n=0 cuando `D` está
  vacío, antes de `resumen_e0`; (3) test que reproduzca el caso (ventana de un solo mes) y uno que verifique que el calentamiento no
  cuenta operaciones; (4) desbloquear las 5 con sus mismas actas (N y nivel de LORD++ ya reservados) — no se miró ninguna operación,
  así que no hay consumo nuevo del holdout.
- Avisá en la sala cuando esté resuelto, con el commit.

## 2026-10-27 (01:55 UTC) — de Nico (redactado por la sesión en la nube): generador caído y estado sin publicar

1. **`edgelab-autopilot-generate.service` en `failed` desde el 26-oct 06:19.** El bug conocido del paso `propose` (`TypeError: dict() got
   multiple values for keyword argument 'lente'`) está arreglado desde el PR #127 (mergeado el 25-oct), que SV1 ya tiene (está en
   `87b11b78` o posterior). Con el código actual `propose` corre bien (probado en la nube con `proponente: true`). Lo más probable es que
   el `failed` sea de una corrida con código viejo y la unidad quedó marcada. Hacé:
   `sudo systemctl reset-failed edgelab-autopilot-generate.service && sudo systemctl start edgelab-autopilot-generate.service`
   y mirá `journalctl -u edgelab-autopilot-generate -n 50`. Si vuelve a fallar con otro error, arreglalo vos (causa raíz en el commit).
2. **PR #141 (sync_state: heartbeat.json) mergeado.** Actualizá con `update.sh` (con pausa, sin corrida en curso) para que el estado
   empiece a publicarse en `autopilot/state`; confirmá en el próximo ciclo que la rama aparece en GitHub.
3. Avisá en la sala cuando los dos estén en verde.

## 2026-10-27 (01:45 UTC) — de Nico (redactado por la sesión en la nube): todo junto

1. **Actualizá el código del SV1 a foundation con `update.sh`, ya** (con pausa y sin corrida en curso, como siempre). Trae los kernels
   pre-armados reconstruidos (`tools/kaggle_grilla/kernel_*.py`): sin ellos algunas etapas fallan o quedan desalineadas.
2. **El archivo de credencial lo revisa una persona, no vos** (tu clasificador lo bloquea y está bien que lo haga). Gonza o Nico
   corren en el SV1 estos dos comandos; ninguno imprime el token:
   ```
   sudo -u edgelab curl -sS -o /dev/null -w '%{http_code}\n' -H @/opt/edgelab/.kaggle_auth_header.nicobuttaro https://www.kaggle.com/api/v1/datasets/view/nicolasbuttaro/edgelab-holdout-sellado
   sudo awk '{print NR": "$1, $2, substr($3,1,5)"…", "largo="length($3)} END{print "lineas="NR}' /opt/edgelab/.kaggle_auth_header.nicobuttaro
   ```
   200 = resuelto. Si da 403 y la segunda no muestra exactamente una línea `Authorization: Bearer KGAT_…` (token nuevo) o
   `Authorization: Basic …` (clave vieja), hay que reescribir el archivo con ese formato.
3. **Vos sí podés** verificar (sin leer el archivo) que `EDGELAB_KAGGLE_OWNER=nicobuttaro` le llega al proceso que lanza los kernels de
   las tres campañas fijadas (U1-ZONAS-NQ, ZGAP-CFD, ZGAP-NQ): `embudo_runners.KaggleRunner._env`. Si no llega, arreglalo vos.
4. Cuando quede en 200, avisá en la sala y dejá que esas tres campañas se lancen con `nicobuttaro`.

## 2026-10-27 (01:35 UTC) — de Nico (redactado por la sesión en la nube): el 403 de `nicobuttaro` en `edgelab-holdout-sellado`

Nico dice que **el token de `nicobuttaro` está bien y lo tenés**. Y el dataset **ya está compartido**: desde la nube, con la credencial
de `nicobuttaro`, `datasets/view/nicolasbuttaro/edgelab-holdout-sellado` da **200** y la descarga da **302** (autorizada); lo mismo
`edgelab-zonas-u1` y `edgelab-liquid-ticks-20261014`. Lo más probable es que lo hayas probado antes de que Nico lo compartiera.

Qué hacer, en orden (sin preguntar; arreglá vos lo que encuentres):
1. **Repetí la prueba ahora**, con la cabecera de esa cuenta:
   `curl -sS -o /dev/null -w '%{http_code}\n' -H @/opt/edgelab/.kaggle_auth_header.nicobuttaro https://www.kaggle.com/api/v1/datasets/view/nicolasbuttaro/edgelab-holdout-sellado`
   Si da 200: listo, avisá en la sala y dejá que las campañas fijadas a `nicobuttaro` sigan su curso.
2. Si sigue en 403, revisá **el formato del archivo** (sin imprimir el token): tiene que ser exactamente una línea
   `Authorization: Bearer KGAT_...` (token nuevo) o `Authorization: Basic <base64 de usuario:clave>` (clave vieja), sin comillas ni
   saltos de línea extra. Un token KGAT con Basic, o usuario/clave con Bearer, falla.
3. Revisá **qué cabecera usa el servicio de verdad**: `tools/kaggle_auth.py` elige `<KAGGLE_AUTH_HEADER_FILE>.<EDGELAB_KAGGLE_OWNER>`
   sólo si `EDGELAB_KAGGLE_OWNER` llega al proceso (`embudo_runners._env`). Si la variable no llega, cae a la cabecera única (la de
   `nicolasbuttaro`) y un kernel de `nicobuttaro` se crea con la cuenta equivocada.
4. Si con todo eso sigue el 403, decilo en la sala con el código exacto y la URL (nunca el token).

## 2026-10-27 — de Nico (transcripto por la sesión en la nube)

> «Auto corregí tus propios errores, ya que estás en modo prueba.»

Alcance, tal como lo entiende la sesión que lo transcribe (si hay duda, preguntale a Nico en la sala):
- Si algo que **vos** hiciste falla (un CI rojo por tu PR, un kernel desactualizado, un conductor caído, una campaña que no arranca),
  arreglalo y pusheá sin esperar confirmación, con causa raíz en el commit.
- **Aclaración de Nico (2026-10-27): es todo autónomo.** Aprobar las corridas y abrir el holdout los decide el agente, con los
  protocolos en código (`edgelab/autopilot`, `edgelab/autopilot/holdout_apertura.py`), sin esperar a nadie. Lo único que CLAUDE.md
  deja fuera de eso es *modificar* esos protocolos y gates (FDR, mandato, archivos protegidos) y operar con dinero real.
- Errores conocidos a no repetir: `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` (por ejemplo O6: tocar un módulo embebido
  obliga a `python tools/reconstruir_kernels.py`; O12: `python tools/docs_index.py --write` antes de commitear estado).

## 2026-10-29 — Actualización Directa a Arquitectura Multi-Agente Debian v2, Cierre Ola 10 y Paridad NT8

1. **Arranque en un solo comando**: Ejecutá `python3 tools/actualizar_y_arrancar_debian_v2.py` desde la raíz del repo (`/opt/edgelab`). Ese script sincroniza sin pérdida los libros append-only (`TRIAL_REGISTRY_GLOBAL.jsonl`, `LIBRO_LORD.json`, `HOLDOUT_VENTANAS.jsonl`), verifica las `28` campañas (`6` en `CONTEO` con `ACTA_HOLDOUT.json` + `19` en `PISTAS_VIVAS`, con `0` pendientes en `DESC`), regenera el catálogo en espiral (`config/autopilot/CATALOGO_MODULOS_ESPIRAL.json` y `docs/MODULOS_ESPIRAL.md`) y deja lista la cola de auditoría en `docs/research/auditoria_corridas_20261029/COLA_AUDITORIA_DEBIAN_20261029.json`.
2. **Paridad con NinjaTrader 8 y Ejecución de Canastas de Regímenes**: Usá `edgelab/research/paridad_nt8_canastas.py` (`filtrar_solapadas_nt8`, `reporte_paridad_nt8`, `simular_canasta_regimen`) junto con `edgelab/research/analizador.py` y `nt8/strategies/EdgeLabSpiralBasketExecutor.cs` para auditar cada regla individual y cada canasta de régimen bajo semántica estricta de NinjaTrader 8 (`EntriesPerDirection = 1`, `Flat-Only`, `aplicar_tope` y `BE = 1` al cierre de `+1R`).
