# Pre-registro: confirmación del filtro de INTENTO-FALLIDO-HACIA (03/11/2026)

Estado: PRE-REGISTRO (commiteado antes de correr). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa **EF4 réplica no mirada**.
Origen: las marginales de `RESULTADO_IF_HACIA.md`. OK de Nico el 03/11.

## Regla congelada (se elige antes de mirar los datos nuevos)

- **Celdas**, con los cortes congelados de DESC de cada campaña:
  - `A/H` alto, `dur_ida` alto, entrada **CONF**, el resto en «cualquiera»;
  - en IFH-LUX-CFD-NQ además `vol_zona` alto (la única fuente donde repitió).
  - r ∈ {50, 80, 100 %} × TP ∈ {Z1, Z2, Z3, 2R}: 12 celdas por fuente.
- **Datos no usados por estas familias**: 2024-01-02 → 2025-07-31, anterior al DESC (2025-08-05 → 2026-03-31). Holdout cerrado.
- **Fuentes**:
  - IFH-LUX-CFD-NQ (CFD → NQ) e IFH-LUX-NQ.
  - Racimos no entra: su almacén de zonas empieza en agosto de 2025.

## Prueba (una por fuente, Holm sobre 2)

- **Estadístico**: R medio de la unión de operaciones de las 12 celdas, con IC90 por bootstrap por sesión.
- **Confirma** si la cota inferior del IC90 es > 0 y p unilateral < 0,05 tras Holm. Se publica también cada celda, como información.
- **Refuta** si la media es ≤ 0 con potencia, o si el IC90 queda por debajo de cero.
- **No concluyente** si no hay potencia para 0,05R.

## Cómo podría refutarse

El filtro se eligió mirando DESC y abr–sep. Si en 2024–jul 2025 no rinde, era ajuste a esas ventanas.
