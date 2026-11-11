# Confirmación congelada — «el cluster HFT grande no defiende el nivel» (réplica abr → sep 2026)

Estado: RESULTADO (2026-11-11). Pre-registro: `CONFIRMACION_NO_DEFIENDE.md`. Análisis congelado: `tools/confirmar_no_defiende.py`
(corrido una vez). Cifras: `RESULTADO_CONFIRMACION_NO_DEFIENDE.json`. Reserva LORD++ `HFT_RUPTURA::rep_no_defiende_20261110`
(nivel 0,0109), resuelta. Orden declarado respetado: el banco de REBOTE_NIVEL_SESION se corrió antes.

## H1 — real − control (ruptura), NQ + RTY + YM: **replica, pero NO se confirma al nivel de LORD++**
| | Sesiones | Real − control | Bloques + | p (inversión de signo) |
|---|---|---|---|---|
| NQ + RTY + YM | 247 | **+0,087** | **5/5** | 0,052 |
| NQ | 117 | +0,089 | 4/5 | 0,022 |
| RTY | 73 | +0,049 | 3/5 | 0,36 |
| YM | 57 | +0,133 | 5/5 | 0,17 |
| ES (diagnóstico) | 36 | +0,182 | 3/5 | 0,13 |
Bloques: +0,063 +0,120 +0,020 +0,089 +0,144. Lote LORD++ (Simes, m = 2): p 0,104 > 0,0109 → **no confirmada**. Por la regla 08/11
(≥ 4/5 bloques y p < 0,10) es **estable**: el mismo efecto que en DESC (+0,10/+0,107), con el mismo signo en los cuatro activos
(ES ahora también positivo).

## H2 — retroceso contra la sesión (NQ/ES, cortes de DESC): **muere**
n 687, ruptura −0,023, 2/5 bloques, p 0,73.

## Lectura
1. «El cluster grande no defiende» se reprodujo con el mismo tamaño en datos que nadie miró, estable en los 5 bloques; lo que no
   alcanzó es el nivel estricto de LORD++ (la familia ya gastó α). Es un efecto chico, real y consistente: candidato a canasta y al
   holdout en modo exploratorio (regla 08/11), con la probabilidad de azar de desarrollo declarada (0,088 DESC independiente;
   0,052 réplica).
2. Combinado con REBOTE_NIVEL_SESION (un nivel cualquiera NO rebota en abr–sep), lo operable no es «fade del nivel limpio» sino lo
   inverso: **continuación cuando el precio vuelve a un cluster grande** (OP-2), del orden de +0,09 sobre el control; en bruto absoluto
   la ruptura del cluster es chica, así que la geometría y los fills deciden.
3. El retroceso queda NO_REPETIR.
