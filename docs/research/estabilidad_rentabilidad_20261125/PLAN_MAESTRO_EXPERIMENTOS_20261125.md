# Plan Maestro de Experimentos EdgeLab — Rentabilidad y Estabilidad (`2026-11-25`)

Estado: VIGENTE (hoja de ruta de investigación pre-registrada; ningún experimento se ejecuta sin pasar `tools/registro_global.py preregistrado`)  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Rama base: `fix/fundedsync-il-parity`

---

## 1. Referente rector y restricción de holdout (K32 / K51 / HOLDOUT-A5)

- **Referente único:** hacer más rentable (mayor `R/mes` neto después de fricción canónica y ejecución realista) y estable en el tiempo (menor `MaxDD`, mayor `%` de años/meses positivos, menor dependencia de una época o régimen único) la cartera operable.
- **Aviso crítico de datos (`NOTA_HOLDOUT_A5_VISTO_EN_NT8.md`):** como los meses `HOLDOUT` de A5 (`3/12` meses por año hasta `2026-09`) ya se vieron en las corridas exploratorias de NT8 de las familias `FUNDEDSYNC`, `SOM`, `Franklin`, `RQ5`, `CARRIL2` y `ES5N`, **la única confirmación limpia pendiente para promoción a dinero real es el holdout terminal (`>= 2026-10-01`) + forward secuencial (`e-proceso`)**.
- **Disciplina sobre `DESC` y `REP`:** los `6` experimentos (`43` pruebas acotadas totales) se diseñan y evalúan primero en `DESC` (`BH q = 0,10` + bootstrap por sesión + `diagnostico_grilla`), con paso a `REP` congelado sólo cuando haya potencia (`K49 >= 0,80`), evitando toda búsqueda ad-hoc sin pre-registro (`K51`).

---

## 2. Mapa de la Suite (`6` Experimentos · `43` Pruebas Pre-registradas)

| ID | Pre-registro | Familia | Pruebas | Palanca / Pregunta exacta | Impacto esperado en Rentabilidad y Estabilidad |
|---|---|---|---:|---|---|
| **EXP-1** | [`PREREGISTRO_EXP1_T_ESCALA.md`](PREREGISTRO_EXP1_T_ESCALA.md) | `FUNDEDSYNC` | `7` | **T invariante de escala:** reemplazar tope fijo `100 pts` (`86,5%` de trades capeados en `2026`) por `%` del precio (`0,6%–1,0%`) o `ATR20` (`0,50×–0,75×`) en `NQ` y `ES`. | Restaura coherencia geométrica del stop `2019–2026+` y mejora consistencia inter-época y transferencia en `ES`. |
| **EXP-2** | [`PREREGISTRO_EXP2_SOM_NOTICIAS.md`](PREREGISTRO_EXP2_SOM_NOTICIAS.md) | `SOM_QUANTLAB` | `7` | **`SOM_sin_finde` + Noticias + Riesgo Adaptativo:** evitar entradas `09:35 NY` cuando hay noticia `10:00 NY` (`21%` cierres forzados a las `09:58`), activar `use_adaptive_risk` causal y evaluar ancho de stop (`6×/8×/10× ATR14_M5`). | Elimina el recorte de `-4.945 pts` en `2020–2026` por cierres tempranos `NEWS_VETO` y estabiliza el `2022–2024`. |
| **EXP-3** | [`PREREGISTRO_EXP3_SIZING_VOLTARGET.md`](PREREGISTRO_EXP3_SIZING_VOLTARGET.md) | `CANASTA_CORRELACION` | `5` | **Sizing dinámico y control de racha:** comparar `fijo_micro`, `R_const`, `VolTarget_20d` causal (`[0,5×, 1,5×]`), `DD_step` (`0,5R` si `DD <= -8R`) y combinado sobre `Core3` y `MultiEstable` (`MNQ/MES` + `LucidFlex`). | Sube Calmar, acota `worst_day_R` y mejora `EV` y tasa de pase en cuentas prop (`LucidFlex 25K/50K`). |
| **EXP-4** | [`PREREGISTRO_EXP4_RQ5_SELECTIVIDAD.md`](PREREGISTRO_EXP4_RQ5_SELECTIVIDAD.md) | `RQ5_REGIMEN` | `5` | **`RQ5` selectivo:** probar `m=1,2`, corte `11:00 NY` y salto del slot `10:00` en días de noticia tier-1 `10:00 NY` en `NQ+ES`. | Reduce ruido y drawdowns (`2019`), sube `+0,038 → +0,044+ R/op` manteniendo `>35 ops/mes`. |
| **EXP-5** | [`PREREGISTRO_EXP5_ENSAMBLE_MULTIESTABLE.md`](PREREGISTRO_EXP5_ENSAMBLE_MULTIESTABLE.md) | `CANASTA_CORRELACION` | `12` | **Ensamble descorrelacionado `MultiEstable`:** incrementalmente agregar `SOM_sf`, `RQ5(NQ+ES)`, `C2_VZ(ES+NQ)`, `ES5N(ES)` y `Franklin(NQ)` sobre `Core3`, bajo `W0_cap3R` y `W5_ERC_cap3R` (`MaxOpenR = 3,0`). | Lleva `2020–2023` en `DESC` de `+23,4 R/año` a `+40,8 R/año` sin destruir `2024–2026` (`100%` años positivos, `Sharpe ~1,87`). |
| **EXP-6** | [`PREREGISTRO_EXP6_EJECUCION_Y_SATELITES.md`](PREREGISTRO_EXP6_EJECUCION_Y_SATELITES.md) | `EJECUCION_Y_SATELITES` | `7` | **6A (target-free):** medir costos `M2K/M6E/CL/EMD`. **6B (`4` pruebas):** entrada límite pasiva (`0/-1/-2` ticks) en ticks `2025–2026`. **6C (`3` pruebas):** cartera satélite pura en `ES/MES`. | Ahorra fricción por operación (sube neto directo) y habilita diversificación real `ES` + activos externos con costo `K33`. |

