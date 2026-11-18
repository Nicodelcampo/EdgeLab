# «Atrás» de 5 reglas congeladas de la v2 y la v4 sobre M1 real de futuros, v2 con el motor corregido (K40): REFUTADA_ATRAS (2026-11-18)

Estado: RESULTADO — reemplaza a la v1 del 2026-11-17 (`descartada_v1/RESULTADO.md`), que el motor de la grilla sesgó en contra
(K40: cobraba el stop en el extremo de la vela M1).
- **Pre-registro:** `PREREGISTRO.md` (con la enmienda 1: relanzamiento con el motor corregido). Decisión sin cambios.
- North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Datos:** `CALIBRACION.json`, `ATRAS.json` y `resultados/`. **Herramienta:** `tools/atras_m1.py`.

## Calibración (ago-25 → sep-26): las 5 calibran, con menos sesgo
| Regla | M1 − ticks, v1 (R/sesión) | M1 − ticks, v2 | Corr. v2 |
|---|---|---|---|
| CVGAP2-GC#11 | −0,052 | −0,031 | 0,89 |
| COMEX-CIERRE-GC-R#0 | −0,007 | +0,014 | 0,999 |
| IF-LUX-NQ-R2#1 | −0,160 | −0,076 | 0,998 |
| CVGAP-ES-C | −0,137 | −0,086 | 0,98 |
| PREAPERTURA-NQ | −0,162 | +0,015 | 1,000 |

- **Lo que cambió:** el sesgo pesimista de la v1 bajó a la mitad o desapareció.
- **Lo que queda:** en CVGAP-ES-C e IF-LUX el M1 todavía da algo menos que los ticks (−0,08 R). Lo de abajo puede ser levemente
  pesimista en esas dos.

## Atrás: ventana primaria (años que su linaje no miró), costos canónicos
Potencia de la v1: mismas operaciones y mismo efecto de desarrollo.

| Regla | Canasta | Ventana | Ops | R/op v2 (v1) | IC90 v2 | Años + | Potencia | Veredicto v2 |
|---|---|---|---|---|---|---|---|---|
| CVGAP2-GC#11 | v4 | 2018 → jul-2025 | 431 | −0,128 (−0,156) | [−0,19, −0,06] | 1/8 | 0,99 | **EN_CONTRA_ATRAS** |
| COMEX-CIERRE-GC-R#0 | v4 | 2018 → jul-2025 | 523 | −0,181 (−0,227) | [−0,25, −0,11] | 1/8 | 0,97 | **EN_CONTRA_ATRAS** |
| IF-LUX-NQ-R2#1 | v4 | 2018 → 2022 | 95 | −0,092 (−0,142) | [−0,30, +0,12] | 1/5 | 0,50 | NO_CONCLUYENTE |
| CVGAP-ES-C | v2 | 2018 → jul-2025 | 769 | −0,044 (−0,082) | [−0,11, +0,02] | 3/8 | 1,00 | **EN_CONTRA_ATRAS** |
| PREAPERTURA-NQ | v2 | 2018 → 2022 | 656 | −0,002 (−0,188) | [−0,16, +0,17] | 3/5 | 0,57 | NO_CONCLUYENTE (≈ 0) |

**Canasta** (suma por sesión): 1.453 sesiones, **−193 R** (v1 −386), −0,13 R por sesión, p 0,996, 1 de 8 años positivo →
**REFUTADA_ATRAS**.

**Tramo descriptivo** (2006/2008 → 2017, no decide): las cinco siguen negativas (−0,15 a −0,64 R/op).

## Qué cambia respecto de la v1
- **El veredicto no cambia:** canasta REFUTADA y las mismas tres reglas EN_CONTRA. El tamaño de la refutación es la mitad: la v1
  exageraba la pérdida.
- **PREAPERTURA-NQ ya no está «en contra»:** con el motor corregido da ≈ 0 (−0,002 R/op, 3/5 años positivos). La v1 decía «IC90 entero
  < 0»; eso era K40. Sigue sin evidencia a favor: el IC90 va de −0,16 a +0,17.
- **CVGAP-ES-C:** sigue EN_CONTRA por la regla pre-registrada (media ≤ 0 con potencia 1,0), pero ahora con −0,04 R/op y el IC90
  cruzando cero. Es una regla sin ventaja más que una regla que pierde.
- **La lectura de fondo se mantiene:** lo elegido por el embudo en 14 meses de ticks no tenía ventaja en los años limpios anteriores.

## Consecuencias (pre-registradas, sin cambios)
- **v2:** CVGAP-ES-C sale en la próxima versión. PREAPERTURA-NQ queda NO_CONCLUYENTE, sin tamaño.
- **v4:** CVGAP2-GC#11 y COMEX salen en la próxima versión.
- Ninguna canasta habilita tamaño real.
- La mirada ya estaba registrada como consumida para el linaje de las 5 (`HOLDOUT_VENTANAS.jsonl`, `consumida_atras`).
