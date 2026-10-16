# Auditoría de la Pasada 2 (EmaCorridorTrend v4.0, ES) — batería anti-sobreajuste

Estado: PROVISIONAL (auditoría de un solo auditor)
Fecha: 2026-10-15 · Auditor: Claude (un solo auditor) · Objeto: `REPORTE_PASADA2_...md`, `RESULTADOS_PASADA2_...json` (kernel 138895158, v2), script `edgelab_es_corridor_pass2_falsification_v4_sym.py` (sha256 `10e8fa9f22693b9269754e73b8fafe18b7694ccc70702f9a843ebea7b584c0ec`). Continúa `AUDITORIA_CORRIDA_KAGGLE_ES_MULTIRES_CORRIDOR_V4_20261015.md`.

## Veredicto
**Pasada 2 es una mejora metodológica real, pero NO confirma ningún edge operable.** Lo único que sobrevive la corrección de Holm es una estructura (`orig_px`) cuyo efecto bruto es menor que la fricción. Las dos "configuraciones sobrevivientes" para operar (F1 en 100T, F2 en 500T) **no sobreviven Holm ni el nulo emparejado**. El resumen ejecutivo del reporte sobreestima lo que muestran sus propias tablas.

## Lo que mejoró (verificado en el JSON)
- Guarda de sesión, purga `no_overlap`, SE clusterizado por sesión con MDE, MCPT por signos de sesión (2.000), Holm/FDR, mitades S1/S2, 6 contratos, espejo, RTH/ETH y handicap de −1 tick. Aplicados a 343 pruebas.
- El candado de espejo detectó un error real (doble signo que dejaba sin zonas bajistas) y se corrigió: buena práctica.
- Falsificó correctamente lo que v1 mostraba en 25T/100T para penetración 25–33%: eso era artefacto de solapamiento/entradas pre-cierre. Coincide con mis hallazgos B2/B4/M1 de la auditoría anterior.

## Hallazgos

### Bloqueantes
**P2-B1. No es una prueba preregistrada ni independiente.** El reporte habla de "343 pruebas pre-registradas", pero no hay manifiesto ni commit previo a la corrida; las dos familias se eligieron mirando los ganadores de la Pasada 1 **sobre las mismas 299 sesiones**. Selección y prueba comparten datos: el Holm sobre 343 no descuenta las ~10.250 celdas de la Pasada 1 de las que salieron los candidatos, y las mitades S1/S2 son partición *dentro* de la muestra de selección, no OOS. Estas 299 sesiones de ES quedan **quemadas para confirmar** estas hipótesis.

**P2-B2. Sólo F3 sobrevive Holm, y F3 no es operable.** De las 31 celdas "sobrevivientes", las 6 con `p_holm ≤ 0,05` son todas `F3A_ORIGIN_100` (25T y 100T). Ninguna celda de F1 ni F2 tiene `p_holm` < 0,43 (F2F 500T: 0,429; F1A 100T: 1,0). El reporte llama "sobreviviente" a lo que pasa los filtros *sin* corrección.

**P2-B3. F3: significativo pero menor que la fricción.** Bruto por trade = (2w−1)·D:
| Celda | w | D (ticks) | Bruto | Fricción ES | 
|---|---|---|---|---|
| 25T 0,5H (N=28.338, z=9,81) | 53,06% | ≈10 | +0,6 | 3,4–3,5 |
| 25T 1,0H | 52,37% | ≈20 | +0,9 | 3,4–3,5 |
| 100T 0,5H (N=6.109) | 52,68% | ≈19 | +1,0 | 3,4–3,5 |
| 100T 1,0H (N=2.744) | 52,81% | ≈38 | +2,1 | 3,4–3,5 |
Además, en 25T el win rate con −1 tick adverso es 47,4% (<50%). Es una estructura real y robusta (6/6 contratos, simétrica), útil como **nivel** (`orig_px`), no como edge: "una zona bien almacenada no es un edge".

