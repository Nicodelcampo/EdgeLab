# IDM-2 — resultado (8 pruebas, Holm 8, nivel familiar 0,0351; 119 s)

Datos crudos: `IDM2_RESULTADOS.json`. Estadístico: coeficiente del componente de SALTOS del resto del día sobre el retorno de la última media hora (unilateral positivo).

**Veredicto: sin hallazgo (0 rechazos).** La prueba de la pista (`idmj/GC_spot_old`, spot 2022-07→2025-06, n = 926): b_salto = +0,0088, p 0,083, Holm 0,66. Signo esperado pero débil: 5 veces menor que en la muestra que originó la pista (referencia GC futuro 2025-26: +0,0475, p 0,0083, fuera de Holm).

| Prueba | n | b_salto | p | Holm 8 |
|---|---:|---:|---:|---:|
| **GC spot 2022-25 (la pista)** | 926 | +0,0088 | 0,083 | 0,66 |
| ES spot 2018-25 | 2.312 | +0,0333 | 0,086 | 0,66 |
| ES, NQ, YM (futuros 2025-26) | 236 a 272 | −0,03 a −0,015 | 0,81 a 0,91 | 1,0 |
| ZB / 6E / 6J | 258 a 280 | −0,013 a +0,0007 | 0,48 a 0,97 | 1,0 |
| *Referencia:* GC futuro 2025-26 (fuera de Holm) | 269 | +0,0475 | 0,0083 | — |

**Lectura según el mandato (`MANDATO.md`):** el mecanismo de saltos **no se confirma fuera de la muestra de origen**. Con signo débil en GC spot 2022-25 y en ES spot (p ≈ 0,08), pero sin pasar la corrección, y sin efecto en los otros activos del 2025-26. La pista `GC_LH_MOMENTUM` pasa a `FAILED_REPLICATION`; **sigue en nivel C** (información episódica, sin forma operable estable) y el generador deja de proponer candidatas sobre ella (incluida la petición de datos de metales, que ya no es prioritaria: aun si se confirmara en 2025-26, un efecto de un solo régimen no sirve para challenges).
**Costo:** 8 pruebas al registro global; riqueza de alfa 0,0392.

## Dos correcciones de sistema que salieron de esta corrida
1. La configuración no tenía el nombre de resultado de la familia nueva (`IDM_JUMP`) y el ciclo se cayó al traerlo. Corregido: un error al traer un resultado ahora queda registrado y se reintenta sin tumbar el ciclo, y la corrida de humo de infraestructura ya no intenta traer resultado.
2. El mandato (`MANDATO.md`) quedó protegido y pesa la selección.
