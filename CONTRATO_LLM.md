# CONTRATO para proponer estrategias (para LLMs y humanos)

Este documento define lo UNICO que tenés que implementar para testear una
estrategia tick en EdgeLab, y lo que tenés PROHIBIDO implementar. El diseño
minimiza tu responsabilidad: las clases de bug que mataron edges anteriores
(signo invertido, fills sin spread, lookahead de la decisión) son
**imposibles por construcción** si respetás el contrato, y una batería
mecánica rechaza la corrida si algo está mal — no hace falta que "razones"
sobre la corrección: el harness lo decide con PASS/FAIL.

## Lo único que escribís: la función de señal

```python
def señales(times_ms, last, bid, ask):
    """times_ms: int64[] época ms, ordenado. last/bid/ask: float64[].
    Devuelve (idx, dirs):
      idx : int64[] — índice del ÚLTIMO tick de información usada para decidir
      dirs: int64[] — +1 long / -1 short
    """
```

Reglas de la señal (las chequea la máquina, no vos):
1. Para decidir la señal en `idx[k]` solo podés mirar ticks `<= idx[k]`.
   No importa si te equivocás: el **prefix_check** lo detecta solo.
2. No calcules PnL, fills, TP/SL, spreads ni costos. Nunca. El motor
   compartido (`edgelab/engine.py`, ya verificado) hace eso:
   entra al tick SIGUIENTE a tu señal, LONG paga el ASK y SHORT vende el BID,
   el TP exige trade-through, el SL dispara por last y llena al bid/ask,
   y el PnL tiene una sola fórmula en un solo lugar.
3. Si tu estrategia es intencionalmente asimétrica (solo-long, etc.),
   declaralo (`symmetric=False`); si no, el **mirror_check** exige que
   longs y shorts se espejen al invertir los precios.

## Cómo se corre

```python
from validation.harness import full_audit
full_audit("mi-estrategia", señales, times_ms, last, bid, ask,
           tp_grid=np.array([4.,6.,8.,12.,16.,24.]),
           sl_grid=np.array([2.,3.,4.,6.,8.]),
           headline=(24., 8.))   # el combo que pre-registrás como principal
```

## Qué te devuelve y cómo leerlo (cero interpretación)

- `PREFLIGHT RECHAZADO` + la falla exacta → hay un bug. NO se interpreta
  ningún número; arreglá lo señalado. (Falsos positivos minimizados:
  tolerancias de redondeo de tick ya contempladas; el prefix descarta
  trades con hold cortado; el mirror admite ±2%.)
- `PREFLIGHT APROBADO (4/4)` + `VEREDICTO: MUERTA: <causas>` → la estrategia
  no tiene edge. Las causas son mecánicas (expectancy≤0, OOS de signo
  contrario, PBO>0.5, concentración mensual).
- `SOBREVIVE esta tanda` → **todavía no es un edge**. Falta lo que decide un
  humano/sesión principal: registro en el ledger, doble simulador si aplica
  resolución alternativa, y multi-régimen.

## Prohibiciones duras (aunque "parezca necesario")

- Reimplementar fills/PnL/exits "porque mi estrategia es especial" → NO.
  Si el motor no soporta algo (p.ej. trailing), se extiende EL MOTOR con su
  batería de verificación, nunca en el código de la estrategia.
- Tocar grids/umbrales después de ver resultados → cada variante nueva es un
  trial nuevo del presupuesto de multiplicidad y se declara.
- Saltarse el preflight o interpretar números de una corrida rechazada.

## Contexto de por qué existe esto

- EXP-041: filtro evaluado en la barra de entrada con fill intrabar =
  lookahead → mató el mejor "edge" M1. El motor ahora fuerza entrada
  post-decisión. El prefix_check caza cualquier otra fuga.
- EXP-043: un signo invertido en el stop del short convirtió pérdidas en
  ganancias; MCPT p=0.002 no lo vio (GIGO). Los escenarios sintéticos y el
  verificador de ledger lo cazan en segundos, sin razonamiento.
- EXP-044: fills al last sin spread inflaban el fade tick (bid-ask bounce).
  El motor cobra el spread siempre.
