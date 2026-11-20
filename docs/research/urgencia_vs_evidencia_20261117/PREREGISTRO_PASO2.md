# Paso 2: contracción empírica por selección — pre-registro (2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de calcular. Nico: «sí» a seguir con el paso 2. Etapa EF2 (diagnóstico; no elige reglas ni toca el
holdout: usa réplicas ya corridas por el embudo). North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Antecedentes: «contracción por selección réplica descubrimiento pistas embudo» — familias parecidas: HFT_CLUSTERS_INFO, HFT_RUPTURA, HFT_RUPTURA_OTROS; NO_REPETIR: F-SELECCION-EN-GRILLAS-GRANDES, F-HFT-RUPTURA-RETROCESO-CONTRA-SESION-D, F-FRECUENCIA-POR-SELECCION; código: edgelab/research/contraccion.py:1, tools/contraccion_empirica.py:1, edgelab/research/embudo.py:775

Potencia previa: 1.876 pares pista-réplica en 136 campañas de 91 familias (contados sin medias). En sintético con la misma estructura (136 campañas) el IC90 de b mide ≈ 0,05 de ancho (b verdadero 0,12 → [0,09, 0,14]; 0,28 → [0,26, 0,30]): alcanza para distinguir la «mitad» que se usa hoy de valores como 0,25 o 0,75.

## Qué se mide y por qué
Hoy la «media contraída» usa una mitad fija (Lucid, canastas) o un James-Stein entre las reglas de la cartera que nunca se comprobó contra
lo que pasó fuera de muestra. La media de partida del paso 3 (tamaño según la evidencia) tiene que ser la contracción REAL de lo elegido.

## Diseño (`edgelab/research/contraccion.py`, `tools/contraccion_empirica.py`)
- Población: todas las pistas con réplica de todas las campañas del embudo (`docs/research/*/embudo/*/estado.json`), sin elegir campañas.
- Por par: d = media de descubrimiento / sd por operación; r = media de réplica / el mismo sd (sd = se del IC90 · √n): adimensional.
- **b** = pendiente por el origen de r sobre d, cada campaña con el mismo peso; IC90 por bootstrap de campañas (2.000). Tests: recupera una
  contracción conocida (0,28) y da ≈ 0 sin efecto.
- Descriptivos: b por multiplicidad de la familia (< 1.000, 1.000–20.000, > 20.000 pruebas), mediana de r/d, fracción de réplicas
  positivas, y calibración del recorte de Harvey-Liu que el embudo ya calcula (`conservado`).

## Decisión
- La contracción a usar en el paso 3 y en las simulaciones de cuenta es **b** con su IC90 (reemplaza la «mitad» fija si el IC90 la excluye).
- Alcance: lo elegido por el embudo (nominación en descubrimiento, réplica no mirada). Las carteras se eligieron con descubrimiento Y
  réplica: para ellas b es una cota inferior de lo que conservan (una segunda criba sube lo conservado); se informa sin transportarlo de más.

## Justificación económica / cómo podría refutarse
Lo mejor de muchas pruebas sobrestima su efecto por selección (ganador de la maldición); cuánto, depende de cuánta ventaja real había entre
lo probado. Si b ≈ 0, lo elegido por el embudo no conserva nada y el paso 3 debe partir de cero; si b ≈ 1, la selección no infla. Se refuta
la «mitad» si el IC90 de b la excluye.

## Contador
`urgencia_vs_evidencia_20261117/PASO2`, familia VIDA_VENTAJA, 1 prueba (la pendiente global; lo demás descriptivo).
