# Estrategia JForex U1-CRUZADO (señal causal sobre USATECH)

Estado: VIGENTE (2026-11-02). Pedido de Nico: «Escribí la estrategia en JForex, yo la compilo y corro, luego comparamos la paridad».
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

## Qué es
`nt8_tools/jforex/EdgeLabU1Cruzado.java` porta 1:1 `u1_cruzado.senales` con `areas_expansion.disparos_causales`:
- la regla congelada de U1-CRUZADO (N ≥ 3 zonas LUX-IMB en 40 pts, regreso al 25 % de A, A/H ≥ 8);
- **la versión causal**, la que se puede operar en vivo.

**No opera:** sólo calcula la señal. La orden va en NQ, en NT8.

## Cómo correrla
1. En JForex: Strategies → New → pegar el archivo → Compile. Correrla sobre `USATECH.IDX/USD`.
2. Parámetros:
   - calentamiento: por defecto 48 h de ticks históricos, que alcanza porque zonas y áreas viven 500 min;
   - carpeta de salida: vacío = la carpeta de archivos de JForex.
3. Salida:
   - `ticks_USATECHIDXUSD_YYYYMMDD.csv`: todos los ticks usados, incluido el calentamiento;
   - `senales_U1_USATECHIDXUSD.csv`: `t_cierre_s, lado, lo, hi, H, E, A, D, c, t_area_s, fase`.
4. Cada señal se imprime en la consola. `lado = 1` significa que el precio vuelve desde arriba del área: venta hacia el borde lejano.
   `lado = -1` es compra.

## Ejecución en NQ (NT8)
- **Base:** cierre NQ − cierre USATECH en el minuto de la señal (`t_cierre_s`).
- **Entrada:** primer tick de la vela NQ siguiente.
- **Objetivo T3:** borde lejano + base, redondeado al tick.
- **Stop:** E + base, un tick más afuera, con tope de 3 × la distancia al objetivo.
- **Sin vela NQ en ese minuto:** no se opera.

## Paridad
**Medida acá (núcleo Java compilado con javac contra Python, mismos ticks):**

| Datos | A/H ≥ 4 | A/H ≥ 8 |
|---|---|---|
| Muestra 1 (141 mil ticks) | 47/47 | 15/15 |
| Muestra 2 (343 mil ticks) | 22/22 | 8/8 |

- La diferencia máxima en E y A es de 4e-12.
- Test: `tests/research/test_paridad_jforex_u1.py`.
- Las muestras son sintéticas: así se prueba la lógica, no el feed.

**Con la corrida real de Nico:**

```
python tools/paridad_jforex_u1.py comparar --ticks "<carpeta>/ticks_USATECHIDXUSD_*.csv" --senales <carpeta>/senales_U1_USATECHIDXUSD.csv --desde-s <fin del calentamiento + 1000 min>
```

- Compara las señales de JForex con las de Python sobre **los mismos ticks** que logueó JForex.
- Una diferencia ahí es de lógica o de orden de ticks. No es del feed: el feed se compara aparte, contra el parquet de Dukascopy de
  Kaggle.

## Riesgos conocidos
- **Empalme entre calentamiento y vivo:** se descarta un tick vivo idéntico al último del historial. Si JForex entrega ticks
  repetidos con la misma marca, el log lo muestra.
- **Cierre de vela:** se cierra en `onBar` M1 o con el primer tick del minuto siguiente. Un tick tardío del minuto anterior se ignora,
  igual que en el armado de Python, que exige orden.
