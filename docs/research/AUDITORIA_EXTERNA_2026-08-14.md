# Auditoría externa de contexto y referente — 2026-08-14

**Autor:** auditor externo (sandbox de Notion; sin acceso a la máquina local ni a datos adjudicadores).
**Objeto:** segunda pasada de razonamiento e investigación sobre el estado del proyecto, a pedido de Nico. Lee: el repo completo (ramas, commits, docs rectores, specs, `nt8/`, kernels Python, artefactos sellados F2.7–F2.10 / AVOLT / L3), los PDF operativos del 12-08 y 14-08, dos `.cs` recibidos por chat, y literatura pública (sección de fuentes al pie).
**Firewall:** este documento no computó outcomes, ni P&L, ni tocó el holdout. No promueve, no relaja gates, no decide merges. Todo número citado del repo se verificó contra el artefacto o doc referenciado.
**Referente:** `docs/NORTH_STAR.md` (sha256 del cuerpo: `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`).

---

## 1. Verificación de los `.cs` recibidos (regla de oro)

| Archivo | sha1 git-blob | Veredicto |
|---|---|---|
| `aVolClusterPOI.cs` | `d512d91a606d41609b21ef244c896ead1dc52a10` tras normalizar EOL | ✅ Byte-idéntico al blob sellado v0.5 de `nt8/aVolClusterPOI.cs`. El adjunto trae BOM + 1 CRLF suelto (los "EOL mixtos" ya registrados). Para NT8: checkout CRLF del repo, como siempre. |
| `BigTrap2.cs` | `ee984f6ef4d92827101eaf56a8a60d0a43ab53f6` (CRLF puro, 62.401 B) | ⚠️ Es v2.5.2 por marcadores internos (meta `version=2.5.2`, `LogEventAt` en los 7 sitios de evento, drenaje en `State.Terminated`), pero **no coincide con ningún blob del repo**: `fix/bigtrap2-v252-tick-export` = `dbf226138af813bb035e08e339ba5dadc4b3a910` (v2.5.2 completa) y research/audit = `78f6909dcb75f8aa78dafb354ca4cf851eaa2093` (era v2.5.1: el helper `LogEventAt` existe pero los sitios de export no se cambiaron). Hay una diferencia de contenido real, de localización desconocida desde acá. Registrada como **P-08**. |

Regla derivada: ningún CSV exportado desde un `.cs` sin identidad sellada tiene procedencia completa. El diff exacto es un `git diff` local contra `fix/bigtrap2-v252-tick-export`.

---

## 2. Material Kaggle: re-enlace al programa vigente

El mapeo del *Kaggle panorama* §14 (2026-08-12) quedó desactualizado por el pivot: el programa vigente (handoff 2026-08-14) es R0→R4 + ES + baja resolución de ticks + rangos. Re-enlace:

| Prueba vigente | Recurso | Uso |
|---|---|---|
| BT2 / aVol en tick:5/10 (absorción) | DSLOB/ABIDES (LOB sintético con regímenes etiquetados) | Calibración truth-known: plantar zonas con absorción conocida y verificar recuperación **por resolución** antes de cualquier endpoint. |
| | `welford` (PyPI) | sigma60 online numéricamente estable por resolución (el warmup de sigma60 fue el delta 1005→988). |
| | Lección JS 2024 (responders con lags exactos) | Ya internalizada: medir la construcción del target antes de modelar (tick:25). |
| Rangos (L3 PreRange) | Estimadores OHLC (Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang; `jasonstrimpel/volatility-trading`) | σ causal intradía para cualquier variante del nulo de rango que normalice por volatilidad. Parkinson es un estimador de rango por construcción. |
| | G-Research (target residualizado + CPCV, discusión 302445) | El nulo condicional implementado por un host. |
| Absorción: covariables candidatas | Canon imbalance Optiver Close (dobletes, tripletes, `market_urgency`); DRW (`order_imbalance`, `trade_imbalance`, repo Kalyan1210); mapa IC/IR de las 384 features de Lingjun (repo Ovenchan) | Candidatas al feature_manifest. **Caveat vigente: los ticks NT8 son prints, no profundidad en reposo** — sólo transfieren features de trades. Toda covariable nueva al matcher cambia la positividad: contra F2.6 primero. |
| Transversal | Curva de especificación + PBO + DSR + CPCV + Romano-Wolf | Barrer indicadores × resoluciones × tests es el jardín de senderos que la curva pre-registrada hace honesto. |
| | Semper Augustus (`scaomath/kaggle-jane-street`) | Modelo congelado: 34% de amplitud en LB vivo; dispersión entre semillas 7,4× en el fold difícil → ≥3 semillas pre-registradas y min/mediana/máx en todo reporte. |
| | Optiver RV como banco de pruebas del stack (M4) | Gobernanza completa contra un problema de respuesta conocida; no toca M0. |
| Replicación externa / M0 | CME Liquidity Tool (oficial, gratis, 6E **y ES** desde 2017); `choweric/cme-es` (ES 2000-2022) | Verificar cobertura, formato y licencia antes de usar (nivel snippet). Relevante con el pivot a ES. |

