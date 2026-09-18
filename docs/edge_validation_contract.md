# Contrato de edge válido y aplicable — gates G0–G5

**Versión canónica:** 2026-08-11  
**Enmienda vigente:** `G2-A1 calibration hardening`  
**Cambio de gates:** exige enmienda versionada y aprobación de Nico antes de correr la campaña afectada.

Este contrato implementa el referente rector de [`docs/NORTH_STAR.md`](NORTH_STAR.md). Un resultado no puede elegir su propio gate, población, estimando, nulo, horizonte ni corrección de multiplicidad.

## 0. Definiciones

- **Gate duro:** un FAIL bloquea promoción.
- **Gate blando:** exige revisión registrada; nunca se resuelve en silencio.
- **Candidato:** estrategia + población + parámetros + `bar_spec` dentro de una campaña preregistrada.
- **Estimando económico primario:**

```text
theta_trade = sum(pnl_net) / sum(n_trades)
```

- **Sesión elegible:** fila del calendario preregistrado, incluso si tuvo cero trades.
- **Cadena de estados:**

| Gate | Estado otorgado |
|---|---|
| G0 | `technically_valid` |
| G1 | `exploratory_candidate` |
| G2 | `statistically_supported` |
| G3 | `economically_viable` |
| G4 | `holdout_confirmed` |
| G5 | `paper_validated` → `live_candidate` |

Reglas duras:

- no se saltean estados;
- todo intento se cobra al presupuesto de su campaña;
- un FAIL queda en el registro append-only;
- `EDGES_DISCOVERED.md` exige al menos G2 y paridad propia de la configuración;
- `LIVE_CANDIDATES` exige G5.

---

## G0 — Integridad técnica

1. **Lineage:** `dataset_id → config_id → run_id → campaign_id → strategy_id`, con digests.
2. **Features as-of:** nada usa información posterior a `available_at`.
3. **Ejecución:** la señal se genera al cierre y sólo puede llenar en el siguiente instante ejecutable.
4. **Fills:** market/stop-market; gaps llenan al peor entre nivel y open; un limit tocado no cuenta como fill.
5. **Identidad:** `config_id` y `bar_spec` externos e inmutables.
6. **Store:** desarrollo exige `api_verified`; G2+ exige paridad suficiente para la familia.
7. **Disponibilidad live:** warmup y feed declarados.
8. **Determinismo y procedencia:** misma entrada produce mismos digests; se persisten repo, worktree, HEAD inicial/final, dirty state, diff hash, entorno y código cargado.

Falla cualquiera ⇒ no hay campaña económica.

---

## G1 — Evidencia exploratoria

Sobre desarrollo, sin abrir el holdout:

- al menos 100 trades agregados; menos ⇒ `insufficient_n`;
- expectativa neta por trade positiva bajo costos base;
- P&L sin los cinco mejores trades todavía positivo;
- ningún subperiodo aporta más de 80% del P&L neto.

Se publican siempre: bruto/neto en ticks y USD, número de trades, cuantiles, concentración top-1/5/10, MAE/MFE y resultados por subperiodo.

G1 no adjudica robustez estadística ni aplicabilidad.

---

## G2 — Robustez estadística calibrada

### G2.0 Población, estimando y evidencia

Todos los componentes usan el mismo estimando:

```text
sum_d(pnl_net_d) / sum_d(n_trades_d)
```

Queda prohibido:

- rankear por suma de P&L cuando difiere la cantidad de trades;
- promediar ratios de folds con denominadores distintos;
- eliminar sesiones sin trades;
- declarar un método de dependencia sin ejecutarlo;
- confiar en un booleano `passed` recibido.

La decisión persiste y reconstruye: campaña/run/config, hash del contrato, `null_id`, cinco gates, IC primario, evidencia DSR completa, método de multiplicidad, `N_eff`, timestamp UTC y digests.

### G2.1 Nulo específico de campaña

No existe un MCPT universal. Cada campaña define antes de outcomes:

- hipótesis nula;
- estadístico;
- nuisance preservado;
- supuesto de intercambiabilidad;
- generador y versión;
- seed;
- número de réplicas;
- `null_id` y digest.

Reducción finita unilateral:

```text
p = (1 + #{T_null >= T_observed}) / (1 + B)
```

Requisitos: `B >= 1000` y `p <= 0.05`.

`temporal_concentration_test()` permanece sólo como diagnóstico de dónde se acumuló el resultado. No es evidencia de expectativa positiva y no integra los gates.

### G2.2 IC primario

Bootstrap-t estacionario por sesión:

- `method = stationary_bootstrap_t`;
- `n_sessions >= 160`;
- cota inferior estrictamente mayor que cero;
- calendario elegible completo persistido como `calendar_sha256`.

El IC estima `theta_trade`; las réplicas agregan numerador y denominador antes de dividir.

### G2.3 PBO por ratio

CSCV con `S=8` y matriz de celdas `(pnl_net, n_trades)`:

- selección IS por ratio de totales;
- ranking OOS por ratio de totales;
- `PBO <= 0.50`;
- empates tratados conservadoramente;
- celdas sin denominador evaluable fallan cerrado.

Implementación canónica: `edgelab/research/g2_ratio.py::pbo_ratio_cscv`, expuesta por `g2_protocol.pbo_cscv` y `g2.pbo_cscv`.

### G2.4 DSR por calendario de sesiones

Gate: `DSR >= 0.95`.

Método vigente: `session_hac_bartlett_v2`:

