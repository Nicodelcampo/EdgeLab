# G2 — cobertura del estimando ratio por sesiones

> Estado: **PASS PROVISIONAL EN SANDBOX; REPLAY CANÓNICO PENDIENTE**.
>
> Implementación: `422be1af4cff935da90c4eb521ca364fa70efa5b`.

## Estimando

`theta_trade = sum_d(u_d) / sum_d(v_d)`, donde `u_d` es PnL neto y `v_d` es número de trades. Se remuestrean pares `(u_d,v_d)`; nunca medias diarias.

## Secuencia de refutación y corrección

1. Bootstrap i.i.d. percentil, AR(0.7): **64,2%**.
2. Bootstrap estacionario percentil `b=5`: **80,0%**.
3. Sensibilidad `b=2…30`: ninguna variante superó **80,0%**; elegir otro bloque no arreglaba el método.
4. Se studentizó con HAC Newey-West sobre `psi_d = u_d - theta_trade*v_d`.
5. PPW2009 elige el bloque sobre `psi_d`; HAC usa `lag=b`.

## Dominio validado

El método falló en `n=100` con colas pesadas (89,33%). La API sancionada impone `MIN_STUDENTIZED_SESSIONS = 160`; el caller no puede reducirlo.

## Matriz productiva

200 simulaciones × 400 réplicas. Nominal 95%; criterio interno mínimo 90%.

| escenario | n=160 | n=197 | n=250 |
|---|---:|---:|---:|
| balanced iid | 96,0% | 94,0% | 95,0% |
| tamaño informativo | 93,0% | 93,5% | 94,0% |
| colas pesadas | 92,5% | 92,5% | 92,0% |
| AR(0.7) | 92,5% | 92,0% | 91,5% |

Peor celda: 91,5%. Todas superan 90%; esto no implica cobertura exacta de 95% ni validez universal.

## Prohibiciones

- usar intervalo percentil como gate;
- ejecutar bootstrap-t con menos de 160 sesiones;
- estimar PPW sobre medias diarias o sólo P&L;
- elegir `b` mirando el intervalo;
- allowlistear antes del replay canónico;
- extrapolar a DGP no incluidos.

## Pendientes antes de aprobar G2

1. ejecutar tests y batería en Python 3.12 canónico;
2. guardar JSON con digest y entorno;
3. suite completa;
4. integrar PBO, DSR, WF y `ValidationDecision`;
5. aprobación explícita;
6. recién entonces allowlistear el SHA-256 contractual.

## Referencias

- https://www.sciencedirect.com/science/article/abs/pii/S0167947399000146
- https://www.ssc.wisc.edu/~bhansen/718/HardleHorowitzKreiss.pdf
- https://www.researchgate.net/publication/220136520_Bootstrap_confidence_intervals_for_ratios_of_expectations

**Aporte al referente:** una implementación que sólo remuestrea no es válida; debe demostrar cobertura sobre el estimando económico real.