No transferible: Jane Street 2021 (features anonimizadas, cero semántica; su métrica de utilidad mete la regla de trading dentro del detector = Fase 4, cerrada); features de profundidad en reposo (inexisten en prints NT8); Databento (pago: decisión "no" vigente); cómputo Kaggle de ticks reales (`NO_UPLOAD` se mantiene).

---

## 3. VWAP / SMA / EMA como features de contexto

Jerarquía honesta de evidencia (de mayor a menor):

1. **VWAP como benchmark institucional es real**: literatura de ejecución óptima (Boyd et al., *VWAP Optimal Execution*, Stanford). El mecanismo (order flow institucional benchmarked a VWAP) es la base plausible de cualquier efecto. Mismo criterio que GEX: mecanismo primero, señal después.
2. **El patrón "contexto primero, señal después" tiene referente directo**: SSRN 6454659 (2026) — reversión al VWAP en FX *condicionada* a agotamiento de momentum (ADX). Es la hipótesis de Nico con otro nombre.
3. **Medias móviles como filtro de régimen**: la evidencia fuerte es momentum de series de tiempo a 1–12 meses (Moskowitz, Ooi, Pedersen 2012, JFE); Kim, Tse y Wald (2016) muestran que buena parte es *volatility scaling*. Las reglas de MA de Brock-Lakonishok-LeBaron (1992) **murieron out-of-sample** (replicación con 25 años frescos; Sullivan-Timmermann-White sobre data-snooping). La distancia entre MA corta/larga predice la cross-section diaria de acciones (Avramov, Kaplanski, Subrahmanyam 2021). En 175 backtests públicos, un filtro EMA-200 **dañó sistemáticamente estrategias de breakout en rango** (eliminó ~50% de las señales, incluidas ganadoras contra-tendencia): un filtro de contexto es una hipótesis de interacción que puede ir en cualquier dirección — se mide, no se asume.
4. **A nivel intradía/minuto no existe evidencia pública fuerte** de que VWAP/SMA/EMA condicionen nada por sí mismas. Territorio sin ocupar: el valor se produce midiendo acá, no importando.
5. **Implementación pública de referencia**: repo `WhiteRabbit-TB/vwap-mean-reversion` — mean-reversion a bandas de VWAP sobre ES tick data con bootstrap, condicionamiento por régimen y métricas con ejecución. Referencia de diseño; verificar antes de citar en spec (nivel repo).

**Cómo entra al proyecto sin violar el referente:**

- No es familia nueva de indicadores (F9 pausada, decisión sellada). Entra como **covariable de régimen / estrato pre-registrado** de una campaña existente — el estatuto de `sigma60_ticks` o del día de la semana en F1.1-régimen. Cada covariable declara su ledger as-of.
- El test ya existe: la carrera de primer pasaje de F2.7 **estratificada** (¿Δ cambia sobre/bajo el VWAP de sesión, o con SMA/EMA alineadas?) es target-free si se mide sobre la carrera, no sobre P&L. F2.10 ya midió un objeto de esta familia (ventana t+1/t+2).
- La trampa de potencia (números del propio proyecto, L3 §8): con ~210 sesiones el MDE es un split ~63/37; condicionar por régimen **corta el n de cada celda**. Pocas covariables, declaradas, con la curva de especificación como techo.
- Simetría útil: F2.9 descubrió que el sello fuerte es el barato (S1 = vela extrema), no el kernel. VWAP/MA son el mismo tipo de objeto (sello barato de contexto). La pregunta correcta: "¿contexto × sello suma sobre sello solo?", con contraste pareado por sesión.

---

## 4. Ancla académica para la línea de rangos (L3)

