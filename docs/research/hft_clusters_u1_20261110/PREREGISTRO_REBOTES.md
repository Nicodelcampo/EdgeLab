# Pre-registro — HFT-REBOTES: siete definiciones de rebote en clusters de zonas HFT

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-11-10. Pedido de Nico.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Familia `HFT_CLUSTERS_INFO` (misma familia y linaje). Etapa **EF2/EF3 información** (no es P&L de una estrategia).
Código: `edgelab/research/hft_rebotes.py`, modo `rebotes` de `tools/kaggle_grilla/hft_clusters_info_main.py`, `tools/hft_clusters_info.py rebotes`.
Tests: `tests/research/test_hft_rebotes.py` (cada definición dispara en su caso y no en el vecino; causalidad).

## 1. Clusters
Los elegidos por el E0-b sin retornos (`RESULTADO_E0B.md`): NQ `K8_A050_V1800` (20 por sesión, ancho mediano 19,75 pts) y ES
`K12_A100_V1800` (10 por sesión, 17 pts). YM y GC quedan afuera (sin definición estable o sin potencia). DESC 2025-07-01 → 2026-03-31.

## 2. La historia de visitas (común a todas)
Sólo ticks posteriores a la detección, reloj en segundos, vida del cluster 1.800 s. Una **visita** empieza cuando el precio entra al
rango [lo, hi] y termina cuando se aleja al menos X/4. Entre visitas se miden excursión máxima, tiempo afuera, lado del regreso y
velocidad de aproximación; dentro de cada visita, penetración, segundos y volumen negociados adentro y lado de salida. X = fricción /
0,08 (NQ 19,5; ES 11,25 pts). Cada definición elige como mucho UN evento por cluster: el primero que cumple su condición.

## 3. Las definiciones (umbrales fijos, sin grilla)
| Código | Condición | Hipótesis económica |
|---|---|---|
| D0_BASE | primer regreso tras alejarse X/2 | referencia (la del paso INFO) |
| D1_FRESCO_LEJANO | regreso tras excursión ≥ X desde la última visita; sólo si es la visita nº ≤ 3 y el precio negoció ≤ 600 s adentro en total | un nivel se defiende mientras no fue «gastado»; cada visita consume las órdenes que lo sostenían |
| D2_ACEPTADO_Y_ABANDONADO | en los primeros 300 s: ≥ 120 s adentro y ≥ 40 % del volumen de esa ventana; después se aleja ≥ X; primer regreso (después de los 300 s) | el nivel fue aceptado como valor: quienes compraron/vendieron ahí lo defienden al volver |
| D3_RECHAZADO_AL_NACER | en los primeros 300 s: ≤ 30 s adentro y ya se alejó ≥ X; primer regreso | el nivel fue rechazado de inmediato: el ejecutor terminó ahí y el regreso encuentra liquidez opuesta |
| D4_MEMORIA | regreso tras ≥ 900 s afuera y excursión ≥ X | ¿el nivel se recuerda pasado un rato o se olvida? |
| D5_DERIVA | regreso tras excursión ≥ X/2 en el que los últimos X/2 tardaron ≥ 120 s | llegar sin impulso favorece que la liquidez del nivel frene; el impulso tiende a atravesar |
| D6_PENETRACION_FALLIDA | tras excursión ≥ X/2, entra ≥ 2 ticks y a lo sumo min(ancho/2, X/4), no toca el borde lejano y sale por el mismo lado ≥ 2 ticks dentro de 120 s; evento en la salida | entrada confirmada: el rechazo ya ocurrió; mide si continúa |

Población (CLAUDE.md): cubre aproximación (D5), primer toque tras alejarse (D0, D1, D3), toque n-ésimo acotado (D1), estado al nacer
(D2, D3), expiración por tiempo (D4) y confirmación (D6). Quedan NO MEDIDOS: estado continuo por barra e invalidación por ruptura.

## 4. Desenlace, control y estadístico
- **Desenlace:** carrera simétrica ±X desde el precio de referencia (el borde; en D6, el precio de salida): +1 rebote, −1 atravesó,
  0 sin definir en 3.600 s. Bruto: el neto sería desenlace medio − 0,08 R.
- **Control:** pseudo-clusters del mismo ancho centrados en el precio de 20 y 40 minutos antes y después, a más de 300 s de todo cluster
  real, con el mismo procedimiento. Comparten la condición («el precio negoció en ese nivel»), así que D2 y D3 también tienen control
  con su propia condición al nacer.
- **Estadístico:** por definición y activo, diferencia real − control con bootstrap por sesión; por definición, Stouffer NQ + ES.
  **Nominación:** BH q 0,10 entre las 7 definiciones. Pasa a réplica (abr → sep 2026, una vez, mismo código) una nominada con
  desenlace real medio > 0,08. Una sin eventos suficientes se informa SIN_POTENCIA con su MDE.
- **Pruebas:** 7 definiciones × 2 activos + 7 combinadas = **21** (`hft_clusters_info/rebotes`).

## 5. Cómo podría refutarse
Ninguna definición nominada con MDE < 0,10; o nominadas sólo en un activo; o desenlace real ≤ 0,08 (no paga la fricción).

## 6. Riesgos declarados
- Las definiciones se escribieron después de conocer el E0 y el E0-b (sin retornos) y sin conocer ningún resultado con retornos.
- D0 comparte eventos con el paso INFO de la definición de 4 zonas: no es independiente de ese resultado.
- Los umbrales (300 s, 120 s, 40 %, 600 s, 900 s, X/4) son redondos y fijos; no se ajustan después de ver resultados.
