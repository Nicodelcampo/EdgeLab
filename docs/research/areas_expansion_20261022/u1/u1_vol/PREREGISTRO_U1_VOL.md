# Pre-registro: U1-VOL, banda y separación escaladas por la volatilidad del mes anterior (experimento 2 de 4)

Estado: VIGENTE, registrado antes de correr. Aprobado por Nico el 2026-11-02. Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3: exploratorio, sobre datos de desarrollo ya vistos.

## Hipótesis y justificación económica
U1 usa una banda fija de 40 pts y una separación de 1 pt. Si el mercado se mueve el doble, la misma banda junta zonas de otra
naturaleza. Escalar banda y separación por la volatilidad reciente debería mantener constante el objeto que se mide y estabilizar
el resultado entre regímenes (2023–2025 contra 2025–2026).

## Regla
`u1_cruzado.senales_vol`: la celda de U1-CRUZADO (N ≥ 3, x = 0,25, A/H ≥ 8), con W = 40·f·e y G = 1·f·e.
- f = rango M1 mediano del mes **anterior** / 6,25, que es el valor de referencia del DESC (`u1_oro.escala_por_mes`). Es causal.
- e ∈ {0,5; 1; 2}: 3 variantes.
- A/H es adimensional y no cambia.
- Las zonas se arman por mes y el primer mes de cada tramo no opera.

Ejecución igual que U1-CRUZADO: E1A/T3/S3 con tope `mult:3`, en NQ (2025-08 → 2026-09) o en el propio USATECH (2023-01 → 2025-07).

## Comparación
Contra U1-CRUZADO fijo, medido con el mismo código causal (experimento 1), por tramo:
- media neta;
- IC90 por sesiones;
- dispersión de la media mensual entre tramos.

## Lectura fijada
- **Una escala mejora el resultado de 2023–2025 sin empeorar 2025–2026** (las dos medias > 0 y la de 2023–25 mayor que la fija): pista.
  Se confirma sólo forward, en papel, con la escala fijada acá.
- **Si no:** escalar por volatilidad no rescata U1 en otros regímenes. Se reporta con su MDE.

## Cómo podría refutarse
Que ninguna escala dé media > 0 en 2023–2025, o que la escala 1 no mejore a la regla fija.

## Registro
3 pruebas (una por escala) en `TRIAL_REGISTRY_GLOBAL.jsonl` (`exp2/U1-VOL`).
