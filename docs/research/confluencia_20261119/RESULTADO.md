# CONFLUENCIA: confirmar con otra señal no da neto; las señales comparten la misma información (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO.md` (2 pruebas en `CONFLUENCIA_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS.csv.gz`, `DESC.json`, `REP.json` (sin nominadas: REP no se
leyó). DESC de A5 2006–2025, NQ+ES, R neto.

| Prueba | Valor | ee | p | BH q 0,10 |
|---|---|---|---|---|
| P1 contraste confirmadas − no confirmadas | +0,021 (−0,004 contra −0,025) | 0,016 | 0,092 | no |
| P2 R neto de las confirmadas (n 15.140) | −0,004 | 0,018 | 0,58 | no |

| Confirmaciones previas | 0 | 1 | 2 | 3 o más |
|---|---|---|---|---|
| n / R neto | 7.764 / −0,025 | 5.633 / −0,026 | 6.277 / +0,005 | 3.230 / +0,020 |

| Estrategia | n | % confirmadas | R confirmadas / sin confirmar / con 2+ |
|---|---|---|---|
| FM1 | 5.670 | 70 % | +0,001 / −0,035 / −0,002 |
| FM2 | 1.544 | 87 % | +0,013 / −0,056 / +0,040 |
| Franklin | 2.148 | 100 % | +0,002 / — / +0,016 |
| RQ5 | 3.782 | 94 % | +0,004 / −0,097 / +0,023 |
| RQ6 | 4.483 | 92 % | −0,024 / −0,087 / −0,008 |
| SOM | 5.277 | 0,1 % | (casi sin señales previas a las 09:35) |

**Diagnóstico de mecanismo (independencia de las señales, % de días con la misma dirección):** Franklin–FM1 100 %, RQ5–FM1 90 %, RQ6–FM1
86 %, FM2–FM1 81 %, Franklin–SOM 81 %, FM1–SOM 66 %, FM2–SOM 65 %. Franklin y FM1 miden lo mismo (la dirección de la primera media hora);
RQ5/RQ6 casi siempre coinciden con FM1. La «confirmación» cuenta varias veces la misma información: hay ≈ 2 señales independientes, no 6.

Episodios: media -0.004 (n 15140); sin los 3 peores meses +0.008; sin los 3 mejores -0.014; peores {'201308': -59.97, '201606': -57.98, '200911': -49.09}; mejores {'201803': 44.36, '202407': 53.01, '201807': 54.97}.

- Datos para tu lectura: lo que sin confirmación pierde (RQ5 −0,097, RQ6 −0,087, FM2 −0,056) es una minoría de días (6–13 %); con 3+
  confirmaciones el neto es +0,020. Ninguna prueba pre-registrada pasa; REP sellado.
