# FILTROS-CONTEXTO: ningún indicador de la captura separa días buenos de malos en A20, T, R, Z-banda ni RQ5 (resultado, 2026-11-20)

Estado: RESULTADO — lectura pre-registrada (`PREREGISTRO.md`), 35 pruebas contadas antes de correr. Veredicto **SIN_FILTRO**.
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `RESULTADO.json` (todas las celdas), `CONTEO.json` (operaciones por tercil, sin desenlaces). Herramienta `tools/filtros_contexto.py`.

Diagnóstico de grilla: no es una grilla de perillas. Son 7 indicadores × 5 estrategias = 35 contrastes. El número efectivo de indicadores es 4,1, porque VIX, GEX y VIX9D/VIX son casi un solo eje (Spearman |0,62–0,66|).
Episodios: no aplica. No hubo nada nominado, así que no hay contraste por año para leer.

## Resultado
- **Nominadas por BH q 0,10: 0 de 35.**
  - La p más baja es 0,023 (Z-banda × SKEW), con p ajustada 0,59.
  - Dos de las 35 pruebas tienen p < 0,05. Por azar se esperan 1,75.
- **Nada que replicar en REP.**

Contraste tercil alto − tercil bajo (R neto por operación) en DESC 2018-01 → 2025-07. Las nueve pruebas de menor p:

| Estrategia | Indicador | Alto − bajo | p | MDE80 | Terciles bajo / medio / alto |
|---|---|---|---|---|---|
| Z-banda | SKEW | +0,48 | 0,023 | 0,60 | −0,08 / +0,36 / +0,40 |
| A20 | VIX9D/VIX | +0,35 | 0,034 | 0,49 | −0,17 / +0,20 / +0,19 |
| A20 | GEX | −0,33 | 0,060 | 0,49 | +0,21 / +0,18 / −0,12 |
| RQ5 | SKEW | +0,10 | 0,141 | 0,12 | −0,00 / +0,04 / +0,09 |
| A20 | SKEW | −0,23 | 0,179 | 0,48 | +0,17 / +0,14 / −0,06 |
| A20 | VIX | +0,21 | 0,249 | 0,49 | −0,03 / +0,03 / +0,18 |
| RQ5 | VIX9D/VIX | +0,07 | 0,306 | 0,13 | −0,02 / +0,13 / +0,05 |
| R | DIX | −0,38 | 0,317 | 1,00 | +0,96 / +0,14 / +0,59 |
| Z-banda | VIX9D/VIX | −0,23 | 0,317 | 0,66 | +0,33 / +0,22 / +0,11 |

**T:** las siete pruebas dan |alto − bajo| ≤ 0,054 con MDE ≈ 0,24. Ningún indicador mueve a T, y eso confirma F-GEX-DIA-TENDENCIA.

**RQ5:** las siete dan |alto − bajo| ≤ 0,10 con MDE ≈ 0,13. Es la única estrategia con potencia para un efecto moderado, y no lo hay.

## Lectura
- **No hay filtro que cambiar** en ninguna de las cinco estrategias. Por la regla del pre-registro, sigue la apertura del holdout terminal de
  A20 NQ.
- **A20, la única pista y sin significancia:**
  - Tres indicadores casi colineales apuntan al mismo lado: VIX9D/VIX bajo, GEX alto y VIX bajo, es decir días calmos con gamma larga de
    los dealers, son los peores.
  - Encaja con el mecanismo declarado: la gamma larga frena las tendencias.
  - Es un solo hallazgo, no tres. Su p sin corregir es 0,03–0,06 con MDE 0,49, así que **no se adopta**.
  - Queda como pista para mirar en el forward, como variante paralela si Nico lo pide.
- **R y Z-banda** no tienen potencia (MDE 0,6–1,0 R). Su nulo no dice nada (K49).
- **El R por mes con filtro** en la tabla de `RESULTADO.json` es el del tercil peor excluido, elegido en los mismos datos. Es optimista por
  construcción y no se lee como mejora.
