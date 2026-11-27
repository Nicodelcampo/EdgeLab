# CANASTA-AMPLIA: la ventaja medida a nivel canasta (registro posterior, 2026-11-27)

Estado: REGISTRO POSTERIOR — la exploración se corrió en la sesión antes de escribir esto (scripts de trabajo, consolidados después en
`tools/canasta_amplia.py`). Se registra para que entre al contador; es EF2 exploratorio y no confirma nada. Los meses HOLDOUT A5 de las
familias selladas no se leen. Las del pozo CME ya estaban mirados desde antes.

- **Pedido de Nico (2026-11-27):** «me parece que estás demasiado estricto… el n diluye las exigencias tanto en nuestra como en cantidad
  de estrategias»; «continuá largo y tendido tomando como referente mi mensaje anterior».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF2. Familia nueva:** `CANASTA_AMPLIA` (linaje: CARRIL2_A5, MULTIACTIVO_MECANISMOS, CRIPTO_BINANCE, FUNDEDSYNC,
  CANASTA_CORRELACION). **Pruebas:** 9 (5 grupos del pozo, 3 pozos sellados, 1 combinada).

Cambio respecto a falla previa: las pruebas anteriores exigían a cada estrategia una confirmación que, con los datos que hay, ninguna
puede tener. Acá la hipótesis es una sola por canasta, con una regla fija de inclusión (DESC > 0) y pesos 1/sd. Además, el encogimiento
se calibra con todo el pozo, no sólo con las sobrevivientes.

Antecedentes:
- `ESTADO_DEL_EDGE_20261127.md` §5 (evidencia conjunta de 12 candidatas);
- `carril2_extension_20261126/` (operaciones DESC/REP de Carril 2);
- `auditoria_cartera_20261126/` (Kaggle);
- `cripto_pit_20261127/`.

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v4 — §0–§7 (K36 unidad: R por operación sumado por día, canastas en unidades de sd mensual
de DESC; K27 potencia antes de abrir; K56 episodios por mes y año).

Potencia previa: descriptivo, sin lectura de holdout. La potencia de una lectura única del HOLDOUT A5 de cada pozo sellado se informa en
`EXPLORACION.json`; la apertura tiene su propio pre-registro.

Diagnóstico de mecanismo: sin grilla; la única perilla es la regla de inclusión (todas / DESC > 0 / t > 1 / t > 2), que se publica
completa. Para Carril 2 se publica el aporte por regla y por instrumento y la canasta sin cada regla.

## Justificación económica
Ventajas chicas con mecanismos distintos, correlación baja y costos medidos se suman. La canasta concentra la información que cada
regla sola no alcanza a mostrar. Carril 2 junta reversión de corto plazo, calendario y régimen de volatilidad implícita en índices:
mecanismos documentados (cobertura de opciones, flujo de fin de mes, prima de volatilidad).

## Cómo podría refutarse
La canasta elegida por DESC tiene media ≤ 0 fuera del bloque de selección (REP y, cuando se abra, HOLDOUT A5); o la ventaja depende de una
sola regla o un solo instrumento (sin esa regla, t ≤ 0).
