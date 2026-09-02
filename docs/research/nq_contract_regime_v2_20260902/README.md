# Scan v2 fail-closed de régimen contractual NQ — 2026-09-02

**Estado: `ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED`. El scan pesado SÍ se ejecutó;
el manifiesto NO está certificado.**

Corrida en Kaggle sobre los 5 parquets NQ pre-holdout (119.153.201 filas),
autorizada explícitamente por Nico. Runner `nq_contract_regime_manifest_runner_v2`,
code_commit `90cb98a6a8829fafd6c48d8a63b358fba8200f14`.
`outcomes_accessed=false`, `holdout_accessed=false`.

## Qué corrigió respecto de `c3d575f` (invalidado, ver `NQ_CONTRACT_REGIME_C3D575F_AUDIT_2026-09-01.md`)

| | v1 `c3d575f` | v2 (esta) |
|---|---|---|
| fechas de fin de semana en el calendario | **28** | **0** |
| `complete_session` | inferido con 1 tick | requiere evidencia explícita |
| días elegibles | 263/265 | **0/237** (abstención) |
| rolls | 4 "confirmados" | 0 (no certifica sin evidencia) |

## Por qué 0 elegibles no es un fallo

Es el fail-closed funcionando: el scan genera
`nq_complete_session_evidence_template_v1.json` con **todo en
`complete_session=false`** (`approved=false`), y sin evidencia aprobada el
constructor no elige contrato ningún día. Kaggle marca el kernel como ERROR
porque el runner devuelve exit code 3 al abstenerse — es el comportamiento
diseñado, no un crash. El log no tiene traceback y los 5 contratos se
escanearon completos.

## Lo que el scan sí midió (dato real, sin certificar)

| contrato | filas | días obs. | rango | volumen | ticks en mantenimiento |
|---|---|---|---|---|---|
| NQ 09-25 | 13.624.675 | 42 | 20250801→20250919 | 14.906.724 | 0 |
| NQ 12-25 | 34.264.511 | 86 | 20250911→20251221 | 37.278.791 | 13 |
| NQ 03-26 | 30.825.016 | 79 | 20251211→20260320 | 33.404.698 | 10 |
| NQ 06-26 | 34.203.535 | 72 | 20260312→20260618 | 37.129.232 | 0 |
| NQ 09-26 | 6.235.464 | 19 | 20260608→20260630 | 6.385.687 | **363.601** |

Schema observado en Kaggle: las 13 columnas canónicas completas
(`ts_utc_ns, ts_local_ns, sequence, price_ticks, bid_ticks, ask_ticks, volume,
aggressor, tick_type, instrument, contract, source_file, source_row`) — **no se
podó ninguna columna** en el paquete subido.

### Dos anomalías que merecen decisión

1. **NQ 09-26 tiene 363.601 ticks dentro de la ventana de mantenimiento
   (16:00–17:00 CT), 5,8 % de sus filas**, contra 0/10/13 en los otros cuatro.
   Es el único contrato que fue **físicamente recortado** por el re-corte del
   holdout (`source_bytes` 305.577.901 → `bytes` 72.525.040, sha distinto, ver
   `effective_input_registry.json`). No está establecido si la anomalía es
   artefacto del recorte o real. **Sin resolver.**

2. La regla de completitud no puede ser `active_minutes == 1380`. De 298
   sesiones observadas, 219 (73,5 %) tienen exactamente 1380 minutos activos;
   de las 79 restantes, 48 caen en día hábil y su perfil muestra **tres
   familias distintas que no se deben confundir**:
   - **medias sesiones de feriado US**, con un patrón consistente de **1140
     minutos**: 20250901 (Labor Day), 20251127 (Thanksgiving), 20260119 (MLK),
     20260216 (Presidents Day), 20260525 (Memorial Day). Son sesiones
     *completas para ese día*, no datos faltantes. 20251225 (Navidad) aparece
     con 1 minuto / 1 tick.
   - **1377–1379 minutos** con cientos de miles de ticks: sesión completa con
     1–3 minutos sin ningún trade. Normal.
   - **contrato naciendo o muriendo**: NQ 09-26 el 20260608 (795 min, 6.555
     ticks), NQ 09-25 el 20250919 (480 min, 2.014 ticks). La sesión de mercado
     estuvo abierta; el que casi no operaba era ese contrato.

## Lo que falta, y es una decisión, no un cómputo

**No existe un calendario CME de research** que diga, por fecha: si hubo
sesión, si fue media sesión de feriado, y cuál era su duración esperada. Sin
eso no se puede distinguir *"faltan datos en la fuente"* de *"el mercado
estuvo cerrado / abrió medio día"* — que es exactamente lo que
`complete_session` debe certificar. Es el mismo bloqueo ya registrado para
`H-SWEEP-1_YM_PRERANGE` («construir calendario de research propio para YM, que
todavía no existe»).

Aprobar la evidencia de completitud es una decisión de Nico, reservada por
diseño del contrato v2. No se toma acá.
