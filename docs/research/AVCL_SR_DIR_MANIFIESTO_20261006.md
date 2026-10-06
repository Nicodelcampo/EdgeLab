# AVCL-SR-DIR — soporte/resistencia y dirección del desplazamiento — manifiesto — 2026-10-06

Aprobado por Nico en el chat del 2026-10-06 ("si, armá el manifiesto y correlo en kaggle").
Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
Información direccional, **no P&L**: sin costos, sin estrategia y sin sizing.

## Por qué
- VOL-2 mostró que, después de la zona, la ventana de 10 barras recorre más sin que las barras crezcan. Eso indica
  desplazamiento hacia algún lado.
- Nico observa en el chart que las zonas actúan como soporte/resistencia.
- Se miden las dos cosas, con nulos que eviten las trampas ya conocidas (BigTrap2 F2.7–F2.9: la carrera contra la
  zona espejo).

## Población (enumeración previa, regla de población)
Espacio de eventos del indicador: creación, aproximación, primer toque, toque n-ésimo, invalidación, expiración,
confluencia, estado continuo. Acá se congelan **dos familias**, por separado:
- **D1, creación**: la zona OFF recién creada; la pregunta es hacia dónde se desplaza el precio.
- **D2, primer toque**: el primer regreso del precio a una zona OFF; la pregunta es si respeta o rompe.

Toque n-ésimo, estado continuo y confluencia quedan **no medidos**. Las zonas AT, con el precio adentro y sin lado,
se excluyen de D1/D2 y se reportan sólo como descriptivo de D1, con signo crudo.

## Datos
Cache de AVCL-VOL-2 (`edgelab-avcl-cache-mnq-k1..k4`): MNQ 2025-07 → 2026-09, sesiones aprobadas, sólo RTH para lo
formal. Holdout no leído. Parámetros del indicador congelados (VOL-1).
**Delta de la zona: NO MEDIDO**, porque el cache guarda el footprint total y no bid/ask.

## D1 — dirección del desplazamiento después de la creación (2 pruebas)
- `s = direction × (close[b+H] − close[b])` en ticks, con direction +1 = soporte (precio arriba de la zona) y
  −1 = resistencia, y H ∈ {10, 50}.
- s > 0 significa que el precio se aleja de la zona (rechazo); s < 0, que vuelve hacia ella (atracción).
- Controles: bloques sin zona a más de 2H barras, con pseudo-lado = signo del retorno de las 10 barras previas. El lado
  de la zona está correlacionado con el movimiento reciente, y este control saca el momentum.
- β del evento con FE (S0 de VOL-1, decil `int10`, vigintil de volumen, decil de |retorno 10 barras|).
- SE clusterizado por sesión. **Bilateral.**
- Descriptivo: soporte y resistencia por separado, H=200, y el retorno crudo de AT.

## D2 — primer toque: respeta o rompe, contra zona espejo (3 pruebas)
Para cada zona OFF con ancho w = upper − lower + 1:
- **Real**: banda de la zona.
- **Espejo**: banda del mismo ancho a la misma distancia, del otro lado del close de creación.
- Toque = primera barra posterior a la creación cuyo rango alcanza el borde cercano de la banda, dentro de 500 barras
  y en la misma sesión.
- Desde el toque, carrera de hasta 200 barras en la misma sesión:
  - **respeta**: el precio vuelve X ticks más allá del borde cercano, hacia el lado de origen;
  - **rompe**: el precio pasa X ticks más allá del borde lejano.
  - La misma barra con los dos resultados es empate y se excluye. Sin resolución también se excluye, y se reporta.
- X ∈ {8, 16, 32} ticks (2, 4 y 8 puntos).
- Estadístico: Δ = P(respeta | real) − P(respeta | espejo), con SE por bootstrap de sesiones (2.000). **Bilateral.**
- Descriptivo: tasas de toque y demora, soporte contra resistencia, y la distribución completa.

## Multiplicidad
5 pruebas (D1 ×2, D2 ×3), Holm, bilaterales. Se publica el MDE de cada una (≈ 2,8 × SE).

## Justificación económica
Una zona que separa respeto de ruptura mejor que su espejo es un nivel operable: entrada en el toque con stop del otro
lado. Si en cambio el precio se desplaza en un sentido después de la creación, hay un sesgo direccional de corto
plazo que se puede filtrar.

## Cómo podría refutarse
- D2 con Δ ≈ 0: la zona no respeta más que un nivel equidistante cualquiera. En ese caso lo que se ve en el chart es
  geometría, o supervivencia en la memoria visual.
- D1 con β ≈ 0: la expansión no tiene sentido sistemático respecto del lado de la zona.

## Registro
5 pruebas, familia `AVCL_SR_DIR`. Resultado y MEDIDO/NO MEDIDO van en el mismo commit.
