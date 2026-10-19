# Diferencial A/B de `g2-a1` — CORRIDO. Y **no los distingue**

**Fecha:** 2026-08-16 · Sin outcomes · Holdout intacto · **Sin datos de mercado**
**Corrige:** `docs/research/ADJUDICACION_G2A1_2026-08-15.md`, que decía «gana B».
**Responde:** `docs/audits/REVISION_ENTRADA_005_2026-08-16.md` §1 y §2.

---

## 1. El auditor tenía razón en las dos

### §1 — «g2-a1 no fue adjudicada»

Escribí simultáneamente *«gana B»*, *«no corrí ninguno»* y *«si la medición
contradice este veredicto, manda la medición»*. **Las tres no cierran juntas.**
Acepto sin reservas.

### §2 — «P-31 ítem 1 no bloquea el diferencial»

**Verificado, y es cierto.** El job `differential-suite` de
`.github/workflows/g2-a1-validation.yml` (blob
`6191cd5999562b069423c0a45a6b8cdd26df704f`) usa **un segundo
`actions/checkout@v4` con `path: _baseline`** y dos venvs. **No usa
`git worktree`.**

Y lo comprobé donde importa: **ninguno** de los cinco archivos de test de G2 toca
`data_root`, `parquet` ni `nt8`. La calibración es **sintética**.

> **Mi cadena publicada era falsa.** `P-31 ítem 1 → diferencial` no existe como
> dependencia. La corrí hoy, en esta máquina, sin arreglar nada.

Método: `git archive` de cada rama a un árbol aislado, `PYTHONPATH` apuntado ahí,
el `.venv` del repo. Verificado que cada corrida importa **su propio**
`g2_decision`.

## 2. Resultado — estadísticamente **indistinguibles**

Los dos emiten la evidencia de calibración sintética. Comparadas excluyendo los
`sha256` de archivo:

```
escenarios: ar1_rho_050_null · ar1_rho_050_signal_030 · iid_gaussian_null
            iid_gaussian_null_n48 · iid_gaussian_signal_020
            student_t5_null · zero_trade_40pct_null

IDENTICOS excluyendo sha256:  True
```

**Siete escenarios, 400 réplicas cada uno, coincidencia al dígito** — incluso
`mean_n_effective = 70.03146776034659` es el mismo número. Artefactos
commiteados al lado de este documento.

Lo único que difiere son los hashes, que difieren por construcción:

| | A | B |
|---|---|---|
| `implementation_sha256` | `de294404…` | `90a66492…` |
| `method_sha256` | `9406b682…` | `9dcd1b8e…` |

## 3. Lo que sí los distingue, y va en contra de B

| | A | B |
|---|---:|---:|
| `test_g2.py` | **27** | 8 |
| `test_g2_decision.py` | 10 | 9 |
| `test_g2_dsr_calibration.py` | 1 | **2** |
| `test_g2_protocol.py` | — | **(existe)** |
| `test_g2_ratio.py` | 8 | 8 |
| `test_promotion.py` | **16** | 14 |
| **superficie G2 completa** (`tests/research` + `tests/stats`) | **83** | **66** |

Las dos **verdes**. Pero B tiene **17 tests menos** en la superficie G2 completa,
**ya contando** su `test_g2_protocol.py` propio. El split de módulos no explica el
neto.

> Es exactamente lo que el auditor advirtió: *«docstrings y nombres no sustituyen
> tests»*. Mi veredicto estructural apuntaba a que B era estrictamente mejor. **La
> medición dice que no.**

## 4. Veredicto corregido

```
B = candidato estructural preferido        (nombre honesto del gate, DSR anclado
                                            por contenido, operadores explicitos)
A = mayor cobertura de tests               (83 contra 66 en la superficie G2)
Estadisticamente                           INDISTINGUIBLES en los 7 escenarios
ADJUDICACION                               NO CERRADA
```

**Lo que el diferencial sí cierra:** el riesgo principal —que B introdujera una
regresión estadística— **queda descartado con medición**. No la introduce.

**Lo que no cierra:** cuál se mergea. Y hay una salida que ninguna rama ofrece
sola: **mergear B y portar los tests que sólo tiene A**, o explicar por escrito
cuáles de esos 17 quedaron obsoletos por el split. Sin eso, mergear B es cambiar
auditabilidad por cobertura sin decirlo.

## 5. ⚠ Este diferencial NO cubre la lista del addendum §4

El auditor pide que la adjudicación pruebe: 7 configs que fabrican Sharpe 1 bajo
Sharpe verdadero 0; `N_eff` incluyendo intentos abandonados; `MIN_DSR_SESSIONS`
calibrado como MinTRL; 424 eventos en 201 sesiones como dependencia por sesión;
DSR e IC sobre la misma población; purge + embargo; CPCV o múltiples caminos.

**Los 7 escenarios existentes no son esa lista.** Cubren nulo IID, AR(1), t de
Student, `n=48`, 40 % de sesiones sin trade y dos con señal — es calibración de
tamaño y potencia del DSR-HAC, no las siete propiedades de arriba.

> **Este diferencial es necesario y no suficiente.** Descarta regresión; no valida
> el estimando contra la investigación.

## 6. Estado que dejo

| | |
|---|---|
| adjudicación `g2-a1` | **NO CERRADA** — B preferido por estructura, A por cobertura |
| riesgo de regresión en B | **descartado con medición** |
| `P-31 ítem 1` como prerequisito | **RETIRADO** — era falso |
| lista estadística del addendum §4 | **sin cubrir** |
| merge | **no**, y ahora con motivo medido, no con prudencia |

**Cadena corregida** (sin `P-31`, y con G2 fuera de la ruta crítica según el
addendum §1):

```
0 ledgers -> 3 costos -> 5 poblacion + 2 N_eff -> 1 F4 -> 4 simulador -> 6 G2
                                                     g2-a1 sanea EN PARALELO
```
