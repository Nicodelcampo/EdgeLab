# HFT-RUPTURA — indagación (versión 4, revisión R2)

Estado: RESULTADO (2026-11-10). Pre-registro: `PREREGISTRO_RUPTURA.md` (§2, enmienda A1 §7, revisiones R1 §8 y R2 §9). Datos:
`HFTC_ruptura.json` / `.csv` (DESC jul-2025 → mar-2026, NQ y ES, toques D0 de los clusters del E0-b, reales y control). Código
vigente verificado por `traer` (SHA de los módulos). Las versiones 1–3 del kernel se descartaron sin mirar.

## Global
- Ruptura media (carrera ±X, +1 = atraviesa): **real +0,013**, control −0,064 (un nivel cualquiera rebota; el cluster grande no).
- Por mes, NQ entre −0,05 y +0,07; ES más ruidoso (−0,09 a +0,34, pocos eventos).

## Selección mecánica: **ninguna celda** (0 de 67 nominadas por BH q 0,10)
Por la regla de §9 no se gasta la réplica. Lo que queda son pistas, no evidencia (todo esto es DESC ya usado).

Mejores celdas (ordenadas por p, bootstrap por sesión):

| Rasgo, estrato | n | Ruptura | IC90 | p | vs control | Meses + | NQ / ES |
|---|---|---|---|---|---|---|---|
| tendencia_alineada, bajo (la sesión va CONTRA la llegada) | 1.067 | **+0,082** | [+0,034, +0,131] | 0,0024 | +0,114 | 8/9 | +0,086 / +0,066 |
| picos_dentro = 1 | 456 | +0,105 | [+0,028, +0,183] | 0,013 | +0,172 | 6/8 | +0,065 / +0,188 |
| salida_s, alto (salida LENTA, no expansión limpia) | 1.066 | +0,052 | [+0,002, +0,101] | 0,043 | +0,103 | 6/9 | +0,035 / +0,133 |
| visita, 2 | 1.736 | +0,037 | [−0,002, +0,075] | 0,058 | +0,110 | 7/9 | +0,035 / +0,043 |
| edad_s, medio | 1.065 | +0,048 | [−0,005, +0,101] | 0,069 | +0,243 | 5/9 | +0,034 / +0,117 |

La primera queda a un paso del umbral de BH (necesitaba p ≤ 0,0015 entre 67) y cumple todo lo demás (≥ 0,08, 8 de 9 meses, los dos
activos, mejor que el control).

## Los rasgos pedidos por Nico (enmienda A1 y revisión R1)
| Rasgo | Estratos (ruptura real) | Lectura |
|---|---|---|
| picos de liquidez dentro | 0: −0,001 · **1: +0,105** · ≥ 2: −0,027 | Un solo pico dentro se asocia a ruptura; no es monótono (dos o más no). Pista débil. |
| picos sin tomar en el camino | 0: +0,026 · ≥ 1: **−0,075** (n 482, p rebote ≈ 0,035) | Dejar picos atrás se asocia a REBOTE (canal opuesto al pre-registrado). |
| expansión limpia (`salida_s`) | rápida −0,006 · media −0,008 · lenta +0,052 | La salida limpia no predice nada; la lenta, algo de ruptura. |
| eficiencia de la salida | +0,016 · +0,020 · +0,002 | Nada. |
| última pasada (`pasada_s`) | −0,012 · +0,022 · +0,028 | Nada. |
| volumen del cluster (proxy) | +0,007 · +0,003 · +0,028 | Nada. |
| pendiente EMA 9 | +0,022 · −0,002 · +0,015 | Nada. |
| pendiente EMA 21 | +0,038 · −0,011 · +0,010 | Nada (el tercil «EMA en contra del cluster» +0,038, p 0,11). |

Estratos degenerados (< 10 % en algún estrato, diagnóstico R2): `ancho_x` (ES), `n_zonas` (NQ), `flujo_alineado` (el flujo nunca es
neutro), `picos_dentro` y `picos_sin_tomar` (la mayoría 0). Sus celdas chicas se leen con esa salvedad.

## Lectura y próximo paso (como guía, no como 0/1)
1. **INDAGAR — retroceso contra la tendencia de la sesión que llega a un cluster grande lo atraviesa** (+0,08, estable por mes y en
   los dos activos). Mecanismo plausible: el cluster quedó del lado del movimiento de la sesión y el retroceso que lo alcanza tiene
   impulso; el control rebota. La indagación más barata: medirlo con la magnitud continua y con la tendencia de las últimas 2 h en vez
   de la sesión, sin réplica todavía.
2. **INDAGAR (canal opuesto)** — picos sin tomar en el camino → rebote −0,075. No estaba en la dirección pre-registrada: se
   pre-registra aparte si se sigue.
3. Los rasgos de volumen, EMAs, expansión limpia, eficiencia y última pasada no muestran nada: NO_REPETIR con esta definición.
4. **Réplica**: no se lanza (§9). Usarla para la pista 1 sola sería una prueba congelada de una hipótesis elegida en DESC: decisión
   de Nico.
5. **Banco de eventos**: la especificación `HFT_RUPTURA_banco` **ya no puede correr sobre esta tabla** (todo DESC quedó mirado:
   las dos mitades). Sirve para una tabla nueva (otro activo u otra ventana no usada).
