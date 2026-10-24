# LUXIMB-GRILLA — la familia LUX-IMB de impulsos en grilla masiva, con la regla del visor como una celda (2026-10-24)

Estado: PROPUESTA — lista para lanzar el E0 y el DESC; **nada corrido con desenlaces**. Campañas `LUXG-NQ` y `LUXG-CFD` apagadas (`"activa": false`).

**North Star:** `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`
Familias: **LUXIMB_GRILLA** (señal y ejecución en NQ) y **LUXIMB_GRILLA_CFD** (señal en USATECH de Dukascopy, ejecución en NQ).
Etapa del embudo: **EF2** (exploratorio masivo: DESC con tamiz FDR) → el embudo automático (`edgelab/research/embudo.py`) decide el resto.
Código: `edgelab/research/luximb_grilla.py`. Tests: `tests/research/test_luximb_grilla.py` (14). Preflight: `python -m edgelab.research.preflight edgelab.research.luximb_grilla` → ok.
Campañas: `config/autopilot/grillas/campanas/LUXG-NQ.json`, `LUXG-CFD.json`. Linaje: `docs/research/LINAJES.jsonl`.

## 1. Pedido y antecedente
Pedido de Nico (2026-10-24): pasar la familia LUX-IMB por una grilla masiva filtrada por el embudo, igual que se encontró U1, con
la regla congelada del visor como **una celda** de la grilla. La regla congelada
(`luximb_parity_20261020/CANDIDATO_HOLDOUT_REGLA_VISOR_NQ_20261021.md`): fade, TP 1,0·D (el origen A) / SL 0,2·D, entrada al cierre
de la vela de confirmación −1 tick, tope de 240 min, sin BE.

Lo que ya se sabe (todo mirado, nada confirma):
- Regla del visor sobre el release con costos canónicos: +4,05 pts/op, IC90 por sesiones [+0,36, +7,56], 500 op. en 212 sesiones,
  **SIN_POTENCIA** (`RESULTADOS_RECALCULO_CANONICO_RELEASE_20261024.md`). Mirada exploratoria del holdout: 14 SL / 0 TP.
- M1–M11 (rebalanceo, penetración, inicio cargado, escalonadas, franjas, distancia y tiempo, grilla SL/TP/BE de 40 celdas): sin
  efecto con su MDE (`LUXIMB_MEDIDO_Y_NO_MEDIDO.md`).
- **EXPANSION_ZONAS** (familia hermana, 233.280 celdas por canal): 0 nominadas por FDR y 0 por Romano-Wolf en NQ y en el CFD.
  LUXIMB-GRILLA **no** es la misma grilla: (a) el objeto es el impulso ESPEJO-IND con umbral de amplitud por percentil causal y
  marca en tiempo real (el del visor), no una expansión de R·ATR; (b) las zonas cuentan si el tramo las **atraviesa enteras**
  después de nacer (no si nacen dentro); (c) la salida es la geometría del visor (TP y SL en múltiplos de D, stops cortos de 0,1–0,5·D)
  con entradas límite; (d) régimen y hora como perillas. Si las dos grillas midieran lo mismo, el nulo de EXPZ ya anticipa éste: se
  declara acá antes de correr.

## 2. Justificación económica
Un impulso amplio y rápido que **atraviesa enteras** zonas de desequilibrio recién nacidas (OG/VI de LuxAlgo: huecos y velas sin
superposición) consume en un solo sentido la liquidez que quedaba en esos precios. Si quien empujó fue flujo urgente sin
información (cobertura, stops, liquidaciones), al terminar el empuje el precio vuelve hacia el origen A: gana el **FADE**, y lo hace
con un stop corto porque el extremo es justo donde se agotó el flujo. Si el empuje trae información, el precio sigue: gana la
**CONTINUACIÓN**. La carga de zonas en el tramo inicial (cerca de A) es la marca de un arranque «en vacío», y la hora y el régimen de
volatilidad cambian quién está del otro lado. Quién pierde: el que persigue el impulso tarde (FADE) o el que lo desvanece contra
información (CONT).

