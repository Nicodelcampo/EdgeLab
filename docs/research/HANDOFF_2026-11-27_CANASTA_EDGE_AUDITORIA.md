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

## 12. Revisión de Claude del trabajo de Antigravity del 2026-11-27 (tarde)
Antigravity sumó cinco commits a esta rama; su índice es `HANDOFF_ANTIGRAVITY_2026-11-27.md`. Incluyen:
- la auditoría del PR;
- CRIPTO-PIT v2 y v3;
- los frentes ortogonales (FundedSync O y Global_VolComp en M1 de Dukascopy);
- SUPERCARTERA-V2 con CSCV en Kaggle.

La revisión de Claude está en `auditoria_claude_20261127/REVISION_CLAUDE.md` (commit `a6c643e4`).

**Se acepta:**
- la custodia del holdout (verificada sobre las 4 series publicadas);
- el defecto de neutralización del XSMOM, heredado de la regla del 26-nov;
- la invalidez de los `=F` de Yahoo (no toca la tendencia en ETF);
- el decaimiento de Carril 2 después de 2018;
- que FundedSync O con 1 micro empeora la cartera.

**Se objeta:**
- Global_VolComp es la misma señal que C2_VZ/EVRP: correlación mensual 0,48 con su versión de ES/NQ, y t 1,37 en la muestra completa;
- la REP de cripto quedó iterada entre v1, v2 y v3;
- `HRP_Weekly` es idéntica a EQ;
- la potencia del pozo sin CME (0,54 con el efecto × 0,7) está sobreestimada.

K27 sigue bloqueando toda apertura.

En ese commit Claude también corrigió las fallas de CI de los commits de Antigravity:
- funciones copiadas;
- catálogo de herramientas;
- líneas K55/K56;
- `Estado:`;
- enlaces locales de Windows;
- índice y `ESTADO_VIVO.md`.

Factor nuevo: `F-GLOBAL-VOLCOMP-M1DK-B`.

## 13. Trabajo de Claude del 2026-11-27 (tarde), después de la §12
| Tema | Documento | Commit |
|---|---|---|
| Revisión de la apertura conjunta HOLDOUT A5 sin CME | `holdout_a5_nocme_20261127/REVISION_CLAUDE.md` | `47bfd37f` |
| Arreglos de CI sobre commits de Antigravity | `REMEDICIONES_CANDIDATAS.md` regenerado y 4 factores `-B` | `b2a9faef`, `fac1dbc8` |
| Ratios de bonos argentinos (video de Gus Lucioni) | `biblioteca_ideas_20261028/RATIOS_BONOS_LUCIONI_20261126_RESUMEN.md`, `…_TRANSCRIPCION.md` | `ca8e4375` |
| Fuentes de datos y costos de los ratios de bonos | `biblioteca_ideas_20261028/RATIOS_BONOS_FUENTES_DE_DATOS_20261127.md` | `54dc28a8` |
| Curvas de lo que confirma y de lo que va a forward | `curvas_forward_20261127/CURVAS.md`, `tools/curvas_confirma_forward.py` | `62c680a0` |

**Revisión de la apertura conjunta:**
- Procedimiento conforme: K27 citado, pre-registro anterior al resultado, TERMINAL sellado.
- Carril 2 confirma limpio: p 0,0077, sobrevive Holm sobre las 5 familias.
- El pozo confirma por BH q 0,10, pero lo arrastra Carril 2.
- Macro, cripto v3 y OFI quedan NO_CONCLUYENTE y gastaron su holdout con potencia de 0,10 a 0,21.

**Ratios de bonos:** no se midió nada.
- Falta el intradía histórico. Open BYMA Data (PyOBD) todavía no se probó: el permiso para instalarlo se denegó en el entorno.
- Abrir este mercado, las fuentes y el uso de una cuenta propia es decisión de Nico.

**Para auditar con prioridad:**
1. Si la multiplicidad de la apertura conjunta se lee bien: 9 cortes rotulados CONFIRMA contra 5 familias independientes.
2. Si el escalado a 10 % de volatilidad con el desvío de DESC de las curvas es el mismo que usa `SERIES_HOLDOUT_A5_NOCME_MENSUAL`.

