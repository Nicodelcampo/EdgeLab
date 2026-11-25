# EXP-7: estabilizadores de la canasta de la mañana y entrada en retroceso

Estado: PRE-REGISTRO  
Fecha: 2026-11-25  
North Star sha256: `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`  
Etapa: EF3 (DESC con BH q 0,10 por bloque; confirmación en REP congelado; nada se promueve sin holdout terminal + forward).  
Familia: `ESTABILIZADORES_MANANA` (12 pruebas registradas: 6 estabilizadoras + 6 variantes de entrada).  
Antecedentes: DIAG-CAIDA-2026 (`RESULTADO_DIAG_CAIDA_2026.md`: caída en R/op, más reversión de 5 min en ES y más movimiento nocturno en NQ); pistas `OVERNIGHT-INV-NQ-R`, `OVERNIGHT-INV-ES-R` (programa_r_20261103), `KALMAN-FADE-NQ` (paquete_20261031), `SOM_sin_finde` y `C2_VZ` (corridas NT8 de `candidatas_nt8_20261125`); familias parecidas KALMAN_FADE, OVERNIGHT_INVENTARIO; NO_REPETIR F-VWAP-BANDA3-REVERSION, F-IB-MADONNA-NO-DEFIENDE, F-OP1-FADE-NIVEL-LIMPIO, F-ATLAS-CONTEXTO-ES-FRICCION.  
Cambio respecto a falla previa: no se diseña ningún fade nuevo (los refutados de arriba); se evalúan reglas YA congeladas (celdas y cortes de su embudo, sin re-optimizar) por una propiedad distinta —estabilizar la canasta— y una sola modificación estructural de entrada (retroceso) sobre las señales existentes.  
Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§6 (K33, K40, K48, K49, K51, K53, K55/K56).  
Potencia previa: meses DESC 2020–2025 de A5 ≈ 42, meses malos de la canasta ≈ 15–20 → con sd mensual ≈ 1–2 R el MDE de la media en meses malos es ≈ 0,8–1,5 R/mes (sólo efectos grandes); variantes de entrada: ≈ 900 (T) y ≈ 1.300 (RQ5) señales en DESC, MDE de la diferencia pareada ≈ 0,05 R/op. Las pruebas sin potencia publican su MDE y quedan SIN_POTENCIA, no refutadas.  
Diagnóstico de mecanismo: sin grilla (reglas congeladas y 2 niveles de retroceso); se publica por prueba: operaciones por mes, % de señales llenadas en el retroceso, resultado por año y por bloque A5, y los meses que más aportan (sin los 3 mejores).  
Pedido de Nico (2026-11-25): «crear estrategias estabilizadoras… probá todo lo útil. iterá una vez para eliminar errores y sesgos».

## Justificación económica
1. Si la apertura de NY dejó de pagar la continuación con stops cortos (más reversión de 5 min, más movimiento ya hecho de
   noche), las reglas que viven del inventario nocturno, de la reversión de corto plazo o de mantener de un día para otro
   deberían rendir mejor justo en los meses en que la canasta de la mañana pierde.
2. Si las rupturas de la mañana pierden por retrocesos de 5–15 min que tocan el stop antes de que el movimiento siga,
   entrar en el retroceso (más barato y con stop relativo más chico) debería mejorar el R por operación de las mismas señales.

## Objeto y datos (congelados)
- **Canasta de la mañana** (lo que se quiere estabilizar): T_NQ, RQ5_NQ, RQ5_ES, ES5N_ES, Franklin_NQ (corridas NT8, 1 contrato,
  veto de noticias), R neto por operación = (pts − fricción canónica `edgelab/costos.py`, base) / riesgo_pts; R del mes de la
  canasta = media de los R mensuales (suma por estrategia) de las 5.
- **Mes malo** = R mensual de la canasta < 0.
- **Partición**: DESC = meses DESC de A5 entre 2020-01 y 2025-12; REP = meses REP de A5 en el mismo tramo. Los meses HOLDOUT
  de A5 (ya vistos en NT8) y 2026 (tramo que inspiró el diseño) se publican sólo descriptivos.

## Pruebas (12)
**Estabilizadoras (6)**, cada una con su regla congelada, R neto mensual:
1. `OVN_NQ`: OVERNIGHT-INV-NQ-R, celdas `[[1,0,1,2,0],[0,1,0,2,1]]`, cortes `apertura_rth` del embudo (media de las 2 celdas).
2. `OVN_ES`: OVERNIGHT-INV-ES-R, celdas `[[0,1,0,1,1],[0,2,0,2,1]]`, cortes del embudo.
3. `KAL_NQ`: KALMAN-FADE-NQ, celda `[[2,2,1,2]]`, cortes `regimen_vol` del embudo.
4. `SOMSF_NQ`: SOM sin_finde (corrida NT8).
5. `C2VZ_NQ`, 6. `C2VZ_ES`: C2_VZ (corridas NT8).
Estadístico primario: media del R mensual de la candidata en los meses malos de la canasta (t unilateral, H1 > 0), BH q 0,10
sobre las 6 en DESC. Se publican además la correlación mensual con la canasta, el R en meses buenos y la diferencia
malos − buenos.

**Entrada en retroceso (6)**: sobre las señales de T_NQ, RQ5_NQ y RQ5_ES, orden límite a `entrada − lado × k × riesgo_pts`
(k ∈ {0,25; 0,50}) válida 30 min desde la entrada original y antes de su salida; mismo stop en precio; la salida es la de
la operación original (precio y hora: aproximación declarada — el break-even y los objetivos dependientes de la entrada no se
recalculan). Estadístico primario: diferencia pareada por mes del R neto total (variante − original; las señales no llenadas
cuentan 0), t unilateral, BH q 0,10 sobre las 6 en DESC.

**Confirmación**: una prueba que pasa BH en DESC confirma si su estadístico es > 0 en REP congelado con p ≤ 0,10. Sin eso,
SIN_POTENCIA o REFUTADA según su MDE.

## Cómo podría refutarse
- Una estabilizadora queda refutada si su R medio en meses malos no es mayor que 0 (o es menor que en meses buenos con
  MDE suficiente): no estabiliza aunque gane en promedio.
- La entrada en retroceso queda refutada si la diferencia pareada mensual es ≤ 0: las señales perdidas al no llenarse
  cuestan más que lo que se gana en las llenadas.

## Iteración (pedido de Nico)
Después de la primera corrida se audita (look-ahead, unidades, costos, meses, conteos) y se corre UNA vez más con los
errores corregidos. La segunda corrida es la que cuenta; la primera y la lista de correcciones se publican.
