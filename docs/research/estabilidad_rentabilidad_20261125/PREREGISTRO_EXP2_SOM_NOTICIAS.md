# EXP-2: `SOM_sin_finde` — Manejo Causal de Noticias `10:00 NY`, Riesgo Adaptativo y Ancho de Stop

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 en `DESC` (`BH q = 0,10`), `REP` con `K49 >= 0,80`; confirmación limpia en holdout terminal (`>= 2026-10-01`) + forward.  
Familia: `SOM_QUANTLAB` (`7` pruebas registradas).  
Antecedentes: `docs/research/candidatas_nt8_20261125/SOM_sin_finde/RESULTADO_SOM_SIN_FINDE_NQ_NT8.md`, `docs/research/candidatas_nt8_20261125/SOMEOD/RESULTADO_SOMEOD_NQ_NT8.md`, `docs/research/regimen_som_franklin_20261119/RESULTADO.md`, `F-SOM-TRANSFER-NO`.  
Diferencia respecto a NO_REPETIR: respeta `F-SOM-TRANSFER-NO` (corre **exclusivamente en `NQ`/`MNQ`** a la apertura `09:30 NY`, no en `YM/RTY/GC/6E`); estudia mejoras operativas netas del módulo ganador `SOM_sin_finde` bajo `NewsVetoCalendar` real.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (`K33`, `K36`, `K40`, `K48`, `K49`, `K51`, `K53`, `K55`, `K56`).  
Potencia previa: `SOM_sin_finde` genera ~`1.316` ops (`2020–2026 DESC+REP`), ~`16,5` ops/mes. El filtro `09:30–10:15 NY` modifica ~`274` operaciones afectadas (`20,8%`), dando MDE pareada de `~0,13 R` sobre los días con noticia.  
Diagnóstico de mecanismo: reporte `diagnostico_grilla` + desglose anual `2018–2025 DESC` separado en días CON noticia `09:30–10:15 NY` vs días SIN noticia `09:30–10:15 NY`, frecuencia efectiva, `PBO` de grilla y episodios ±3 meses (`K55/K56`).

---

## Justificación económica
En la verificación NT8 (`NT8_SOM_sin_finde_NQ_fijo1.csv`), `SOM_sin_finde` entra a las `09:35 NY` y el calendario de noticias tier-1 de las `10:00 NY` (`ISM`, `CB Consumer Confidence`, `JOLTS`, `New Home Sales`, etc.) **cierra a la fuerza el `21,5%` de sus operaciones (`357/1.660`) a las `09:58 NY`** tras apenas `23` minutos abiertas. Eso obliga a pagar spread/comisión completo sin dejar madurar el impulso de sesión ni el swing lunes–jueves (`-4.945 pts` brutos en Python `2020–2026`, dejando `2024` casi plano). Asimismo, `SOM` en QuantLab incluye un módulo de `use_adaptive_risk` causal desactivado en la configuración actual que conviene medir bajo el protocolo A5 estricto.

## Cómo podría refutarse
- Saltar entradas antes de noticia (`SOM_SKIP_1000`) o entrar tras el veto (`SOM_POST_1005`) produce igual o peor `R_neto_mini` mensual que abrir y cerrar a las `09:58 NY`.
- `use_adaptive_risk` empeora `Calmar` o concentra pérdidas en cambios de volatilidad (`2020`, `2022`).
- Ninguna variante supera al control `SOM_BASE_VETO` con `BH q = 0,10` en `DESC`.

---

## Variantes congeladas (`7` pruebas en `NQ`/`MNQ`, `2012–2025 DESC`)

| Variante | Regla de noticia `09:30–10:15 NY` | `use_adaptive_risk` | `atr_stop_mult` | Objetivo |
|---|---|---|---|---|
| `SOM_BASE_VETO` (Control) | Entra `09:35` y `NEWS_VETO` cierra `09:58` | `false` | `8,0` | Control actual NT8 |
| `SOM_SKIP_1000` | No abre si hay evento tier-1 en `[09:30, 10:15]` NY (calendario conocido de antemano) | `false` | `8,0` | Evitar trades abortados a 23 min |
| `SOM_POST_1005` | En días con evento tier-1 `10:00 NY`, evalúa `C(10:05) vs EMA12` a las `10:05 NY` (tras veto) | `false` | `8,0` | Capturar tendencia post-dato |
| `SOM_ADAPT_RISK` | Control + `NEWS_VETO` | `true` (`QuantLab`) | `8,0` | Medir ajuste causal por régimen vol |
| `SOM_SKIP_ADAPT` | `SOM_SKIP_1000` | `true` (`QuantLab`) | `8,0` | Combinación limpia noticia + vol |
| `SOM_ATR6_SKIP` | `SOM_SKIP_1000` | `false` | `6,0` | Sensibilidad stop más ceñido (`+R/año`) |
| `SOM_ATR10_SKIP` | `SOM_SKIP_1000` | `false` | `10,0` | Sensibilidad stop más holgado (`-ruido`) |

## Criterio de decisión
1. Evaluación en `DESC` (`2012–2025` y régimen post nov-`2017`): `R_neto_mini`, `R/año`, `MaxDD_R`, `Sharpe`, `%` años positivos y diferencia pareada contra `SOM_BASE_VETO` (`BH q = 0,10`).
2. Toda variante ganadora en `DESC` pasa a `REP` congelado sólo si alcanza potencia `K49 >= 0,80` y reduce el bache `2022–2023/2024` sin sacrificar `2025–2026`.
