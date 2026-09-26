# REPORTE LOCAL — 2026-08-04g

**TICKBAR-001 / PRED-003 — el oráculo se gastó. Las dos predicciones fallaron.**

Capturas hechas por Nico en NT8 hoy, `BigTrap2.cs` v2.2
(`75910484b7d87510…`, instalado y verificado por hash contra el canónico).
Ventana `6E 09-26`, End date 18/06/2026, Days to load 5. **Tick Replay
destildado** — confirmado por Nico, así que el resultado es válido y no un
artefacto de configuración.

---

## 1. Resultado

| corrida | K | barras | `FOOTPRINT_MISMATCH` | resyncs | zonas creadas |
|---|---:|---:|---:|---:|---:|
| 1 | **25** | 12.395 | **485 = 3,91 %** | 1 | 322 |
| 2 | **10** | 30.993 | **25.347 = 81,78 %** | 3 | **0** |
| 3 | **10** | 30.993 | **25.347 = 81,78 %** | 3 | **0** |

Las corridas 2 y 3 son idénticas fila por fila: el defecto es **determinista**.

### Contra lo pre-registrado

- **P1** — «0 % sobre barras interiores, umbral de corte 1 %» → **3,91 %.
  REFUTADA.**
- **P2** — «si funciona en `tick:25` pero no en `tick:10`, era un parche atado a
  N=25 y se rechaza» → **81,78 % en K=10. REFUTADA.**

Por la regla de la campaña, **el fix se rechaza como está y no se parchea**:
está prohibido arreglar antes de clasificar (TICKBAR-001 §6). Este documento no
propone una corrección.

## 2. Lo que el fix sí consiguió — y no es menor

El defecto viejo era **asignación de volumen**: baldes de 15 a 34 eventos donde
debían ir 25, y NT8 creando ~2× las zonas que Python, **sin que nada lo
denunciara**. Eso desapareció: los 25.832 mismatches de hoy dicen todos
`n_eventos=K; k=K`. **El conteo quedó correcto en las dos resoluciones.**

Lo que falla ahora es la **identidad OHLC** del bloque, que es el verificador
nuevo de v2.2 y no existía antes.

Y la política de rotura hizo exactamente lo suyo: en K=10 suprimió **todas** las
zonas en vez de dejar entrar 30.000 barras de footprint corrupto al store. Por
eso Nico no vio ninguna burbuja en el chart — no es una falla de configuración,
es el fail-closed funcionando.

**El cambio de v2.1 a v2.2 convirtió una corrupción silenciosa en una detenida y
puesta en cuarentena.** La predicción falló; el diseño defensivo no.

## 3. Evidencia para clasificar (NO es la clasificación)

Dos hechos medidos que acotan el espacio de hipótesis:

**(a) El offset es simétrico y chico.** Diferencia `open_blk − open_bar`, en
ticks de precio:

| K | 0 | −1 | +1 | −2 | +2 | ≠0 |
|---|---:|---:|---:|---:|---:|---:|
| 25 | 211 | 137 | 128 | 5 | 2 | 56,5 % |
| 10 | 9.906 | 6.470 | 6.448 | 1.010 | 1.116 | 60,9 % |

Simétrico alrededor de cero y sin dirección preferida. **Eso descarta un
desfase de fase sistemático**, que sería direccional. En ~40 % de los casos el
open coincide y lo que difiere es otro componente del OHLC.

**(b) La tasa escala mal con K.** De K=25 a K=10 hay 2,5× más barras pero
**21× más mismatch** (3,91 % → 81,78 %). Un desalineamiento absoluto fijo de
unos pocos eventos corrompe una fracción mucho mayor de un bloque de 10 que de
uno de 25, y el OHLC de 10 ticks es más sensible a un corrimiento de 1–2 eventos
que el de 25.

