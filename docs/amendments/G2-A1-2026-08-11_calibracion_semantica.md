# Enmienda G2-A1 — calibración, calendario y semántica canónica

**Fecha:** 2026-08-11  
**Estado:** propuesta implementada en PR #8; draft; no autoriza promociones.  
**Base:** `foundation/f0b-compatibility-probe` en `02ab31aa4d708d0271a1365b10a24c4e3031bef2`.

## 1. Causa

La primera corrección G2-A1 integrada en la base resolvió un error real: el ex-MCPT medía concentración temporal y contradecía la estabilidad exigida por G1. También elevó DSR a 0,95 y activó el IC primario.

La auditoría posterior encontró huecos independientes:

1. `dependence_method` era texto declarativo, no una estimación ejecutada;
2. el DSR aceptaba dos observaciones y omitía días sin trades;
3. no persistía calendario ni identidad AST;
4. el hash autorizado cubría una fórmula escalar, no la construcción de retornos por sesión;
5. no existía calibración de tipo I/potencia;
6. al retirar el MCPT no quedó un nulo específico de campaña;
7. las rutas históricas de PBO/walk-forward aún podían agregar por suma.

## 2. Decisión

- `temporal_concentration_test` queda diagnóstico.
- Cada campaña aporta un nulo versionado y al menos 1.000 réplicas.
- El IC primario sigue siendo bootstrap-t estacionario por sesión.
- DSR usa `session_hac_bartlett_v2`, calendario completo, ceros explícitos y mínimo 160 sesiones.
- PBO y walk-forward usan celdas `(pnl_net,n_trades)` y ratio de totales.
- La decisión liga DSR, IC, calendario, población y presupuesto.
- Promotion Registry exige aprobación separada de contrato e implementación.

## 3. Compatibilidad

La fachada `edgelab/research/g2.py` conserva:

- generador determinista usado por tests;
- diagnóstico de concentración;
- `deflated_sharpe` y `expected_max_sharpe` para compatibilidad;
- sensibilidad paramétrica.

Los nombres `pbo_cscv` y `walk_forward` pasan a las primitivas de ratio. Datos sin `n_trades` fallan cerrado; no se infiere un denominador.

## 4. Evidencia sintética

Panel determinista preregistrado:

| Escenario | Rol | Sobre |
|---|---|---|
| IID gaussiano | tipo I | 1%–9% |
| AR(1), rho=0,50 | tipo I adversarial | <=11% |
| Student-t(5) | colas | <=11% |
| 40% sesiones cero | inactividad | <=11% |
| IID con N_eff=48 | multiplicidad | no aumenta PASS |
| IID mu=0,20 | potencia | >=70% |
| AR(1) mu=0,30 | potencia | >=60% |

400 réplicas × 160 sesiones por escenario. El workflow publica JSON y fingerprints en su summary.

## 5. Seguridad

- holdout intacto;
- sin datos económicos;
- allowlists productivas vacías;
- PR en draft;
- no mergear ni activar sin PASS diferencial, revisión y aprobación explícita de ambos hashes.

## 6. Migración desde PR #5

PR #5 fue construido contra la base documental anterior. La rama canónica recibió en paralelo la primera implementación A1 y generó conflictos no resolubles automáticamente. PR #8 reconstruye la propuesta desde el nuevo tip y reemplaza a #5 sin reescribir historia ajena.
