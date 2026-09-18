# HP-008 — replicación causal multicontrato NQ

## Dictamen

El resultado favorable original no se reproduce al fechar cada señal en la primera barra de 25 ticks que comienza estrictamente después de `available_ts_ns`, eliminar el filtro de reversión futura y comparar contra sobreextensiones no-HFT emparejadas.

## Protocolo congelado

- detector y umbrales `ACCEPT_DEFAULTS` sin retuning;
- barras de 25 ticks reiniciadas por sesión CME;
- EMA de 200 barras calculada causalmente;
- umbral de sobreextensión de 30 puntos, heredado de la hipótesis original;
- exclusión de `END_OF_INPUT`;
- separación mínima de 50 barras entre eventos;
- controles de misma sesión y dirección, emparejados por distancia a EMA, volatilidad previa y preferencia por el mismo bloque UTC de 30 minutos;
- controles fuera de ±100 barras de cualquier señal HFT;
- bootstrap por cluster contrato-sesión, semilla fija, 10.000 remuestreos;
- ningún acceso al holdout abierto en `2026-06-30T22:00:00Z`.

## Resultados

| Contrato | Pares | Δ H20 HFT−control | Δ H50 HFT−control |
|---|---:|---:|---:|
| NQ 09-25 | 11 | −7,70 pt | −11,75 pt |
| NQ 12-25 | 15 | −9,70 pt | −8,73 pt |
| NQ 03-26 | 58 | −7,04 pt | −12,75 pt |
| NQ 06-26 | 539 | −8,97 pt | −15,43 pt |
| **Pooled** | **623** | **−8,78 pt** | **−14,96 pt** |

Intervalos pooled por bootstrap contrato-sesión:

- H20: `[-11.12, -6.21]` puntos.
- H50: `[-18.25, -11.40]` puntos.

El retorno HFT bruto pooled fue `+0,21` puntos a H20 y `−1,42` puntos a H50. Los controles promediaron `+9,00` y `+13,54` puntos respectivamente.

## Interpretación

La marca HFT no aporta la reversión observada en la selección retrospectiva original. En estas ventanas, una sobreextensión comparable sin HFT revierte más. La conclusión es consistente en signo en los cuatro contratos, aunque NQ 09-25 y NQ 12-25 tienen muy pocos pares y no deben interpretarse por separado.

## Limitaciones

- diseño observacional emparejado, no experimento aleatorizado;
- ventanas externas deterministas y acotadas, no contratos completos;
- desbalance de tamaños entre contratos;
- sin comisiones ni slippage: la premisa predictiva ya falla antes de fricción;
- se requiere sensibilidad predeclarada a decongestión, radio de exclusión y caliper de matching antes del cierre definitivo.

## Estado

`HP008_NOT_REPRODUCED_CAUSAL_MULTICONTRACT_PREHOLDOUT`
