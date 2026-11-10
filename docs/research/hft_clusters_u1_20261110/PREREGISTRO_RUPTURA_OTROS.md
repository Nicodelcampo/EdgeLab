# HFT-RUPTURA-OTROS — la ruptura de clusters HFT grandes en activos que nadie miró, con el banco de eventos

Estado: PRE-REGISTRO (2026-11-10, antes de correr nada en estos activos). Familia `HFT_RUPTURA_OTROS` (linaje: `HFT_RUPTURA`).
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Etapa: EF2 (banco,
exploración en A y prueba en B) + EF3 (hipótesis previas elegidas en NQ/ES, probadas en datos independientes).

## 1. Por qué
HFT-RUPTURA (NQ y ES) dejó efectos chicos sin nominar y una pista viva: el retroceso contra la tendencia de la sesión que llega a
un cluster grande lo atraviesa (+0,082). Con la postura de la directiva 17 (efectos chicos, cuerdas profundas), el paso que más
informa es medir lo mismo en activos que nadie miró: confirma o mata la pista sin gastar la réplica de NQ/ES, y deja que el banco
explore cientos de combinaciones de rasgos con poca multiplicidad.

## 2. Espacio de eventos y población
El mismo de HFT-RUPTURA (`PREREGISTRO_RUPTURA.md` §1): creación, alejamiento, primer regreso, toques posteriores, expiración. Se
mide el **primer regreso tras alejarse X/2** (D0) de cada cluster grande, real y de control (pseudo-cluster desplazado ±1.200 /
±2.400 s que no se superpone con un cluster vivo). Razón: es el evento con más N y el único con tabla comparable a NQ/ES.

## 3. Activos y definición (sin retornos)
- RTY, 6E, 6B y MBT: los activos del release con costo medido que no tienen E0-b. **6J y ZB quedan afuera** (spread sin medir;
  no se presta de otro instrumento).
- YM: con la definición que ya eligió el E0-b original (K4_A025_V1800); su ruptura nunca se midió.
- La definición de cluster de cada activo nuevo la elige la **regla mecánica del E0-b** (`hft_clusters_info.elegir_equilibrio`:
  CV mensual ≤ 0,5 y mínimo `2,49/√N + fricción / ancho`), sin retornos (`python tools/hft_clusters_info.py e0b_otros`). Un activo
  sin definición elegible queda afuera.
- X = fricción / 0,08 por activo (`edgelab/costos.py`): RTY 5,6 pts; 6E 0,0026; 6B 0,0049; MBT 735; YM 64.

## 4. Datos
DESC jul-2025 → mar-2026 (la réplica abr → sep de estos activos queda sin usar para una confirmación futura). Holdout intacto.
**Tabla no mirada**: el kernel `ruptura_otros` sólo guarda la tabla y diagnósticos sin desenlaces (conteos y estratos); nadie
calcula marginales antes del banco (K19).

## 5. Análisis (banco de eventos, `docs/research/banco_eventos/specs/HFT_RUPTURA_OTROS.json`)
- Desenlace `rompe` (carrera ±X, +1 atraviesa), dirección 0 (se exploran ruptura y rebote), nulo 0, umbral económico 0,08, k = 3,
  q = 0,10, 23 rasgos de `hft_ruptura.RASGOS`, cortes fijos de los discretos.
- Mitad A: todas las celdas de 1 y 2 rasgos y el modelo aditivo. Mitad B: k + 1 pruebas congeladas.
- **Hipótesis previas** (elegidas en NQ/ES, probadas en TODA esta tabla con BH q 0,10 aparte):
  1. `tendencia_alineada` = tercil bajo → ruptura (+). La pista viva.
  2. `picos_dentro` = 1 → ruptura (+).
  3. `picos_sin_tomar` = 1 → rebote (−).
- Diagnósticos: control con la misma celda, celda contra el resto (mecanismo, no herencia de la media) y por activo.
- Calibración contra permutaciones en el preflight (bloquea si la tasa de falsos supera 2q).

## 6. Pruebas contadas
Las registra el banco al correr: `banco/HFT_RUPTURA_OTROS/A` (exploratorias), `/B` (k + 1) y `/previas` (3).

## 7. Justificación económica
Un cluster HFT grande es tamaño ejecutado. Si la liquidez que lo formó ya no está cuando el precio vuelve, el nivel no frena;
si el precio vuelve como retroceso contra la sesión, llega con flujo que no se agota en el nivel. Si el mecanismo es de la
microestructura de los clusters y no de NQ/ES, tiene que aparecer en otros futuros líquidos.

## 8. Cómo podría refutarse
La pista del retroceso no se nomina entre las previas (o va en contra) en activos independientes; o el banco no nomina nada en B y
la calibración está sana: los rasgos de llegada no discriminan ruptura en clusters grandes fuera de NQ/ES.

## 9. Riesgos declarados
- Los parámetros de zona (`Z_CERT`) se calibraron con volúmenes de NQ/ES: en 6E, 6B o MBT puede no haber clusters elegibles.
- MBT tiene X = 735 pts: pocos eventos resuelven en la vida del cluster.
- El banco junta activos con cortes por activo; un efecto de un solo activo se ve en el diagnóstico por activo.
- Lo nominado acá no es edge: sigue la réplica abr–sep de estos activos y P&L con ejecución fija.
