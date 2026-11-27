# PRESET-DIVERSIFICADA — adenda: límite diario de pérdida sobre el mínimo intradía (pre-registro, 2026-11-27)

Estado: PRE-REGISTRO (corrección del simulador de cuentas antes de que Nico decida el tamaño; se escribe antes de recalcular).

- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- Etapa EF2 (descriptivo de cuenta). Familia `CANASTA_CORRELACION`. Pruebas: 1.
- Herramientas:
  - `tools/intradia_min_cartera.py`: camino minuto a minuto de cada estrategia por sesión, desde las corridas NT8 y el arnés más el M1
    de NT8;
  - `tools/cartera_lucid.py simular --intradia`.

Cambio respecto a falla previa: `cartera_lucid._sim_cuenta` (y `lucid_canastas._sim`) aplican el límite diario (DLL) sobre el P&L de
**cierre** del día: `p = max(p, −DLL)`. En Lucid la pausa se dispara cuando el P&L del día toca −DLL **durante** el día, y las posiciones
se liquidan ahí.

Un día que tocó −$3.000 y cerró en −$1.000 se simulaba como −$1.000; en la cuenta se cierra en −$2.700. Con tamaño grande pasa más, así que
el resultado «más tamaño rinde más por mes» (`RESULTADO.md` §5) puede estar inflado.

Antecedentes:
- `RESULTADO.md` §3 y §5 de esta carpeta;
- `docs/research/propfirm_lucidflex_20261117/RESULTADO.md` (reglas oficiales: DLL blando, liquidación al tocarlo).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K28: el simulador cambia, se recalibra con series de resultado conocido; K36
USD con 1 micro y fricción canónica del micro).

Potencia previa: no aplica (descriptivo, sin contraste). Mismos 10.000 caminos y semilla que `RESULTADO.md`.

Diagnóstico de mecanismo: sin grilla. Se recalculan los mismos planes (UNOx1–4, RIESGO_IGUAL e INV_VOL B 100–800), los mismos
universos (INTRA8, DIVERSIFICADA10) y las mismas cuentas.

## Justificación económica
El límite diario existe para cortar los días malos. Si el simulador mira sólo el cierre, regala las recuperaciones intradía que la cuenta
real no permite. El tamaño grande depende justamente de que esos días no corten.

## Qué se corre (fijo)
1. **Camino intradía por estrategia y sesión:** en cada minuto, el P&L realizado más el no realizado. El no realizado se toma en el
   extremo adverso de la vela de 1 minuto (bajo si va largo, alto si va corto). La fricción canónica del micro se descuenta al entrar.
2. **Mínimo intradía de cada plan:** suma de los caminos ponderada por los micros del trimestre; se toma el mínimo del día.
3. **En el simulador:**
   - si el mínimo intradía del día ≤ −DLL, el día cierra en −DLL (liquidación);
   - si no, cierra en su P&L de cierre;
   - el recentrado a la media declarada desplaza igual el cierre y el mínimo.
4. **Recalibración K28:** series constantes con mínimo intradía conocido. Un día de cierre +100 con mínimo −700 en la 25K (DLL $600)
   debe contar −600.

## Cómo se lee (decidido antes)
- **Métrica:** la misma de `RESULTADO.md` §5, la ventaja por mes (valor esperado por mes con media contraída, menos el de «sin
  ventaja»).
- **Si con el DLL intradía el plan de más ventaja/mes de la 150K sigue siendo uno grande** (≥ 2 micros por estrategia), se mantiene la
  recomendación de §5, con los números nuevos.
- **Si pasa a ser 1 micro por estrategia**, §5 queda corregido: el tamaño grande vivía del cierre.

## Cómo podría refutarse
La conclusión «más tamaño rinde más por mes» queda refutada si, con el DLL intradía, la ventaja/mes de 4 micros por estrategia en la 150K
cae por debajo de la de 1 micro.
