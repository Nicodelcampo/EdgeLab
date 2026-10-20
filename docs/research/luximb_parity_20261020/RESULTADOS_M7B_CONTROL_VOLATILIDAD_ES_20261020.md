# Resultados M7b — control por volatilidad previa de M7-H2 (ES, descubrimiento)

Estado: MEDIDO. Manifiesto `MANIFIESTO_M7B_CONTROL_VOLATILIDAD_ES_20261020.md` (OK de Nico). Codigo `luximb_m7b.py` +
`luximb_m7_es.py` (solo se agrego `vol_pre`; M7 se reprodujo identico: H2 Holm 0,0008). Eventos `RESULTADOS_M7B_ES_BASE_eventos.csv`.
n = 7.696 (3 sin vol_pre).

**La confusion es real:** la volatilidad de los 60 min previos es mucho menor en las areas cargadas.
| vol_pre (pts) | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|
| T (>= 3 zonas) | 5,8 | 8,3 | 13,5 | 20,5 | 29,7 |
| C (0-2 zonas) | 9,8 | 13,8 | 22,3 | 33,3 | 47,0 |

| | estimacion | IC 95 % (por dia) | p unilateral (< 0) | Holm | MDE80 |
|---|---|---|---|---|---|
| efecto crudo M7 (referencia) | -3,30 pts | [-4,86, -1,62] | | | |
| **H2b recorrido T - C, estratos vol_pre (quintiles) x franja** | **+0,23 pts** | [-0,93, +1,45] | 0,65 | 1,0 | 1,71 pts |
| H2c recorrido / vol_pre, T - C | +0,37 | [+0,30, +0,46] | 1,0 | 1,0 | 0,12 |

Recorrido medio por quintil de vol_pre (T vs C): 13,0 vs 12,0; 18,0 vs 16,4; 24,1 vs 20,9; 31,2 vs 27,3; 38,0 vs 34,2 —
**en los 5 quintiles T recorre MAS que C**. Ningun T quedo fuera de estratos.

## Decision (segun manifiesto)
- H2b nula. Por la regla escrita, con MDE 1,71 > 1,5 pts corresponde **"indeterminado por potencia; no se promueve"**.
  Hecho adicional que no cambia la regla pero si la lectura: el IC de H2b excluye cualquier freno mayor a 0,93 pts (el
  efecto crudo era 3,30) y el signo condicionado es el opuesto en los 5 quintiles.
- **El "freno" de M7 se explica por la volatilidad previa:** las areas cargadas aparecen en mercado lento, y el mercado
  lento sigue lento. No es un efecto de las zonas. H2 **no** pasa a replicacion; la replicacion ES (abr-sep) queda intacta.
- H2c (relativo a vol_pre) da incluso mas recorrido con zonas; no se interpreta (direccion opuesta, no preregistrada).

## Estado de la familia LUX-IMB tras M1-M7b
Ninguna senal ni regularidad propia de las zonas sobrevive. Lo unico robusto es descriptivo: **las zonas OG/VI finas se
acumulan en mercado de baja volatilidad** (contexto, no edge).

Aporte al referente: evita promover un falso efecto de zonas (era volatilidad de regimen) y conserva intacta la
replicacion de ES para otra familia.