## 3. Cómo podría refutarse
- **La familia:** ninguna celda nominada por FDR q 0,10 con el linaje cobrado (compuerta dura de DESC) y el nulo publicado con su MDE
  por nivel de perilla; o, si alguna pasa, integridad (placebo, latencia), OOS en contra con potencia, o media neta ≤ 0 en el
  holdout a N fijo.
- **La celda del visor:** si queda sin nominar en DESC con un MDE del tamiz por debajo de su efecto medido (+4 pts), la grilla dice que
  ese +4 era selección. Si el MDE está por encima, no la refuta (sin potencia).
- **La población:** si el E0 muestra que la condición de zonas no cambia el objeto (las definiciones con y sin zonas marcan casi los
  mismos tramos en la misma vela), la perilla de zonas es redundante y se informa así, sin rediseñar después de ver P&L.
- **Ruido y plantado:** ruido puro → 0 nominadas; reversión plantada → el embudo nomina FADE (tests; si no, la definición está mal).

## 4. Espacio de eventos (enumerado antes de congelar la población; regla de CLAUDE.md)
| familia de evento/estado | qué sería con zonas LUX-IMB e impulsos | ¿se mide acá? |
|---|---|---|
| creación | nacimiento de una zona OG/VI (o una ráfaga de zonas) | no — el nacimiento sólo entra como condición («zona nacida antes de ser atravesada») |
| aproximación | precio acercándose a una zona viva | no |
| primer toque | primera vuelta del precio a una zona | no (M4, M9 lo midieron sin efecto) |
| toque n-ésimo | vueltas siguientes | no |
| invalidación | zona atravesada entera (mitigada) | **sí, como condición**: el impulso las atraviesa enteras |
| expiración | zona que vence sin tocarse (vida 500 velas) | sólo como límite de vida |
| confluencia | varias zonas en el mismo tramo de precio | **sí**: ≥ N zonas en la franja inicial del rango (perilla `zonas`) |
| estado continuo | zonas activas / distancia en cada vela | no (sería otra familia; la marca es un evento) |

**Se mide** el EVENTO «impulso en curso que ya cumple amplitud, rapidez y confluencia de zonas atravesadas en su tramo inicial»,
marcado en la primera vela M1 que lo cumple (tiempo real). **Por qué:** es el objeto exacto de la regla del visor, y la grilla barre
su vecindario. **Evento vs estado:** un evento da ~cientos a miles de marcas; el estado tendría más potencia pero es otro objeto (otra
familia, con su propio registro). La perilla `zonas` incluye el nivel **sin condición de zonas** como control dentro del mismo tensor.
**Refutación de la población:** §3, tercer punto.

## 5. Objeto (todo con velas ≤ k, la vela de marca)
Idéntico a `tools/luximb_parity/luximb_impulsos.py --modo inicio` (congelado en el candidato), salvo lo marcado ⚠.
1. **Zonas** LUX-IMB OG+VI en M1: `areas_expansion.zonas` (copia del detector con paridad NT8 1507/1507), FVG apagado.
2. **Tramos** ESPEJO-IND en M1 (`luximb_grilla.detectar`, port del `detect_act` con el fix de supervivencia del 21/10): neto ≥ 3·ATR(14)
   cerrado en la vela anterior dentro de 20 velas, eficiencia ≥ 0,3, umbral ≥ 2 ticks; A = origen; confirma por retroceso ≥ 30 % del
   tramo, por tope de 20 velas, por hueco > 30 min o por fin de datos. En ticks enteros, como el original. Un segmento (contrato) a la vez.
3. **Zona atravesada** (regla de `crossed`): nacida en [i0 − 500, k), entera dentro de [A, extremo en k], y que después de nacer el
   precio tocó primero su borde cercano y después el lejano, todo dentro del tramo, a ≤ 500 velas de su nacimiento.
4. **Marca:** para cada vela kb entre la activación del tramo y su confirmación, con el extremo conocido en kb: hay ≥ 500 tramos
   confirmados antes de kb (ventana de 2.000); rango ≥ max(percentil causal `p` de las amplitudes, piso en puntos); rapidez
   (rango / velas) ≥ el mínimo causal (p0); y la condición de zonas. La marca es la **primera** kb que cumple todo. Cada definición
   (amplitud × zonas) marca su propia vela: son perillas de EVENTO, no filtros sobre una vela fija.
   ⚠ La rapidez cuenta velas M1 (el original, velas de 25 ticks). Sólo afecta al piso p0 de rapidez. Con una vela de 25t por minuto
   las dos cuentas coinciden (fixture del oráculo).