Lo que la primera pasada no cubrió y cambia el encuadre de L3:

- **Gao, Han, Li, Zhou (2018, JFE 129(2):394–414), *Market intraday momentum***: el retorno de la primera media hora predice el de la última media hora; significativo dentro y fuera de muestra, con ganancia económica en market timing. **La ventana de apertura transporta información real en índices de equity.**
- Li, Sakkas, Urquhart (2022, J. Financial Markets): momentum intradía en 16 mercados desarrollados (global).
- Iwanaga y Sakemoto (2025, SSRN): **reversión** intradía (overnight → primera media hora), más fuerte en alta volatilidad, **más débil post-2010** — régimen-dependiente, exactamente el patrón que L3 debe medir y no asumir.
- ORB: Holmberg, Lönnbark, Lundström (2012, Umeå 845) reporta rentabilidad positiva del opening range breakout con su diseño; Syu et al. (2018, IEEE Access) lo extiende a futuros de índice con M1. Ambos son **diseño-dependientes y sensibles a costos** — y la tesis de Heldens (NYSE 2000–2015) encuentra que el momentum intradía **no cubre costos de transacción**: el recordatorio exacto de G3.
- Barardehi, Bogousslavsky, Muravyev (RFS 2021): descomposición día/noche de momentum y reversión — marco para pensar ETH vs RTH, que es una decisión de población de L3.

Qué apoya esto y qué no: **apoya que la apertura es informativa**; no apoya ninguna ventana específica (08:12–09:12 sigue siendo `a_priori_external` con el techo de procedencia que el protocolo impone), ni dirección (momentum vs reversión es régimen-dependiente), ni ninguna tasa de barrido (la tautología ya adjudicada: 72,38% vs 68,33% browniano, p=0,103 → NO_ADJUDICABLE). L3 sigue bloqueada por dos insumos: CSV de fechas macro 08:30 y la zona horaria de los archivos; y el set limpio de T5 es forward-only desde 2026-08-14, mínimo 60 sesiones.

---

## 5. Fortalezas contra el referente

1. **Gobernanza con dientes**: firewall de holdout en código + log append-only; INC-006 revertido aunque el sello lo movió el propio dueño; NORTH_STAR con autocita y test de regresión.
2. **El sistema rechaza falsos edges — la mitad del referente**: D1/D2 de F2.7 cazados a costo cero antes de correr; la tautología del 72,38% adjudicada NO_ADJUDICABLE; el dictamen AVOLT que puso en cuarentena un paquete P2 FAIL y tumbó la lectura "descartar aVol" (MDE ~0,13 vs efecto esperado ~0,15: sin potencia; ausencia de evidencia ≠ evidencia de ausencia).
3. **Contabilidad honesta**: `EDGES_DISCOVERED.md` dice "ninguno" sin maquillaje; correcciones formales en público (CF-1/CF-2); xfail estrictos que no esconden drift.
4. **Maquinaria reutilizable**: carrera de primer pasaje con nulo exacto sin estimar σ, HAC Bartlett, contrastes pareados por sesión, placebos con piso dentro de `decide()`, caps de procedencia. L3 heredó todo eso.
5. **Ingeniería curada por incidentes**: grilla entera de ticks, close en medios ticks, un archivo por resolución y por corrida, export OBS con piso para barrer selección offline.

---

## 6. Debilidades (= lo contrario al referente) y su saldo

**D1. La energía está en la capa de medios; la cadena geometría → información → P&L → edge neto está detenida en geometría.** F4 constitucional jamás ejecutada; cero candidatos en G0→G5; y lo más fuerte medido (F2.7, Δ≈+0,048) resultó no ser del objeto: F2.8 (control sin zona ≈ igual), F2.9 (S1 ≥ kernel: K0−S1 = −0,017, IC excluye cero). Lo que sobrevive es una morfología (vela extrema → ventana asimétrica de 1–2 barras), no un instrumento. **Saldo:** próxima campaña según el propio acta de cierre: aVolCellPOI2 sola, target-free, nulo propio; F4 con manifiesto presentado a Nico antes de tocar retornos (la regla STOP ya lo exige).

