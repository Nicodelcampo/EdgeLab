# Respuesta Forense a la Revisión de Claude (2026-11-27)

Estado: VIGENTE — audita punto por punto [REVISION_CLAUDE.md](REVISION_CLAUDE.md) (commits `a6c643e4` y `71ae1583`), verifica costos canónicos de `Global_VolComp_M1DK` en `NKD` y `GC`, corrige la causa raíz de `HRP = EQ` y fija el plan limpio de avance hacia frentes sin iteración de `REP`.

## 1. Qué aceptamos íntegramente de la revisión de Claude

| Objeción de Claude | Verificación independiente | Acción adoptada |
|---|---|---|
| `Global_VolComp_M1DK` no es una familia independiente de `Carril 2`: dispara con `VIX/VXN/GVZ` de EE. UU. | Confirmado: correlación mensual contra `C2_VZ + C2_EVRP` de `ES/NQ` = **`0.475`** (`14–26`, `n=109`) y **`0.502`** (`21–26`, `n=51`). El `0.130` era sólo contra `Carril2_Sell16` (que excluye `VZ/EVRP`). En los `109m` completos `DR t = 1.37` (`SR = 0.454`). | No contarlo como frente independiente en la potencia de `Super-Canasta v3`; reclasificarlo como transferencia regional. |
| `CRIPTO-PIT v1 -> v2 -> v3` iteró sobre la misma `REP` (`12m`) | Correcto: la `REP Sh = 1.72` de `v3` es exploratoria (`v1 -> v2 -> v3` miraron los mismos `51m`); `Cripto_v3_XSMOM_BAB` (`Sh = 1.47`) es selección post-hoc hasta pre-registrarse aparte. | **Detener iteraciones sobre `CRIPTO-PIT v1–v3`.** La única prueba limpia pendiente de esa serie son los `18m` de `HOLDOUT A5`. |
| Higiene de CI (`test_existente`, catálogo, `K55/K56`, `Estado:`, enlaces relativos) | Aceptado: Claude corrigió las copias de funciones, regeneró índices/catálogo y añadió `Diagnóstico de grilla:` / `Episodios:`. | Incorporado en todos los scripts y reportes nuevos (código compartido por `import`, enlaces relativos, regeneración completa de índices/catálogo antes del push). |

## 2. Verificación de costos canónicos en `Global_VolComp_M1DK` (`NKD` y `GC`, cierre de `F-GLOBAL-VOLCOMP-M1DK-B`)

Auditamos las operaciones ya generadas (`0` pruebas nuevas) usando `edgelab.costos.friccion_rt_puntos`:
- **`GC` (`XAUUSD`, medido canónico `0.605 USD/oz` ~ `3.8–4.1 bps` equiv vs `8 bps` proxy)**: `C2_EVRP_Oro_GC` (`256` ops `DR`, `fricR = 0.0157R`) mejora a `DESC Sh = 0.198`, `REP Sh = 0.919`, `DR Sh = 0.357` (`21–26 = 0.617`); `C2_VZ_Oro_GC` (`fricR = 0.0239R`) sube a `DR Sh = 0.196` (`REP = 0.813`).
- **`NKD` (`JPNIDXJPY`, estimado K33 `21.064 pts` ~ `9.1–9.3 bps` equiv vs `8 bps` proxy)**: `C2_VZ_Nikkei_NKD` (`295` ops `DR`, `fricR = 0.0506R`) mantiene `DR Sh = 0.415` (`DESC = 0.406`, `REP = 0.460`, `21–26 = 0.789`); `C2_EVRP_Nikkei_NKD` (`171` ops `DR`, `fricR = 0.0350R`) baja a `DR Sh = 0.129` (`21–26 = 0.734`).
- Respaldo completo en [`COSTOS_CANONICOS_NKD_GC.json`](../frentes_ortogonales_20261127/COSTOS_CANONICOS_NKD_GC.json). (`DAX`, `EuroStoxx` y `FTSE` siguen sin entrada canónica en `config/costos/costos_canonicos.json`, por lo que `16 bps` sigue siendo la cota adversa válida).

## 3. Dos precisiones técnicas sobre el diagnóstico de Claude

1. **Causa raíz de `HRP_Weekly == EQ` (no fue ausencia de `sklearn`):** `scipy` y `sklearn` estaban instalados (`LedoitWolf` se ejecutó en `156` semanas `DESC`), pero como los `4` frentes ya venían estandarizados a varianza unitaria y con correlación muestral cercana a cero, `LedoitWolf().fit(sub_w)` aplicó **`shrinkage_ = 1.0000`** exacto (`cov = 0.243 * I_4`), reduciendo la matriz de covarianza a una identidad escalada y forzando `HRP = [0.25, 0.25, 0.25, 0.25]`. En `Super-Canasta v3` se corrige usando covarianza muestral con regularización diagonal acotada (`0.85 * S + 0.15 * diag(S)`).
2. **Aritmética de potencia del pozo (`supercartera_v2` §3):** el `0.539` dinámico (`63m`, `0.7x`) **no** aplicó una fórmula asumiendo `rho = 0` entre `Global_VolComp` y `Carril 2`; se calculó empíricamente desde las series mensuales combinadas frente a `Carril2_Sell16` (cuya correlación observada es `0.099` en `14–26` porque `Carril2_Sell16` excluye `VZ/EVRP`). Lo que sí infla ese `0.539` frente al `0.464` de `marco_sin_forward` es usar la `REP` iterada de `CRIPTO-PIT v3` y el tramo reciente `21–26` de `Global_VolComp`.

## 4. Ruta para avanzar sin iteración de `REP` ni sesgo CME

1. Abrir **dos familias genuinamente nuevas y ortogonales**, pre-registradas sin grilla paramétrica antes de mirar datos:
   - **`MACRO_RISK_PREMIA` (`2006–2026-09`)**: `5` primas multi-clase (`Sectores XSMOM beta-neutral`, `Sectores BAB`, `Países XSMOM beta-neutral`, `Curva/Crédito de tasas ^TNX/^IRX`, `Tendencia multi-velocidad no-equity`) sobre ETFs `adjclose` limpios (`63m` de `HOLDOUT A5`, `0` iteración de `REP`) para reforzar el pozo limpio de `63m` junto con `Carril 2`.
   - **`CRIPTO_OFI_PIT` (`2021–2026-09`)**: información **no-OHLC** real de flujo de órdenes agresoras (`taker_buy_quote_volume`, `quote_volume`, `count`) en `226` perpetuos PIT, separando señales de flujo de órdenes respecto de `XSMOM`.
2. Integrar ambos en **`SUPERCARTERA v3`** separando estrictamente el **pozo `63m` cero-iteración (`Carril 2 + MACRO_RISK_PREMIA`)** del pozo completo y del bloque descriptivo CME.

Aporte al referente: concilia todas las objeciones válidas de Claude, documenta los costos canónicos de `NKD/GC`, explica por qué `LedoitWolf` colapsó `HRP` a `1/N` y abre un frente de `20+` años con `63` meses sellados limpios para subir la potencia conjunta sin esperar forward.
