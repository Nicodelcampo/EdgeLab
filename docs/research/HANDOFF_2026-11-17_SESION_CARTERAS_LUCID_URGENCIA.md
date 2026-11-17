# Handoff de la sesión 2026-11-15 → 11-17: carteras, estrategias de afuera, guardas, Lucid y urgencia contra evidencia

Estado: VIGENTE — escrito para continuar SIN acceso a la conversación que lo produjo (pedido de Nico: «que no se pierda nada de este
chat»). Rama `claude/vibrant-clarke-s9z6e2` (repo `nicodelcampo/edgelab`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. 0 edges promovidos; nada opera con dinero real.

## 1. Decisiones y preferencias de Nico (textuales o casi)
- **Cartera**: «una cosa es el umbral de quemar y otra la rentabilidad y la diversificación» → la Cartera B (T+Z+R) se sigue aparte de la
  v2/v3 (`fundedsyncstack_20261115/PREREGISTRO_CARTERA_B.md`).
- **Forward bajo demanda**: «los datos los descargo yo periódicamente» → no hay seguimiento diario (el trigger diario
  `trig_01KM6SpNJxonFeBD3bzmEHLp` está DESHABILITADO). Cuando sube datos sellados: `python tools/seguimiento_forward.py <AAAAMMDD> [commit]`.
- **Fin de semana**: «comerse el gap está bien, el del domingo no: nada abierto el fin de semana» (celdas `sin_finde` / cierre del viernes).
- **Cuenta**: estática/sin decidir del todo; Nico mira LucidFlex 25K (capturas de las 4 configuraciones, 2026-11-17).
- **«Opera demasiado poco»**: una regla de 5 operaciones por año no sirve; «mínimo 4 por mes es arbitrario, la idea es que no opere tan
  poco» → criterio único = meses para decidir el forward (información por mes), tope 60.
- **«Salteártela demuestra que hay que cambiarlo: tiene que usarse todo EdgeLab, y bien»** → guardas K27–K34 en código y CI (§4).
- **Urgencia contra evidencia**: «balancear el riesgo de que se apaguen los regímenes con el de operar con pocos días»; propuesta ACEPTADA
  («dale con la propuesta», «razonala bien»).
- **Publicar**: «subí las canastas a donde se lean y puedan auditar»; «registralo donde se lea».
- Licencias de traducciones (QuantLab, FundedSync): decisión de Nico; nosotros sólo medimos. Datos «@» de SQX no salen de SQX.

## 2. Lo que se midió (todo con pre-registro, contador global y FACTORES)
| Tema | Resultado | Dónde |
|---|---|---|
| Reels (Franklin, otros) | Franklin pasa como pista de régimen (NQ/ES desde 2020); holdout +0,27 R, NO_CONCLUYENTE; sirve como filtro de T | `docs/research/reels_20261116/` |
| QuantLab SOM (MT5) | Traducción validada 617/617 contra el Tester (Antigravity); SOM `sin_finde` NQ pasa (2020+ +0,08 R); holdout +0,16 R NO_CONCLUYENTE; no transfiere a RTY/GC/6E | `docs/research/quantlab_mt5_eas_20261116/`, `som_transfer_20261117/` |
| Programa de mejora (SOM, T, ronda 2) | Ninguna variante le gana a la base (meseta, L1–L9) | `docs/research/mejora_estrategias_20261116/CRITERIOS_Y_PLAN.md` |
| Auditoría de corridas | 5 clases de error (zona horaria M1, stop final de FundedSync, fuga de holdout a medianoche, gap, µs); 8 re-mediciones, ninguna cambia una decisión | `docs/research/auditoria_corridas_20261116/` |
| Catálogo SQX (10 fichas de Antigravity, 136 pruebas) | 0 pasan; corrida v1 descartada por sesgo pesimista del motor (enmienda 1, M1 intrabarra); pistas: Connors en índices, Turtles en oro | `docs/research/sqx_catalogo_20261117/` |
| Turtles en oro | 5,3 ops/año; réplica 2004–2010 +0,03 (no replica); 8 variantes, ninguna mejora; holdout 0 ops; FUERA del forward (196 meses para decidir) | `docs/research/turtles_oro_20261117/` |
| LucidFlex 25K «rinse» (reel @la.tradez) | Reglas oficiales verificadas; sin edge EV +$28 a +$74 por cuenta (no +$157; el documento de verificación erraba el signo); 4 configuraciones: DLL $600 + 50 % la mejor; ≈ $2.500–3.800/mes con 5 fondeadas, no $10.000 | `docs/research/propfirm_lucidflex_20261117/RESULTADO.md` |
| Canastas en Lucid | Con media «contraída» +$440 a +$1.900 por cuenta; B (T+Z+R) +$654 (T sostiene, Z sola no cobra); **la «contraída» resultó optimista (paso 2)** | mismo, `CANASTAS_LUCID.json` |
| Urgencia vs evidencia, paso 1 (catálogo) y 1b (M1 intradía 8 índices) | No hay regímenes que se apaguen en meses: deriva muy lenta (ρ ≥ 0,97), en NQ/ES/YM es fricción (bruto p 0,11); sólo el ORB tiene deriva de mercado lenta | `docs/research/urgencia_vs_evidencia_20261117/RESULTADO_PASO1*.md` |
| Paso 2 (contracción empírica) | Lo elegido por el embudo no conservó nada en réplica: b −0,26, r −0,08 desvíos/op, 37 % positivas; 104/135 campañas comparten la misma ventana de réplica → media de partida ≈ 0 | `RESULTADO_PASO2.md` |

## 3. Qué se opera (papel/forward) y cómo auditarlo
- **Documento generado**: `docs/cartera/CANASTAS_VIGENTES.md` (`tools/canastas_vigentes.py --write`; test en el cierre).
- **Página**: https://claude.ai/artifact/UKHJZyWZH1L8tr2cWtWo2s (tipo «Data», privada; se comparte desde su menú). Copia exacta de lo publicado
  (página y CSV, versión 3 del 2026-11-17) en `docs/cartera/pagina_canastas/`; si la página se pierde, se republica desde ahí.
- Forward: `tools/seguimiento_forward.py` corre cartera v2/v3, B, Franklin, SOM (TURTLES-ORO salió).

## 4. Errores cometidos y guardas que quedaron (no repetir)
`docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` §E5, K27–K34, y CLAUDE.md (Rituales):
- K27: 4 holdouts ad hoc abiertos sin potencia → `holdout_ventanas.registrar_apertura` exige `plan_potencia` (N fijo ≥ 0,8; forward ≤ 60 meses).
- K28: simulador propio sin calibrar → `config/simuladores_baseline.json` + test de calibración obligatorio.
- K29: pruebas con n < 30 inflaban BH → `escalera.separar_por_n`.
- K30/K32: pre-registro sin potencia ni antecedentes; corridas contadas por fuera → `preflight.validar_preregistro`,
  `tools/registro_global.py preregistrado`, test de CI sobre cada fila nueva del contador global.
- K31: commit con el cierre en rojo por un tubo → `tools/cierre.py && git commit` sin tubos.
- K33: spreads estimados cargados como canónicos apagaron `CostoNoMedido` en todo EdgeLab → sólo dentro de `costos.estimados_permitidos(...)`.
- K34: el cierre no veía kernels embebidos ni tests de costos/embudo → `tools/cierre.py` reconstruye kernels y corre ≈ 77 tests (≈ 1 min).

## 5. Datos: de dónde sale cada cosa (para reproducir)
- M1 de Dukascopy (CFD) exportadas de SQX: dataset Kaggle privado `nicolasbuttaro/edgelab-sqx-m1`; barras D1/H1 y `spreads.json`:
  `nicolasbuttaro/edgelab-sqx-barras` (en local, `data/sqx_barras/`, gitignorado). Zonas horarias: `*_M1_dukas` = NY+7; Russell, DAX,
  EuroStoxx, FTSE, Nikkei, LIGHTCMD y otros 11 en UTC (`m1_intradia.EN_UTC`, confirmado por Antigravity con SQX).
- Holdout sellado: `nicolasbuttaro/edgelab-holdout-sellado` (frontera única `edgelab/holdout.py`).
- COT (CFTC, Socrata legacy): copia committeada en `docs/research/sqx_catalogo_20261117/datos/COT_LEGACY_CFTC.csv.gz`.
- Agregados mensuales de la grilla M1 (paso 1b): `docs/research/urgencia_vs_evidencia_20261117/M1_VIDA.json` (kernel `edgelab-m1-vida`).
- Costos: `config/costos/costos_canonicos.json` (SI/SIL, 6J, ZB, CL, ZN, HG, MHG, NKD con spread ESTIMADO marcado; comisiones de Topstep).
- Reglas de Lucid: support.lucidtrading.com (leídas 2026-11-17); precios con cupón de las capturas de Nico.

## 6. Coordinación con Antigravity
Prompts en `docs/research/encargos_antigravity_20261117/PROMPTS.md`. Antigravity entregó: revisión de SOM con el Tester
(`quantlab_mt5_eas_20261116/REVISION_ANTIGRAVITY_20261117.md`), catálogo SQX (fichas 01–10 e INDICE con secciones E y F: blog oficial y 237
estrategias del Marketplace). Pendiente de tanda aparte: Turnaround Tuesday y Tight 5D Range Breakout (adaptar a futuros).

## 7. Pendiente (en orden)
1. **Paso 3** de `urgencia_vs_evidencia_20261117/PROPUESTA.md`: tamaño = presupuesto × evidencia (Kalman desde media ≈ 0 con el forward) ×
   fricción en R según la volatilidad del día; **paso 4**: simularlo en cuentas Lucid contra «esperar» y «fijo».
2. **Forward**: que Nico suba datos sellados de noviembre → `tools/seguimiento_forward.py <AAAAMMDD>`; sin forward, ninguna cuenta se
   justifica con números de desarrollo.
3. Verificar con Lucid: política de algoritmos («condicional» en el catálogo) y escalado de contratos de la fondeada 25K.
4. Pistas vivas para canastear (no solas): Connors en índices sin fin de semana; rupturas semanales multi-activo.
5. Spreads estimados (6J, ZB, CL, HG, SI…): medirlos.
6. Fallas preexistentes de la suite (no de esta sesión): `jsonschema` ausente en el entorno (10), tamaño del núcleo del proponente,
   `docs/CURRENT.md` con fecha vieja.
