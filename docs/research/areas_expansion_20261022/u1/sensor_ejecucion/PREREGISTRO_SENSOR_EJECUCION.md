# Pre-registro: eje sensor / ejecución (experimento 3 de 4)

Estado: VIGENTE, registrado antes de correr. Aprobado por Nico el 2026-11-02. Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa EF3: exploratorio, sobre datos ya vistos.

## Pregunta
¿La ventaja de U1-CRUZADO viene de calcular la señal en el CFD (sensor USATECH) y ejecutarla en NQ, o la misma regla con sensor NQ da
lo mismo?

## Qué existe y qué falta
- **CVGAP: el par ya existe.** CVGAP-NQ (sensor NQ, réplica causal +15,8) y CVGAP-CFD-NQ (sensor CFD, +5,8). No se corre nada nuevo.
- **U1 sobre LUX-IMB: falta sensor NQ con código causal.** Se corre la celda congelada de U1-CRUZADO (N ≥ 3, 40 pts, x = 0,25,
  A/H ≥ 8, E1A/T3/S3 con tope 3×) con sensor y ejecución en NQ, en desarrollo y en réplica (`SENSOR_U1=NQ`, modo TOPES).
- **U1-ZONAS, AVCL y RACIMOS no tienen par posible.** Sus zonas salen del volumen real del futuro, que el CFD no tiene.

## Lectura fijada
- Comparación por tramo, misma ejecución: media neta y diferencia, con IC por sesiones (bootstrap).
- **Sensor NQ ≥ sensor CFD:** el cruce no aporta, y U1 se simplifica a un solo instrumento (NT8 directo).
- **Sensor CFD claramente mejor en los dos tramos:** el CFD aporta información, por ejemplo por su feed continuo o por su volumen.

## Cómo podría refutarse
Que las diferencias cambien de signo entre desarrollo y réplica.

## Registro
2 pruebas (desarrollo y réplica) en `TRIAL_REGISTRY_GLOBAL.jsonl` (`exp3/U1-SENSOR-NQ`).
