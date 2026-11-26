# EXP-4: `RQ5` Selectivo — Severidad de Banda (`m`), Corte Horario y Veto Pre-Noticia `10:00 NY`

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 en `DESC` (`BH q = 0,10`), paso a `REP` congelado con `K49 >= 0,80`; confirmación limpia en holdout terminal (`>= 2026-10-01`) + forward.  
Familia: `RQ5_REGIMEN` (`5` pruebas registradas).  
Antecedentes: `docs/research/rq5_regimen_20261119/RESULTADO.md`, `nt8/strategies/EdgeLabRQ5.cs` v1.1 (`NewsVetoCalendar`), `docs/research/candidatas_nt8_20261125/ESTABILIDAD_Y_MATRIZ_ACTIVOS_20261125.md`.  
Diferencia respecto a NO_REPETIR: no incluye **`YM`** (negativo en `RQ5_REGIMEN`, `-0,022 R`) ni índices externos sin costo; focaliza en los dos índices positivos confirmados en desarrollo (`NQ` `+0,082 R`, `ES` `+0,093 R p=0,007`, `8/8` años `+`), probando la dosis-respuesta observada en el diagnóstico de grilla (`m`, `corte`) más la nueva compuerta causal `NewsVetoCalendar` en el slot `10:00 NY`.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (`K33`, `K36`, `K40`, `K48`, `K49`, `K51`, `K53`, `K55`, `K56`).  
Potencia previa: fábrica `NQ+ES` genera ~`1.453` ops en `DESC` (`2018–2025`, `~20 ops/mes`). Las restricciones a `m=1,2` o `corte=11:00` dejan ~`950–1.150` ops (suficiente para `MDE ~0,09 R` en contraste directo en días filtrados).  
Diagnóstico de mecanismo: reporte `diagnostico_grilla` en `RQ5` (`N_eff`, Spearman operaciones vs `R`, contraste trades retenidos vs filtrados, episodios ±3 meses `K56` — especialmente impacto sobre el peor año `2019` de `NQ`).

---

## Justificación económica
En `docs/research/rq5_regimen_20261119/RESULTADO.md` la grilla mostró relación monotónica negativa entre cantidad de operaciones y calidad neta (`Spearman = -0,552`): subir `m` de `1,0` a `1,2` eleva la media de `+0,038 → +0,044 R`, y cortar a las `11:00 NY` en vez de las `11:30` evita rupturas tardías con menor persistencia de flujos de apertura (`+0,043` vs `+0,032`). Además, al evaluar `EdgeLabRQ5` con `NewsVetoCalendar` activo en NT8, el slot de las `10:00 NY` coincide exactamente con publicaciones tier-1 de las `10:00 NY`: omitir la entrada de las `10:00` los días con evento macro evita abrir inmediatamente antes de un spread spike y luego esperar señal válida a las `10:30`.

## Cómo podría refutarse
- Subir `m = 1,2` o cortar a las `11:00` reduce el `R/mes` total más de lo que mejora `R/op` (menos frecuencia útil para el ensamble `MultiEstable`).
- El veto `10:00` en días de noticia empeora el neto frente a operar normal con `NewsVeto` o ninguna de las `4` variantes bate a `RQ5_FAB` en `BH q = 0,10`.

---

## Variantes congeladas (`5` pruebas en `NQ + ES`, `2018–2025 DESC`, `L = 60, s = 0,45, tp = 2,0`)

| Variante | `m` | Corte horario NY | Regla noticia `10:00 NY` | Propósito |
|---|---|---|---|---|
| `RQ5_FAB` (Control) | `1,0` | `11:30` | Normal (aplica cierre `NEWS_VETO`) | Control fábrica |
| `RQ5_M12_C1130` | `1,2` | `11:30` | Normal | Probar mayor exigencia de ruptura |
| `RQ5_M10_C1100` | `1,0` | `11:00` | Normal | Filtrar entradas tardías de baja persistencia |
| `RQ5_M12_C1100` | `1,2` | `11:00` | Normal | Combinación selectiva de alta calidad |
| `RQ5_SKIP_1000_NEWS` | `1,0` | `11:30` | Saltea slot `10:00` si hay noticia tier-1 `[09:50, 10:10]`, habilita `10:30+` | Evitar falsa ruptura pre-dato `10:00 NY` |

## Criterio de decisión
1. Evaluación en `DESC` (`2018–2025`, `NQ`, `ES` y combinado `NQ+ES`), reportando `R_neto`, `R/mes`, `Sharpe`, `MaxDD_R` y años positivos (`BH q = 0,10` en `5` pruebas).
2. Se promueve a `REP` (para reemplazar o complementar `RQ5_FAB` en `MultiEstable`) la variante que mejore simultáneamente `R/op` y `Calmar` en `DESC` sin caer debajo de `14 ops/mes` combinadas en `NQ+ES`.