## 14. Auditoría forense Antigravity sobre los 22+ commits de Claude (2026-11-27)
Auditoria completa y correcciones en código/registros ejecutadas tras hacer fast-forward a `2f79ce6d`:

| Frente | Hallazgo verificado | Corrección / Evidencia |
|---|---|---|
| `CRIPTO-V3-2019` | `stats_serie(cana[ok])` incluyó 3 meses vacíos (`2020-01..03` = `0,0` por `<10` monedas), bajando `t` de `1,73` a `1,64`. En 2020 y HOLDOUT `XSMOM` gana y `BAB` falla. | `python tools/cripto_v3_2019.py auditar`: 6m activos `t=1,73 (p=0,0414) -> CONFIRMA`. Factor `-B`. |
| `CONFIANZA-SIN-FORWARD` (`DSR` / H1 / H3) | Doble estándar en `DSR_HAIRCUT.json`: no deflactaba HOLDOUT de Carril 2 pero sí los de Macro (`N=7`) y Cripto v3 (`N=33`). En H1, `C2_VBB` usaba `^VIX` de EE. UU. (sin VBB `t=3,84`); `DAX` TR cae igual post-2009 (`0,093`) que PR (`0,256`); H3 `DESC` difiere de `canasta_amplia` por 279 ops censuradas en frontera. | `python tools/confianza_sin_forward.py dsr && auditar_h1_h3` → `DSR_HAIRCUT.json` simétrico + `AUDITORIA_H1_H3.json`. Factor `-B`. |
| `TRZ-EXTRANJEROS` | Fricción fija `1,5455 pts` aplicada a precios `2.200–4.500` de `2010–2019` infló el costo `3,5–5x` (`0,12–0,14 R/op`). | `python tools/trz_extranjeros.py auditar_friccion` → `AUDITORIA_FRICCION.json`: `T+R` neto prop `t=−1,37` (`Sh=−0,34`), bruto `2020–26` sigue `≈0` en Europa (`NO_REPETIR` se sostiene en fondo). Factor `-B`. |
| `BONOS-ROTACION` / `RATIOS` | Rebalanceo lineal continuo sin banda muerta (`11%/día`) + spreads post-cierre (`19:07` BA) destruyeron un bruto DESC positivo; `GD30/AL30` REP sigue `~0` bruto. | Addenda en ambos `RESULTADO.md`; factor `-B` acota `NO_REPETIR`. |
| Fuentes intradía bonos AR | Verificación en vivo Chrome + APIs: **TradingView descartado** (`1m–4h` `disabled` en bonos `BCBA`); sin puntas L1/L2 históricas para particulares; quedan **BYMADATA Prefer** (12m al segundo en Excel, 7d gratis) y **Primary `getTrades (external=true)`** (si hay cuenta ALyC). | `RATIOS_BONOS_FUENTES_DE_DATOS_20261127.md` §9 (descartados TradingView, Rava, PPI intradía, EODHD, Open BYMA/`PyOBD`, `data912`, Yahoo, TwelveData y BYMA institucional para personas físicas). |

**Revisión Claude de §14 (2026-11-27):**
- Se aceptan las correcciones de fricción de TRZ (sensibilidad: el veredicto no cambia), del DSR sobre un HOLDOUT único, de H1 sin VBB y del
  alcance de BONOS-ROTACION.
- **No se acepta el CONFIRMA de CRIPTO-V3-2019:** sale de sacar los meses en cero después de ver el resultado, sobre 6 meses. El veredicto
  pre-registrado sigue NO_CONCLUYENTE. Detalle en `cripto_v3_2019_20261127/RESULTADO.md` §«Revisión Claude».

## 15. Cierre del 27/28-nov: errores, guardas, virtudes y siguiente paso
- **Errores convertidos en guardas (K58–K64):** `ERRORES_Y_GUARDAS_AGENTE_DEBIAN_20261026.md` y `LEER_ANTES_DE_CADA_CORRIDA.md` §8 (v5).
  - Guardas en código: alineación horaria de fuentes (`edgelab/research/alineacion_horaria.py`), `registro_global.py` sin
    consolidación accidental, máscara de ventanas que tocan meses sellados.
  - Guardas en la guía: costo en pb del destino, ningún cambio de muestra post hoc, insumos locales al transferir, verificar una fuente
    de datos antes de recomendar pagarla.
