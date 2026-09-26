# Manifiesto AXF (agotamiento por flujo → barrido → reversión confirmada) — NQ, exploración, 2026-09-26

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Aprobación:** Nico en chat, 26/09: «Probá distintos parámetros, distintas variantes, niveles de SL/TP (incluso muy largos), distintos niveles de alejamiento a la zona inicial, más agotamiento requerido, filtros de tendencia. Y todo lo que consideres». Se toma como OK de la regla STOP para una búsqueda de **exploración**, con este manifiesto escrito antes de medir. La reserva abr–jun y el holdout no se tocan.
**Idea y diseñador:** `docs/research/IDEA_AGOTAMIENTO_FLUJO_BARRIDO_20260926.md`. Herramienta: `tools/axf.py`. Ledger propio: `artifacts/hippocampus/axf_20260926.jsonl`.
**Regla de alcance:** conclusiones por celda (INFO+ / INFO− / SIN_INFO con MDE / SIN_POTENCIA), con lista de lo no medido. Nada de «el agotamiento por flujo no funciona» a partir de una grilla.

## 1. Datos
NQ, research-v2, contrato canónico, sesiones de exploración ≤ 2026-03-31. Velas de 25 ticks por sesión con volumen agresor comprador y vendedor. El agresor de NQ está validado al 99 % (P-93); las filas del agresor se verifican contra las del loader, igual que en `build_delta_layer.py`.

## 2. Secuencia (causal; los parámetros en negrita se barren)
1. **Extremo:** máximo o mínimo de las últimas `lookN` = 200 velas. **Alejamiento de la zona inicial:** el extremo tiene que estar a ≥ **`farVWAP` ∈ {0, 4} ATR** del VWAP de sesión.
2. **Agotamiento** en las `exhW` = 30 velas de la zona (**4 variantes**, de menos a más exigente):
   - D05: delta en contra ≥ 5 % del volumen;
   - D20: delta en contra ≥ 20 %;
   - A2: absorción, volumen ≥ 2× el normal con avance ≤ 1,5 ATR;
   - A3: absorción, volumen ≥ 3× con avance ≤ 1 ATR.
3. **Último extremo participante:** **`lastDef` ∈ {vela de más volumen, vela de más delta a favor}.**
4. **Barrido:** el precio pasa ese extremo por **`sweep` ∈ {2, 6} ticks** dentro de 60 velas.
5. **Reversión confirmada** desde el extremo posterior al barrido, dentro de 60 velas:
   - distancia **`revDist` ∈ {1, 3} ATR**;
   - delta a favor **`revDelta` ∈ {0,05; 0,20}**;
   - desplazamiento **`revDisp` ∈ {0,4; 0,7}**;
   - velocidad ≥ 0.
6. **Filtro de tendencia**, aplicado como máscara: **`trend` ∈ {ninguno, a favor, en contra}**, según la pendiente de 100 velas de la EMA(200) respecto de la dirección de la operación.
7. **Entrada:** apertura de la vela siguiente a la confirmación.

**Variantes de detección:** 2 × 4 × 2 × 2 × 2 × 2 × 2 × 3 = **768**.

## 3. Embudo
- **Etapa A (información):** retorno direccional en ATR a **60 y 1.000 velas**, contra el control **C-EST** (otra sesión, misma hora ± 1 h, mismo estado: distancia al VWAP, pendiente de la EMA(21) y actividad; ±50 % o ±0,15 ATR). **1.536 pruebas, BH q = 0,10.** También el canal no direccional y el signo en las dos mitades.
- **Etapa B (economía), sólo para las celdas que pasan A:**
  - salidas: SL {E + 4 t, E + 16 t} × TP {1R, 2R, 4R, 8R, zona, VWAP, 3 ATR, 10 ATR} × tiempo máximo {200, 2.000 velas} = **32 variantes** («incluso muy largos»);
  - neto con costo provisional de NQ (2,0 t);
  - dos controles:
    - **C-EST** con la misma geometría transferida en ATR;
    - **C-SEQ**, la misma reversión confirmada **sin** agotamiento ni barrido previos (otra sesión, misma hora).
  - **Pasa** si el R neto es > 0 con IC, le gana a los dos controles y tiene el mismo signo en las dos mitades.
