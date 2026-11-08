# Atlas de ideas en R: resultado final (03/11/2026)

Estado: VIGENTE. Pre-registro: `PREREGISTRO_ATLAS_IDEAS_R.md`. 118 de 118 marginales (DESC y réplica de las campañas del relanzamiento
en R). `RESULTADO.json` se generó con `python tools/atlas_ideas_r.py analizar`.

**Integridad antes que interpretación.** La primera pasada dio efectos de millones de R. La causa raíz eran stops en la entrada con riesgo
≈ 1e-10. Se corrigió `riesgo_ops` y se relanzaron las 12 marginales contaminadas (las originales están en `crudo_descartado_riesgo_flotante/`,
sin mirar). El arreglo excluye entre 0 y 96 operaciones por familia, con 77 mil a 515 mil operaciones por nivel (≤ 0,03 %). La ventaja de
S3 **no** viene de esa exclusión.

**Método.** Para cada componente de ejecución, el efecto es la media en R de su nivel contra la media de su familia. Se combinan entre
familias con DerSimonian-Laird. BH q 0,10 sobre 59 etiquetas en DESC; confirma en réplica el mismo signo con p unilateral < 0,05.

| Componente | Familias | DESC (IC90) | Réplica | Estado |
|---|---|---|---|---|
| stop=S3 (más allá del extremo de la formación) | 15 | **+0,134R** (+0,096 a +0,171), 15/15 mismo signo | +0,121R (p < 0,0001) | **confirmado** |
| objetivo=T3 (borde lejano) | 15 | **+0,065R** (+0,033 a +0,098), 15/15 | +0,051R (p bil. 0,054) | **confirmado** |
| objetivo=T1 (borde cercano) | 15 | **−0,070R** (−0,107 a −0,033), 15/15 | −0,051R (p bil. 0,073) | **confirmado (resta)** |
| stop=S2 (1× la distancia al objetivo) | 18 | −0,074R | −0,045R | no pasa BH |
| be=0,5 | 4 | +0,179R | +0,140R | no pasa BH (4 familias) |
| entradas (RET, VOL, HACEV, E1A, ANCLA…) | | \|efecto\| < 0,05R | | sin señal |

**Lectura.** Las tres ideas que se transfieren dicen lo mismo: **dar espacio y dejar correr**. El stop estructural, más allá del extremo,
suma unos 0,13R por operación contra la media de la familia. El objetivo lejano suma y el cercano resta. Coincide con el Programa R:
cortar ganancias, objetivos de 0,5R, BE y trailing restan R. La entrada casi no importa: ningún tipo de entrada mueve más de 0,05R.

**Alcance.** Son efectos **relativos** a la media de cada familia, no edges propios: una familia negativa con S3 sigue siendo negativa. Las
15 familias que comparten S3/T1/T3 son todas de la gramática U1 (ES, YM, 6B, 6E, oro, CFD, zonas). Que se transfiera a familias de otra
gramática **no está medido**.

**Uso.** Toda familia nueva con stop y objetivo propios declara, en su pre-registro, la variante «stop estructural + objetivo lejano» como
nivel de la grilla, no como filtro elegido después. El atlas no habilita a reemplazar la ejecución de una regla ya congelada (v5): eso
sería una regla nueva con su propio paso por el embudo.
