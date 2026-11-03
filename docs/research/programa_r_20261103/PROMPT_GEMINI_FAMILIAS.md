# Prompt para Gemini: diseñar familias nuevas de estrategias en EdgeLab

Estado: VIGENTE (2026-11-03). Para pegar en una sesión de Gemini con acceso al repo.

---

Sos un investigador cuantitativo que trabaja en el repo **EdgeLab** (rama `claude/vibrant-clarke-s9z6e2`). Tu tarea es **diseñar e
implementar 3 a 5 familias nuevas de estrategias intradía**, listas para que el embudo automático las mida. **No lances corridas en
Kaggle ni abras el holdout:** entregás código, tests y documentos en una rama nueva; las corridas las lanza otro agente después de
revisar.

## Contexto (lo que ya se sabe, medido)
- **El objetivo** (`docs/NORTH_STAR.md`) es encontrar ventajas netas, fuera de muestra, robustas y operables. El progreso se mide por
  cuánto acerca a eso, no por infraestructura.
- **Todo se mide en R:** resultado neto con fricción / riesgo inicial (entrada real a stop). En puntos se sobrestimaban reglas cuyas
  ganancias caían en stops lejanos. Ver `docs/research/MEDIR_EN_R_20261102.md`.
- **Resultado duro: de 68 familias relanzadas en R, ninguna llegó al holdout.**
  - Las mejores celdas de 44 grillas rinden **−0,042R** en su réplica no usada (maldición del ganador).
  - **Eso no depende del tamaño de la grilla:** el problema son las lógicas, no cuánto se busca.
  - Ver `docs/research/programa_r_20261103/PROGRAMA_R.md`.
- **Las reglas vivas** (canasta v5: zonas, racimos, áreas y corredores sobre NQ y ES) rinden entre +0,05 y +0,2R por operación con pocas
  operaciones por mes. Son casi independientes entre sí: el valor está en **sumar apuestas independientes** (Grinold: IR ≈ IC × √amplitud).
- **Cortar ganancias resta R:** cierre por tiempo, objetivo chico, break-even y trailing empeoraron en desarrollo y en réplica.
- **Ya hay 3 familias nuevas en curso:**
  - PAR-REL: pares NQ/ES y YM/ES;
  - LEAD-LAG: EURUSD → oro;
  - VWAP-REV: reversión al VWAP del horario regular.

  No las dupliques. Ver `docs/research/programa_r_20261103/DISENO_FAMILIAS_NUEVAS.md`.
- **Datos disponibles:**
  - futuros CME (NQ, ES, YM, GC y micros) en ticks desde agosto de 2025;
  - CFD y FX de Dukascopy desde 2023;
  - L2 sólo de julio a septiembre de 2026.
- **Ventanas:** DESC 2025-08-05 → 2026-03-31 y réplica 2026-04-01 → 2026-09-30. **Holdout desde la sesión CME del 2026-10-01: prohibido
  mirarlo, usarlo o elegir con él.**

## Qué leer antes de arrancar (en este orden)
1. `CLAUDE.md`: reglas permanentes, rituales, firewall del holdout y reglas de población, causalidad y costos.
2. `docs/NORTH_STAR.md`.
3. `docs/research/MEDIR_EN_R_20261102.md` y `docs/research/programa_r_20261103/PROGRAMA_R.md`.
4. `docs/research/programa_r_20261103/DISENO_FAMILIAS_NUEVAS.md`: el ejemplo de diseño a imitar.
5. Tres módulos de ejemplo:
   - `edgelab/research/eod_momentum.py`: plantilla simple con salida forzada por tiempo;
   - `edgelab/research/par_relativo.py`: dos instrumentos con `CONFIRMADOR`;
   - `edgelab/research/vwap_rev.py`: exclusión de eventos macro.
6. La interfaz y las reglas del motor:
   - `edgelab/research/grilla_generica.py`: `Variable`, `n_celdas`, `correr`, `simular_ops`;
   - `edgelab/research/preflight.py`: lo que se verifica antes de lanzar;
   - `edgelab/research/indicadores.py`: causalidad por disparo;
   - `config/autopilot/grillas/indicadores_agente.json`: registro `NATIVO_AGENTE`.
7. `docs/research/GUIA_GRILLA_MASIVA.md`, `docs/research_funnel_playbook.md` (ATJ) y
   `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`.
8. Para no repetir mecanismos:
   - la lista de módulos de `edgelab/research/` y `docs/MODULES.md`;
   - `python tools/existente.py buscar "<lo que querés hacer>"`.
9. Ideas y literatura:
   - `docs/research/DEEP_RESEARCH_EDGES_CUENTA_2026-08-15.md`;
   - `docs/research/EDGE_BRAIN_SSRN_BIBLIOGRAPHIC_CORTEX_20260921.md`;
   - `docs/research/DISENO_IPC_ABANICO_DE_MECANISMOS_20260927.md`;
   - el atlas `docs/research/atlas_ideas_r_20261102/`, si ya tiene resultados.

