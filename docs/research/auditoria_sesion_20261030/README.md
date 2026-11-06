# Auditoría de la sesión 2026-10-29/30 (gonzasib-claude, Gonza-PC)
Punto de entrada para un auditor externo. Todo lo de abajo está en esta carpeta salvo donde se indica. Holdout (>= 20261001): NO abierto por este agente.

## Reproducir
- Canasta y límite: `python scripts/canasta_12.py` desde una carpeta con `bt_res/` y `btt_res/` descomprimidos de `resultados/`. Esperado: 519 ops, 116 sesiones, +0,12 R, t 1,74, peor día -7,6 R.
- Backtests: REP sobre 20250805..20260930, código e1e817d2. Slugs en `*_handles*.json`. Operaciones por regla en `resultados/`. `perillas`, `codigo` y `modulos` de cada JSON fijan qué corrió.
- Perturbación: `resultados/pt_res`, ±1 nivel en perillas ordinales.
- Almacén HFT: `scripts/lanzar_almacen_hft.py`, rama del PR #159 (`refs.txt`). Parquet fuera del repo, hash en `resultados/zonas_parquet.sha256`.
- Filtros y momentum: `patch_filtros_lado_features.diff` sobre e1e817d2 (no mergeado). Kernels FLT en curso; `resultados/flt_res` puede estar incompleto.

## PR
#155, #156, #157, #158 (canasta_regimen; mergeado con 5 fallos de CI heredados de la base), #160 y #161 (pre-registro). #159 PRERANGE-HFT: abierto, CI sin revisar.
Pre-registro vigente: `docs/research/canasta_12_20261030/PREREGISTRO.md`.

## Decisiones tomadas por delegación de Nico en sala
Criterio del holdout, stop -2 R, tamaños, merges de #158, #160 y #161.

## Puntos débiles que el auditor debería atacar
1. El OOS abr-sep se miró varias veces antes del pre-registro, incluida la elección de tope sobre DESC ya conociendo OOS. t 1,74 no es limpio.
2. U1-YM y U1-ES tienen DESC desde 2024 en el acta; estos backtests arrancan en 20250805, así que desvíos y comparaciones DESC son de un tramo recortado.
3. CVGAP tiene OOS de campaña hasta 20260925; la REP pide hasta 20260930.
4. El bootstrap de propfirm recorta el día exacto en el stop: no modela deslizamiento ni trailing intradía. Es optimista. Axi Select: reglas sin fuente oficial (7 % o 10 %).
5. Listón del holdout (t >= 1,28, ~20 sesiones) elegido por este agente, sin potencia para confirmar edge.
6. Prompt de SV1: su primera versión tenía un error de pesos, corregido en #161. El cargador sellado puede no cubrir todas las reglas.
7. Un subagente vio cifras de octubre en `DESCUBRIMIENTO_U1_CRUZADO_REGISTRO.md:38`. Dice no haberlas usado; no es verificable.
8. Lectura de 650 posts: muestra filtrada por subagente, no completa. Hipótesis de `lado` y umbrales son propuesta, no resultado.
9. `REVISION_V2_SV1_20261029.md` sección D: las cifras DESC son del canal reciente. Sin corregir.
10. HFTNQ satura en ES (4.845 zonas por sesión) y casi no da zonas en YM (36). Paridad certificada solo sobre ES.
11. `canasta_12.py` contiene el bootstrap con semilla fija; los escenarios se corrieron además en un script inline con los mismos parámetros, no archivado.
12. El patch de filtros no tiene tests; asume que `k` indexa el contexto del sensor. Sin verificar contra una operación conocida.

## Estado de lo sin hacer
Backtest independiente, retornos barajados, filtros V2, TensorTrade, finvizfinance, informe multiagente, reconciliación de SV1.

## Proceso persistente
Tarea `EdgeLabBtWorker` en Gonza-PC, cada 5 min, `scripts/bt_worker.py`. Log: `bt_worker.log` (copia al momento del commit).
