# Pre-registro — U1 sobre rectángulos de BigTrap2 y sobre la grilla de racimos de aVolZonePOI2 (ES, NQ, YM)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-26.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Pedido de Nico (2026-10-26): «barrido masivo estilo U1 para racimos de aVol (los tipos de racimo son parámetros, también los de la zona
individual) y sobre zonas BigTrap2 (rectángulos extendidos, no círculos) en YM, ES y NQ»; «optimizalo bien y usá las variantes que valen
la pena». Etapa: **EF2/EF3** (DESC → … → OOS), embudo automático; holdout desde 2026-10-23 (como U1-ZONAS-AVCL).

## 1. Familias y campañas
| familia | experimento | instrumentos | celdas por canal |
|---|---|---|---|
| `U1_ZONAS_BT2_<INST>` | `edgelab/research/u1_zonas_bt2.py` | ES, NQ, YM | 4.478.976 (gramática completa de U1-ZONAS) |
| `U1_RACIMOS_GRILLA_<INST>` | `edgelab/research/u1_racimos_grilla.py` | ES, NQ, YM | 46.656 (nivel 1) |
Cada instrumento es una campaña y una familia propia (sin transportar resultados). Linaje: `U1_ZONAS_<INST>` y `AREAS_EXP_1_CRUZADO`.

## 2. Zonas (almacén target-free, `tools/kaggle_grilla/almacen_zonas_main.py`)
- **BT2**: zona dibujada de BigTrap2 (bottom/top), oráculo O1 (Diagonal, barras de 1 min, parámetros por defecto), viva desde el cierre
  de la vela que la crea hasta la vela en que el indicador la invalida (CloseThrough) o la expira (`t_fin_ns`; muerta ya en esa vela).
  No se usan los círculos (TRAPs exportados). Agresor por bid/ask del release.
- **AVZRG**: racimos de AVZP2 (25 ticks) al formarse, para 36 definiciones de zona (percentil {90, 95, 98} × multiplicador de la mediana
  {1,5; 2; 3} × velas por bloque {10, 20} × ancho mínimo {2, 3} ticks) × 12 de racimo (mínimo {4, 6, 8} × ventana {500, 1.000} × altura
  {30, 45} ticks). Lo demás del indicador = réplica AVZP2. Los racimos se arman con la regla `_racimo` del indicador (test de igualdad).
  Por qué esas variantes: los extremos razonables de cada perilla de detección; en el racimo, ventanas largas y alturas medias/anchas,
  donde AVZP2-RACIMO-GRILLA midió compresión 23/23 y O1. Ventanas 250 y altura 20 quedan fuera (racimos chicos, poca N).

## 3. Diseño en dos niveles (aprobado por Nico)
- **Nivel 1** (estas campañas de racimos): definición de zona × racimo como perillas con U1 reducida a su vecindario (N × x × A/H ×
  6 ejecuciones E1A/RET10/VOL_VUELTA × T1/T2, stop S3, escala 1). Mide qué definición tiene algo.
- **Nivel 2**: la gramática completa de U1 sólo sobre las definiciones que salgan como pistas, en una campaña nueva con linaje heredado,
  declarada antes de su DESC.

## 4. Caveats declarados
- Paridad: AVZP2 es PASS en MNQ (25t y 200t); BigTrap2 PASS_CON_CAVEAT en 6E. En ES/NQ/YM corren sin oráculo propio en ese
  instrumento: un resultado positivo exige paridad en ese instrumento antes de operar (no antes de medir).
- Datos: release `liquid_tick_v1` v4 (CANDIDATE_NOT_RESEARCH_APPROVED), como el resto de U1-ZONAS.

## 5. Justificación económica
U1 (regreso al área después de estirarse) es lo más rentable medido; si el mecanismo es «el precio vuelve a donde hubo volumen
concentrado o atrapado», las zonas de volumen real (racimos de AVZP2) y las de traders atrapados (BigTrap2) son áreas mejores que los
huecos de cotización de LUX-IMB.

## 6. Cómo podría refutarse
Sin nominadas por FDR q 0,10 ni pistas confirmadas en lote a réplica; nominadas que no pasan INTEGRIDAD; OOS en contra con potencia; o,
en racimos, que ninguna definición se separe de las demás (la perilla no agrega nada). Muere para esa fuente e instrumento.

## 7. Adenda (2026-10-26, antes de correr): zonas individuales en YM
U1-RACIMOS-GRILLA-YM dio **0 celdas evaluables** (52.629 racimos repartidos en 432 definiciones: N insuficiente, no es un nulo).
Nico: «relajá el filtro para considerar zonas individuales». Campaña **U1-ZONAS-GRILLA-YM** (familia `U1_ZONAS_GRILLA_YM`,
`edgelab/research/u1_zonas_grilla.py`): cada zona de AVZP2 es un área, sin racimo; definición de zona (las mismas 36) como perilla; U1
reducida igual que el nivel 1. 3.888 celdas por canal. Almacén `ZONAS_AVZG_YM`. Linaje: hereda de `U1_RACIMOS_GRILLA_YM` (misma fuente,
mismo instrumento; la de racimos no produjo resultados que mirar). Refutación: igual que §6.