5. **Dirección:** d = +1 impulso alcista, −1 bajista. **D** = d·(E_ref − A), con E_ref = cierre(k) − d·tick (la entrada del visor).

## 6. Perillas
| perilla | tipo | niveles | celdas |
|---|---|---|---|
| amplitud (evento) | grupo | max(p60, 0) · **max(p60, 60 pts)** · max(p80, 60) · max(p90, 60) (percentiles causales) | 4 |
| zonas (evento) | grupo | sin condición · ≥1 en el 25 % · **≥3 en el 25 %** · ≥5 en el 25 % · ≥3 en el 50 % (y ≥ 50 % del total en esa franja) | 5 |
| rapidez | extremos | terciles del E0 de la fuente (pts por vela M1 de A al extremo) | 3 |
| actividad | extremos | terciles del E0 (volumen por vela del impulso / de la sesión anterior) | 3 |
| reg_vol_diaria | extremos | terciles del E0 (rango de la sesión anterior / mediana de las 20 previas; `agente/regimen.py`) | 3 |
| reg_hora | eq_any | bloques UTC fijos 0 Asia 22–07 · 1 Europa 07–13:30 · 2 NY 13:30–20 · 3 cierre 20–22 (no ajusta horario de verano) | 5 |
| dirección | eq_any | alcista · bajista | 3 |
| ejecución | grupo | 112 (abajo) | 112 |

**Celdas por canal: 4·5·3·3·3·5·3·112 = 907.200** (`grilla_generica.n_celdas` = `n_celdas_por_canal` de las dos campañas). En
negrita, la celda del visor. Los cortes de las continuas salen de cuantiles del E0 de la misma fuente y período (nunca a ojo); el
piso de 60 pts y los percentiles 60/80/90 son los del visor y su vecindario geométrico, declarados acá antes del E0. Un faltante
(primera sesión sin sesión anterior) queda fuera de toda celda (índice −1; test `test_faltante_no_cae_en_un_nivel`).

**Ejecuciones (112)** = 4 entradas × (17 salidas FADE + 11 CONT):
- entradas: `CIERRE` (al cierre de la marca; niveles desde E_ref = cierre − d·tick, como el visor), `SIG` (primer tick de la vela
  siguiente, mismos niveles), `LIM10` / `LIM25` (límite a 10 % / 25 % de D: FADE más allá del cierre, CONT en el retroceso hacia A;
  niveles desde el precio límite). El momento de llenado se declara por operación (guía §2).
- FADE (hacia A): TP ∈ {0,5; 1,0; 1,5}·D × SL ∈ {0,1; 0,2; 0,5}·D; CONT: TP ∈ {0,5; 1,0; 1,5}·D × SL ∈ {0,2; 0,5}·D.
- BE (stop a la entrada al recorrer 1R) sólo donde TP ≥ 2·SL: si no, no se arma antes del objetivo (perilla muerta, error de U1-INDAGA).
- Tope de 240 velas y fin de sesión: los fija el simulador común (`areas_expansion.simular`); **no es perilla** (cambiarlo es tocar el
  núcleo compartido: queda NO MEDIDO).
- `ejecuciones_equivalentes` = [] en el preflight (sintético de 150 días).

Ordinal para la meseta: amplitud. `BASE` (indagación) = la celda del visor.

## 7. La celda del visor dentro de la grilla
Índices `[1, 2, 2, 2, 2, 4, 2, EJECUCIONES.index(("FADE", "CIERRE", 1.0, 0.2, 0))]` (`luximb_grilla.celda_visor()`).
- **Reproduce la estructura** del script congelado (test `test_celda_visor_reproduce_el_script_congelado`, fixture sintético con
  el piso bajado a 10 pts en los dos lados): mismas marcas (vela, dirección, A, origen) y mismos niveles (entrada al cierre, TP = A,
  SL = E_ref + 0,2·D) que `luximb_impulsos.py` + la contabilidad de `escalera_candidatos_20261022.lux_trades` usada en el recálculo
  canónico. También para las definiciones de zonas `≥1 en el 25 %` y `sin condición`.
