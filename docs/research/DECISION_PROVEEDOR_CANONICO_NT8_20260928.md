# Decisión: NT8 como proveedor canónico prospectivo (Nico, 28/09/2026)

**Decisión (Nico):** desde hoy NinjaTrader 8 es el proveedor canónico de ticks y L2 **de acá en adelante**.
Motivo: es la fuente del L2 y la ruta de ejecución en vivo; research y operación miran el mismo feed.

**Alcance preciso (auditoría 054):**
- Es una elección de fuente, **no** una prueba de equivalencia. La paridad `PARIDAD_PROVEEDOR_LUCID_NT8_20260928.md`
  sólo muestra agregados por minuto parecidos; en NQ la mediana de cierres 25t idénticos es 53 %.
- Lo medido sobre Lucid (IPC, espejos, research-v2) queda **etiquetado Lucid**: no se reetiqueta, no se borra, no se
  concatena con NT8 como si fuera una serie homogénea.
- Barras de ticks (25t, 100t, 500t): siempre de **un solo proveedor** de punta a punta dentro de un análisis.
- Para sostener con NT8 una conclusión obtenida con Lucid, se repite el protocolo congelado sobre NT8 y se reportan los
  dos resultados por separado.
- Series NT8 nuevas se canonizan en artefactos propios (`nt8_overlap_2025_2026`, extensión jul–sep, L2 en `E:\l2_parquet`);
  el histórico Lucid no se sobrescribe.

**Pendiente derivado:** el comparador de paridad todavía resume sesiones con contrato distinto (054 §1); filtrarlo antes
de usarlo como evidencia.