---

## 3. Guardas explícitas `NO_REPETIR` (heredadas de `FACTORES.jsonl`)

Ninguno de los 6 experimentos vuelve a probar combinaciones ya refutadas o marcadas `NO_REPETIR`:
- **No** transferir reglas de índices (`T, R, Z, V, W, A20, SOM, Franklin, Q, A1, P, E`) a **`GC` / Oro** (`F-ORO-TRANSFER-NO`, `0/60`).
- **No** correr **`RQ5`, `SOM`, `Franklin`, `A20`, `R`, `Z`, `V`, `W`** en **`YM`** (`F-SOM-TRANSFER-NO`, `A20_MULTIACTIVO`, `RQ5_REGIMEN`).
- **No** correr **`Z`** en **`RTY`** (`F-Z-RTY-REP-COLAPSA`), ni `A1, P, Q, W_tal_cual` (`F-FUNDEDSYNC-SIN-VENTAJA`), `HobbieCode`, `Dual Thrust GC X038`, `PREAPERTURA-NQ Intento 1`, `CVGAP-ES-C` ni `DRC/TORI` con fricción `> 0,08 R`.

---

## 4. Orden recomendado y registro en contador global (`K51`)

1. **Prioridad 1 (corregir cuello de botella de las dos pistas más grandes de `NQ`):** `EXP-1` (`T` escala) y `EXP-2` (`SOM_sin_finde` + noticias + riesgo adaptativo).
2. **Prioridad 2 (ejecución real + `RQ5` selectivo + ensamble):** `EXP-6B` (ahorro de slippage real en ticks), `EXP-4` (`RQ5`) y `EXP-5` (ensamble `MultiEstable` con las versiones ganadoras de EXP-1/2/4).
3. **Prioridad 3 (sizing y expansión multi-activo):** `EXP-3` (`VolTarget` + `LucidFlex`), `EXP-6A` (`costos.py` de `M2K/M6E/CL/EMD`) y `EXP-6C` (satélite puro `ES/MES`).

Para habilitar cualquier experimento antes de escribir su runner y medir resultados:
```powershell
python tools/registro_global.py preregistrado EXP1_T_ESCALA FUNDEDSYNC 7 docs/research/estabilidad_rentabilidad_20261125/PREREGISTRO_EXP1_T_ESCALA.md
python tools/registro_global.py preregistrado EXP2_SOM_NOTICIAS SOM_QUANTLAB 7 docs/research/estabilidad_rentabilidad_20261125/PREREGISTRO_EXP2_SOM_NOTICIAS.md
python tools/registro_global.py preregistrado EXP3_SIZING_VOLTARGET CANASTA_CORRELACION 5 docs/research/estabilidad_rentabilidad_20261125/PREREGISTRO_EXP3_SIZING_VOLTARGET.md
python tools/registro_global.py preregistrado EXP4_RQ5_SELECTIVIDAD RQ5_REGIMEN 5 docs/research/estabilidad_rentabilidad_20261125/PREREGISTRO_EXP4_RQ5_SELECTIVIDAD.md
python tools/registro_global.py preregistrado EXP5_ENSAMBLE_MULTIESTABLE CANASTA_CORRELACION 12 docs/research/estabilidad_rentabilidad_20261125/PREREGISTRO_EXP5_ENSAMBLE_MULTIESTABLE.md
python tools/registro_global.py preregistrado EXP6_EJECUCION_Y_SATELITES EJECUCION_Y_SATELITES 7 docs/research/estabilidad_rentabilidad_20261125/PREREGISTRO_EXP6_EJECUCION_Y_SATELITES.md
```
