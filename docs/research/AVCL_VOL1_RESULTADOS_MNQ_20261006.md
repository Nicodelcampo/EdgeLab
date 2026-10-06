# AVCL-VOL-1 — resultados MNQ (con paridad) — 2026-10-06

Es la réplica de la referencia `AVCL_VOL1_RESULTADOS_MYM_20261006.md`, con el mismo manifiesto, el mismo código
(`c1763699`) y los mismos parámetros congelados.
- Kernel `nicolasbuttaro/edgelab-avcl-vol1-20261005` v3, 12.477 s.
- MNQ 2025-07-01 → 2026-09-30: 261 sesiones aprobadas, 6 contratos. Holdout no leído.
- Paridad NT8↔Python PASS 934/934 (MNQ 12-26 50t).
- JSON: `docs/research/avcl_vol1_20261005/AVCL_VOL1_MNQ_RESULTADOS.json`. 12 pruebas más en el registro.

## RTH (12 pruebas, Holm; p mínimo alcanzable = 1/20.001)
| tipo | H | canal | n | D | IC95 | Holm | MDE |
|---|---|---|---|---|---|---|---|
| OFF | 10 | y_rv | 19.978 | +0,004 | [−0,016; 0,025] | 1 | 0,016 |
| **OFF** | **10** | **y_rg** | 19.978 | **+0,063** | [0,055; 0,070] | **0,0006** | 0,010 |
| OFF | 50 | y_rv | 19.944 | −0,016 | [−0,027; −0,005] | 1 | 0,010 |
| **OFF** | **50** | **y_rg** | 19.944 | **+0,012** | [0,006; 0,017] | **0,0009** | 0,010 |
| OFF | 200 | y_rv | 13.853 | −0,041 | [−0,053; −0,030] | 1 | 0,018 |
| OFF | 200 | y_rg | 13.853 | +0,008 | [0,000; 0,017] | 0,60 | 0,022 |
| **AT** | **10** | **y_rv** | 13.814 | **+0,047** | [0,025; 0,068] | **0,0006** | 0,020 |
| **AT** | **10** | **y_rg** | 13.814 | **+0,081** | [0,072; 0,089] | **0,0006** | 0,012 |
| AT | 50 | y_rv | 13.784 | −0,025 | [−0,037; −0,013] | 1 | 0,012 |
| AT | 50 | y_rg | 13.784 | +0,002 | [−0,005; 0,008] | 1 | 0,012 |
| AT | 200 | y_rv | 9.507 | −0,041 | [−0,054; −0,029] | 1 | 0,018 |
| AT | 200 | y_rg | 9.507 | +0,010 | [0,000; 0,020] | 0,60 | 0,024 |

## Lectura
- **La referencia de MYM replica en MNQ:** AT H10 `y_rg` +0,081, frente a +0,067 en MYM. Mismo signo, magnitud
  parecida, y acá con un MDE 7 veces menor.
- Además sobreviven OFF H10 `y_rg` (+0,063), OFF H50 `y_rg` (+0,012, chico) y AT H10 `y_rv` (+0,047).
- El patrón es el mismo que en MYM: **expansión inmediata y corta, seguida de compresión** (`y_rv` negativo a H50 y H200).
  La compresión no fue testeada, porque la prueba es unilateral; queda como hipótesis a pre-registrar.
- **Por lado (descriptivo):** OFF resistencias H10 `y_rg` +0,073 [0,064; 0,082], soportes +0,049 [0,040; 0,058].
  Es la misma asimetría que en MYM, ahora con dos instrumentos. Sigue siendo descriptiva.
- **ETH (descriptivo):** mismo signo que RTH (AT H10 `y_rg` +0,063; OFF +0,052). La inversión que se vio en MYM-ETH
  no se repite y era ruido de una muestra chica.
- **Aviso de cobertura:** MYM dio unos 6 eventos por sesión en 126 sesiones; MNQ, unos 77 por sesión en 260. La
  diferencia de densidad de zonas entre instrumentos con el mismo bar_spec de 50t está **sin explicar** y queda pendiente.

## Qué es y qué no es
Es información: la creación de una zona anticipa unas 10 barras de rango más amplio que en el control emparejado.
**No es dirección ni P&L.** Siguientes pasos de la cadena:
1. Control "volumen alto sin zona".
2. Contexto pre-registrado (lado, intensidad, régimen GEX, hora), en AVCL-VOL-2.
3. Traducción operable, por ejemplo filtro de breakout o stop, neta de costos (con STOP antes de correr).

## Estado
`INFORMACIÓN REPLICADA (MYM→MNQ) — AT/OFF H10 expansión`. No promovido a edge.
