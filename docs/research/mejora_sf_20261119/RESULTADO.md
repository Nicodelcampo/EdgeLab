# MEJORA-SF: tres mejoras de la curva de SOM y Franklin pasan DESC, pero los datos limpios que quedan no alcanzan para confirmarlas (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (4 pruebas en `SOM`, 5 en `FRANKLIN`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `TABLA.csv.gz`, `DESC.json`, `REP.json`. Etapa EF3; REP sin leer
(K49) y holdout A5 sellado.

## 1. DESC (meses DESC de A5, 2006–2025; SOM NQ+ES+YM, Franklin NQ+ES; R neto)
| Prueba | Contraste (dentro − fuera) | p | R neto dentro / fuera / base | % dentro | BH q 0,10 |
|---|---|---|---|---|---|
| SOM · M2 saltear fricción > 0,08 R | **+0,089** | 0,001 | +0,013 / −0,076 / −0,012 | 72 % | **nominada** |
| SOM · M3 ATR alto | +0,013 | 0,32 | | | no |
| SOM · M6 VIX alto | +0,027 | 0,18 | | | no |
| SOM · M8 a favor de la tendencia | +0,024 | 0,21 | | | no |
| Franklin · M1 concordante con SOM | +0,064 | 0,19 | | | no |
| Franklin · M2 saltear fricción | +0,104 | 0,07 | +0,062 / −0,042 | 43 % | no |
| Franklin · M3 ATR alto (tercio superior) | **+0,172** | 0,017 | **+0,120** / −0,052 / +0,005 | 33 % | **nominada** |
| Franklin · M6 VIX alto (tercio superior) | **+0,211** | 0,009 | **+0,152** / −0,059 / +0,002 | 29 % | **nominada** |
| Franklin · M8 a favor de la tendencia | −0,051 | 0,75 | | | no |

## 2. REP: bloqueada por K49
- Potencia en días al nivel LORD++ con la mitad del efecto de DESC: SOM·M2 0,06 (816 días), Franklin·M3 0,05 y Franklin·M6 0,06 (408 días).
  Ni con REP + holdout A5 juntos se llegaría a 0,8 (≈ 0,2 con la mitad del efecto; ≈ 0,5 con todo el efecto de DESC). No se gastó REP.

## 3. Lectura
- **Franklin rinde donde hay volatilidad:** en el tercio de días con ATR alto o VIX alto su neto pasa de ≈ 0 a +0,12/+0,15 R por operación
  (DESC, 20 años). Es coherente con lo visto desde 2020 (más volatilidad en puntos, menos fricción relativa) y con el mecanismo de cobertura
  de gamma. M3 y M6 miden casi lo mismo (días volátiles): son una sola mejora con dos nombres.
- **SOM mejora con el filtro de fricción**, pero su neto filtrado sigue siendo chico (+0,013 R en DESC).
- **No están confirmadas.** Los meses limpios que quedan no tienen potencia para un contraste de este tamaño con este ruido. Vías válidas,
  a pre-registrar aparte: (a) el mismo contraste VIX/ATR de Franklin en YM, EMD, RTY y GC (sus operaciones existen y el contraste nunca se
  miró ahí: más días y otra muestra); (b) el forward desde la frontera A4 con vigilancia secuencial.

## 4. Confirmación en YM + EMD + RTY (`PREREGISTRO_CONF.md`, 2 pruebas en FRANKLIN)
- Potencia calculada antes de leer, con la mitad del efecto de DESC y 2.165 sesiones: M3 0,18 y M6 0,23 (< 0,8) → **no se leyó**
  (`SIN_POTENCIA_PREVIA`, `CONF.json`). Ni REP ni otros índices tienen datos suficientes para confirmar un contraste de este tamaño con este
  ruido. La pista queda viva sólo para forward con vigilancia secuencial; no se usa para dar tamaño.
