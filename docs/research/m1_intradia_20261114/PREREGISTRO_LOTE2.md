# M1 intradía lote 2: gap de apertura y ruptura del día previo (pre-registro, 2026-11-15)
Estado: VIGENTE. EF3. Fichas del banco: gaps (linaje ZONAS_GAPS/CVGAP) y EL-NIVELES-NO-DEFIENDEN (ruptura de niveles visibles continúa).
Código: `edgelab/research/m1_intradia.py` (`gap_apertura`, `ruptura_previo`, `familia2`); kernel `edgelab-m1-intradia-lote2` (LOTE=2).
Datos: M1 Dukascopy 2012 → 2026-09 en Nasdaq, S&P, Dow y DAX (los demás índices tienen costos de CFD que no se pagan intradía).
- GAP: apertura 09:30 vs cierre RTH previo, tamaño en ATR20 (0,1–0,3 / 0,3–0,6 / > 0,6); FILL (hacia el cierre previo) o CONT (a favor, 1 R),
  riesgo 0,5·|gap|; entrada 09:31; cierre 15:55.
- PREVIO: primer cierre fuera del máximo/mínimo RTH del día previo desde las 10:00: CONT (stop a mitad del rango previo; 1 R o 2 R) o
  FALSA (vuelve adentro en ≤ 15 min: en contra, stop detrás del extremo, objetivo la mitad del rango previo).
- 9 variantes × 4 índices + 9 canastas = 45 (contador). Nulo intradía (minuto del día de otro día al azar), 20 réplicas; mismo criterio
  que el lote 1 (t neto DESC > p95 del máximo del nulo y R neto > 0 en OOS y RECIENTE), más lectura en BRUTO. Validado en caminatas
  aleatorias (|t| < 2).
Refutación: nada supera el nulo y el bruto ≈ 0 en los cuatro tramos.
