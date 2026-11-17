# Propuesta de enmienda HOLDOUT-A5: holdout intercalado por bloques para las campañas nuevas (2026-11-17)

Estado: PROPUESTA — requiere la firma de Nico (cambia el firewall del holdout: decisión sólo humana, CLAUDE.md). No se aplica a nada ya
medido. North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.

Pedido de Nico: «definí si para las próximas corridas conviene organizar el holdout de otra manera, para no tener que esperar forward y
validar hoy mismo las nuevas estrategias; podría haber holdouts en ventanas internas de 1 mes separadas entre sí».

## 1. El problema
Hoy el holdout es un solo tramo terminal (sesión CME del 2026-10-01 en adelante, HOLDOUT-A4). Todo lo anterior se usa para descubrir y
replicar, y la confirmación tiene que esperar datos nuevos: con 4–50 operaciones por mes y efectos de 0,1–0,2 R, decidir lleva meses
(la v4 necesita 6,3). Desde hoy tenemos M1 real de futuros desde 2006/2008 (`edgelab-nt8-m1-futuros`), lo que permite separar
confirmación de espera.

## 2. Propuesta
**Tres capas, asignadas una sola vez y para siempre (como la frontera), antes de que ninguna familia nueva mire los años viejos:**

1. **Bloques intercalados (era M1, 2008-01 → 2026-09).** Unidad: mes calendario CME. En cada año, una permutación fija (semilla
   declarada en `edgelab/holdout.py`, hash publicado) asigna **7 meses a DESC, 2 a REP y 3 a HOLDOUT** (25 %). Una permutación por año, no
   un sorteo global: así cada año y cada estación aportan holdout y ningún régimen queda sólo de un lado.
2. **Embargo.** La sesión anterior y la posterior a cada bloque de holdout no pertenecen a ninguna partición (López de Prado: purga y
   embargo). Una operación que cruce el borde de un bloque se descarta, y las reglas de varios días cierran al borde. Los indicadores
   (zonas, medias, ATR) se calculan de corrido sobre toda la serie porque son target-free: lo que no cruza el borde son los
   **desenlaces**.
3. **Terminal (sin cambios, A4).** Desde la sesión CME del 2026-10-01 en adelante sigue siendo holdout + forward. Pasa a tener otro
   papel: no confirma, **vigila que la ventaja siga viva hoy** (e-proceso, futilidad) y **gobierna el tamaño** (paso 3 de
   `urgencia_vs_evidencia_20261117`).

**Camino de una regla nueva, el mismo día:**
- DESC sólo en meses DESC, con selección robusta: FDR, y CPCV/PBO sobre los meses DESC.
- Réplica de pistas en meses REP.
- **Una apertura por familia de TODOS los meses HOLDOUT a la vez**, a N fijo. El plan de potencia (K27) se calcula antes y suele
  alcanzar: una regla de 4 operaciones por mes tiene ≈ 3 × 18 años × 4 ≈ 220 operaciones de holdout, y con efecto/desvío 0,2 hacen falta
  ≈ 155.
- Confirma si se cumplen las tres:
  - p ≤ nivel LORD++ de la familia;
  - media > 0;
  - **estabilidad**: positiva en ≥ 60 % de los años con operaciones, y ningún tercil de volatilidad en contra significativo.
- La confirmada pasa a papel/forward al tamaño mínimo; el terminal decide si crece.

## 3. Por qué así (y no de otra forma)
- **Potencia hoy.** El holdout pasa de crecer 1 mes por mes a tener ≈ 4,5 años de datos ya disponibles.
- **Robustez temporal.** Un tramo terminal mide «un período». Los bloques intercalados miden el mecanismo a lo largo de 18 años y
  regímenes distintos: la prueba de estabilidad viene incluida. El paso 1/1b mostró que en este dominio la deriva es lenta
  (ρ ≥ 0,97), así que el pasado informa.
- **Contra el sesgo del embudo.** El paso 2 mostró que lo elegido cae a ≈ 0 en datos nuevos. Con miles de operaciones intercaladas, ese
  encogimiento se mide en la misma corrida y no meses después.
- **Por qué mes y no semana.** Bloques más cortos dan más bloques pero más bordes, y cada borde pierde 2 sesiones de embargo
  (≈ 20 % con semanas, ≈ 9 % con meses). El mes además conserva el ciclo intramensual.

## 4. Riesgos y cómo se cubren
| Riesgo | Cobertura |
|---|---|
| Reúso adaptativo del mismo holdout por muchas familias (Dwork et al. 2015, «reusable holdout») | Una apertura por familia, α de LORD++ reservado, linaje: una familia derivada de otra que ya abrió hereda la apertura consumida. El diseñador recibe CONFIRMADA/REFUTADA/SIN_POTENCIA, no la curva. |
| Fuga por autocorrelación en los bordes | Embargo de 1 sesión a cada lado y descarte de operaciones que cruzan |
| «Funcionó en 2008–2025 pero no ahora» | El terminal (A4) vigila hoy con e-proceso; la confirmación intercalada no habilita tamaño, sólo entrar al mínimo |
| M1 no es ticks (llenado aproximado) | Calibración por familia en la era de ticks (ago-25 → sep-26), criterios de `papel_m1_20261115/VALIDACION.md`; una familia que no calibra se valida sólo con ticks |
| Reglas de footprint (necesitan ticks, sólo desde ago-25) | Mismo esquema dentro de la era de ticks (≈ 3–4 meses de holdout): poca potencia. Esas familias siguen dependiendo del terminal. Conviene priorizar mecanismos medibles en barras. |
| Contratos y rollover | M1 no ajustado (MergeNonBackAdjusted): precios reales. Las sesiones de rollover se marcan y se pueden excluir por regla declarada. |
| La era 2025-08 → 2026-09 ya está gastada para las familias existentes | La enmienda rige sólo para familias NUEVAS sin linaje en esos meses. Para las derivadas de familias ya medidas, esos meses no son holdout. |

## 5. Qué hay que firmar y qué se implementa después
- **Firma de Nico:** esquema 7/2/3 por año con permutación fija, embargo de 1 sesión, criterio de confirmación (§2) y que el terminal
  pase a vigilar y dar tamaño.
- **Implementación (después de la firma):**
  - `edgelab/holdout.py`: `bloque(sesion)` → DESC/REP/HOLDOUT/EMBARGO, fuente única, con test;
  - los lectores de investigación (ticks, M1 de NT8, M1 de Dukascopy) excluyen HOLDOUT y EMBARGO salvo con un acta abierta;
  - el embudo usa la nueva partición para las campañas nuevas.
- **La reserva de septiembre** (`docs/research/DECISION_RESERVA_PREFRONTERA_20261117.md`) queda absorbida: septiembre 2026 es un mes más
  de la asignación.
- **Hasta la firma** nada cambia: el lector de M1 de NT8 corta en la frontera del 1-oct, y las reglas ya congeladas (v2, v4) usan el M1
  sólo para su «atrás» confirmatorio.
