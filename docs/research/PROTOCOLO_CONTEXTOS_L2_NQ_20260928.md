# Protocolo de entrenamiento de contextos L2 (4 climas) en NQ — PRE-REGISTRO target-free (2026-09-28)

**North Star:** `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`
**Estado:** escrito antes de extraer ni entrenar. Target-free: no mira retornos, P&L ni MAE/MFE. Auditoría pedida a GPT-6 Sol (entrada 050) **antes** de correr.
**Código:** `edgelab/context/l2_gate.py` (features, overlay tóxico, etiquetado, join), `edgelab/context/hmm3.py` (HMM de 3 estados), rama `work/futures-l2-context-foundation-20260825` mergeada.

## Datos
- NQ, catálogo `docs/research/contract_regimes/L2_sessions_catalog_20260927.json`: **60 sesiones** (26-jun → 23-sep), contrato líder por sesión, roll al 12-26 el 15-sep; mediana de liquidez sólo con el pasado (control de calidad de fin de día).
- Reloj: `ts_us` es hora de pared ART; las franjas horarias se calculan en hora de Chicago.
- Parquets `E:\l2_parquet\NQ_{09,12}-26\{l2_depth,l1_quotes}` (convertidos con el conversor corregido: unidad 100 ns por archivo).

## Split
- **Entrenamiento:** las primeras **20** sesiones del catálogo. **Evaluación:** las 40 restantes, etiquetadas sólo hacia adelante con el modelo congelado.
- Sin re-entrenamiento en esta corrida (la ventana creciente queda para cuando haya más sesiones).

## Modelo
- 6 variables del HMM (config por defecto de `HMM3Config`) + overlay tóxico (5 variables, umbrales q90/q75 de entrenamiento).
- **Desestacionalización:** perfil por franja de 5 min (hora de Chicago) estimado sólo en entrenamiento; log(valor/mediana) para variables positivas, diferencia para el resto. Guardado dentro del modelo con su hash.
- **Semillas:** 10 inicializaciones aleatorias (semillas 1–10); se elige la mejor verosimilitud de entrenamiento; se publica el acuerdo de etiquetas de cada semilla con la elegida.
- Sticky: 3 minutos de confirmación y posterior mínimo 0,45 (los de la spec).

## Compuertas target-free (antes de cualquier uso con eventos)
1. **Estabilidad:** acuerdo mínimo entre semillas ≥ 0,80. Si no, el clima no es estable: se publica y no se usa.
2. **Cobertura** de etiquetas en evaluación ≥ 99 % de los minutos elegibles.
3. **Persistencia y cambios:** duración mediana de cada estado y tasa de cambio por hora; se publican.
4. **No es sólo la hora:** proporción de cada estado por franja horaria; si un estado queda > 80 % concentrado en una franja de 2 h, se reporta como «estado horario».
5. **Deriva por contrato:** distribución de estados antes y después del roll del 15-sep.
6. **Uso con eventos (futuro):** ≥ 40 sesiones de evaluación **con eventos elegibles** en cada celda (G-operable / G-stress), ids de sesión publicados; join con `attach_context_at_t0` (fila anterior + minuto publicado + edad máxima), sólo eventos del **mismo stream** L2.

## Cómo podría refutarse (que los climas sirvan)
- Acuerdo entre semillas bajo, estados que son sólo la hora del día, o persistencia de 1–2 minutos (ruido).
- Más adelante, con eventos: ninguna diferencia del estimand entre celdas con MDE adecuado (eso ya mira retornos y requiere su propio manifiesto y OK de Nico).

## Enmienda 1 (28/09, tras la auditoría 051; antes de extraer)
- Runner nuevo `tools/build_l2_contexts_nq.py` con **preflight que aborta** (60 sesiones exactas, contrato, archivos y tamaños, unidad 100 ns por archivo, plan congelado con hash `f88ccbfc…`).
- Extractor: inversión de reloj intercalada, BBO > 60 s al cierre y libro invalidado vuelven el minuto **no elegible**; trades sin BBO fresca (≤ 5 s) se clasifican por tick rule y se cuentan; ventanas por tiempo transcurrido, sin cruzar huecos.
- Overlay `toxic` **desestacionalizado** también.
- Verosimilitud final recalculada con los parámetros guardados.
- Reporte con **PASS/STOP automático** sólo sobre evaluación: cobertura ≥ 99 %, estabilidad por semilla y **por estado** ≥ 0,80 en evaluación, **STOP por estado** si > 80 % de sus minutos cae en 2 h, **STOP global** si un clasificador de sólo-hora acierta ≥ 90 %, deriva antes/después del roll (15-sep).
- Compuerta de eventos (≥ 40 sesiones con eventos por celda): con 40 sesiones de evaluación se espera **SIN_POTENCIA**; no se relaja.
- Gobernanza: preguntas condicionadas por estos climas se confirman sólo en oct+ (adenda de A3).
