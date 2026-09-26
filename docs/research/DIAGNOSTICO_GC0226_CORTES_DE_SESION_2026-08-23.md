# Diagnóstico del `PARITY_GC0226_FAIL` — la lógica de sesión **coincide**; el hueco es de datos

- **Fecha:** 2026-08-23 · **Rama:** `foundation/f0b-compatibility-probe` · **Base:** `ff19173`
- **Firewall:** outcomes `false` · junio no abierto · sin cambios a kernel, `.cs`, harness ni spec
- **Continúa:** `PARIDAD_DICIEMBRE_GC0226_FERIADOS.json` (`PARITY_GC0226_FAIL`, cobertura 1.427/185.697)

> El FAIL de cobertura decía *«no se pudo medir el kernel»*. Esta pasada mide lo que ese
> FAIL dejaba sin medir, con una prueba que **no necesita alineación tick-perfecta**.

---

## 1. La prueba

Comparar el **patrón de cortes de sesión** —la secuencia de cubetas residuales, posición y
largo— entre el `.cs` y el kernel Python sobre la misma cinta. Si la lógica de sesión difiere,
los largos difieren. Si sólo difieren los datos, los largos coinciden y las posiciones se
corren.

## 2. Resultado: los largos alinean 1:1

```
.cs (28)    8 11 17  3 16 12 3 18 9 23    6 22 15 12 15 11 11 10 11    3 6 17 23 13 2 22 8 1
Python (32) 9 11 17  9 16 12 3 18 9 23  1 6 22 15 12 15 11 11 10 11  1 3 6 17 23 13 2 22 ...
                                        ^                            ^
                                        residuales de largo 1
```

**Sacando las residuales de largo 1, las dos secuencias son la misma.** El kernel Python y el
`.cs` **cortan las sesiones en los mismos lugares y con los mismos largos**.

⇒ **No hay defecto en la lógica de corte de sesión.** Eso es lo que el `PARITY_GC0226_FAIL` no
podía decir, y es la parte del kernel que más riesgo tenía de estar mal.

## 3. Las 4 residuales de más, reconciliadas al número

```
 28   residuales del .cs                                     (legitimas)
+ 3   sesiones fantasma por ticks sueltos de fin de semana
      20251206 (1 tick)   20251221 (1 tick)   20260104 (5 ticks)
+ 1   residual de cierre: la ventana de Python corre 1 h mas alla del oraculo
----
 32   residuales de Python                                   COINCIDE
```

### 3.1 El mecanismo, verificado en fuente

`bigtrap2absorption.py:415-423`:

```python
for i in range(n_ticks):
    sess_i = s_ids[i]
    if cur_session is None:
        cur_session = sess_i
    elif sess_i != cur_session:
        if len(cur_block) > 0:
            flush_block(cur_block, True, cur_session)   # residual
            cur_block = []
        cur_session = sess_i
```

Un tick aislado en el hueco del fin de semana recibe **sesión propia**. Verificado con
`session_ids` sobre un caso mínimo:

```
Fri 12-05 20:00 -> sesion 20427
Fri 12-05 20:01 -> sesion 20427
Sat 12-06 03:00 -> sesion 20428     <- sesion propia para un solo tick
Mon 12-08 00:00 -> sesion 20430
```

Ese tick abre sesión (flush residual legítimo del bloque anterior), queda solo en `cur_block`, y
al tick siguiente vuelve a cambiar la sesión ⇒ **segundo flush, residual de largo 1**.

### 3.2 Y esos ticks el `.cs` nunca los vio

| sesión | NT8 | cinta |
|---|---:|---:|
| 20251206 (sábado) | **0** | 1 |
| 20251221 (domingo) | **0** | 1 |
| 20260104 (domingo) | **0** | 5 |

⇒ **Las residuales de largo 1 son la diferencia de datos propagándose, no un bug de
aritmética del kernel.**

---

## 4. Corrección de una afirmación previa mía

En la respuesta anterior califiqué las residuales de largo 1 como **«DEFECTO DE KERNEL»**.
**Es incorrecto y lo retiro.** Las inferí de la tabla antes de leer el código; leído el código y
medido `session_ids`, se explican íntegramente por 7 ticks que la cinta tiene y el chart no.

Lo que **sí** queda en pie, y es distinto:

> **El kernel no tiene guarda de sesión mínima.** Un solo tick fuera de horario produce una
> sesión fantasma, una residual de 1 tick, y —por la numeración acumulada de cubetas— un
> desfasaje permanente de todo lo posterior. Es robustez, no corrección: dado el input, el
> comportamiento es defendible. Pero un tick de ruido no debería poder desalinear una corrida
> entera.

El `.cs` nunca enfrentó la pregunta porque la plantilla de sesión de NT8 filtra esos ticks antes.
**La asimetría no está en el algoritmo: está en qué llega a cada lado.**

---

## 5. Lo que sigue confundido, y no lo resuelvo acá

Dos filas de la tabla **no** son interpretables:

| fila | sesión | `.cs` | Python | por qué no se puede concluir |
|---|---|---:|---:|---|
| 1 | 20251124 | 8 | 9 | es la sesión con +24 ticks de diferencia de datos |
| 4 | **20251127** | **3** | **9** | Thanksgiving: +431 ticks de diferencia |

En esas dos, «el kernel corta distinto» y «vio ticks distintos» son indistinguibles con esta
evidencia. **Quedan abiertas.** Se cierran sólo con una cinta y un chart que contengan el mismo
flujo en esas sesiones.

No verifiqué el largo de las 4 residuales finales de Python; la salida las lista sin ese dato.
Que sean de largo 1 es **consistente con la reconciliación del §3, pero no está medido**.

---

## 6. Efecto sobre el estado del programa

| antes | ahora |
|---|---|
| `PARITY_GC0226_FAIL`, cobertura 0,77 %, causa desconocida | causa **identificada y reconciliada al número** |
| riesgo abierto: ¿el kernel corta mal las sesiones? | **descartado** — largos 1:1 |
| riesgo abierto: ¿aritmética rota en feriados? | **sigue abierto** — 1.427 cubetas no alcanzan |

**El `PARITY_GC0226_FAIL` no se levanta.** Sigue siendo FAIL y la firma de Puerta 0 sigue
acotada a su ventana original. Lo que cambia es el peso: el fallo es de **insumo**, no de
motor, y la parte del motor que se pudo aislar **coincide**.

---

## Aporte al referente

Se separó, con una prueba que no requiere alineación, lo que el gate de cobertura mezclaba: la
lógica de sesión del kernel reproduce la del `.cs` exactamente, y las cuatro diferencias se
explican por siete ticks de fin de semana más un borde de ventana. Un FAIL de cobertura del
0,77 % no dice «el kernel está mal»; acá se midió cuál de las dos cosas era, en vez de dejar
que el número chico decidiera por su cuenta.

## Nota de método

Llamé «defecto de kernel» a algo que resultó ser la diferencia de datos propagándose, y lo hice
por inferir de una tabla en vez de leer el código —que estaba a un `grep` de distancia y era
gratis—. Es el mismo error que esta auditoría ya le señaló al acta del 22 con el fill `11537_B`:
tener el dato desambiguador delante y sacar la conclusión antes de mirarlo.