- una observación por sesión elegible;
- sesiones sin trades como retorno exactamente cero;
- mínimo 160 sesiones;
- Sharpe no anualizado;
- varianza de largo plazo HAC Bartlett;
- lag por defecto `ceil(sqrt(n))`, acotado a `[1,n-1]`;
- factor de dependencia nunca permite `n_effective > n`;
- varianza no positiva/no finita falla cerrado;
- `n_trials_effective` proviene del manifiesto;
- `calendar_sha256`, `zero_trade_sessions`, momentos, varianzas, lag y tamaños efectivos quedan persistidos.

Identidad doble:

1. SHA-256 de la especificación matemática;
2. SHA-256 del AST canónico de `expected_max_sharpe`, `deflated_sharpe` y `deflated_sharpe_sessions`.

Cambiar cualquiera exige nueva versión y recalibración.

### G2.5 Walk-forward por ratio

Para cada fold `k >= 1`:

1. re-seleccionar con folds anteriores solamente;
2. elegir por `sum(pnl_net)/sum(n_trades)`;
3. evaluar en `k`;
4. agregar todos los folds OOS por ratio de totales.

Gate: agregado WF-OOS estrictamente positivo.

### G2.6 Sensibilidad paramétrica

Vecinos ±1 paso de grilla del ganador. Gate: mediana de expectativas netas por trade estrictamente positiva. Sin vecinos evaluables ⇒ evidencia insuficiente, no un cero inventado.

### G2.7 Composición canónica

`G2ValidationDecision.passed` exige:

- IC primario PASS;
- `campaign_null` PASS;
- `pbo` PASS;
- `dsr` PASS y coincidente con la evidencia embebida;
- `walk_forward` PASS;
- `parameter_sensitivity` PASS;
- DSR e IC con igual número de sesiones y mismo calendario;
- `N_eff` de decisión igual al `n_trials_effective` del DSR;
- semántica exacta de cada `value/threshold`.

No existe otra función ejecutable de “G2 aprobado”.

### G2.8 Calibración preregistrada

Antes de autorizar el método se ejecutan 400 paneles × 160 sesiones por escenario:

- IID gaussiano nulo;
- AR(1), `rho=0.50`, nulo;
- Student-t(5), nulo;
- 40% sesiones sin trades, nulo;
- IID nulo con `N_eff=48`;
- señal IID `mu=0.20`;
- señal AR(1) `mu=0.30`.

Sobres:

- error tipo I IID entre 1% y 9%;
- cada nulo adversarial como máximo 11%;
- aumentar multiplicidad no aumenta aprobaciones;
- potencia IID al menos 70%;
- potencia AR(1) al menos 60%;
- `n_effective` AR medio menor que IID medio.

Los valores exactos, hashes y head se guardan en el summary de CI del PR.

### G2.9 Autorización de promoción

Promotion Registry exige dos allowlists independientes:

```text
APPROVED_G2_CONTRACT_SHA256S
APPROVED_G2_IMPLEMENTATION_SHA256S
```

Ambas permanecen vacías hasta aprobación explícita de Nico. Que tests internos las simulen no autoriza producción.

---

## G3 — Robustez económica

Modelo de costos específico de instrumento e implementación: broker, exchange/clearing, tasas, spread, slippage y adverse selection.

| Escenario | Uso | Slippage por pata |
|---|---|---:|
| ideal | diagnóstico únicamente | 0 |
| base | gate principal | 1 tick |
| adverso | resistencia | 2 ticks |
| severo | estrés | 3 ticks |

Duros:

- expectativa neta base > 0;
- adverso > `-0.5 × expectativa_base`.

Se publican drawdown, turnover, ganancia por contrato-día, capacidad y sensibilidad a costos. No se transporta el costo de H1/6E a ES, NQ, YM ni a otra ejecución.

---

## G4 — Confirmación OOS

Holdout sellado: **2026-07-01 a 2026-12-31**.

Una sola apertura por candidato después de G3, con protocolo firmado. Prohibido usarlo para elegir dirección, población, nulos, costos, parámetros o `bar_spec`.

PASS:

- expectativa neta base > 0;
- al menos 30 trades;
- al menos 50% de la expectativa de desarrollo.

FAIL: neta <= 0.  
WARN: neta positiva pero <50% o n<30.

Todo acceso usa `holdout_guard.py`, declara propósito y queda en log append-only. `target_free_validation` sólo cubre integridad/paridad; nunca outcomes.

---

## G5 — Aplicabilidad

- paper/shadow durante al menos 20 sesiones o 30 señales, lo que ocurra después;
- paridad research↔live al menos 95%;
- slippage observado no peor que adverso;
- sizing y límites predeclarados;
- riesgo por trade como máximo 1% de cuenta;
- límite diario `-3R`;
- kill switch por DD >1,5× desarrollo o paridad <90% durante cinco sesiones;
- reactivación manual;
- tamaño inicial mínimo.

---

## Anti-gaming transversal

1. Gates y métrica primaria antes de outcomes.
2. Nada corrido desaparece del presupuesto.
3. Horizontes, tolerancias y superficies se publican completos.
4. Un cambio semántico crea nueva versión, hashes y calibración.
5. Un nulo publica MDE.
6. Canal direccional y no direccional siempre presentes.
7. La muerte tiene alcance exacto.
8. El holdout no reabre una hipótesis fallida.
9. Integridad y paridad preceden a interpretación.
10. Sólo Promotion Registry reconstruye y autoriza el cambio de estado.
