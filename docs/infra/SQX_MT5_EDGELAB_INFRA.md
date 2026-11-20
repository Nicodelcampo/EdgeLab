# Infraestructura Claude ↔ EdgeLab ↔ StrategyQuant X ↔ MetaTrader 5

Estado: PROPUESTA VIGENTE (2026-11-14). Referente: ganar dinero neto en cuentas (prop firms de futuros o de CFD; la cuenta la elige
la esperanza medida, no la preferencia). Cliente MCP: `tools/mcp_cliente.py`.

## Piezas y quién hace qué
| Pieza | Dónde | Rol |
|---|---|---|
| Claude (nube, esta sesión o el Debian) | contenedor + repo | Orquesta: diseña, pre-registra, cuenta pruebas, lanza en SQX/Kaggle, analiza, decide con las reglas de EdgeLab |
| EdgeLab | repo + Kaggle | Inferencia (nulo de búsqueda, SPA/Romano-Wolf, LORD++), costos canónicos, motor único sobre ticks, holdout, propfirm EV |
| StrategyQuant X | laptop, MCP `:8080` | Generador masivo (Builder), robustez barata (MC, What-If, multi-mercado), carteras, exportación a MQL5 |
| MetaTrader 5 | laptop, MCP terminal `:22346`, MetaEditor `:22345` | Datos del bróker de la prop firm, compilación de EAs, Strategy Tester (paridad), demo forward, cuentas reales |

## Conexiones
- Nube → SQX: túnel ngrok con basic auth (secreto de red del host del túnel en el entorno de la nube; nunca en el repo ni en el chat).
- Nube → MT5: mismo esquema, segundo endpoint (o un proxy local que sirva `/sqx` y `/mt5` bajo un solo túnel). En MT5
  (Tools > Options > MCP): **trading desactivado** para el acceso remoto; sólo lectura (cuenta, posiciones, historial, símbolos).
- SQX ↔ MT5: `import_mt5_data` (datos del bróker dentro de SQX) y, del lado del asistente Q de SQX, `/mcp add mt5 …`.
- Túneles prendidos sólo mientras se trabaja. `execute_shell`/`run_python` de SQX y las órdenes de MT5 quedan bloqueados en el
  cliente (`--permitir-riesgo` sólo con OK humano). Operar con dinero real: sólo humanos (CLAUDE.md).

## Flujo de una estrategia (embudo con compuertas de dinero)
1. **Pre-registro + contador** (EdgeLab): mecanismo, bloques permitidos, activos, tramos, proyecto nulo hermano, total a generar.
2. **Build** (SQX, por MCP): proyecto por mecanismo + nulo (entrada aleatoria, mismas salidas). Se registra el total generado.
3. **Robustez barata** (SQX): MC retest/manipulación, What-If, mercados adicionales; sólo sobre las sobrevivientes.
4. **Inferencia** (EdgeLab): trades exportados (`get_strategy_trades csv`) → R neto, SPA/Romano-Wolf con K = total generado,
   sub-bloques, comparación con el nulo del proyecto.
5. **Tramos no usados** (una vez): reciente sin mirar en SQX; pseudo-réplica ago-2025 → sep-2026 (SQX en CFD + EdgeLab en futuros).
6. **Cartera + cuenta** (EdgeLab `edgelab/propfirm/`): Monte Carlo del P&L diario contra las reglas de cada cuenta relevada
   (futuros que admiten algoritmos; CFD con EAs y tenencia overnight/fin de semana) → esperanza por intento y por mes con costo
   de evaluación y tasa de COBRO; se elige cuenta y tamaño que la maximizan.
7. **Paridad** (MT5): SQX genera el EA (`get_strategy_source` engine MetaTrader5) → MetaEditor compila → Strategy Tester con datos del
   bróker real; trades contra los de SQX (misma regla, otro motor). Diferencia → causa raíz antes de seguir.
8. **Demo forward** (MT5): el EA corre en demo; Claude lee el historial por MCP en una tarea programada y lo evalúa con
   `edgelab/funnel/secuencial.py` (válido mirando cada semana). Kill switch pre-declarado.
9. **Desafío chico** (humano): sólo si 6–8 pasan.

## Datos
- SQX: Dukascopy M1 de 27 activos (descarga completa 2026-11-14). Los 10 originales quedaron con barras hasta el 2026-10-01 y el holdout
  empieza con la sesión CME del 1-oct (apertura 2026-09-30 22:00 UTC): **todo proyecto de SQX fija su rango de fechas con fin ≤ 2026-09-29**
  (regla mecánica, sin mirar esas barras); la pseudo-réplica termina el 29-sep. Construcción hasta 2019;
  OOS de SQX 2020–2023; reciente sin mirar 2024 → jul-2025; pseudo-réplica ago-2025 → sep-2026. Bonos y Russell (desde 2017–2019) sólo
  como mercados adicionales.
- MT5: datos del bróker de la cuenta objetivo, importables a SQX para backtest con sus spreads reales.

## Repo (estado compartido entre computadoras)
`sqx/corridas/<id>/manifest.json` (máquina, versión, datos con rango y huella, configuración `.cfx`, semilla, total generado,
nulo), `estrategias/*.sqx`, `trades/*.csv`; `mt5/ea/*.mq5` (generados), `mt5/forward/<cuenta>/historial.csv`. Nada con licencia «@»,
ningún secreto.

## Herramientas
- `tools/mcp_cliente.py sqx|mt5 <herramienta> '<json>'`: cliente MCP con guardas.
- `tools/sqx_corrida.py preparar IDEA SIMBOLO TF [--plantilla ...]`: clona el proyecto base (Build + 9 Retests de SQX), fija datos y costos
  del instrumento con tope 2026-09-29 y escribe `sqx/corridas/<id>/manifest.json`; `lanzar` exige el manifiesto committeado; `estado`
  vuelca el total generado al contador global; `exportar` baja trades (CSV) y pseudocódigo de cada estrategia al repo.
- `tools/sqx_nulo.py crear SIMBOLO TF SEMILLA`: serie sintética (bloques de semanas o de barras del propio activo) subida a SQX como
  símbolo `NULO_*`; el mismo Builder corre sobre ella para el umbral del nulo de la búsqueda.
- Contrato de calidad (qué estrategia vale la pena): `docs/infra/CONTRATO_CALIDAD_ESTRATEGIAS.md`.
- `tools/ideas.py`: banco de ideas multi-fuente y lote balanceado (de ahí sale el IDEA de cada corrida).

## Pendiente
- MT5: activar su MCP con trading apagado y exponerlo (segundo túnel o proxy).
- Relevar reglas oficiales de prop firms de CFD (FTMO Swing, FundedNext, The5ers, Blue Guardian, FundingPips) y sumarlas a `config/propfirms/`.
- Módulo puente `edgelab/sqx_puente.py` (trades de SQX → R neto, SPA, cartera) cuando haya la primera corrida.