- **Etapa C:** PBO (CSCV) y DSR (`edgelab/research/g2.py`) con el número **real** de variantes evaluadas en A y B; mesetas en la grilla.
- Si nada pasa A, **B y C no se corren** y se publica el paisaje de A.

## 4. Riesgos
- **Búsqueda amplia (768 × 32):** la contienen el embudo, BH, PBO/DSR y la reserva intacta. Nada se confirma acá.
- **Potencia:** un solo activo y ~8 meses. Se publica el MDE.
- **Agresor:** válido en NQ; el resultado no se transporta a ES, YM ni MYM.
- **Velas de 25 ticks:** orden dentro de la vela conservador (stop antes que target).

## 5. No medido (abierto)
Otros `exhW` y `lookN`; agotamiento por L2 (icebergs, cola del libro); otros activos (ES con L2 de NT8, YM/MYM tras validar el agresor); trailing; velas de tiempo; eventos macro.

## 6. Resultado etapa A (26/09; `artifacts/axf/reportA.json`, sha `c19ad91c77f9`, cobertura de controles 99,6 %, auditoría PASS)
- **Estados:** INFO− 240 · INFO+ 6 · SIN_POTENCIA 522 (celdas con < 50 eventos o MDE > 0,25 ATR). **Ninguna celda pasa a B**, así que B y C no se corren, como estaba pre-registrado.
- **Eventos:** 6.235 confirmaciones distintas en 171 sesiones (unión de las 256 detecciones).
- **Lo dominante:** la secuencia **rinde menos** que el control de mismo estado. En la variante más poblada (sin filtro de alejamiento, D05, barrido 2 t, reversión de 1 ATR), a 60 velas da 0,13 contra 0,66 ATR (diferencia −0,53, IC −0,80; −0,25) y a 1.000 velas 0,98 contra 4,30 ATR. Es negativo en las dos mitades del período.
- **Por qué el control es alto:** empareja la pendiente de la EMA(21) en la vela de confirmación, cuando el precio ya viene girando. Por eso rinde a favor de la operación en las dos direcciones (compras +5,1 y ventas +3,4 ATR a 1.000 velas): es **inercia genérica**. La pregunta que contesta es exactamente la de Nico: ¿el agotamiento con barrido agrega algo a un giro con fuerza? **No, en estas variantes: resta.**
- **Las 6 INFO+** son la misma muestra de 50 eventos (D20, reversión de 3 ATR con desplazamiento 0,7, a 60 velas), de 36 sesiones y **todas de la segunda mitad** (la primera no tiene eventos suficientes). No pasa el requisito de las dos mitades. Queda como observación de muestra chica, no como pista.
- **Sin potencia (no descartadas):**
  - las variantes de **absorción** (A2 y A3) casi no producen eventos con esta definición;
  - el filtro de **tendencia a favor** también: una reversión casi nunca va a favor de la EMA(200).

**Alcance:** con extremo de 200 velas, zona de 30 velas, agotamiento por delta del 5 % o 20 %, barrido de 2 o 6 ticks y reversión de 1 o 3 ATR (delta 5 % o 20 %, desplazamiento 0,4 o 0,7), en NQ en exploración, entrar tras la secuencia rinde **menos** que una barra con la misma inercia a la misma hora. No se descarta:
- el agotamiento por absorción, que hay que redefinir para que tenga eventos;
- el agotamiento por L2 (icebergs, cola del libro);
- otras ventanas (`exhW`, `lookN`);
- ES (con L2 de NT8) y otros activos;
- las salidas (B no se corrió).
