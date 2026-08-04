# REPORTE LOCAL — 2026-08-04h

**TICKBAR-001 — la clasificación se corrige: NO es `BAR_BUILDER_MISMATCH`.
Es atribución. Y el clasificador no puede verlo por construcción.**

Captura completa `TickBarDiag` v1.1, 10 Tick, `skip_bars=0`, `max_bars=40000`,
6E 09-26, ventana 2026-06-14 → 06-18 (las cuatro fronteras de sesión adentro).
340.936 filas, 309.939 eventos, 30.994 barras.

---

## 1. Lo que dijo el clasificador

```
CLASIFICACION: BAR_BUILDER_MISMATCH
H1 stream      : OK        (NT8=Python=309.939, digest 9639232233418205644 IGUAL)
H2 cortes      : MISMATCH  (5.702/30.994 = 18.4%, drift -2, no monotono)
H3 atribucion  : no evaluable
```

## 2. Lo que dice la medición directa

Se comparó el **OHLC** de cada barra NT8 (campos del ledger) contra
`bars.build_tick_bars(tk, 10)` sobre el parquet F2, índice contra índice:

```
barras NT8 = 30.994   Python = 30.995   (la extra es el residual final)
OHLC identico en 30.994 de 30.994 barras = 100.00 %
```

**Open, high, low y close coinciden en el 100 % de las barras.**

Por lo tanto: **los cortes de barra son idénticos.** `build_tick_bars` con
reinicio por sesión ya reproduce exactamente las barras de 10 ticks de NT8. El
constructor de barras de Python **no tiene nada que arreglar**.

## 3. Entonces qué falla

Las tres cosas medidas juntas:

| | resultado |
|---|---|
| stream de ticks | idéntico (digest igual sobre 310 k eventos) |
| cortes de barra | idénticos (OHLC 100 %) |
| `n_events` por barra | difiere en **81,6 %** de las barras |

Si el stream es el mismo y los cortes son los mismos, la única variable que
queda es **a qué barra se le asigna cada evento**. Eso es **H3 —
`ATTRIBUTION_MISMATCH`**, no H2.

Coincide con todo lo demás: la media de eventos por barra es **exactamente
10,00** y el drift acumulado es **−2 sobre 30.994 barras**. Los eventos se
conservan; lo que está mal es el reparto. Un constructor de barras equivocado
no produciría una media exacta.

Es, además, exactamente el defecto que el secuenciador v2.2 dice atacar: junta
los eventos BIP1 en **bloques de K por orden de llegada** y los empareja con el
snapshot de la barra N. Pero los bloques de K eventos consecutivos **no son**
los eventos de la barra N, aunque la barra N esté bien cortada.

## 4. Defecto en `tools/tickbar_diag.py` — la firma H3 es inalcanzable

El test de H2 usa `n_events` como proxy de los cortes de barra
([`tickbar_diag.py:200`](../tools/tickbar_diag.py)):

```python
cuts_ok = cuts_equal == m and m > 0      # cuts_equal cuenta nt_n == py_n
```

y H3 está condicionada a que H2 se descarte (línea 212 y 248):

```python
if not (stream_ok and cuts_ok):  -> H3 "NO EVALUABLE"
if stream_ok and cuts_ok and not attr_ok:  -> firma ATTRIBUTION
```

`n_events` **no es el corte de barra**: es la atribución que hizo el indicador.
Usarlo como proxy confunde exactamente las dos hipótesis que la herramienta
existe para separar, y como H3 exige `cuts_ok`, **la firma
`ATTRIBUTION_MISMATCH` es inalcanzable siempre que la atribución esté rota** —
que es el único caso en que hace falta detectarla. Rama muerta, misma forma que
el `PASS` inalcanzable del capture-auditor.

El ledger **ya trae el OHLC por barra**, así que el test correcto está
disponible sin recapturar nada.

**No lo corrijo**: cambiar el criterio de un clasificador después de ver los
datos que clasifica es precisamente lo que el pre-registro impide. Queda
registrado como contradicción para que lo decidan Nico y el auditor.

Hasta que se resuelva, **la clasificación de §1 no debe usarse**: contradice la
evidencia de OHLC del §2, que es directa y no depende de ningún proxy.

## 5. Consecuencias

1. **El lado Python está exacto y no se toca.** Es un resultado positivo
   fuerte: valida `build_tick_bars` con reinicio por sesión y, de paso, valida
   el conversor F2 por una vía independiente (el digest de 310 k eventos
   coincide con NT8).
2. **El fix va en el `.cs`**, en cómo el secuenciador empareja eventos BIP1 con
   barras — no en cómo se cortan las barras.
3. **PRED-003 sigue refutada** (3,91 % en K=25, 81,78 % en K=10). Lo que cambia
   es *dónde* está la causa, no si la predicción falló.

## 6. Lo que NO se hizo

No se diseñó ni implementó ningún fix. TICKBAR-001 §6 exige clasificación →
predicción falsable registrada → recién ahí código. La clasificación acaba de
cambiar de H2 a H3; la predicción se escribe sobre la clasificación corregida,
y antes hay que decidir qué pasa con el clasificador (§4).

Dos hipótesis propias cayeron hoy antes de llegar acá, y las dos por medición:
empates de timestamp (67 % de fronteras en las dos resoluciones, no discrimina)
y corrimiento constante de eventos (predice 23 % para K=25 y K=10; observado
3,91 % y 81,78 %). Por eso el orden importa.

## 7. Abierto

- Decisión sobre `tickbar_diag.py` §4 (semántica del test H2).
- Predicción falsable para el fix de atribución en `BigTrap2.cs`.
- `BigTrap2.cs` appendea el EventLog — portar la rotación de `TickBarDiag` v1.1.
- Filtro de mecha de BigTrap2: `use_wick_filter=false` ya es PASS 393/393 (O3),
  corrible en `time:1` sin depender de nada de esto.
- HP-001 (burst HFT al cierre en ES) — pospuesta.