- **Virtudes que se reutilizan:** ATJ-28 a ATJ-31 en `docs/research_funnel_playbook.md`. Las dos primeras quedan también como
  PALANCA_DE_DISENO en FACTORES (`F-PALANCA-CONFIANZA-SIN-FORWARD`, `F-PALANCA-CALIBRAR-CIRCUITO-DE-DATOS`).
- **Siguiente paso, sin bonos:** `PLAN_ESPIRAL_20261127.md`. Recomendado: guardas (hechas), Carril 2 en EMD, Carril 2 con volatilidad
  local, serie canónica de Carril 2; después el mecanismo de T por ETF apalancados.
- **Bonos:** `biblioteca_ideas_20261028/OPERACIONES_AMIGO_AL29_AL30_MATRIZ_20261127.md` y `RATIOS_BONOS_FUENTES_DE_DATOS_20261127.md`
  §6–§9.
  - Grabador diario: `tools/bonos_masella_grabar.py`; la rueda del 2026-11-27 ya está grabada.
  - Para el intradía histórico: BYMADATA Prefer o la API de Primary con cuenta. TradingView no sirve (K62).

## 16. Avance en Espiral Fase 1 (Antigravity, 2026-11-27)

Trabajo nuevo **estrictamente en `DESC + REP` (`< 2026-10-01`)**, con `HOLDOUT A5` (63m / 18m) y `TERMINAL` **100 % sellados** y pre-registrado en `TRIAL_REGISTRY_GLOBAL.jsonl` antes de correr:

1. **`CRIPTO-FUNDING-CARRY-20261127` (`tools/cripto_funding_carry_20261127.py`, `226` perpetuos USDT-M PIT, `2021 → 2026-09`, `39m DESC + 12m REP = 51m DR`, 20 pb RT + funding real):**
   - `CFC1_FundingCarry_14d_Stag5d`: `DESC Sh=-0,05 | REP Sh=-0,64 | DR Sh=-0,20 (t=-0,41)` → **FALLA**.
   - `CFC2_FundingShock_Rev_Stag5d`: `DESC Sh=+0,03 | REP Sh=+0,17 | DR Sh=+0,06 (t=+0,12)` → **FALLA**.
   - `CFC3_CarryFilt_XSMOM_Stag5d`: `DESC Sh=+1,24 | REP Sh=-1,03 | DR Sh=+0,68 (t=+1,40) | corr_CR3=+0,441 | corr_OFI=+0,518` → colapsa en REP.
   - `CFC_Canasta_InvVol` (`100% CFC3`): `+257,3 USD/m, Sh=0,68, p=0,0802`. Veredicto honesto: `NO_REPETIR` para carry puro y shock 8h; próximo frente cripto candidato verificado `HTTP 200`: `data.binance.vision/data/futures/um/daily/metrics` (OI + Top-Trader L/S).

2. **`M1-RELVAL-EVENTOS-20261127` (`tools/m1_relval_eventos_20261127.py`, `2008-01 → 2026-09`, `129m DESC + 38m REP = 167m DR`, `159` eventos FOMC):**
   - `MRV1_CrossIdx_Disp_5d`: `DR Sh=-0,344 (t=-1,28)` → **FALLA**.
   - `MRV2_OvnVsRTH_RelVal`: `DR Sh=-0,452 (t=-1,69)` → **FALLA**.
   - `MRV4_TrueM1_VRP_ESNQGC`: bruto `Sh=0,713`, pero **exceso vs igual exposición BH `=-0,205 (t=-0,77)`** → excluido limpiamente.
   - **`MRV3_PreFOMC_Drift_M1`**: `DESC Sh=0,733 (t=2,40) | REP Sh=0,577 (t=1,03) | DR Sh=0,685 (t=2,56, p=0,0053) | 2x=0,618 | MDD@10%=-7,70% | Calmar=0,89 | corr_Carril2=-0,038 | corr_RP4=-0,207` → **SOBREVIVIENTE ORTOGONAL**.

