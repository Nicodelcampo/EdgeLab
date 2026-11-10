# Resultado E0 (sin retornos) — HFT-CLUSTERS-INFO

Estado: RESULTADO (2026-11-10). Pre-registro `PREREGISTRO_E0_E_INFORMACION.md` §2. Datos: `HFTC_e0.json`, `HFTC_e0.csv`.
Ventana 2025-07-01 → 2026-03-31, horario regular: NQ 166 sesiones, ES 178, YM 150, GC 150. Ningún retorno mirado.

## Definición elegida por la regla mecánica (la más cercana a 2 clusters por sesión entre las estables)
| Activo | Zona | Cluster | Clusters por sesión | CV mensual | Ancho mediano (pts) | X (pts) | Más angostos que X | Fricción en R si stop = ancho |
|---|---|---|---|---|---|---|---|---|
| NQ | Z_CERT | K4_PK125_V300 | 22,5 | 0,19 | 9,5 | 19,5 | 91 % | 0,16 |
| ES | Z_CERT | K4_PK125_V900 | 30,7 | 0,16 | 4,25 | 11,25 | 82 % | 0,21 |
| YM | Z_CERT | K4_PK085_V900 | 1,85 | 0,27 | 24,5 | 64 | 93 % | 0,23 |
| GC | Z_VOL10 | K4_PK125_V900 | 72,9 | 0,17 | 2,0 | 7,6 | 92 % | 0,30 |

## Lectura
1. **Un cluster de 4 zonas HFT NO es un evento infrecuente.** Con la zona certificada hay 22 a 33 por sesión en NQ y 31 a 39 en ES;
   con volumen mínimo 10, de 90 a 110 en NQ. Sólo YM queda cerca de 2 por sesión. La propuesta original los trataba como
   «trincheras» raras: con estos umbrales son parte del flujo normal.
2. **Confirmado el problema de fricción (K5):** 82 a 93 % de los clusters son más angostos que el stop mínimo X; con stop = ancho la
   fricción mediana sería 0,16 a 0,30 R por operación.
3. **Estables mes a mes** (CV 0,16 a 0,27 en las elegidas): la definición es reproducible. En GC con la zona certificada la
   frecuencia cae fuerte en feb–mar 2026 (1 a 3 por sesión contra 5 a 18 antes): por eso la regla eligió `Z_VOL10` ahí.
4. **Consecuencia para el paso INFO (declarada antes de ver su resultado):** con 20 a 70 clusters por sesión, el control temporal del
   imán (a más de 10 minutos de todo cluster real) va a quedar con pocos casos en NQ, ES y GC; si no alcanza, el imán se informa
   como sin potencia en esos activos, no como refutado. El placebo del rebote (nivel corrido) no tiene ese problema.
5. Los umbrales del detector están en ticks y contratos calibrados para NQ; que GC necesite la zona de volumen 10 y YM dé 15 veces
   menos clusters que NQ muestra que no son comparables entre activos sin reescalar. Pendiente si la familia sigue.

No se cambió ninguna regla después de ver esto: el paso INFO corre con la elección mecánica tal cual.
