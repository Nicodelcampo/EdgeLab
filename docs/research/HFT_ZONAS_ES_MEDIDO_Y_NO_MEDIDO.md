# Zonas HFT sobre ES — qué está medido y qué NO

> Pedido de Nico, 2026-08-20: *«hay que dejar bien claro y registrado lo que NO probamos,
> para no confundirnos y darlo por probado».*
>
> Este archivo se actualiza **en el mismo commit** que cualquier medición nueva sobre esta
> familia. Un resultado que no aparece acá no está medido, por más que alguien lo recuerde.

**Población de referencia**: oráculo `HFTZonesESPureV2Flat`, ES 03-26, 62 sesiones
pre-firewall (2025-12-22 → 2026-03-19), 9.486 zonas, 51,8 % bajistas / 48,2 % alcistas.
Snapshot congelado `runs/oraculo_espurev2flat_ES_snapshot.sqlite`, sha256 `a7dec2ee382c32ea`.

---

## MEDIDO — y muerto

| qué | resultado | alcance exacto |
|---|---|---|
| **Soporte / resistencia** | ~96 % de ruptura, invariante a los 12 parámetros | 6E, no ES |
| **Imán de zona / revisita** | cerrado en F2.7–F2.10 | 6E, 201 sesiones, 15.947 zonas |
| **Retorno a la zona** | pasa el 99,7 % de las veces; **control inválido** | ES Flat — ver retractación |
| **Tasa de volumen dentro → excursión** | ρ ≈ 0 dentro de sesión, terciles sin ordenar | ES V2 (población sesgada) |
| **Costo de cruce borde a borde** | delta pareada +0,0 en 5 métricas; la zona gana < 50 % | ES Flat, 9.234 zonas, control casi-zona |

### Retractación vigente (2026-08-20)
El control **«espejo»** de *retorno a la zona* y de *tasa de volumen* está **degenerado**.
Se construía a la misma distancia del precio de creación, del otro lado — pero la zona
*es* el rango del barrido que la crea, y el barrido termina adentro. Esa distancia tiene
mediana **1 tick** y el **39 %** de las zonas la tiene en **cero**: el espejo cae encima de
la zona. 630 de 1.601 pares daban valores idénticos.

**El «contraste ≈ 0» de esas dos mediciones no es evidencia de ausencia de efecto.**
Está garantizado por construcción. Ambas quedan **retractadas, no muertas**: hay que
re-medirlas con el control casi-zona.

Lo que **no** se retracta: el ρ ≈ 0 de la tasa de volumen se sostiene sobre la zona misma;
y el hallazgo de que una ventana de outcome de largo variable fabrica correlación con
cualquier variable de tendencia intradiaria no dependía del control.

---

## MEDIDO — y vivo

| qué | resultado |
|---|---|
| **Paridad NT8 → Python** | 9.481/9.486 zonas EXACT (**99,95 %**); el residual son claves `start_ts` en ms degeneradas dentro de ráfagas de hasta 182 ticks en el mismo milisegundo |
| **El bug `isDown`-first** | confirmado y corregido: 8,1 % → 48,2 % de zonas alcistas |
| **El algoritmo corre sobre 1 tick** | `AddDataSeries(Tick, 1)`; el gráfico de 25 Tick es sólo dibujo |

---

## NO MEDIDO — y por qué importa decirlo

### Cosas que suenan medidas pero no lo están

1. **Retorno y costo de cruce CONDICIONADOS a contexto.** Todo lo medido es agregado sobre
   la población entera. La dispersión pareada del costo de cruce es enorme (p25 −704 /
   p75 +881 ticks) con mediana cero: la firma que P-55 describe como *dos efectos opuestos
   cancelándose*. **Un nulo agregado no es un nulo condicional.**
2. **Cualquier cosa direccional sobre la población V2 original.** El 92 % bajista era el
   orden de dos `if`. Todo estadístico direccional calculado antes del parche mide eso.
3. **Los otros instrumentos.** Todo esto es ES 03-26. **Nada** se transporta a 6E, NQ o YM
   — ni el resultado, ni los costos, ni el presupuesto de multiplicidad.
4. **El holdout.** 2026-07-01 → 2026-12-31 intacto. Ninguna medición de esta familia lo tocó.

### Cosas que nadie intentó todavía

5. **Combinación con otros indicadores.** Hay catálogo (`aVolClusterPOI` con paridad
   medida, BigTrap2, TRAPs) pero **nunca se midió co-ocurrencia** con las zonas HFT.
   Distinción que hay que sostener: **co-ocurrencia** (¿pisan el mismo terreno?) es
   target-free y se puede medir ya; **«se complementan para atraer al precio»** es un
   outcome y va después, con contexto declarado.
6. **Zonas de otros parámetros.** Todo corre con los `SetDefaults` del `.cs`. No hay
   barrido de `MinPasos`, `MinSweepTicks`, `MaxPausaMs` ni ninguno de los otros.
7. **El lado de la zona.** Se mide la banda entera. Nunca se separó qué pasa al tocar el
   borde superior contra el inferior, ni contra la dirección del barrido que la creó.
8. **Ejecutabilidad.** Cero. No hay reglas de entrada/salida, ni sizing, ni fricción
   estimada para ES, ni fills. La cadena `geometría → información → P&L bruto → edge neto`
   está frenada en el primer eslabón.
9. **`aVolCellPOI2`**: paridad en FAIL (P-42), aparcada. No usar hasta resolverla.
10. **Zonas vivas al cruzar el firewall**: 0 en este oráculo, verificado. Pero si se
    regenera el oráculo con otra ventana, hay que volver a verificar.

### Cosas que el censo descriptivo SÍ está midiendo ahora (target-free, sin outcomes)

Tasa normalizada por actividad · fase de sesión con DST real · solapamiento ·
agrupamiento (Fano) · posición en el rango del día · régimen de volatilidad previo ·
distancia a VWAP/SMA20/SMA50/EMA9/EMA21 · memoria de nivel dentro de la sesión ·
persistencia entre sesiones.

**Ninguno de esos mira qué pasó después.** Ese es el punto: describir dónde la población
varía, para que los contextos se declaren informados y no a ciegas. En el momento en que
una de esas dimensiones se cruce con «y después el precio…», ese corte tiene que estar
**declarado antes**.

---

## Números que circulan y NO corresponden a esta población

Cuidado con estos, que vienen del censo sobre el oráculo **V2 original con el bug**
(23.863 zonas, 8,1 % alcistas) y **no describen** la población corregida:

- «202 zonas/sesión mediana»
- «54,4 % concentrado en 3 bloques horarios»
- «solape 1,6 %»
- «duración mediana 108 ms», «altura mediana 3 ticks»

La población Flat tiene **9.486 zonas en 62 sesiones**. Cualquier comparación contra
aquellos números compara dos poblaciones distintas.
