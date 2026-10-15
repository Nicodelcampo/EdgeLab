# Revisión del cierre direccional de AVZP2 y de los parches 06/07 v2 (Gemini)

Estado: VIGENTE
Fecha: 2026-10-14
Familia / módulo: research · AVZP2 · strategies (revisión; sin aplicar)
Procedencia: archivos de Gemini en `EdgeLab_Bridge` (`RESULTADOS_EMPIRICOS_REALES_KAGGLE_V4_Y_CIERRE_DIRECCIONAL_AVZP2_20261014.*`, `CORRECCIONES_A_C_SUBASTA_Y_MODULOS_v3_20261014.*`, `patches_for_review/06_..._v2.patch`, `07_..._v2.patch`) contrastados con las salidas crudas de los kernels guardadas en `docs/research/kaggle_v4_kernels_20261014/` y `docs/research/avzp2_replica_v2_20261014/`.

## 1. Cifras de Gemini contrastadas con las salidas crudas
| Afirmación | Veredicto |
|---|---|
| O1 con nulo espejado: 0/6 en ES, MES, MNQ y NQ | **Confirmada** (réplica v2, 4 instrumentos) |
| O5 replica 7/7 en ES, MES, MNQ | **Confirmada** |
| O6rev 0/7 ES, 0/7 MNQ, 0/4 NQ | **Confirmada** |
| Kernel 08: interacción γ con `session_auction` v3, 0/6 tras Holm en ES y 0/6 en MNQ | **Confirmada**: mín. p_γ ES 0,0175 (Holm 0,105), MNQ 0,557 (Holm 0,89) |
| `y_O6_d5` ES `6_1000_30`: 26,87 % en balance vs 25,44 % pseudo (p = 0,328) | **Confirmada** (valores exactos del JSON) |
| Break-even de esa carrera: 38,43 % (límite) / 51,48 % (mercado) | **Mal citado.** Esos valores corresponden a TP = 5 ticks (fila de la tabla de frontera); con distancia al centro ≈ 15 ticks y stop 5, el break-even sale de otra fila (TP ≈ 16 ticks, R:R 3:1: ≈ 29,6 % límite / 34,1 % mercado). La conclusión (26,87 % < break-even y sin diferencia contra el nulo) se mantiene, con el umbral correcto. |
| Kernel 09, NQ: O5 6/6 y O5_t0 6/6 con barra de 10 ticks | **Confirmada** (z de −11,6 a −18,4) |
| Kernel 09, MGC: O5 6/6 | **Confirmada**; **O5_t0 no**: 3/6 (p < 0,05 y signo negativo) |
| Kernel 09, GC: O5 4/6 y O5_t0 6/6 | O5 confirmada; **O5_t0: 4/6**, no 6/6 |
| Kernel 09, 6E: O5_t0 6/6 | **No reproduce**: O5_t0 3/6 y O5 2/6; 6E queda débil |
| NORTH_STAR `ed4293b5…` | **Desactualizado**: el cuerpo vigente es `05df5c7c…` (enmiendas HOLDOUT-A1/A2/A3) |
Criterio usado para contar "replica": signo negativo y p < 0,05 por celda de los JSON crudos. Si Gemini usó otro (p. ej. Holm o signo solamente), que lo declare; hasta entonces valen estas cifras.

## 2. Cierre direccional de AVZP2: registrado con alcance preciso
Se acepta cerrar, **con este alcance y no más**: O1 (continuación) con nulo espejado en ES, MES, MNQ, NQ; O6rev (reversión al centro del racimo); la interacción con `session_auction` v3 en ES y MNQ (N_eff = 6 por instrumento); y la carrera al centro con stop de 3/5/8 ticks (`y_O6_d*`) en ES/MNQ `6_1000_30/45`. **Vigente como estado target-free:** O5 (compresión de rango) en ES, MES, MNQ, NQ (barra 10t) y MGC; débil en GC y 6E. No se transporta a otras definiciones de racimo, a otros activos ni a otros estimandos, y **no es una promoción**: O5 es un efecto sobre el rango, no direccional.

## 3. Parches 06 y 07 v2 (no aplicados a `foundation`)
- Se aplican limpios (`git apply --check`) en una copia aislada y sus 10 pruebas pasan; el código se leyó completo antes de ejecutar (sin red, sin `exec`/`eval`, sin subprocesos).
- Corrigen lo observado: IB anclada a 08:30–09:30 CT por reloj de Chicago, señales sólo 09:30–15:00 CT, `tick_size` desde `edgelab.instruments` (más 0,1 para MGC y RTY), pruebas con `np.random.default_rng(42)`.
- **Decisión:** quedan revisados y correctos como código de señal pura, pero **no se incorporan a `strategies/`** hasta que exista el manifiesto de esa familia (regla: cada familia se registra antes de estudiarse). Siguen en `patches_for_review/`.
