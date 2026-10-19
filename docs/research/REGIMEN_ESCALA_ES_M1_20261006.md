# ¿Persiste la dirección o la tendencia en escalas mayores? — ES, M1 2015–2026 — 2026-10-06

Decisión de Nico: opción 1 del repaso (cambiar de escala antes que de indicador). Target-free respecto del P&L.
Script: `tools/regimen_escala_m1.py` (+ bloque diario). Datos: M1 de NT8, serie del líder por calendario de roll, 3.458
sesiones (2015-01 → 2026-09-30, holdout excluido). JSON: `regimen_escala_ES.json`.

## Intradía (barras de 5–60 min, ventanas de 30 min a 6 h; n entre 5 k y 130 k ventanas)
| escala | ac retorno (ventana → siguiente) | ac eficiencia (nulo) | ac amplitud desestacionalizada |
|---|---|---|---|
| 5 min, 30 min–2 h | +0,001 / +0,003 / −0,007 | −0,01 (≈ +0,005) | 0,81 / 0,78 / 0,75 |
| 15 min, 1,5–6 h | −0,014 / **−0,027** / +0,002 | −0,01 (≈ +0,005) | 0,79 / 0,69 / 0,73 |
| 30 min, 3–6 h | +0,007 / −0,018 | ≈ 0 | 0,74 / 0,62 |
| 60 min, 6 h | −0,001 | +0,006 | 0,62 |

- **Dirección:** no persiste. Lo único distinto de cero es una **reversión leve** a 3 h (−0,027, unos 3 SE; −0,045
  cuando la ventana previa venía "en tendencia").
- **Tendencia (eficiencia):** no persiste en ninguna escala; es igual o un poco peor que el nulo.
- **Amplitud:** persistente en todas, **incluso desestacionalizada** (0,62–0,81). No es sólo la hora del día.

## Escala diaria (retorno apertura → cierre de sesión, para no contaminar con los rolls)
- 1 sesión: **ac −0,089** (unos 5 SE): reversión día a día.
- 5 sesiones: −0,045. 20 sesiones: −0,098. 60 sesiones: −0,29 (n = 56, ruido).
- P(mismo signo en bloques de 20 sesiones) = 0,54. Rango diario muy persistente (0,74–0,86).

## Lectura
En **ES**, de 30 minutos a semanas, **no hay persistencia de dirección ni de tendencia**. Lo que hay es reversión leve
(intradía a 3 h, y día a día). Los filtros de tendencia tipo EMA/momentum no tienen base en este instrumento a ninguna
de estas escalas; si algo, el signo útil sería **contrario**. La volatilidad sí es predecible en todas las escalas.

Coherente con la literatura: el momentum de series de tiempo está documentado en futuros **diversificados** (commodities,
divisas, tasas) a horizontes de meses. Los índices accionarios son el caso más débil.

## Siguiente (barato y con datos que faltan)
- Repetir en **otra clase de activo**: oro (GC/MGC), 6E, ZB. Hace falta el M1: correr el addon `EdgeLabMinuteHistory`
  con las tandas pendientes (sólo está bajado ES).
- Pre-registrar la **reversión** intradía a 3 h y la diaria como hipótesis formal **direccional**: es lo primero con
  signo estable que aparece. Requiere manifiesto, porque mira retornos.
