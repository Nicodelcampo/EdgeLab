# IPC-NIVEL-MES — resultado del descubrimiento (2026-09-28)

**Veredicto: 1 de 8 pruebas sobrevive (BH q = 0,10), y va en contra de la hipótesis del imán.** En techos, el nivel con
≥ 3 visitas es barrido **6,2 pp menos** que un pivote suelto emparejado. Mismo resultado con y sin febrero.
OK de Nico (28/09). Código `tools/ipc_nivel_run.py`, commit `517150f6`, **árbol limpio**. Artefactos
`artifacts/ipc_nivel/{eventos,reporte}.json`. MES 25t, Lucid, 171 sesiones ago-2025 → mar-2026, precio de trade.
3.381 zonas, 3.315 controles emparejados.

| Prueba | Variante | Lado | n zona / control | Estimado | IC 90 % | p | MDE 80 % | barre zona / p0 / control |
|---|---|---|---|---|---|---|---|---|
| P1 | v2 | techo | 1.751 / 1.723 | −0,018 | [−0,035; −0,001] | 0,078 | 0,029 | 0,425 / 0,443 / 0,487 |
| **P2** | **v2** | **techo** | | **−0,062** | **[−0,088; −0,035]** | **< 0,001** | 0,044 | **sobrevive** |
| P1 | v2 | piso | 1.630 / 1.592 | +0,021 | [+0,002; +0,042] | 0,078 | 0,035 | 0,461 / 0,441 / 0,490 |
| P2 | v2 | piso | | −0,032 | [−0,058; −0,007] | 0,042 | 0,044 | |
| P1 | N4 | techo | 782 / 765 | −0,014 | [−0,041; +0,015] | 0,41 | 0,048 | |
| P2 | N4 | techo | | −0,051 | [−0,090; −0,017] | 0,028 | 0,063 | |
| P1 | N4 | piso | 735 / 711 | +0,033 | [+0,002; +0,062] | 0,078 | 0,051 | |
| P2 | N4 | piso | | −0,040 | [−0,086; +0,003] | 0,13 | 0,075 | |

## Lectura
- **No es imán.** Contra el paseo sin memoria, el nivel se barre más o menos como el azar (techos −1,8 pp, pisos +2,1 pp,
  ninguno sobrevive).
- **Es lo contrario de un imán, respecto de cualquier extremo reciente:** un pivote suelto se barre 4–5 pp **más** que el
  azar (0,49 contra 0,44). El nivel con ≥ 3 visitas se barre **menos** que ese pivote en las 4 celdas (−3 a −6 pp);
  sobrevive la de techos v2. El nivel **resiste** más que un extremo cualquiera.
- Asimetría techo/piso: en pisos el nivel se barre algo más que el azar (+2 a +3 pp) y en techos algo menos. Descriptivo;
  en el período el MES fue mayormente alcista.
- **Aviso de Nico sobre efectos que se anulan:** es exactamente el tipo de caso. «Resiste más que un pivote» puede ser la
  suma de «a veces lo barre fuerte» y «a veces rebota». Separarlo por contexto (L2, tendencia) queda **pendiente**.
- Alcance: MES 25t, detector v2 (82 % de acuerdo con Nico), evento en la formación, carrera simétrica d/d, precio de trade.

## Qué habilita
La celda que sobrevive es un candidato para la confirmación única de abr–jun 2026 (Lucid), en el sentido observado:
«un techo IPC-NIVEL se barre menos que un pivote suelto». Operativamente sugiere lo opuesto al imán: **vender el techo
formado** (o no comprar su ruptura), a comparar contra la misma operación en un pivote suelto. Eso requiere su propio
pre-registro económico (fricción MES propia).
