# HFTZones — ES-range + escalas por activo (2026-08-19)

Nico prefiere `HFTZonesESPureV2` (no está en el repo) a `HFTZones2` (sí).
Razón vista en el gráfico: HFTZones2 marca **demasiadas** y **solo el borde**.
ES pinta la zona entera. Pedido: mejorar el de ES con microestructura, y que
se adapte solo al activo al colocarlo.

Esto alimenta **P-48** (no es un P nuevo). No es F4. Sin MAE/MFE/P&L.

## 1. Por qué se ven distintos (leído en el .cs, no en el chat)

| | ESPureV2 | HFTZones2 v2.3 |
|---|---|---|
| Geometría | `[swL, swH]` = rango del barrido | 1 tick en el origen (`ZoneHeightTicks=1`) |
| Qué dibuja | el tramo que se negoció | un filo |
| Umbrales | fijos de ES (vol 200 / 500, 15 ms, 5 ticks) | cuantiles de la sesión anterior |
| MinPasos / sweep | 10 / 5 | 8 / 4 |
| Absorb | altura &lt; MinSweep | igual, más laxo |
| Merge | no | no |
| Vida | para siempre | close_through + MaxAgeBars |

El “solo el borde” **no es un bug**: está declarado. Alcista → soporte
`[swL − 1 tick, swL]`. Bajista → resistencia de 1 tick sobre `swH`.
Nico quiere el **otro objeto**: el intervalo donde corrió la racha.

Las “demasiadas” salen de umbrales más flojos + absorb corto + sin merge +
filo de 1 tick que se lee como zona nueva cada vez.

## 2. Qué quedarse de cada uno

**Del ES (el objeto):** rectángulo `[swL, swH]`. CVD / no-move / max-level
como *features*, no como semáforo.

**De HFTZones2 (la ingeniería):** grilla entera de ticks; no arrancar en
plano ni `isDown`-first; calibración **congelada** en la sesión previa;
CSV de eventos (no `C:\LoggerHFT\…`); dibujo solo en la barra primaria;
expirar; `CALIBRATION` auditable.

No se portan: SQLite en el indicador, rutas hardcodeadas, MAE/MFE.

## 3. Mejoras de microestructura (las que sí valen)

Literatura útil: tick-rule ~76–81 % (Lee–Ready; Chakrabarty et al.);
absorción = mucho volumen, poco avance (iceberg / Bookmap / NexusFi);
Kyle λ = impacto / flujo firmado. Nada de eso autoriza a “ver el gráfico
y tunear”.

1. **La zona es el rango transado**, no el origen. Ahí estuvo la subasta.
2. **ABSORB no es “salió chato”.** Hoy ambos dicen absorb si
   `height &lt; MinSweepTicks`. Eso es una racha corta. Absorb de verdad:
   `no_move_vol / total_vol` alto **y** `|Δp|` chico frente al volumen.
   ES ya calcula `NoMoveTicks`, `NoMoveVol`, `MaxLevelTicks`. Usarlos.
   Tick-rule no es intención institucional; es un proxy.
3. **Merge.** Dos rachas mismo lado que se pisan en precio y están a
   &lt; T ms son **una** zona. Sin esto, cualquier umbral “adaptable”
   vuelve a llenar el chart.
4. **Escalar altura en ticks del activo, no copiar el 5 del ES.**
   5 ticks ES ≠ 5 ticks 6J ≠ 5 ticks YM. El piso = `max(H_floor, Qp de
   high-low de 1 s en ticks)` congelado con la sesión previa.
5. **Volumen en múltiplos de la mediana del tick**, no 200 contratos.
   MES es 1/10 de ES; 6E no se parece. HFTZones2 ya hace
   `k × median(vol_tick) × MinPasos`. Eso se queda.
6. **Velocidad: cuantiles de intervalos inter-tick con pausas afuera**,
   no de todas las rachas que “se ven bien”. Congelar. Primera sesión =
   `CALIBRATION_PENDING`, sin fallback lindo.
7. **No adaptar MinPasos / FallosTolerados / la definición** mirando
   densidad. Eso es elegir el umbral después del dibujo.
8. **No DOM ⇒ no icebergs de verdad.** El proxy es ocupación de nivel.
   Declararlo.

## 4. Cómo se adapta solo (sin que Claude mire el chart)

Al colocar el indicador, NT8 ya tiene la serie 1-tick del gráfico.
Claude **no** elige números a ojo. Corre la misma cuenta.

**En el indicador (automático, causal):**

- `AdaptiveMode=true` por defecto.
- Al cierre de cada sesión se congelan, para la **siguiente**:
  - `eff_max_avg_ms`, `eff_max_pausa_ms`, `eff_max_total_ms`
    (cuantiles de ms, mismas fórmulas que HFTZones2)
  - `eff_min_total_vol`, `eff_min_vol_rate` (mediana de vol/tick)
  - `eff_min_sweep_ticks = max(H_floor, Q_height(1s))`
  - `eff_absorb_occ` = cuantil de `no_move_vol/total_vol` **solo si**
    se usa absorb; si no hay historia de rachas, absorb apagado hasta
    tener N.
- Estructural **fijo y único** (hipótesis): `MinPasos`, `FallosTolerados`,
  merge-gap, `H_floor`.
- Exporta un evento `CALIBRATION` con todos los eff_*. Replicable 1:1
  en numpy.

**Offline (Claude + store de ticks), una vez por contrato:**

1. Leer ticks de sesiones **completas** (holdout afuera).
2. Correr el calibrador (mismas fórmulas).
3. Escribir `docs/research/hftzones_calib_catalog.json`:
   `instrument → {eff_*, n_sessions, head_commit, asof}`.
4. El indicador puede leer el catálogo como semilla; si no hay, espera
   una sesión. Nunca inventa.

Si Claude “abre el gráfico y baja MinPasos hasta que se vea limpio”,
es SPARKing. El criterio es la fórmula, no la foto.

## 5. Producto: no parchar HFTZones2

Nombre de trabajo: **HFTZonesRange** (o v3). Motor visual del ES +
ingeniería de HFTZones2 + §3. HFTZones2 se queda para paridad vieja.

No abrir esto en la misma corrida que F4 / manifiesto v2 / MAE.

**Aporte al referente:** adaptar es congelar escalas del activo.
Elegir umbrales mirando el dibujo es el mismo pecado que P-47.
