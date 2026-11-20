# CARRIL2-CRASH: el filtro «no comprar con la curva de VIX invertida» queda refutado — en 2011–2017 esas compras eran las mejores (resultado, 2026-11-19)

Estado: RESULTADO — pre-registro `PREREGISTRO_CRASH.md` (1 prueba en `CARRIL2_A5`). North Star sha256
`16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`. Datos: `OPS_CRASH.csv.gz`, `CRASH_DESC.json`, `CRASH_REP.json` (sin nominada:
REP no se leyó). Señal de curva: VIX9D/VIX ≥ 1 al último cierre CBOE anterior a la sesión de entrada.

**T1 (DESC 2011–2017, IBS + Double Seven + pico de VIX):**

| | n | R neto |
|---|---|---|
| Curva normal (la regla filtrada) | 189 | −0,043 (p 0,71) |
| Curva invertida (lo que el filtro saca) | 362 | **+0,240** |
| Contraste normal − invertida | | **−0,284** (ee 0,125; p 0,99) |

| Regla | Normal | Invertida (n de 2011–17) |
|---|---|---|
| Double Seven | −0,080 | +0,284 (132 de 248) |
| IBS + VIX | −0,047 | +0,133 (130 de 176) |
| Pico de VIX | +0,120 | +0,323 (100 de 127) |

- Descriptivo DESC 2018–2025 (de donde salió la hipótesis): normal −0,038 (n 320), invertida −0,037 (n 340), contraste −0,001.
- Episodios (invertida): Episodios: media +0.240 (n 362); sin los 3 peores meses +0.347; sin los 3 mejores +0.169; peores {'201410': -10.2, '201107': -7.63, '201601': -6.16}; mejores {'201705': 7.98, '201609': 12.02, '201306': 12.09}.
- Episodios (normal): Episodios: media -0.043 (n 189); sin los 3 peores meses +0.075; sin los 3 mejores -0.108; peores {'201501': -8.61, '201205': -6.57, '201606': -5.1}; mejores {'201307': 2.17, '201203': 3.07, '201308': 4.56}.

Diagnóstico de mecanismo: una sola perilla fijada antes (umbral 1,0). La curva está invertida en el 66 % de las señales de estas reglas (disparan
en momentos de estrés): el umbral 1,0 no separa «crash» de «estrés normal». No se prueba otro umbral después de ver esto.
