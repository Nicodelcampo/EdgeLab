# Enmienda candidata G2 — estimando, nulo y autoridad

> **Estado: CANDIDATA, NO APROBADA PARA PROMOVER.**
>
> Fecha: 2026-08-03. Incidente: `INC-007`.
>
> Esta enmienda reemplazará la semántica de G2 de
> `docs/edge_validation_contract.md` sólo cuando su implementación, cobertura
> sintética y tests sean verificados. Hasta entonces,
> `APPROVED_G2_CONTRACT_SHA256S` permanece vacío.

## 1. Motivo

El G2 vigente compone pruebas que no responden a la misma pregunta:

- `mcpt()` ordena sesiones y mide concentración en la primera mitad; no prueba
  expectativa positiva. Un efecto uniforme positivo produce `p=1` porque la
  suma no cambia al permutar bloques.
- PBO usa suma por partición y CSCV `S=8`, mientras el stack legado usa Sharpe y
  `S=10`.
- walk-forward selecciona por suma, favoreciendo actividad sobre expectativa.
- DSR aprueba con cualquier valor estrictamente mayor que cero.
- EXPLORE declara expectativa neta por trade, pero no existe una decisión G2
  persistida que fuerce esa métrica en todos los gates.

No se corrige cambiando un umbral aislado. Se fija primero la pregunta económica
y después se obliga a cada gate a declarar cómo se relaciona con ella.

## 2. Pregunta y estimando canónicos

### 2.1 Estimando primario

Para una campaña, universo y política de ejecución sellados:

```text
theta_trade = sum_j pnl_neto_j / sum_j 1
```

Cada `pnl_neto_j`:

- pertenece a un trade identificable;
- incluye fricción completa dentro del valor;
- respeta `available_at` y política de fills;
- se liga a `campaign_id`, `run_id`, `config_id` y `trade_id`.

El umbral económico primario es:

```text
theta_trade > 0
```

No se resta fricción nuevamente del lado derecho.

### 2.2 Unidad de dependencia

La unidad de dependencia es la **sesión operativa/día**, no el trade. El
manifiesto debe declarar:

- timezone de sesión;
- calendario;
- regla de corte;
- universo completo de sesiones elegibles, incluidas las que generaron cero
  trades.

Para la sesión `d`:

```text
u_d = sum_i pnl_neto_di
v_d = n_trades_d
```

Y el estimando es el ratio de totales:

```text
theta_trade = sum_d u_d / sum_d v_d
```

### 2.3 Lo que queda prohibido como primaria

```text
mean_d(u_d / v_d)
mean(PnL_diario)
sum(PnL) sin dividir por trades
Sharpe
win rate
p_favorable
```

Son descriptivas o estimandos distintos. Pueden registrarse, nunca sustituir
silenciosamente `theta_trade`.

## 3. Inferencia por clusters

### 3.1 Réplica bootstrap

Una réplica selecciona sesiones completas con reemplazo desde el universo
predeclarado. Para los índices sorteados `d*`:

```text
theta_star = sum_d* u_d* / sum_d* v_d*
```

Nunca se promedian medias diarias. Las sesiones con cero trades se conservan
porque la tasa de actividad es parte del proceso generador. Una réplica con
denominador cero es inválida y se registra; no se convierte en cero.

### 3.2 Método de intervalo

El método final —percentil, basic o studentized— no se elige por conveniencia.
Debe aprobar una batería de cobertura sintética que reproduzca:

- tamaños de cluster desiguales;
- correlación entre `v_d` y `u_d`;
- heterocedasticidad;
- colas gruesas;
- concentración de P&L;
- sesiones sin trades;
- dependencia serial entre sesiones.

La allowlist del contrato no se abre hasta que exista un método con cobertura
aceptable bajo escenarios declarados. Los tests de `np.mean` no son evidencia
suficiente para el estimando ratio.

## 4. Nulo: no existe un MCPT universal

Cada campaña debe persistir:

```text
null_id
null_generator_version
null_hypothesis
exchangeability_assumption
seed
n_replicates
test_statistic
cluster_unit
generator_digest
```

Llamar “por bloques” a una permutación no la vuelve válida. El generador debe
preservar exactamente lo que la hipótesis nula considera nuisance y romper sólo
la relación causal que se prueba.

### 4.1 EXPLORE / anclas de zona

Nulo candidato:

- dentro de cada sesión y estrato predeclarado;
- conserva el número real de señales de esa sesión;
- reemplaza cada ancla real por anclas placebo elegibles;
- recalcula outcomes con la misma geometría, horizonte, fills y fricción;
- recomputa `theta_trade` como ratio de totales.

Esto no debe llamarse “permutación” si muestrea con reemplazo. El nombre
sancionado será `placebo_resample_within_session`.

### 4.2 Estrategias completas

Cuando la señal depende del camino o de estados recursivos, barajar P&L ya
materializado no representa el nulo. El generador debe rerunear la estrategia
sobre señales/caminos nulos o declarar que no existe un nulo defendible. En ese
caso G2 queda no evaluado y falla cerrado.

### 4.3 Resultado del test

El estadístico observado y cada réplica usan la misma métrica primaria. El
p-valor conserva la corrección finita:

```text
p = (1 + count(T_null >= T_obs)) / (1 + B)
```

La cola y la corrección por multiplicidad se sellan antes de correr.

## 5. PBO canónico

Se conserva `CSCV_S = 8` por continuidad contractual, sujeto a pruebas de
sensibilidad declaradas antes de resultados. La entrada deja de ser una matriz
de escalares ambiguos.