3. **`MACRO-CTA-VRP-20261127` (`tools/macro_cta_vrp_20261127.py`, `2006-01 → 2026-09`, `186m DR`):**
   - Excluidos `MVC2_VIX_TermStruct_FTQ` (`DR Sh=0,070`) y `MVC3_Rates_RealYield_Carry` (`DR Sh=-0,299`).
   - **`MVC1_CTA_NonEq_MultiHorizon`**: `DESC Sh=0,425 | REP Sh=0,422 | DR Sh=0,426 (t=1,68, p=0,0468) | corr_Carril2=-0,036 | corr_RP4=+0,046 | corr_SPY=-0,256` (alfa direccional ortogonal genuino).
   - **`MVC4_MoreiraMuir_VolManaged`** (`1/var_21d` en `TLT, IEF, GLD, DBC, HYG`): `DESC Sh=0,578 | REP Sh=1,495 | DR Sh=0,766 (t=3,02) | 2x=0,731 | MDD=-17,22% | Calmar=0,45 | corr_Carril2=+0,101 | corr_RP4=+0,475` — aclaración honesta: **NO supera a la referencia estática `1/vol` sobre los mismos 5 ETFs (`Sh=0,838`, `MDD=-19,43%`, `Calmar=0,43`)**.
   - **`MVC_Canasta_InvVol`** (`59,72% MVC1 + 40,28% MVC4`): `DESC Sh=0,663 (t=2,30) | REP Sh=1,138 (t=2,13) | DR 186m Sh=0,773 (t=3,04, p=0,0012; 0,693 t=2,59 en el solape 167m con MRV) | 2x=0,667 | MDD@10%=-15,18% | 81,0% años+ | corr_Carril2=+0,042 | corr_RP4=+0,336`.

4. **Síntesis de Espiral (`tools/espiral_sintesis_20261127.py` → `espiral_sintesis_20261127/RESUMEN.md`):**
   - **`Pool_Nuevo_Sellado_2F_EQ` (`50% MVC + 50% MRV`, `167m` DR, 63m HOLDOUT 100% sellado):** `corr(MVC, MRV)=+0,021`; `DESC Sh=0,937 (t=3,07) | REP Sh=1,150 (t=2,05) | DR Sh=0,964 (t=3,59, p=0,0002) | MDD@10%=-10,29% | Calmar=0,94` | Poder K27 (63m): `0,461` (`0,7x`) y `0,714` (`1,0x`).
   - **`Arquitectura_20y_4F_EQ` (`Carril2 + RP4 + MVC + MRV`, `167m` DR):** `DR Sh=1,211 (t=4,52) | MDD@10%=-9,02% | Calmar=1,34 | N_eff PCA = 3,70 / 4,00`.
   - **`Arquitectura_Multi_6F_EQ_51m` (`4F_20y + Cripto_v3 + Cripto_OFI`, `51m` DR):** `DESC Sh=1,368 | REP Sh=4,018 | DR Sh=1,749 (t=3,61) | MDD@10%=-6,55% | Calmar=2,67`.

## 17. Avance en Espiral Fase 2 (Antigravity, 2026-11-27 — listo para auditoría de Claude)

Ejecutados los `4` pilares pre-registrados y contados (K32/K51/K58/K60/K61/K64) + la reconciliación canónica `#7`:

1. **`FX-MACRO-FIX-20261127` (`tools/fx_macro_fix_20261127.py`, `186m` DESC+REP, HOLDOUT 63m sellado):**
   - **Hallazgo de huso horario K58 en `data/m1dk/*.csv`:** Dukascopy sella en **`America/New_York + 7h`** (desfase vs UTC de `120 min` en enero y **`180 min`** ya en la semana del `18–22` de marzo por DST US antes de Europa). Tras restar `7h` → `America/New_York` → UTC, `exigir_alineada` vs `GC_M1_nonadj_utc.parquet` da desfase `0` con `corr = 0,9255` (ene), `0,9863` (mar) y `0,8548` (jul).
   - `FXF1_FX_Clock_Session_EURJPY`: **`DR Sh=-0,938 (t=-3,69)`** (`1002x/año`) → falla neta severa.
   - `FXF2_Gold_AsianOvn_vs_NY`: `DR Sh=+0,306 (t=+1,20)`, `2x=-0,409` (`501x/año`); la pierna `xau_overnight_long` da `Sh=1,281 (t=5,04)` mientras el short COMEX RTH da `+0,068` pero la doble fricción diaria anula al stress `2x`.
   - **`FXF3_Treasury_MonthEnd_Rebal`** (`TLT/IEF` `24,2x/año`): **`DESC Sh=0,427 | REP Sh=0,254 | DR Sh=0,394 (t=1,55)`**, ortogonal a todo (`corr_MVC=-0,023`, `corr_MRV3=-0,141`, `corr_SPY=+0,014`).
   - `FXF4_NonEq_XS_Mom_12ETFs`: `DESC=+0,370`, **`REP=-1,112`**, `DR=-0,001`. Canasta `FXF_Canasta_InvVol`: `REP=-0,737`, `DR=+0,265`.

