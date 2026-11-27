# Handoff 2026-11-27: auditoría de Antigravity, frentes, simulador de cuentas, estado del edge y canasta amplia

Estado: VIGENTE — índice para auditar, sin depender del chat, todo el trabajo de Claude del 2026-11-27 (rama `claude/vibrant-clarke-s9z6e2`,
PR #203, commits `8d7706d4` → `48dfb5c8`, 32 commits sobre `bbe30dd0` de Antigravity). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## 0. Cómo leer esto (orden sugerido)
1. `docs/research/ESTADO_DEL_EDGE_20261127.md`: dónde está la ventaja, qué la confirma y qué la mejora (síntesis).
2. `docs/research/canasta_amplia_20261127/RESULTADO.md`: lo último (el N diluye; Carril 2 como canasta).
3. Las secciones 2 a 8 de abajo, en orden cronológico. Cada una dice qué se preguntó, qué dio, dónde está y cómo se reproduce.
4. La sección 9: correcciones que Claude hizo sobre sí mismo (para auditar primero).
5. La sección 10: decisiones abiertas de Nico.

**Regla de auditoría.** Todo resultado cita su pre-registro (o registro posterior) y su fila en `docs/research/TRIAL_REGISTRY_GLOBAL.jsonl`.
Para reproducir: correr la herramienta indicada con el comando del encabezado de cada archivo. Los datos locales (`data/`, gitignorado) se
obtienen así:
- `python tools/datos.py traer M1NT8` (futuros M1 de NT8);
- `python tools/cripto_pit.py universo` y `velas` (Binance público);
- `python tools/tendencia_no_equity.py bajar` (Yahoo).

## 1. Contador de pruebas de la sesión (todas en `TRIAL_REGISTRY_GLOBAL.jsonl`)
| Campaña | Familia | Pruebas | Tipo |
|---|---|---|---|
| `AUDITORIA-CARTERA-AG-20261126/*` (4 filas) | FUNDEDSYNC, MULTIACTIVO_MECANISMOS, CRIPTO_BINANCE, CANASTA_CORRELACION | 21 + 120 + 7 + 21 | **posterior** (corridas de Antigravity sin pre-registro) |
| `PRESET-DIVERSIFICADA-20261127` | CANASTA_CORRELACION | 1 | pre-registro |
| `CRIPTO-PIT-20261127` | CRIPTO_BINANCE | 4 | pre-registro |
| `TENDENCIA-NO-EQUITY-20261127` | TENDENCIA_NO_EQUITY (nueva) | 1 | pre-registro |
| `CRIPTO-PIT-TOP8-20261127` | CRIPTO_BINANCE | 2 | pre-registro (adenda diagnóstica) |
| `PRESET-DIVERSIFICADA-DLL-20261127` | CANASTA_CORRELACION | 1 | pre-registro (adenda) |
| `PRESET-DIVERSIFICADA-DLL-SENS-20261127` | CANASTA_CORRELACION | 1 | pre-registro (sensibilidad) |
| `CANASTA-AMPLIA-20261127` | CANASTA_AMPLIA (nueva) | 9 | **posterior** (explorado en la sesión antes de registrar) |
| `CANASTA-AMPLIA-HOLDOUT-C2-20261127` | CARRIL2_A5 | 1 | pre-registro (apertura **bloqueada**, no corrida) |

Linajes nuevos en `docs/research/LINAJES.jsonl`: `MULTIACTIVO_MECANISMOS`, `CRIPTO_BINANCE`, `TENDENCIA_NO_EQUITY`, `CANASTA_AMPLIA`.

## 2. Revisión de la auditoría de Antigravity del 2026-11-26
- **Documento:** `docs/research/auditoria_cartera_20261126/REVISION_CLAUDE.md` (con dos bloques de corrección al inicio).
- **Registro posterior:** `docs/research/auditoria_cartera_20261126/REGISTRO_POSTERIOR.md` (169 pruebas contadas después).
- **Calibración K28 de los simuladores de props de Antigravity:** `tests/research/test_auditoria_cartera_mc20k.py` (registrados en
  `config/simuladores_baseline.json`). Hacen lo que dicen sus reglas; su retiro difiere del de `tools/cartera_lucid.py`.
- **Lo que quedó tras dos revisiones:**
  - **Aceptado:** F, C y O no tienen motor NT8; O no opera desde 2025-10.
  - **Aceptado con matiz:** a igual volatilidad, la regla de cartera de Claude empata en Sharpe y baja la caída ≈ 35 % (el 55–60 % del
    primer informe era tamaño).
  - **Corregido (Claude se había pasado):**
    - los stops ATR de R/Z/N/W vienen de `fundedsync_prop_opt_20261122` (DESC → REP), no del holdout;
    - `Regla_V2_Clean` usa los motores operables;
    - el barrido de Kaggle tiene persistencia por encima del azar (Fisher p 0,014), sin potencia.
  - **En pie:**
    - las series de los estudios de cartera leyeron los meses HOLDOUT A5 de FundedSync;
    - la ventaja cripto de 8 monedas era selección de monedas (§4).

## 3. Cartera NT8: reloj, paridad y preset (frentes 1 y 6)
- **Error encontrado y corregido:** `FundedSyncMath.ResolveTz` (`nt8/strategies/EdgeLabFundedSyncCore.cs`) caía en silencio a UTC si
  el id de Windows no existía (mono/Linux). Ahora usa el id IANA o falla. Commit `b633bff7`. En NT8/Windows no cambia nada.
- **Arnés de paridad:** `tools/nt8_cartera_paridad.py` (compila con mono `mcs`).
  - Cartera de 10: `docs/research/preset_diversificada_20261127/paridad_completa/PARIDAD.json`. Las estrategias con corrida NT8
    emparejan ≥ 98,8 %, con 0 descuadres. Franklin y ES5N empatan la operación pero no el precio (el arnés llena mejor).
  - N no tiene corrida NT8: 950 operaciones en el arnés contra 881 en Python.
- **Preset `Diversificada`** (10 estrategias: Intradía + N + SOMEOD), en `nt8/strategies/EdgeLabCartera.cs` (enum 4, CRLF preservado).
- **Pre-registro y resultado:** `docs/research/preset_diversificada_20261127/PREREGISTRO.md` y `RESULTADO.md` (§1–§6).

## 4. Frente 2: cripto con universo punto en el tiempo
- `docs/research/cripto_pit_20261127/`: `PREREGISTRO.md`, `RESULTADO.md`, `ADENDA_DIAGNOSTICO_TOP8.md`, `RESULTADO_TOP8.md` y
  `UNIVERSO_PIT.csv` (239 monedas, incluidas las dadas de baja).
- Herramienta: `tools/cripto_pit.py` (`universo`, `velas`, `medir [--top 8]`). Reglas congeladas de
  `tools/cartera_cripto_binance.py`, con tres cambios declarados (elegibilidad, escala 8/n, ranking entre elegibles).
- **Resultado:**
  - 1/N con 20 pb: DESC+REP t 1,21; REP −$84/mes.
  - Top-8 punto en el tiempo: REP −$28 (20 pb) y ≈ $0 (10 pb). La REP positiva de Antigravity (+$382) era supervivencia.
  - Queda viva sin evidencia y con el HOLDOUT A5 sellado.

## 5. Frente 3: tendencia mensual no-equity
- `docs/research/tendencia_no_equity_20261127/` (`PREREGISTRO.md`, `RESULTADO.md`, `RESULTADO.json`). Herramienta:
  `tools/tendencia_no_equity.py`.
- TSMOM en 14 ETFs:
  - DESC +0,29 %/mes, t 0,96, MDE Sharpe 0,76;
  - la ganancia viene de energía y metales, y pierde en 2021–2024.
- Sin evidencia: REP no leída, HOLDOUT sellado.

## 6. Simulador de cuentas: DLL intradía (K57)
- **Error encontrado:** `tools/cartera_lucid.py::_sim_cuenta` (y `tools/lucid_canastas.py::_sim`) aplicaban el DLL al cierre del día;
  Lucid liquida al tocarlo durante el día.
- **Corrección:**
  - `tools/intradia_min_cartera.py`: camino minuto a minuto por estrategia, que cierra exacto contra la suma de operaciones;
  - `_sim_cuenta(xmin=…)`;
  - `simular --intradia [--precio extremo|cierre] [--cuentas]`;
  - calibración: `tests/research/test_cartera_lucid_calibracion.py::test_sim_cuenta_dll_sobre_minimo_intradia`;
  - guarda K57 en `docs/research/ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md`.
- **Pre-registros:** `docs/research/preset_diversificada_20261127/ADENDA_DLL_INTRADIA.md` (con la sección de sensibilidad).
- **Resultado (§5–§6 de `RESULTADO.md`, `VENTAJA_POR_MES*.csv`, `SENSIBILIDAD_DLL_150K.csv`):**
  - en la 150K, 2 micros por estrategia es estable (+$217–234/mes de ventaja);
  - 4 micros da entre +$213 y +$309 según la cota;
  - 25K y 50K no tienen plan sensato.
- Métrica: «ventaja por mes» = valor esperado por mes con la media contraída menos el de sin ventaja. La P(cobrar) por intento era
  demasiado estricta para el criterio de frecuencia de Nico.
- **Pedido posterior de Nico:** «enfocate en el edge real, no en cuentas». Las cuentas quedaron en pausa.

## 7. Estado del edge real
- `docs/research/ESTADO_DEL_EDGE_20261127.md`, §1–§6.
  - La información por mes ubica la ventaja medible en T, R, V y Z de NQ. Sumar estrategias débiles alarga la confirmación.
  - Tiempo de confirmación por forward: ≈ 13–15 meses con el efecto de desarrollo y ≈ 27–33 con la mitad. Lo fija la señal/ruido; el
    e-proceso ya apuesta cerca de Kelly.
  - El vendedor de FundedSync vende desde el **2026-09-01** (dato de Nico). Todo 2020–2026 está dentro de su muestra; la adenda de
    `verif_vendedor_20261120/RESULTADO.md` que suponía 2025 quedó corregida.
  - Evidencia conjunta de 12 candidatas por bloque A5 (§5): cartera REP t 2,05 y HOLDOUT t 2,71.

## 8. Canasta amplia («el n diluye las exigencias», Nico)
- `docs/research/canasta_amplia_20261127/`: `REGISTRO_POSTERIOR.md`, `EXPLORACION.json`, `RESULTADO.md`,
  `PREREGISTRO_HOLDOUT_CARRIL2.md` y `PESOS_CARRIL2_SELLADA.json`.
- Herramienta: `tools/canasta_amplia.py explorar` (reproduce todo) y `holdout_carril2` (**se niega a correr** sin la autorización de
  Nico en `AUTORIZACION_K27`).
- **Resultado:**
  - pozo de 40 series: encogimiento DESC → REP 0,43 y DESC → HOLDOUT 0,70;
  - Carril 2 como canasta: REP t 3,11, robusta sin cada regla;
  - ampliar la intradía con más de lo mismo empeora: la caída se duplica.
- **Palanca de diseño:** el N diluye sólo con mecanismos distintos y descorrelacionados.

## 9. Correcciones que Claude hizo sobre su propio trabajo (auditar primero)
| Afirmación original | Corrección | Dónde |
|---|---|---|
| «Stops ATR elegidos mirando el holdout» | Vienen de `fundedsync_prop_opt_20261122` | `REVISION_CLAUDE.md`, corrección 1 |
| «Barrido de Kaggle al nivel del azar» | Fisher p 0,014; persistencia sobre todo de negativos | ídem, corrección 3 |
| «La regla de Claude no supera a igual riesgo» | Empata en Sharpe y baja la caída ≈ 35 % | ídem, corrección 4 |
| «La 150K sigue con 8 estrategias» (P por intento) | Por ventaja/mes, 10 ≥ 8 | `preset_diversificada…/RESULTADO.md` §5 |
| «Más tamaño rinde más» (DLL al cierre) | Inflado; 2 micros es estable | §6 y K57 |
| «Inflado 35–40 %» (sólo cota pesimista) | 6–35 % con las dos cotas | §6, sensibilidad |
| «13 meses fuera de muestra del vendedor» | El vendedor vende desde 2026-09: no hay | `ESTADO_DEL_EDGE…` §2b |
| «La ventaja cripto era selección» (sin probar) | Verificado con el top-8 | `cripto_pit…/RESULTADO_TOP8.md` |

## 10. Decisiones abiertas de Nico
1. **Levantar K27 para la apertura del HOLDOUT A5 de la canasta Carril 2 sellada.**
   - 63 meses, potencia 0,25–0,63.
   - Sin la apertura, la única confirmación es un forward de ≈ 100 meses.
2. **Plan de la LucidFlex 150K** (en pausa): 1 o 2 micros por estrategia, 8 o 10 estrategias.
3. **Datos forward:** subida semanal del M1 de NT8 o del USATECH sellado a Kaggle. Sin eso no avanza la confirmación de T, R y Z.
4. **NT8:** corrida del Strategy Analyzer con `Diversificada` desde 2024-01 (paridad de N; precio de Franklin y ES5N).
5. **Fuentes nuevas:** aprobar para research los ticks de `liquid_tick_v1` o datos de opciones, para buscar ventajas nuevas.

## 11. Qué revisar con más cuidado (riesgos conocidos)
- Las 40 series del pozo y la lista de 12 candidatas vienen de campañas previas: hay selección de sobrevivientes, y sus meses HOLDOUT A5 ya
  estaban mirados. Sólo el HOLDOUT de Carril 2 sin VZ ni EVRP, y los de Kaggle y cripto, siguen sellados.
- `tools/canasta_amplia.py::_ops_carril2_holdout` reutiliza `_senales`, `_senales2` y `sqx_catalogo.simular` de `tools/carril2.py`.
  **Verificado:** `python tools/canasta_amplia.py verificar_motor` reproduce las operaciones DESC/REP de
  `carril2_extension_20261126/OPS_LOTE*.csv.gz` para las 16 series: mismo número y mismo R (diferencia 0 al sexto decimal). No lee meses
  sellados.
- La sensibilidad del DLL usa dos cotas (extremo adverso por vela y cierre de vela); la verdad está entre ambas.
- Los resultados de cuentas usan las reglas de Lucid verificadas entre el 17 y el 22-nov (`config/propfirms/catalogo_20261122_multiprop.json`).

Aporte al referente: deja todo el trabajo del 2026-11-27 auditable por otro agente. Cada resultado tiene su pre-registro o registro
posterior, su herramienta reproducible y sus correcciones explícitas, y las decisiones que faltan quedan separadas.