**D2. La señal no es portable y el ES está en el límite de potencia.** Baseline ES 09-26: 35–49, p≈0,16, signo al revés que 6E, con n=111 zonas (`ABSTAIN_ALIGNMENT`: no es identidad NT8). El overlap P2 de junio: 67/87 `ABSTAIN_P2`. **Saldo:** cerrar P2 de aVol por la ruta del dictamen (H2 mismo contrato declarado en meta; H3 lookback caliente o evaluación post-calentamiento; H4 bloques vs deslizante — respondida a nivel C#: bloques disjuntos de 10; queda verificar la implementación del replay); más P-09.

**D3. La paridad pendiente es el campo minado exacto del plan de baja resolución.** tick:10 tuvo 81,78% de mismatch pre-fix; K=50 el bug de ancla; v2.5.1 el cuelgue; v2.5.2 la atribución temporal. Cada resolución necesita su propio gate P1/P2 — no hay atajo. Y hoy el `.cs` local no tiene identidad sellada (P-08). **Saldo:** tanda de oráculos por resolución según la campaña pre-registrada del contrato de paridad §6, con el `.cs` canónico decidido antes.

**D4. El loop auditoría-en-serie es el cuello de botella** (F2→F2.4: 6 commits, 4 auditorías, cero medición). **Saldo:** correr la curva de especificación descriptiva (~500 celdas, ~2 h en 4 cores, `outcomes_accessed=false`) — declarada "el único trabajo desbloqueado que produce información decisiva". Sigue sin correrse.

**D5. P-05 (CI sin verificación remota) y P-07/M0 (licencia) abiertas.** Saldo: un run remoto registrado + `DATA_LICENSE_DECISION.md` (decisión humana).

**D6. Ramas divergentes sin mergear** (`fix/g2-a1-*`, `research/ym-prerange-session-window`, `docs/lux-imb-source-correction`) — registradas como P-10. La "regla de una sola rama" se viola en la práctica. Saldo: una decisión por rama.

**D7. Falta la capa que conecta con el dinero: costos por instrumento + reglas de prop firm.** La regla "no transportar costos de 6E" existe pero no hay manifiestos de costos ES/YM/NQ; `execution_simulator_spec.md` no modela trailing drawdown en tiempo real (Apex) vs EOD (Topstep), reglas de consistencia ni límite diario — y esas reglas cambian la viabilidad de una estrategia tanto como su expectancy. **Saldo:** manifiesto de costos por instrumento + wrapper de reglas prop en G3/G5, antes de cualquier peso real.

**D8. La potencia es el techo duro** (L3: 55/45 exige ~1.250 sesiones; YM+NQ+ES valen ~1,3 activos por factor común). Saldo: apuntar a efectos grandes/estructurales, acumular forward-only, declarar UNDERPOWERED por construcción antes que forzar.

**D9. Visibilidad del ejecutor local (nueva en esta pasada).** El patrón se repitió: informes que citan artefactos nunca versionados (`runs/f25_*`), HEADs truncados o inexistentes (F2.8, F2.9, F2.10, AVOLT H8), un JSON sellado que no cierra (P-09). El diseño Workers (DESIGN_ONLY_NOT_DEPLOYED) ataca exactamente este dolor (`repoState` + `githubPush` + `specSha256`); W0 (plan + habilitación + deploy) es decisión humana pendiente. Además: el inventario de `nt8/README.md` quedó desactualizado para BigTrap2 (lista v2.1; la línea v2.5.x existe en ramas) — se cierra con P-08.

---

## 7. El objetivo $5.000/mes: matemática honesta

Con fuentes públicas (2025–2026):

- 5–10% pasa evaluaciones; **~7% de quienes compran un challenge reciben algún payout** (dataset FPFX vía Finance Magnates: 300.000 cuentas, 100.000 traders, 10 firms, sep-2024). Topstep publica los suyos (2025, oficiales): 16,8% de Combines completados; 51,8% de participantes fondeados al menos una vez; **33,3% de los fondeados recibieron payout**; 0,71% Express→Live.
- Aritmética del objetivo: ~$5k/mes ≈ 2–3 cuentas de $100k al ~3% mensual con split 80–90% (ejemplo documentado: 3×$100k al 3%/80% = $7,2k/mes). El capital deja de ser el cuello de botella: **lo que liga es tener UNA estrategia neta adjudicada**, y hoy `EDGES_DISCOVERED.md` dice "ninguno".
- Las reglas prop cambian el diseño: trailing drawdown en tiempo real vs EOD, consistencia (ningún día >20–50% del profit), límite diario. Una curva viable en cuenta propia puede ser inviable en prop por su forma, no por su media. Eso se modela en la capa D7, no se descubre pagando resets.
- Conclusión auditada: el objetivo es alcanzable en principio y la vía (prop + diversificación + varios bots) es la correcta; la distancia es la cadena del referente: sello → información (F4) → una monetización → G3 → G4 (una apertura) → G5 paper → live. En meses de gates, no semanas. Nada de esto promete rentabilidad futura (regla del referente).

---

## 8. Qué NO autoriza este documento

- No abre F4 ni ninguna búsqueda sobre retornos/P&L (la regla STOP exige manifiesto + OK de Nico).
- No promueve S1, aVol, BT2, L3 ni ningún objeto a ningún estado de la cadena G0–G5.
- No habilita upload de datos (M0/P-07 intactos; `NO_UPLOAD` se mantiene).
- No decide merges (P-10 es registro, no decisión), no cambia specs selladas ni gates, no toca kernels ni oráculos.
- No autoriza ninguna afirmación sobre rentabilidad futura.

---

Aporte al referente: deja escrita, contra fuentes verificadas, la evidencia externa que aplica a cada línea vigente (contexto VWAP/MA, ancla de momentum intradía para rangos, canon de absorción), nombra los nueve puntos donde el proyecto se aleja de su propio referente con su saldo propuesto, y registra las decisiones humanas que los destraban (P-08, P-09, P-10, W0, M0). No mide nada nuevo: reduce la distancia de dirección, no la de evidencia.

---

### Fuentes (web, verificadas 2026-08-14)

- Moskowitz, Ooi, Pedersen (2012), *Time Series Momentum*, JFE — https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Kim, Tse, Wald (2016), *Time series momentum and volatility scaling*, J. Financial Markets — https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html
- Replicación OOS de reglas técnicas (25 años frescos) — https://www.pure.ed.ac.uk/ws/files/18967583/predictability_of_the_simple_technical_trading_rules.pdf
- Sullivan, Timmermann, White (1999), *Data-Snooping, Technical Trading Rule Performance, and the Bootstrap*, J. Finance — https://eprints.lse.ac.uk/119144/1/dp303.pdf
- Avramov, Kaplanski, Subrahmanyam (2021), MA distance — https://www.sciencedirect.com/science/article/abs/pii/S1042443124001318
- Bhatti (2026), *Momentum Exhaustion and Fair Value Reversion: ADX-conditioned VWAP in FX* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6454659
- Boyd et al., *VWAP Optimal Execution* — http://web.stanford.edu/~boyd/papers/pdf/vwap_opt_exec.pdf
- Gao, Han, Li, Zhou (2018), *Market intraday momentum*, JFE 129(2) — https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351
- Li, Sakkas, Urquhart (2022), *Intraday time series momentum: global evidence*, J. Financial Markets — vía https://ideas.repec.org/a/eee/jfinec/v142y2021i1p377-403.html
- Iwanaga, Sakemoto (2025), *Intraday Time Series Reversal* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5807282
- Holmberg, Lönnbark, Lundström (2012), *Assessing the profitability of intraday opening range breakout strategies* — http://www.usbe.umu.se/digitalAssets/102/102002_ues845.pdf
- Syu et al. (2018), *Timely Opening Range Breakout on Index Futures Markets*, IEEE Access — https://ieeexplore.ieee.org/document/8641124
- Heldens (2017), *Intraday price reversals and momentum: evidence from NYSE* (tesis) — http://arno.uvt.nl/show.cgi?fid=144554
- Barardehi, Bogousslavsky, Muravyev (2021), *What Drives Momentum and Reversal?*, RFS — https://academic.oup.com/rfs/advance-article/doi/10.1093/rfs/hhag036/8626980
- WhiteRabbit-TB/vwap-mean-reversion (repo de referencia, ES tick) — https://github.com/WhiteRabbit-TB/vwap-mean-reversion
- Quant Signals, *EMA 200 Trend Filter (175 backtests)* — https://quant-signals.com/ema-200-trend-filter
- Pass rates / payouts: https://alexfirdaus.com/prop-firm-pass-rate (dataset FPFX vía Finance Magnates), https://www.quantvps.com/blog/prop-firm-statistics, https://topstep.com/topstep-prop (estadísticas oficiales 2025)
- Matemática de ingresos fondeados: https://www.tradezella.com/blog/prop-firm-trading, https://funded.now/guides/how-much-do-funded-traders-make
