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

## Semejanza «a lo Nico» (28/09): rasgos de su descripción, validados contra sus órdenes
Criterio de Nico: simetría ida/vuelta; retroceso en la ida sin retroceso en la vuelta baja; velocidad espejada sube; impulso fuerte contra vuelta escalonada baja. Herramienta `tools/espejo_semejanza_nico.py` (rasgos definidos por su descripción, dada después de ordenar; un solo modelo, sin selección entre variantes).
| Rasgo | Aciertos en pares (96; azar 50 %) |
|---|---|
| DTW de caminos normalizados | 77 % |
| n.º de retrocesos ≥ 10 % W espejados | 75 % |
| profundidad de retroceso | 70 % |
| eficiencia ida vs vuelta | 70 % |
| velocidad espejada | 66 % |
| **logística (5 rasgos), dejando una tanda afuera** | **80 %** |
Pesos del modelo completo: DTW 1,49 y n.º de retrocesos 1,40 dominan; velocidad 0,31; profundidad 0,18; eficiencia 0,03. **Falta validación fuera de muestra** con tandas nuevas (descubrimiento sep–dic 2025) antes de congelarla como definición operativa.

## Validación fuera de muestra (28/09, modelo congelado en `ESPEJO_SEMEJANZA_NICO_CONGELADA_20260928.json` antes de generar la tanda)
Tanda nueva: ES oct–dic 2025, 100t, 31 tandas (93 pares), fuga del corte corregida. Juicios: `viewer/nt8_bridge/labels/espejo_triads_ES_2025Q4_100t.json`.
- **Modelo congelado: 73 % de pares (IC 95 % por tanda: 62–83 %) → PASA** el criterio fijado (≥ 70 %).
- Por rasgo: **DTW 75 %** (estable: 77 % en entrenamiento); velocidad 63 %; eficiencia 63 %; profundidad de retroceso 59 %; **n.º de retrocesos 55 %** (75 % en entrenamiento: no se sostiene solo).
- «¿Alguna es un espejo de verdad?»: sí en 30/31.
- **Lectura:** la forma del camino ida vs vuelta (DTW) es el rasgo robusto de la semejanza de Nico; el conteo de retrocesos se sobreajustó en la primera tanda. El modelo congelado queda como **definición operativa de «parecido»** para futuras pruebas (se usa tal cual, sin reajuste). Alternativa más simple y casi igual de buena: DTW solo.
