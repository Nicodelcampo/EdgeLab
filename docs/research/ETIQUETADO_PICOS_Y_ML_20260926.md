# Etiquetado humano de «picos consecutivos» y plan de aprendizaje automático — 2026-09-26

**Estado:** herramienta lista; sin etiquetas todavía. Idea de Nico: él marca en el visor dónde ocurre el fenómeno y dónde están los picos, y un modelo aprende a reconocerlo fuera de la muestra.

## Herramienta (visor, Parámetros → 🏷 Etiquetado: picos consecutivos)
- **▭ Rango:** arrastrar un rectángulo (tiempo × precio) sobre donde ocurre el fenómeno.
- **⟋ Zigzag:** un clic por pico; cada punto se pega al máximo o al mínimo de la vela (el más cercano al clic). Enter termina el zigzag.
- **✓ Sesión revisada:** marca la sesión en pantalla como revisada completa. **Lo no marcado en una sesión revisada cuenta como negativo.** Sin esto, el modelo no sabe qué no es el fenómeno.
- **↶ Deshacer** y **⭳ Exportar.** Esc sale del modo, y mientras un modo está activo el gráfico no se desplaza.
- **Guardado:** `viewer/nt8_bridge/labels/<activo>.json`, a través del servidor del visor con escritura restringida (`viewer/nt8_bridge/server.py`: sólo JSON, sólo esa carpeta, nombre seguro, ≤ 5 MB), con respaldo en el navegador. Para guardar hay que abrir el visor con este servidor, config `visor-etiquetas`, puerto 8093: `http://localhost:8093/?asset=ES_03-26_202601_25T_HFT`.

## Plan de aprendizaje (después de que haya etiquetas)
1. **Candidatos causales:** un generador amplio y barato (pivotes con n velas a cada lado, grupos de ≥ 2 pivotes del mismo tipo a ≤ τ ticks) propone candidatos **sin mirar el futuro**: cada uno existe desde la vela en que se confirma su segundo pico. El modelo sólo decide sí o no sobre candidatos, así que nunca «ve» algo que el detector real no podría ver en ese momento.
2. **Etiqueta de cada candidato:** positivo si cae dentro de un rango marcado (y sus pivotes coinciden con los del zigzag, a ±1 vela); negativo si está en una sesión revisada y fuera de todo rango. Los candidatos en sesiones no revisadas no se usan.
3. **Rasgos (todos as-of):** tolerancia real entre picos, cantidad de toques, separación en velas y segundos, retroceso entre picos (en ticks y en ATR), volumen y ritmo en cada toque, tamaño relativo a la volatilidad, hora y fase de sesión.
4. **Modelo:** primero uno simple e interpretable (árbol poco profundo o gradient boosting chico). Primero se entiende, después se complica.
5. **Validación fuera de muestra:** por **sesiones** (nunca mezclar la misma sesión en entrenamiento y prueba), con precisión y cobertura contra tus etiquetas en sesiones que el modelo no vio. Meta a fijar con vos, por ejemplo ≥ 80 % en las dos.
6. **Tu revisión final:** el modelo marca sesiones nuevas y vos confirmás o corregís. Esas correcciones son la siguiente ronda de entrenamiento.
7. Recién ahí, **spec congelada** (hash, revisión a ciegas en el Cerebro), censo y enumeración del espacio de eventos, antes de cualquier medición de retornos.

**Cantidad recomendada:** para empezar, 15–20 sesiones revisadas completas de ES, repartidas en distintos meses y horarios.