### Mayores
**P2-M1. F1 (100T) no supera el nulo emparejado (H-03).** Preset 2, `STEEP_SLOPE`, 1,0H: real 53,79% vs pseudo-zonas 53,65% → exceso **+0,35 pp, z=0,14**. Struct_To_Origin: +1,82 pp, z=0,73. En Preset 3 el exceso es **negativo** (−2,85 pp). Sólo Preset 1 da +5,09 pp (z=1,70, no significativo). Es decir, lo que supera 50% es la tasa base de ese contexto, no la condición de zona. El propio reporte marca "RTH domina": la hora explica parte.
**P2-M2. F1 neto de fricción roza cero.** 100T, D≈40 ticks: 54,10% → bruto 3,3 (neto ≈ −0,2); 55,40% (Preset 1 STEEP, N=852) → bruto 4,3 (neto ≈ +0,8, un efecto dentro del error). El handicap de −1 tick no es la fricción (3,4–3,5 ticks).
**P2-M3. F2 (500T): N diminuto, MDE ≈ efecto y nulo emparejado anómalo.** N=73 eventos en 64 sesiones; MDE80 = 15,8 pp contra un efecto de 14,4 pp (maldición del ganador); S1/S2 = 78,8% / 52,5% (inestable). El "+33,5 pp vs pseudo" sale de un nulo de **33,9%** (esperable ≈50% con barrera simétrica), lo que indica un nulo mal especificado o con muy pocas pseudo-observaciones en ese estrato, no un efecto de 33 pp. `p_holm` = 1,0 (F2D) / 0,43 (F2F). Aun así es el único candidato con recorrido económico grande (D≈86 ticks).
**P2-M4. Estratos y régimen elegidos a posteriori.** `STEEP_SLOPE`, `RTH`, `CLEAN_DEPARTURE`, la barrera y el preset son decisiones tomadas mirando resultados; cada una es un grado de libertad no contado.
**P2-M5. El nulo H-03 no iguala el disparador.** Se empareja por (contrato × media hora) con barras `state==0`, pero el evento real es "regreso y cierre dentro de la caja"; las pseudo-barras no condicionan a un movimiento previo comparable. Puede sub- o sobrestimar el nulo (ver el 33,9% de F2).

### Menores
- La corrida usa el hash de manifiesto `06d7fb2a…` (no `db9c42cd…`) sin reconciliar (pendiente de la auditoría previa).
- La paridad Python↔NT8 del detector sigue sin demostrarse.
- Mensaje del reporte: "rigor de nivel producción" no está respaldado por lo anterior.

## Estado de cada familia (alcance preciso)
| Familia | Estado propuesto |
|---|---|
| F3 `orig_px` rebote | **Estructura real; NO es edge** (bruto < fricción). Usar `orig_px` sólo como nivel/objetivo descriptivo. |
| F1 100T RTH STEEP, cierre de reingreso | **Pista sin confirmar**: no supera nulo emparejado; neto ≈ 0. |
| F2 500T STEEP penetración 33–40% | **Pista sin potencia**: N≈73, MDE ≈ efecto, Holm no la sostiene. |
| F2 25T/100T penetración 25–33% | **Refutada** (sin efecto o negativa) bajo guarda de sesión y purga. |

## Qué sigue
Las 299 sesiones de ES no pueden confirmar F1/F2. Cualquier confirmación exige **datos no usados en la selección** y manifiesto previo: ver `MANIFIESTO_PASADA3_CONFIRMATORIA_CORREDOR_20261015.md` (propuesto, requiere OK).

## Límites de esta auditoría
No leí el detector ni las funciones de carrera, no re-ejecuté la Pasada 2 y no vi el universo completo de las 343 pruebas (sólo las 31 y la lista top-35). Netos de fricción: cuentas simples con la fricción de R2 y barreras simétricas.
