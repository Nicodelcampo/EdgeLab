# Espejos: juicios de Nico por tandas de a tres (ES ene–mar 2026, 100t) — resultado target-free (2026-09-28)

**Herramienta:** `tools/build_espejo_triads.py` + `viewer/nt8_bridge/espejo_triads.html`. **Juicios:** `viewer/nt8_bridge/labels/espejo_triads_ES_2026Q1_100t.json`. Ciego al 75 % de la vuelta (sin desenlace). 32 tandas, 96 espejos (58 tipo TBZ: eficiencia ≥ 0,6, ≥ 34 t en ≤ 20 velas; 38 de otros estratos).

## Coincidencia entre el orden de Nico y las métricas del kernel ESPEJO-IND (ρ de Spearman, rango vs métrica)
| Métrica | ρ | Tandas |
|---|---|---|
| S (compuesto de percentiles) | +0,76 | 10 (sólo donde hay referencia previa) |
| sim_vel | +0,34 | 32 |
| vel | +0,35 | 32 |
| forma | +0,31 | 31 |
| eficiencia de la ida | +0,21 | 32 |
| sim_t (tiempo por nivel, semejanza v2) | **+0,05** | 32 |
| velas de la ida / volumen por tick | −0,10 / −0,11 | 32 |

## Otras lecturas
- Rango medio TBZ 1,90 vs otros 2,16: leve preferencia por TBZ; Nico reconoce espejos en ambos estratos.
- «¿Alguna es un espejo de verdad?»: sí en 32/32 → no discrimina con este muestreo (faltan tandas de control).
- **Fuga detectada por Nico:** en 2/96 gráficos la vela que cruza el 75 % ya toca A (vuelta de una vela gigante): se ve el desenlace. Ambos quedaron en el último lugar. Corrección para próximas tandas: cortar en la vela anterior cuando la vela de corte toca A.

## Consecuencias (sin mirar retornos)
- `sim_t` **no** representa la semejanza que Nico ve: no usarla como definición de «parecido».
- Velocidad y forma capturan una parte (ρ ≈ 0,3); ninguna métrica actual representa bien el juicio.
- Próximo paso sugerido: una métrica preelegida (velocidad + forma) validada contra estas 32 tandas (validación, no selección entre muchas), o que Nico describa en palabras qué mira al ordenar.
