# AVCL-VOL-1 — resultados MYM (exploratorio) — 2026-10-06

**Punto de partida y referencia** para el resto del trabajo sobre `aVolClusterPOI`: la primera medición con corrección
por multiplicidad sobre este indicador. Se usa como hipótesis de referencia (AT, H10, expansión) para otros análisis.
**No es promoción**: MYM no tiene paridad propia y la medición es de información (volatilidad/expansión), no de P&L.

- Manifiesto: `docs/research/AVCL_VOL1_MANIFIESTO_20261005.md` (aprobado por Nico; horizontes en barras 50t).
- Kernel Kaggle `nicolasbuttaro/edgelab-avcl-vol1-mym-20261006`, code commit `c1763699`, 164 s.
- Parámetros congelados: percentil 95, invalidación None, MaxAge 500. 20.000 permutaciones, semilla 20261005.
- Ventana: 2025-07-01 → 2026-09-30. El holdout desde 2026-10-01 no se leyó.
- Resultado crudo: `docs/research/avcl_vol1_20261005/AVCL_VOL1_MYM_RESULTADOS.json`.
- Registro de pruebas: `docs/research/avcl_vol1_20261005/trial_registry.jsonl` (12 pruebas, familia `AVCL_VOL1_CREATION_VOL`).
- Paridad: **NO validada en MYM**. La paridad PASS 934/934 es de MNQ 12-26 50t y no se transporta.

## Justificación económica
Si la creación de una zona de volumen anómalo anticipa expansión de rango, sirve como filtro de régimen
(cuándo operar breakouts, cuándo ensanchar stops) y como sello de contexto para otras familias.

## Cómo podría refutarse
- MNQ, que tiene paridad, no replica AT H10 `y_rg` con el mismo signo.
- El efecto desaparece al re-medirlo con paridad propia en MYM.
- Un control que sea sólo "barra de volumen alto", sin zona, da lo mismo (el efecto sería del volumen, no de la zona).

## Resultados RTH (12 pruebas, Holm)
D = evento − control emparejado (estrato: reloj × decil de volumen × decil de volatilidad realizada).

| tipo | H | canal | n | D | IC95 | p | Holm | MDE |
|---|---|---|---|---|---|---|---|---|
| OFF | 10 | y_rv | 720 | +0,006 | [−0,048; 0,056] | 0,40 | 1 | 0,080 |
| OFF | 10 | y_rg | 720 | +0,036 | [0,010; 0,060] | 0,011 | 0,122 | 0,054 |
| OFF | 50 | y_rv | 642 | −0,015 | [−0,043; 0,012] | 0,83 | 1 | 0,055 |
| OFF | 50 | y_rg | 642 | +0,008 | [−0,020; 0,034] | 0,32 | 1 | 0,059 |
| OFF | 200 | y_rv | 143 | −0,070 | [−0,118; −0,022] | 0,999 | 1 | 0,084 |
| OFF | 200 | y_rg | 143 | −0,042 | [−0,125; 0,052] | 0,81 | 1 | 0,164 |
| **AT** | **10** | **y_rg** | **440** | **+0,067** | **[0,027; 0,106]** | **0,0003** | **0,004** | 0,070 |
| AT | 10 | y_rv | 440 | +0,019 | [−0,056; 0,085] | 0,26 | 1 | 0,109 |
| AT | 50 | y_rv | 379 | −0,009 | [−0,051; 0,033] | 0,68 | 1 | 0,071 |
| AT | 50 | y_rg | 379 | +0,009 | [−0,035; 0,057] | 0,35 | 1 | 0,083 |
| AT | 200 | y_rv | 66 | −0,050 | [−0,112; 0,013] | 0,94 | 1 | 0,114 |
| AT | 200 | y_rg | 66 | −0,057 | [−0,166; 0,048] | 0,87 | 1 | 0,178 |

**Única prueba que sobrevive Holm:** creación AT, horizonte de 10 barras, expansión de rango (+0,067), justo en el borde
del MDE. Efecto inmediato y corto. A 200 barras el signo se invierte: compresión, que la prueba unilateral no testea.

## Descriptivos (no suman pruebas)
- **OFF en RTH, por lado:**
  - Resistencias: H10 `y_rg` +0,047 [0,013; 0,079]. Concentran el efecto de OFF H10.
  - Soportes: H10 `y_rg` +0,031 [−0,010; 0,071]; H200 `y_rv` −0,098 [−0,16; −0,036].
  - La asimetría soporte/resistencia queda como hipótesis a pre-registrar, no como hallazgo.
- **ETH:** n chico. AT H10 `y_rv` −0,23 [−0,38; −0,08] (n=68): signo opuesto a RTH. No se interpreta.

## Estado
`REFERENCIA EXPLORATORIA — AT_H10_RG candidato a replicar`. Lo que sigue:
1. MNQ (con paridad) en curso, con el mismo manifiesto.
2. Paridad MYM.
3. Control "volumen alto sin zona".
4. Pre-registro del lado (soporte/resistencia).
