# Entrada 017 · Opus 5 → Auditor · P-43: HFTZones2 transporta a GC (2026-08-17)

**Commit de referencia:** `6a3a4850c1f64e1157c92eea5b71f31164dc5aba`.
**Rama:** `foundation/f0b-compatibility-probe`.
**Artefacto:** `docs/research/paridad_hftzones2_GC_30d_2026-08-17.json`.
**Board:** `PENDIENTE.md` § P-43, mismo commit (regla 4).
**CURRENT.md** actualizado en el mismo commit.

---

## 1. Medido — primera paridad fuera de 6E

Oráculo GC 06-26 exportado por Nico (sha256
`0034a61da8d8e41b44edef707169fdc8cdc101b96d4685b1eb01a07f6de9201a`,
127.329 líneas). COMEX, no CME. `tick_size = 0.1` — decimal sin representación
binaria exacta. Caso duro a propósito.

| ventana | kernel | oráculo | MATCHED | huérfanas | FEATURE_DIFF |
|---|---:|---:|---:|---:|---:|
| 12 días | 1.520 | 1.518 | 1.518 | 2 | — |
| **30 días** | **3.630** | 3.628 | **3.626** | **2** | 2 |

**3.626 / 3.630 = 99,89 %.** Con 2,4× más zonas las huérfanas siguen siendo
**exactamente 2, las mismas**. Un defecto sistemático del porteo habría crecido.
No creció. La divergencia es localizada, no sistemática.

## 2. Qué establece (y qué no)

Establece que el kernel **transporta entre instrumentos y entre exchanges**.
ES/NQ/YM (`tick_size` 0.25 y 1.0) son binarios exactos y por lo tanto *más
fáciles* que 6E (`5e-05`, error de redondeo real medido 3,64e-12).

Nico tenía razón: **ningún kernel del bridge ramifica por instrumento**
(verificado). Un segundo activo no re-testea el porteo. Testea el **calendario**.
Por eso se eligió GC y no ES. La afirmación previa de que «hacen falta oráculos
por instrumento» queda retirada.

## 3. Residual, sin adornar

`Z001500` y `Z001501`: ambas `ABSORB`, `dir=-1`, creadas el 2026-04-02 16:34 UTC,
contiguas, geometrías `4686.90/4686.80` y `4686.60/4686.50`. Vecinas inmediatas
(`Z001499` 16:22, `Z001502` 16:41) **sí** emparejaron. No es «todo ABSORB» ni
«todo ese minuto».

**Hipótesis del feriado, no causa:** el 03-abr es Viernes Santo; GC tiene cero
ticks el 03 y el 04; `sessions.py` no modela feriados. Pero las zonas nacen a
las **11:34 CT, en mitad de sesión**, no en un borde. Circunstancial. Podría ser
un borde de `DetectAbsorb` (`MinAbsorbPasos=6`). Queda anotado en P-43 como
hipótesis, no como causa.

## 4. Aporte al referente

La paridad deja de ser un costo por activo y pasa a ser un costo por familia.
Eso libera presupuesto de tiempo — el recurso que compraba cada oráculo nuevo.
