# Para el auditor (Notion): familia TBZX, «espejo» de la franja de impulso — 2026-09-25

**Qué auditar:** si los controles de TBZX están bien construidos y si el efecto es real o un sesgo de selección.
**Fuente completa:** `docs/research/MANIFIESTO_TBZX_ESPEJO_20260925.md` (§1–§10d, escrito por partes, siempre antes de cada corrida). Código: `tools/tbzx_espejo.py`, `tools/tbzx_iter2.py`; test `tests/research/test_tbzx_path_metrics.py`. Ledger: `artifacts/hippocampus/tbzx_20260925.jsonl`.

## La idea (Nico, observando en el visor)
Impulso A→B en velas de 25 ticks (≤ `maxBars` velas, ≥ `minW` ticks, eficiencia ≥ 0,6; fin por retroceso 0,3·W o por tope de velas). Después, el precio sale de la franja (normalmente por B) y al volver **entra más hondo y llega a A** más que lo esperable. Sin entradas ni P&L: sólo el camino del precio. Exploración ES jul-2025 a mar-2026 (181 sesiones); abr–jun y el holdout están intactos.

## Qué se midió y qué pasó (métrica principal: sale por B y llega a A; configuración de Nico 20 velas / 17 t)
| nulo (otra sesión, misma hora ± 1 h) | real / nulo |
|---|---|
| misma geometría a la misma hora | 0,157 / 0,049 (la mitad resultó ser volatilidad) |
| N-VOL: misma actividad previa | 0,139 / 0,086 |
| N-REV: tramo del mismo tamaño que recién dio la vuelta, lento o sucio | 0,145 / 0,081 (+6,3 pts, FDR 12/12; **sesiones positivas 55 % < piso 60 %**) |
| N-VOLSTR: actividad + estiramiento vs EMA20 | el contexto de estiramiento **desaparece** (descartado) |
| NQ, contra N-REV | **no replica** (−0,7 pts) |
| **N-REVVOL: N-REV + misma actividad (primario)** | **0,138 / 0,173 (−3,5 pts; 26 % sesiones+): el efecto MUERE** |

## Preguntas concretas para el auditor
1. ¿N-REVVOL cierra el sesgo de actividad de N-REV, o queda otro confundidor (p. ej., que el impulso rápido deja el precio con momentum de reingreso por construcción del fin por retroceso)?
2. ¿Los fantasmas de **otra sesión a la misma hora** son válidos para una propiedad que depende del régimen del día? ¿Hace falta un nulo intra-sesión posterior al horizonte (permitido por CTRL_TIMING_V1)?
3. ¿Cómo interpretar un efecto significativo en promedio pero positivo sólo en el 55 % de las sesiones?
4. ¿La divergencia ES/NQ se explica por la escala (W elegido por conteo en NQ: 68 t) o invalida la idea?
5. Integridad: la selección de contrato se pasó a la regla canónica (líder de la sesión anterior; proxy = ticks porque los manifiestos no traen volumen). ¿Alcanza el proxy?

## Estado de integridad
Detector con paridad exacta con el visor (707/707 y 11.594/11.594). Auditoría CTRL_TIMING_V1: PASS. Una observación del Brain registrada por error se invalidó (OBS-TBZX-ESPEJO-ES-V2). Pendiente: verificación tick a tick del toque de A (las métricas usan máximos y mínimos de vela).