Cada celda `bloque × config` contiene:

```text
(sum_pnl_neto, n_trades)
```

En cada split:

- IS selecciona el config que maximiza `sum(sum_pnl) / sum(n_trades)`;
- OOS rankea ese mismo config con el mismo ratio;
- una celda o split sin denominador suficiente queda no evaluable;
- se persisten particiones, ranking, empates y política de desempate.

El PBO no demuestra expectativa positiva: mide fragilidad del procedimiento de
selección. Es un veto complementario, no sustituto del IC primario.

## 6. DSR canónico

El umbral contractual cambia de:

```text
DSR > 0
```

a:

```text
DSR >= 0.95
```

El cálculo debe declarar:

- escala no anualizada;
- unidad observacional usada;
- `N_eff` completo del manifiesto;
- skew y kurtosis;
- tratamiento de dependencia serial.

Como DSR responde a performance ajustada por riesgo y multiplicidad, no
reemplaza el IC de `theta_trade`. Hasta validar una implementación compatible
con dependencia por sesión, DSR no puede emitir PASS formal aunque produzca un
número.

## 7. Walk-forward canónico

Los folds naturales siguen siendo contratos ordenados. Para cada fold `k`:

1. usar sólo folds anteriores;
2. seleccionar config por expectativa neta por trade acumulada:
   `sum_pnl_previo / n_trades_previos`;
3. evaluar en `k` sin reoptimizar;
4. agregar todo el OOS como:
   `sum_pnl_oos / n_trades_oos`.

Se prohíbe seleccionar o aprobar por suma de P&L. El detalle persiste trades,
numerador, denominador, config elegida y folds de entrenamiento.

## 8. Sensibilidad paramétrica

Para vecinos ±1 paso:

- cada expectancy es `sum_pnl / n_trades`;
- la mediana de vecinos debe ser > 0;
- se persisten vecinos faltantes y denominadores;
- cero vecinos evaluables implica FAIL, no `None` interpretable;
- el ganador aislado no se rescata con su propio valor.

## 9. Regla conjunta G2 candidata

Un candidato obtiene PASS sólo si existen y pasan:

1. `mcpt`: test nulo de campaña defendible, `p <= 0.05`, `B >= 1000`;
2. `pbo`: `PBO <= 0.50`, `S=8`, métrica ratio canónica;
3. `dsr`: `DSR >= 0.95`, implementación autorizada;
4. `walk_forward`: expectativa OOS por trade > 0;
5. `parameter_sensitivity`: mediana de expectativas vecinas > 0;
6. cota inferior del IC multiplicity-adjusted de `theta_trade` > 0.

El sexto requisito es el gate primario. Los cinco nombres estructurales se
mantienen para compatibilidad con Promotion Registry; la decisión debe incluir
además el IC primario como evidencia obligatoria. Una implementación futura
puede promoverlo a gate estructural separado mediante otra enmienda.

Todo faltante es FAIL. WARN nunca se convierte solo en PASS.

## 10. ValidationDecision persistida

La autoridad canónica es:

```text
CampaignManifest
  -> CandidateEvidence
  -> G0/G1
  -> G2ValidationDecision
  -> PromotionRegistry
```

`G2ValidationDecision` debe contener como mínimo:

```text
decision_id
campaign_id
run_id
config_id
contract_sha256
evidence_digest
estimand_id
cluster_unit
null_id
required_gates
gate_results
primary_ci
multiplicity_method
N_eff
created_utc
passed
```

Los artefactos referenciados son inmutables y content-addressed. Un print, un
Markdown narrativo o el retorno en memoria de `evaluar()` no son autoridad.

## 11. Impacto histórico

- CAMP-001 permanece `CLOSED`, negativo válido de G1.
- EXPLORE-001 permanece no ejecutado formalmente.
- ARB conserva evidencia histórica, pero entra como `external_candidate`.
- Ningún resultado pasado se promociona retroactivamente con esta enmienda.
- `estimando_diario.py` queda como diagnóstico histórico hasta retirarlo
  formalmente de autoridad.
- `g2.mcpt()` queda retirado de decisiones aunque siga temporalmente en el
  repositorio para reproducir resultados históricos.

## 12. Criterio de aprobación de esta enmienda

Esta enmienda sólo pasa de CANDIDATA a APROBADA cuando:

1. existen implementaciones para el ratio cluster-weighted y `NullGenerator`;
2. tests adversariales refutan el MCPT anterior;
3. cobertura sintética del estimando ratio resulta aceptable;
4. PBO y WF usan numerador/denominador;
5. DSR usa 0.95 y tiene tratamiento explícito de dependencia;
6. `ValidationDecision` se serializa y valida;
7. suite específica y completa pasa en entorno canónico;
8. Nico aprueba el cambio semántico antes de una campaña real;
9. se calcula el SHA-256 exacto del archivo aprobado y recién entonces se agrega
   a `APPROVED_G2_CONTRACT_SHA256S`.

## 13. Lo que esta enmienda no autoriza

- cambiar resultados históricos;
- mirar el holdout;
- elegir método de IC por el resultado observado;
- ampliar hipótesis o grillas;
- usar P1 como evidencia económica;
- afirmar ejecución por haber escrito código o tests;
- promover mientras la allowlist siga vacía.

**Aporte al referente:** todos los gates deben responder o vetar la misma
pregunta económica —expectativa neta por trade— sin confundir dependencia por
sesión con igual ponderación de días.
