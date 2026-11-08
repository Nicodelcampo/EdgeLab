# Pre-registro: apertura exploratoria del holdout de CANASTA-GLOBAL (08/11/2026)

Estado: PRE-REGISTRO (commiteado antes de abrir; Nico: «Sí» a la apertura). Referente `docs/NORTH_STAR.md`, cuerpo SHA-256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Modo exploratorio del protocolo
(`edgelab/autopilot/holdout_apertura.py`, decisión de Nico del 08/11). Una apertura para la familia CANASTA_GLOBAL.

- **Canasta congelada:** las 10 reglas de `RESULTADO_CANASTA_GLOBAL.json` (cubo + celda), con la configuración y los cortes congelados
  de cada campaña (estado.json), igual ponderadas por sesión. Nada se cambia.
- **Datos:** sólo el holdout sellado (`nicolasbuttaro/edgelab-holdout-sellado`), sesiones desde el 01/10/2026 hasta la última sellada,
  menos las excluidas de `edgelab/holdout.py`. Etapa ANALIZAR_REGLA con operaciones, P&L en R.
- **Estadístico:** R medio por sesión de la canasta (0 los días en que una regla no opera), p de una cola por inversión de signo por
  sesión (B = 10.000).
- **Combinación pre-registrada:** Fisher sobre p_selección = 0,0099 y p_holdout, 4 g.l. Meta de Nico: p combinado < 0,10.
- **Decisión:** p combinado < 0,10 y R medio del holdout > 0 → la canasta pasa a papel (seguimiento forward con e-proceso) como
  candidata; si no, queda como pista y no se reintenta. El holdout no se usa para elegir ni ajustar.
- **p_desarrollo declarado:** 0,0099. Potencia: con ≈ 25 sesiones el holdout por sí solo tiene poca; se reporta el MDE.
