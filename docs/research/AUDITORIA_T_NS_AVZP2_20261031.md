# Auditoría: ¿lookahead de `t_ns` de AVZP2 en las reglas U1? — 2026-10-31

Estado: VIGENTE. Heredado de gonzasib-claude (pedido de Nico: «encargate del trabajo que tenía este agente»), que lo dejó como
prioridad antes de abrir el holdout de la canasta: «AVZP2 tiene `t_ns` antes de la decisión de la zona (mediana 79 s, máximo 3 días);
las reglas U1 usan `t_ns`, incluidas reglas de la canasta. Puede ser un lookahead real».

## Veredicto: no hay lookahead en las reglas U1
- En `edgelab/bridge/indicators/avolzonepoi2.py` la zona se crea en la barra `b` con los ticks del bloque que termina en `b`
  (`end_ns = bars.end_ns[b]`); sus bordes no cambian después. La "decisión" (`decided_bar`) llega más tarde y sólo CLASIFICA la zona
  (estado 1 = zona, 2 = order block) según cómo se aleja el precio.
- Las reglas U1 no usan el estado: `u1_zonas.zonas_almacen` lee `t_ns`, `lo`, `hi` y `t_fin_ns`; el racimo (`racimos_de`) se arma con
  la barra de creación. Usar `t_ns` es causal.
- Prueba empírica (`tests/research/test_avzp2_causal_creacion.py`): truncar la serie de ticks en distintos puntos no cambia ninguna
  zona ni racimo creado antes del corte (sintético con umbrales relajados; con los umbrales reales el sintético no genera zonas).
- Indexar en `t_decidida_ns` (como hace PRERANGE-ZONAS) es una elección conservadora válida, necesaria sólo si la regla usa el estado
  o se restringe a zonas decididas. No hace falta corregir la canasta de 7 por esto.

## Alcance
Vale para AVZP2 individual (`zonas_avzp2`, `zonas_avzg`) y racimos (`zonas_avzrg`). No cubre AVCL, BT2 ni HFT: tienen su propia
prueba de causalidad en sus módulos.