- **No reproduce el P&L** del recálculo, a propósito: el simulador común exige atravesar el TP por 1 tick, resuelve la vela ambigua con
  el orden real de los ticks (el visor: velas de 25t, misma vela → SL), llena el stop al precio real, cierra por fin de sesión (el visor:
  hueco > 30 min) y cobra la fricción canónica de NQ (1,5455 pts base, +0,5 adverso). El recálculo ya cobraba la fricción canónica sobre el
  bruto con entrada al cierre: la diferencia que queda es de llenado, más conservadora acá.
- **Chequeo de integridad en el E0 (target-free, sólo conteo):** las marcas de la definición del visor por contrato dentro del DESC
  deben dar **20 (09-25), 99 (12-25), 100 (03-26)** como el recálculo, más las de 06-26 hasta el 31-mar. Una diferencia se explica
  por causa raíz ANTES del DESC (la única fuente admitida es el piso p0 de rapidez en M1 vs 25t); si no se explica, no se lanza.

## 8. Períodos (HOLDOUT-A3/A4) y lo ya consumido
| | LUXG-NQ | LUXG-CFD |
|---|---|---|
| señal / ejecución | NQ / NQ | DK:USATECHIDXUSD / NQ |
| DESC | 2025-08-05 → 2026-03-31 | 2025-08-05 → 2026-03-31 |
| OOS (réplica) | 2026-04-01 → 2026-09-30, **COMPROMETIDO** | ídem, **COMPROMETIDO** |
| holdout | desde 2026-10-22, N fijo 150 | desde 2026-10-23, N fijo 150 |
- **DESC comprometido para la familia:** la regla del visor se diseñó mirando NQ ago-2025 → sep-2026 (los 6 períodos del tablero) y
  M1–M11 midieron en el descubrimiento de NQ. La celda del visor en DESC es ancla y control, no descubrimiento.
- **OOS comprometido** (`LUXIMB_MEDIDO_Y_NO_MEDIDO.md`: «réplica abr–sep comprometida, diseño mirando NQ 09-26»; el tablero miró
  también 06-26). Se corre porque puede refutar, pero **pasarlo no cuenta como réplica limpia**: la confirmación queda a cargo del
  holdout a N fijo. No hay período de NQ anterior a ago-2025 en el release.
- **Holdout:** LUXIMB_FADE_VISOR consumió 2026-10-01..10-21; AREAS_EXP_1_CRUZADO, 10-01..10-22. Se agregaron dos líneas de corrección a
  `HOLDOUT_VENTANAS.jsonl` (sólo protegen más) que vinculan LUXIMB_GRILLA y LUXIMB_GRILLA_CFD con esas miradas: el guard del embudo
  rechaza un `holdout.desde` anterior. **Una sola apertura por familia.**
- **Ventana «reciente»** (ATJ-24): la del conductor genérico, los últimos 3 meses del DESC (ene–mar 2026), fija en código antes de mirar.

## 9. Multiplicidad y registro (NO registrado todavía: lo hace el embudo justo antes de lanzar)
- **DESC:** el embudo registra `2 × n_celdas_por_canal` = **1.814.400 pruebas por campaña** (canales `total` y `reciente`) en
  `TRIAL_REGISTRY_GLOBAL.jsonl` con id `embudo/<cid>/desc`, familia de la campaña, antes de lanzar. Las dos campañas juntas: **3.628.800**.
  Si la grilla cambia, el número cambia y se registra de nuevo (no se reutiliza).
- **Linaje** (`LINAJES.jsonl`, declarado antes del DESC): LUXIMB_GRILLA ← LUXIMB_FADE_VISOR, LUXIMB_IMPULSOS, LUXIMB_ESCALONADAS_AREA,
  LUXIMB_FUT_VS_CFD, en bruto = **106** pruebas heredadas. LUXIMB_GRILLA_CFD ← las mismas + LUXIMB_GRILLA + AREAS_EXP_1_CRUZADO (la
  idea de la señal en el CFD sale de U1-CRUZADO) = **19.409.157** hoy (+1.814.400 cuando corra el DESC de LUXG-NQ). Con m = 907.200
  celdas por canal, el q con linaje de una pista del CFD es ~22× el del tamiz: hace falta q_BH ≲ 0,0045 para pasar. Es el precio de
  haber elegido el sensor mirando otro resultado; se declara ahora para no discutirlo después.
