# OP-1 — fade del nivel limpio con fills pasivos (desarrollo, abr → sep 2026): resultado

Estado: RESULTADO (2026-11-11). Pre-registro: `PREREGISTRO_OP1.md`. Análisis congelado: `tools/op1_niveles.py` (corrido una vez).
Tabla: `HFTC_niveles_op_replica.csv` (código vigente). Cifras: `RESULTADO_OP1_DESARROLLO.json`.

## Filtro (regla mecánica)
El banco de REBOTE_NIVEL_SESION no nominó nada → previa 1: `dist_zona_1800` > 1 X (sin zona HFT a ≤ 1 X en 30 min).

## Primaria: niveles de reloj, fill «atraviesa», objetivo X → **R neto −0,101** (n 8.335, 0/5 bloques, p 1,0). NO pasa al holdout.
R bruto ≈ −0,021 (neto + costo 0,08): un poco mejor que el nulo de selección adversa de la caminata al azar (−0,07), pero la fricción
lo deja en −0,10. Llenado 98 %.

## Grilla descriptiva (R neto, nivel limpio)
| Tipo / fill | g05 (X/2) | g1 (X) | g2 (2X) |
|---|---|---|---|
| reloj / atraviesa | −0,109 | −0,101 | −0,104 |
| reloj / toca | −0,094 | −0,085 | −0,089 |
| pivote / atraviesa | −0,055 | −0,103 | −0,137 |
| pivote / toca | −0,044 | −0,094 | −0,128 |
Las 12 celdas son negativas, en los 5 bloques.

## Lo único que se mueve: niveles de PIVOTE lejos de zonas HFT pierden menos
En pivotes, «limpio − resto» = +0,054…+0,068 (todas las geometrías y fills): un pivote de 1 min cerca de zonas HFT recientes pierde
≈ 0,06 R más como fade que uno lejos. Es coherente con «las zonas HFT no son soporte» (F-HFT-ZONAS-NO-SON-SOPORTE): el pivote
cercano a actividad HFT se atraviesa más. Descriptivo (no es la primaria) y en terreno negativo: no es operable como fade.

## Lectura
1. OP-1 queda NO_REPETIR: el fade pasivo de niveles de la sesión pierde la fricción entera (bruto ≈ 0 o negativo).
2. Coherente con el banco (el nivel no rebota) y con la confirmación de «no defiende» (cerca de actividad HFT se atraviesa más).
3. La versión que queda por medir es la inversa (continuación en clusters grandes, OP-2), con geometría fija, fills por stop y su
   propio nulo; y el veto (OP-3) aplicado a fades de otras familias.
