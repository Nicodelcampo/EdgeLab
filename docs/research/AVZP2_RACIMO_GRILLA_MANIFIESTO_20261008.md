# AVZP2-RACIMO-GRILLA — sensibilidad de la definición de racimo — manifiesto — 2026-10-08

Pedido de Nico: "hacé pruebas con distintos parámetros que definan lo que se considera un racimo, siempre con
configuraciones que den potencia". Hash NORTH_STAR: `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`.
**Información, no P&L.** Escrito antes de ver la grilla.

## Qué se varía (sólo la definición de racimo; las zonas son las mismas)
- Mínimo de zonas ∈ {4, 5, 6, 8}.
- Ventana ∈ {250, 500, 1.000} velas.
- Altura máxima ∈ {20, 30, 45} ticks.

Son **36 celdas**. La detección de zonas y las barras de 25t son las de la configuración de Nico, igual que en el
estudio base. Cada celda corre sobre las mismas zonas.

## Potencia (regla fijada antes)
- Se evalúa una celda sólo si tiene **≥ 300 racimos en descubrimiento** (el base tuvo 454; con MDE de O5 ≈ 0,05).
- Las celdas con menos racimos se listan y no se prueban.

## Desenlaces y nulo
Los mismos del estudio base (O1, O2, O3b, O4, O5): desde t0, contra pseudo-racimos apareados por ocupación previa,
con la misma altura y posición, 5 por racimo, con FE y SE por sesión.

## Corrección
- **Primaria: O5 (compresión)** en todas las celdas evaluables, con **Holm** sobre esas celdas.
- **Secundarias: O1, O2 y O3b.** Holm sobre todas las celdas × 3 desenlaces. Una dirección, seguimiento o rebote que
  aparezca sólo en alguna celda tiene que sobrevivir esa corrección.
- **Confirmación** (09-26, 12-26), una sola vez, sólo en las celdas o desenlaces que pasen. La confirmación ya se miró
  una vez para O5 en la celda base (6 / 500 / 30), y eso queda declarado.

## Qué se publica
**Todas las celdas** (evaluables y no evaluables), con β, MDE, n y tasas. No se elige "la mejor": se informa el
paisaje.

## Cómo podría refutarse
- Que la compresión aparezca sólo en la celda base o en sus vecinas inmediatas: sería sensible a la definición, no
  una propiedad de los racimos.
- Que efectos direccionales aparezcan sólo en celdas sueltas sin sobrevivir a Holm.

## NO MEDIDO
- P&L.
- Otras escalas e instrumentos.
- Otros parámetros de detección de zonas (percentil, bloque, franja).
- Mínimos de zonas mayores que 8 o ventanas mayores que 1.000 (por falta de potencia esperada).
- Interacción con el lado de formación.