## Qué tenés que generar (por familia)
1. **Módulo `edgelab/research/<nombre>.py`** con la interfaz exacta del embudo:
   - `NOMBRE`, `INDICADORES`, `VARIABLES` (pocas: 2 o 3 perillas, entre 50 y 250 celdas por canal), `EJES_ORDINALES`, `EJECUCIONES`
     (2 a 4, triple barrera: objetivo, stop y tiempo), `BASE`, `VACIO`;
   - `disparos(ctx)` causal (sólo datos hasta la vela de decisión), `niveles` y `niveles_lote` idénticos;
   - si corresponde, `CONFIRMADOR = True`, `lineas_salida`, `TOPE_BARRAS` y `EXCLUIR_EVENTOS`;
   - un docstring con fuente (paper o evidencia), hipótesis económica y construcción.
2. **Test `tests/research/test_<nombre>.py`:** causalidad con `indicadores.causal` y `causal_por_disparo`, y forma de
   disparos y niveles (stop del lado malo, objetivo del bueno).
3. **Registro `NATIVO_AGENTE`** en `config/autopilot/grillas/indicadores_agente.json`, con el test de causalidad.
4. **Campaña `config/autopilot/grillas/campanas/<CID>-R.json`** con:
   - `"estadistico": "R"`, `"conductor": "local"` y `"activa": false`: la activa quien revisa;
   - DESC y réplica de arriba y `n_celdas_por_canal` (`grilla_generica.n_celdas`);
   - `justificacion_economica` y `como_podria_refutarse`.
5. **Línea en `docs/research/LINAJES.jsonl`:** familia nueva sin padres, o hija de una existente si comparte mecanismo, y entonces
   hereda la multiplicidad.
6. **Documento `docs/research/<carpeta>/DISENO_<NOMBRE>.md`** con:
   - mecanismo, fuente, por qué debería correlacionar poco con la cartera, población (evento contra estado) y alternativas descartadas;
   - refutación y riesgos;
   - encabezado `Estado:` (ver `docs/DOCUMENTATION_PROTOCOL.md`).
7. **Que pasen:**
   - `python -m edgelab.research.preflight edgelab.research.<nombre>`;
   - `pytest tests/research/test_<nombre>.py tests/test_existente.py`;
   - `python tools/existente.py catalogo --write` y `python tools/docs_index.py --write`.

## Hacia dónde buscar (prioridades)
- **Mecanismos con razón económica** (flujo, microestructura, cobertura, liquidez, calendario institucional, relaciones entre activos),
  no patrones gráficos sin causa.
- **Independencia de la cartera actual:** otro instrumento (GC, YM, FX, CFD), otra franja (Europa, mediodía NY, Asia tardía), otra
  dirección (reversión contra continuación) u otro horizonte.
- **Muchas operaciones por mes**, porque con pocas no hay potencia en R.
- **Objetivos amplios frente al stop.** No cortar ganancias.

## Errores y sesgos a evitar
- **Mirar el holdout** (sesiones desde el 2026-10-01) o elegir algo con él. Usar sesiones de `holdout.SESIONES_EXCLUIDAS_HOLDOUT`.
- **Mirar el futuro:**
  - nada dentro de `disparos` puede usar velas posteriores a la de decisión;
  - las normalizaciones salen de la sesión anterior o de una ventana pasada;
  - no se usa el máximo o el mínimo de la sesión en curso hasta k incluido de forma que dependa del futuro.
- **Grillas grandes o perillas «por las dudas»:** más perillas significa menos potencia y más maldición del ganador.
- **Elegir por P&L máximo de una celda,** o elegir parámetros mirando resultados (ni desarrollo ni réplica): los parámetros se fijan antes,
  con razón.
- **Duplicar mecanismos que ya existen** (zonas, racimos, áreas U1, corredores CVGAP, gaps GAP-RTH, EOD-MOM, OTR930, ASIA-BOS,
  KALMAN-FADE, TAU, PAR-REL, LEAD-LAG, VWAP-REV): usá `tools/existente.py buscar`.
- **Copiar funciones:** importá las existentes. `tests/test_existente.py` falla con copias.
- **Costos propios:** se usan sólo los canónicos (`edgelab/costos.py`). Tampoco se transportan costos ni resultados entre instrumentos.
- **Stops de 1 o 2 ticks:** dan R extremos. Declará un piso de riesgo.
- **Break-even, trailing o salidas muy cortas por defecto:** restaron R en todo lo medido.
- **Congelar una población sin enumerar el espacio de eventos y estados** (regla de `CLAUDE.md`).
- **Tocar** los gates, el FDR, el protocolo del holdout, los archivos protegidos o `edgelab/holdout.py`. Son decisiones humanas.
- **Afirmar resultados:** no corrés nada, así que no reportes rentabilidad. Entregá diseño y código verificado.

## Entrega
- **Rama nueva `gemini/familias-<fecha>`,** con commits chicos por familia. **No hagas push a la rama de trabajo** ni actives campañas.
- **Un resumen final** con:
  - cada familia: mecanismo, fuente, celdas, por qué es independiente de la cartera y cómo se refuta;
  - lo que el preflight y los tests verificaron;
  - las dudas abiertas.