2. **`CARRIL2-EMD-20261127` (`tools/carril2_emd_20261127.py`, `EMD` M1 NT8 `2006–2026-09`, K33 estimado base `0,4378` pts):**
   - `nucleo_5` todo (`249m`): `Regla Sh=0,611 (t=2,78)` vs `Control N Sh=0,095`, **`diff = +0,443 (t=2,02, p=0,0218)`**.
   - Corte pre-registrado **`2009+` (`213m`, `#3` del plan):** `nucleo_5` `diff = +0,220 (t=0,93)` (`NO_CONCLUYENTE`); `todas_9` `diff = +0,097 (t=0,41)`; `2019+` `-0,217`. Valida el mecanismo en instrumento virgen y confirma la reducción de tamaño en vivo esperada (`0,4–0,6`).

3. **`CRIPTO-XSMOM-SPOT-20261127` (`tools/cripto_xsmom_spot_2017_2019.py`, `64` pares Binance Spot PIT, `2017-10 → 2019-08`, `20 pb RT`, muestra K60 intacta):**
   - Sin excluir ceros de `2017-10..2018-06` (`< 10` pares elegibles): `CR3_XSMOM_21d_Stag5d Sh=0,44 (t=0,61)`, `ex-2017 (20m) Sh=0,47 (t=0,61)`; `BetaNeut Sh=0,45 (t=0,62)`. **`NO_CONCLUYENTE`** por potencia (`Q2-2019 -2.557 USD`), consistente en signo positivo ex-2017 (`short_leg=+0,34`, `long_leg=-0,06`).

4. **`CARRIL2-VOL-LOCAL-20261127` (`#4`) + `CARRIL2_CANONICA_H3` (`#7`) + Síntesis Fase 2 (`espiral_fase2_sintesis_20261127/RESUMEN.md`):**
   - Corrección K61 (`ASX200/^AXVI`, `Dow/^VXD`, `Russell2000/^RVX`, `GC/^GVZ`; Yahoo `^V2TX/^VHSI/^JNIV/^VDAX` dan 404 bajo K62): **`C2_VBB`** sube de `-0,075` con `^VIX` a **`+0,427 (t=1,73, diff=+0,589 t=2,32)`** y `C2_EVRP_1F` a `+0,614 (t=2,80)`. **Hallazgo K58/K61 crítico:** en `confianza_sin_forward`, `ASX200` (`16:00 AEST = 02:00 NY`) usaba CBOE `^VIX` del mismo día (`16:15 NY`, **`14h` después**), creando un falso `Sh=2,797 (t=12,11)` en `C2_VZ` que cae a `0,163 (t=0,71)` con `^AXVI` simultáneo.
   - Reconciliación `#7` (`canasta_amplia_20261127/SERIE_CANONICA_H3.md`): `SERIE_CANONICA_CARRIL2` sin censura de frontera da `DESC=1,068 (2249 ops)`, `REP=1,256 (589 ops)`, `HOLDOUT=1,057 (902 ops)`, `TODO 249m=1,098 (t=5,00)`.
   - Síntesis Fase 2 (`167m` comunes DR): **`N_eff PCA 5F = 4,62 / 5,00`** (`C2, RP4, MVC, MRV3, FXF3`); **`Pool_Sellado_3F_EQ (MVC+MRV+FXF3, 63m HO intacto)` = `DR Sh=1,060 (t=3,95)`** (`K27 1,0x=0,783`, `40/40/20: Sh=1,071, K27 1,0x=0,791`); `Arquitectura_5F_20y` = **`DR Sh=1,250 (t=4,66)`**.
