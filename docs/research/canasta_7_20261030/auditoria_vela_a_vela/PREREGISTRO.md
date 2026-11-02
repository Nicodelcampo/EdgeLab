# Pre-registro: auditoría vela a vela de las 7 reglas de la canasta (experimento 4 de 4)

Estado: VIGENTE, registrado antes de correr. Aprobado por Nico el 2026-11-02. Referente: `docs/NORTH_STAR.md`, cuerpo sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Es una verificación de integridad: no mira ni elige por P&L, y no
consume pruebas del contador.

## Qué se audita
Cada operación con llenado de cada regla, con su celda, cortes y tope congelados y el código causal, en DESC y en réplica. La
auditoría (`grilla_generica.auditar_operaciones`) recorre las velas M1 del instrumento de ejecución con un código propio, distinto del
simulador:
1. **Causal:** el llenado ocurre después del cierre de la vela de decisión. E1C, que llena al cierre de esa misma vela, es un supuesto
   declarado y se cuenta aparte.
2. **Entrada posible:**
   - E1A llena en la apertura de la vela siguiente;
   - las órdenes límite llenan en su nivel;
   - en los dos casos el precio de entrada tiene que estar dentro del rango de la vela (±1 tick).
3. **Orden de los tiempos:** la salida no es anterior al llenado.
4. **Sin stop ni objetivo salteados:** ninguna vela entre el llenado y la salida tocó el stop o atravesó el objetivo por 1 tick
   mientras la operación seguía abierta. Con break-even o con salida por línea (CVGAP), el stop pudo moverse: esos casos se informan
   aparte y se revisan uno por uno.

## Lectura fijada
- **Cero fallas en 1–4:** las cifras de la canasta corresponden a operaciones posibles en tiempo real con esa ejecución.
- **Cualquier falla:** causa raíz, corrección del simulador, re-medición de la regla afectada y aviso en la canasta. No se toca
  ningún umbral.

## Cómo podría refutarse
Que aparezca una sola operación imposible.
