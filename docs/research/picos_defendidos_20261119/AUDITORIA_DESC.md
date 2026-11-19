# PICOS-DEFENDIDOS NQ y ES: auditoría del descubrimiento (DESC) con las herramientas de la semana (2026-11-19)

Estado: VIGENTE — auditoría multi-agente. La corrida la lanzó otra sesión y la retoma esta (decisión de Nico del 2026-11-19: «la retomás
vos, auditala y lo aprovechamos como auditoría multi agente»). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

- **Datos:** `RESULTADO.json` de los kernels `nicolasbuttaro/embudo-picos-defendidos-{nq,es}-desc-20250805`, que terminaron el
  2026-11-19 y se leyeron sin tocar el estado del embudo.
- **Período:** DESC 2025-08-05 → 2026-03-31 (166/167 sesiones).
- **Auditoría del diseño:** `../agente/AUDITORIA_PICOS_DEFENDIDOS_20261119.md`.

## 1. Lo que dio
| | NQ | ES |
|---|---|---|
| Disparos (E0) | 957.445 | 1.063.686 |
| Operaciones simuladas | 11,5 millones | 12,8 millones |
| Celdas / evaluables (≥ 30 op.) | 207.360 / 137.804 | 207.360 / 141.668 |
| Nominadas por maxT (criba congelada, α 0,05) | **8** (t máx. 4,79 contra umbral 4,50; p 0,021) | 0 (t máx. 2,28) |
| Nominadas por FDR q 0,10 | 20 | 0 |

R neto y bruto por temporalidad (todas las celdas):

| Temporalidad | NQ neto | NQ bruto | ES neto | ES bruto |
|---|---|---|---|---|
| 1 min (63–64 % de las operaciones) | −0,233 | −0,013 | −0,659 | −0,072 |
| 3 min | −0,111 | +0,008 | −0,348 | −0,021 |
| 5 min | −0,050 | +0,042 | −0,279 | −0,026 |
| 10 min | +0,012 | +0,076 | −0,154 | +0,025 |
| 15 min | +0,004 | +0,057 | −0,175 | −0,028 |

## 2. Diagnóstico de mecanismo de las nominadas de NQ (K55/K56)
Diagnóstico de grilla: 8 celdas nominadas por maxT, con operaciones por celda 34/36/37 (mín/mediana/máx); 0 celdas casi vacías;
número efectivo de variantes ≈ 1; perillas inertes: def_tend. Spearman(operaciones, R) no aplica: es una sola variante.

| Pieza | Qué muestra |
|---|---|
| Qué son | La misma regla: 5 min, nivel Z3, alejamiento 1 ≥ 3,17 A, disparo `ESPEJO_100`, stop estructural y objetivo `T_2TK` (nivel + 2 ticks) |
| De dónde salen las 8 | 4 definiciones de tendencia × (a favor / cualquiera). El disparo `ESPEJO_100` no usa la EMA y «cualquiera» no filtra, así que las 4 definiciones dan las mismas operaciones. El pre-registro lo había anticipado como «celdas duplicadas» |
| Variantes distintas | Una (36–37 operaciones) |
| Muestra | 35–37 operaciones en 32–33 sesiones de 8 meses |
| Resultado | +0,099 a +0,103 R por operación, IC90 [+0,08; +0,12] |
| Movimiento contra fricción | 3,7–4,2 veces la fricción: apenas sobre el piso de relevancia (3) |

Lectura del perfil (datos, no veredicto):
- **Varianza:** un IC90 de ±0,02 R con 36 operaciones implica un desvío por operación de ≈ 0,07 R. Prácticamente todas las operaciones
  cobran el objetivo y ninguna toca el stop.
- **Geometría:** el disparo es la vuelta del 100 % del impulso contrario, o sea que el precio ya está otra vez en la zona del acercamiento,
  a ≤ 1 A del nivel. El objetivo está 2 ticks más allá del nivel. Es una operación de ganancia chica y frecuente con el stop lejos.
- **Lo que no se vio:** con 0 pérdidas en 36 operaciones, el bootstrap por sesiones no ve la cola. La operación se vuelve negativa si la
  tasa de pérdidas (≈ −1 R) supera ≈ 9 %; la cota superior al 90 % de esa tasa con 0/36 es ≈ 6 %.
- **Lo que decide:** la réplica, no el IC de desarrollo.

Episodios: no aplica (sin operaciones por mes en el RESULTADO; el embudo publica la serie mensual en la etapa de pistas).

## 3. Otras pistas de NQ (no nominadas por maxT)
- **Patrón:** las de mayor R son de 10 min y nivel PAR, con objetivos de 1–2 A, disparos `ESPEJO_75` / `REACERCA_50` / `POC`, y
  +0,45 a +1,0 R en 31–79 operaciones.
- **Nominación:** algunas pasan el FDR q 0,10 (q 0,002–0,05) pero no maxT (p 0,64–0,89). Ninguna está en el régimen «reciente».
- **Dato aparte:** la regla de la captura de Nico (10 min, PAR, tendencia E20 a favor, disparo al alejarse) no figura entre las 28 pistas.

## 4. Qué cambia en la conducción
1. **Réplica:** la que sigue (OOS 2026-04 → 2026-09, ticks, una vez por familia) es la lectura que decide. Se mantiene la regla
   congelada del embudo: no se cambian criba ni selección.
2. **Una sola variante:** las 8 nominadas de NQ se leen como **una** variante en la réplica. Los 4 duplicados por la definición de
   tendencia no son 4 confirmaciones.
3. **Potencia de la réplica (K49):**
   - con ≈ 4,5 operaciones por mes, 6 meses dan ≈ 27 operaciones;
   - para un efecto de la mitad (+0,05 R) con un desvío de 0,07 R, la potencia es alta;
   - pero si aparece una pérdida de −1 R, el desvío sube a ≈ 0,2 R y la potencia baja a ≈ 0,4.
   - Un resultado NO_CONCLUYENTE no mata.
4. **ES:** 0 nominadas; sale por la rama de pistas a réplica sólo si el embudo lo dispone. Bruto ≤ 0 en 1–5 y 15 min.
5. **Versión A5** (`../picos_defendidos_a5_20261119/`): sigue siendo la medición de la regla de la captura en 18 años.

Aporte al referente: lo único que el descubrimiento rescata es una sola variante de ganancia chica y casi segura, que la grilla contó ocho
veces. Queda escrito antes de la réplica que se lee como una y que su riesgo está en la cola que el desarrollo no mostró.
