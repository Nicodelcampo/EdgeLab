# EdgeLab — registro de edges promovidos

## Estado actual: ninguno

No existe hoy un edge promovido que cumpla la cadena completa de validez técnica, estadística, económica, OOS y aplicabilidad.

### H1 / BigTrap2 T=34

**Estado:** MUERTA.

- universo: 6E, 201 sesiones pre-holdout;
- población final: 424 eventos;
- bruto: `+0,2995 ticks/evento`;
- fricción: `−2,7680 ticks`;
- neto: `−2,4685 ticks/evento`;
- IC 99,9535%: `[-5,2370; +4,9780]`;
- regla: GRIS → MUERE.

Esta muerte adjudica la regla de primer toque y su monetización. No convierte automáticamente a toda la familia BigTrap2 en nula.

### BigTrap2 — función soporte/resistencia

**Estado:** FUERTEMENTE REFUTADA.

La ruptura permanece alrededor de 96% y prácticamente invariante en la grilla target-free estudiada.

### BigTrap2 — atracción/revisita (imán de zona)

**Estado:** **CERRADA — REFUTADA (2026-08-13).** No es edge y no es hipótesis viva.

Estado del proyecto: `BIGTRAP2_MAGNET_LINE_CLOSED`. Acta:
`docs/research/F27_F210_CIERRE_Y_HERRAMIENTAS_2026-08-13.md`. Cadena sobre 6E, 201
sesiones, 15.947 zonas:

- **F2.7** — la carrera contra el espejo es real (Δ≈+0,048, IC [+0,031, +0,066]).
  Real y espejo equidistantes del close: «gana porque está más cerca» queda descartado.
- **F2.8** — **no es imán**. El efecto no muere en `d≥6` (Δ≈+0,077) y un control
  **sin zona** con la misma geometría da casi lo mismo: el contraste cruza cero.
- **F2.9** — el kernel no es el mejor sello. Vela extrema genérica `S1` = +0,038
  contra creadora BigTrap2 `K0` = +0,021, y `K0 ≈ N0` (no-creadora emparejada).
- **F2.10** — no hay ventana temporal exclusiva; el contraste `t+1` cruza cero.

**Lo que sobrevive, y no es de zona:** una vela extrema marca una carrera
asimétrica. No es exclusiva de BigTrap2 y no es un sistema — es un sello barato de
contexto.

El texto anterior de esta entrada («97,9 % contra ~51,4 % nula… promoción bloqueada
hasta cerrar la procedencia de los reruns») describía el **primer** nulo, con dos
defectos de geometría ya corregidos. Quedó **superado por F2.7–F2.10** y se
mantuvo aquí dos días de más.

### Asian Range Breakout / ARB

**Estado:** LEGACY, NO PROMOVIDO EN EL REGISTRO ACTUAL.

El documento histórico anterior reportaba una validación positiva, pero el README y el contrato vigente lo mantenían pausado y fuera del ledger científico central. Se conserva en el historial de Git; no se presenta como edge activo sin reconstruir su cadena de promoción bajo el contrato actual.

## Regla de inclusión

Una entrada solo puede aparecer como edge promovido si:

1. tiene lineage, paridad y disponibilidad técnica;
2. supera robustez estadística y múltiples pruebas;
3. conserva expectativa neta con costos y stress;
4. confirma OOS/holdout según protocolo;
5. demuestra aplicabilidad research↔live.

Información descriptiva, una señal target-free, un backtest positivo o una hipótesis publicada no cumplen esta definición.
