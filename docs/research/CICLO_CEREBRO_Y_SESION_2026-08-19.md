# Ciclo cerebro + ideas de alto potencial (sesión 18–19 ago)

- **Fecha:** 2026-08-19
- **Por qué existe:** Nico pidió registrar la idea del ciclo LLM↔indicadores y
  **sólo** las partes de esta sesión que (a) apuntan al referente, (b) ahorran
  tiempo/esfuerzo y (c) tienen alto potencial. El resto ya está en 029–031.
- **Firewall:** no autoriza F4, P&L, holdout, Optuna ni miles de trials.
- **Referente:** `docs/NORTH_STAR.md` sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

---

## 1. La idea (textual, lo que Nico pidió)

Un «cerebro» (Grok / Opus) que conoce la infraestructura escribe indicadores,
prueba miles de cosas (prefabricadas y exploratorias), recibe retroalimentación
y reestructura análisis e indicadores. Infraestructura + LLM + indicadores;
ML / evolución genética / CatBoost / Optuna mediados por esa infraestructura.

**Dictamen:** posible como ingeniería. Como ciencia, **el feedback decide**.
Si vuelve p-valor / Sharpe / P&L, quema el holdout. Si vuelve «murió por
paridad / N / sesiones / costos», el próximo indicador nace más limpio.

Los 7 indicadores **ya salieron de un LLM**. El canal (Nico + Claude + auditor)
**ya es** ese cerebro, lento a propósito.

---

## 2. El ciclo válido: tres cajas. El LLM no salta de la 1 a la 3.

| Caja | Qué hace | Feedback que vuelve | Cuándo |
|---|---|---|---|
| **1. Fábrica** | Escribe definición. Recorre el camino a PASS (8 pasos). | falló paridad / blob / warmup | **ahora**, barato |
| **2. Censo / N** | ¿Hay población? ¿En cuántas **sesiones**? | murió por N o por 27 sesiones gordas | v2, en curso |
| **3. Test** | Receta escrita *antes* de correr. Optuna/CatBoost **solo** acá, acotados, holdout no elige | M0/M1/M2, economía | **después** del STOP |

**Muro:** la caja 3 no escribe en la 1. El cerebro no ve el leaderboard.

El primer loop útil (ahorra semanas): **paridad → N → muerte barata → el cerebro
escribe el siguiente**. Sin Optuna. Sin miles. F9 sigue en pausa.

---

## 3. Ideas de esta sesión que sí pagan (filtro: referente + tiempo + potencial)

1. **Tres preguntas, no una.** ¿Le gana al azar? ≠ ¿de qué manera? ≠ ¿es
   explotable (neto, ledger ~3,9 ticks RT en 6E)? Un p-valor no paga comisiones.
2. **Camino a PASS de 8 pasos.** El octavo indicador copia la lista; no se inventa
   un procedimiento. `docs/research/CAMINO_A_PASS_PARIDAD_2026-08-19.md`.
   Único FAIL real: P-42 (`aVolCellPOI2`). Después de v2.
3. **Combinaciones / horarios / grupos de zonas / lógicas post-evento** = espacio
   de búsqueda (la «firma»). Se abre **después de N**, con receta escrita *antes*.
   No un barrido. La matriz de kernels ya tiró la máquina.
4. **`vive_por_N` es eventos ≥ 403.** Las sesiones acotan la potencia. 403
   sesiones es imposible (universo 228). No cambiar el 403. Umbral de sesiones
   **escrito antes** de mirar la tabla. Entrada 031.
5. **21 y 49 no son eventos.** Son pares sintéticos sobre 19.200 comparaciones.
   El censo real ya tenía celdas de 1.505. Entrada 030.
6. **P-45 = (c) episodio.** El retorno se consume entero (salir de la banda, no
   `i=r+1`). MAE/MFE no entra al censo. Hipótesis partida: geometría ahora,
   resultado después del STOP.

## 4. Lo que NO se construye ahora

Evolucionar indicadores contra P&L. Dejar que el LLM lea outcomes y «mejore» el
kernel. Mezclar HFTZones2 + horas + post-evento + CatBoost. Cambiar 403 a
sesiones. Reportar «22 vivas» hasta que el JSON de v2 esté en origin con los
dos criterios.

**Aporte al referente:** el cerebro acelera si aprende de definiciones que mueren
barato. Un ciclo que se alimenta de p-valores no acerca una cuenta.