- No se transportan resultados ni presupuesto entre esta familia y EXPANSION_ZONAS, AREAS-EXP-1 o BigTrap2.

## 10. E0 target-free (preparado, NO lanzado)
Dos caminos, ambos sin desenlaces:
1. **Por el embudo** (resumen E0 + densidad del feed por mes):
   ```
   python -c "import json; from edgelab.research.embudo_runners import KaggleRunner as K; s=json.load(open('config/autopilot/grillas/campanas/LUXG-NQ.json', encoding='utf-8')); print(K().lanzar(s, 'E0', {'cortes': None}, s['desc']))"
   ```
   (equivale a `tools/kaggle_launch.py --slug nicolasbuttaro/embudo-luxg-nq-e0-20250805 --need NQ:2025-08-05:2026-03-31 --env ETAPA=E0 ...`;
   para el CFD, el mismo comando con `LUXG-CFD.json`, que agrega `--extra-dataset nicolasbuttaro/edgelab-dukascopy-nq-usatech`).
2. **Con los disparos completos** (para el chequeo de conteo del §7), kernel committeado `tools/kaggle_grilla/kernel_luximb_grilla.py`
   (código `1e74146e5a4ac57e…`, 15 módulos; se rearma con
   `python tools/kaggle_grilla/construir_kernel_experimento.py edgelab/research/luximb_grilla.py tools/kaggle_grilla/kernel_luximb_grilla.py --extra edgelab/research/agente/regimen.py --extra edgelab/regimes/state.py`):
   ```
   python tools/kaggle_launch.py --slug nicolasbuttaro/luximb-grilla-e0-nq --script tools/kaggle_grilla/kernel_luximb_grilla.py --need NQ:2025-08-05:2026-03-31 --env EXPERIMENTO=edgelab.research.luximb_grilla --env FUENTE=NQ --env MODO=E0 --env DESDE=20250805 --env HASTA=20260331
   ```
   Salida: `LUXIMB-GRILLA_NQ_E0.json` (cortes y distribuciones) y `LUXIMB-GRILLA_NQ_E0_disparos.parquet`. Conteo del visor por contrato:
   `D[(D.amp == 1) & (D.zon == 2)].groupby(seg_de_k).size()` con el segmento del contexto.
Lo que se mira en el E0: marcas por definición (que ninguna quede vacía ni casi igual a otra), cortes de las tres continuas (≥ 10 % por
nivel), faltantes, y el conteo del visor. Los cortes del DESC salen de este E0 (el embudo los recalcula en su DESC sobre el mismo período).

## 11. Qué falta antes de lanzar el DESC
1. Correr el E0 (§10) y cerrar el chequeo de conteo del visor (§7) con causa raíz de toda diferencia.
2. Que el agente active la campaña (`"activa": true`) por su protocolo (pre-registro publicado, doble revisión, guardas); el
   embudo registra las 1.814.400 pruebas y lanza. Lanzar primero LUXG-NQ; LUXG-CFD después (hereda el registro de la primera).
3. Perfilar en el E0 el tiempo de `disparos` con datos reales (~17 k tramos; sintético de 150 días: ~4 s) y el tamaño del lote de
   operaciones (disparos × 112) antes del DESC.

## 12. NO MEDIDO (de esta familia, a propósito)
- Tope de tiempo como perilla (lo fija el simulador común); canal no direccional (rango/volatilidad posterior sin P&L); estado continuo
  de zonas; primer toque y toque n-ésimo; otros instrumentos (ES, YM: la fricción de cada uno es propia).
- ESPEJO-IND figura `VERIFICAR` en `config/autopilot/indicadores.json` (sin paridad NT8 documentada): acá es la lógica propia del
  experimento (port en Python con oráculo contra el original y test de causalidad), válida para research; **no se opera en vivo** sin su
  versión NT8 con paridad.