**(c) La distribución temporal cambia con K.** En K=25 los 485 mismatches están
**confinados a las barras 1–2571** (la primera sesión) y después corre limpio
9.824 barras seguidas — perfil de arranque. En K=10 son 25.347 repartidos por
**todo** el chart con 3 resyncs que no lo estabilizan — perfil persistente.

Que el perfil cambie de "arranque" a "persistente" al bajar K es el dato más
informativo del día, y es justo lo que `TickBarDiag` está construido para
clasificar (H1 `STREAM_MISMATCH` / H2 `BAR_BUILDER_MISMATCH` /
H3 `ATTRIBUTION_MISMATCH` / H4 mixto).

## 4. Defecto nuevo, independiente — `BigTrap2.cs` **appendea** el EventLog

Las tres corridas cayeron en **un solo archivo**, cada una arrancando en
`seq=0`, con un único `# meta` al tope:
`oracles/BigTrap2_tick25_6E_0926_v22.csv`, 647 KB → 11,6 MB.

Es **exactamente el modo de falla del 2026-07-24** que mezcló tres corridas en
un oráculo. `TickBarDiag` v1.1 lo cerró con sufijo automático de resolución
(`__Tick25` / `__Tick10`) y rotación de índice. **`BigTrap2.cs` no tiene esa
protección**: ni sufijo ni rotación, y abre en modo append.

Consecuencias:

1. Un oráculo de BigTrap2 puede quedar contaminado sin ninguna señal visible, y
   el `# meta` del tope describe **la primera** corrida, no las siguientes.
2. Cambiar la resolución del chart sin cambiar la ruta produce un archivo que
   *parece* de una resolución y contiene otra.

**Esto sí se puede arreglar junto con la paridad**, y debería: es el mismo
`.cs`, no toca el kernel y su corrección ya está escrita y probada en
`TickBarDiag` v1.1. No requiere clasificar nada porque no es la causa del
mismatch — es un riesgo de trazabilidad.

### Qué se hizo con el archivo mezclado

**No se editó ni se borró** (contrato §4: prohibido fabricar o editar
oráculos). Se dejó intacto y se escribieron copias derivadas por corrida en
`oracles/split/`:

```
BigTrap2_v22_6E_0926__Tick25_run1.csv    3.612 filas
BigTrap2_v22_6E_0926__Tick10_run2.csv   25.350 filas
BigTrap2_v22_6E_0926__Tick10_run3.csv   25.350 filas
```

**Estas copias NO son oráculos** y no deben usarse como tales: llevan una línea
`# meta` copiada de la corrida 1. Los params del indicador eran idénticos en las
tres y la resolución de barra no vive en esa línea, así que no afirman nada
falso — pero son artefactos derivados. El oráculo limpio exige recaptura con el
`.cs` corregido.

*(La medición del §1 para K=25 se hizo a las 12:47 sobre el archivo original de
647 KB, antes de que las corridas de 10 lo appendearan. No está contaminada.)*

## 5. Próximo paso

**`TickBarDiag` en 10 Tick**, misma ventana, `SkipBars=0`, `MaxBars=40000`.

Es ahora la captura de mayor información del pedido: en K=10 el defecto satura
al 82 %, así que es trivialmente detectable, y `TickBarDiag` emite una fila por
tick y una por barra — que es lo que hace falta para separar H1 de H2. Toma
minutos.

**No** corresponde recapturar el oráculo de BigTrap2 en 10 Tick: ya se gastó y
ya dio su respuesta.

## 6. Abierto

- Clasificación de la causa (H1–H4) — requiere `TickBarDiag` 10 Tick.
- `BigTrap2.cs`: sufijo de resolución + rotación en el EventLog (§4).
- Análisis de reglas y configuración de BigTrap2 (pedido de Nico) — pendiente.
- Lo anterior sigue abierto: criterio #5 de G2, taxonomía del capture-auditor,
  feriados CME en `sessions.py`, paridad `aVolCellPOI2`.
