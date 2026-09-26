# Intake de oráculos: `HFTZones2` y `aVolCellPOI2` — 2026-08-15

Protocolo de interrupción por oráculos (`CLAUDE.md`) sobre los dos CSV que aparecieron
en `E:\EdgeLab\oracles\`. **Diagnóstico, no adjudicación**: no se corrieron gates de
paridad todavía.

## 1. Identidad

| Archivo | sha256 | Bytes | Líneas |
| --- | --- | --- | --- |
| `hftzones2_v23_6E_0626_time1_100d.csv` | `c314e9df39875011fb2e30bfd694226887f2d82406865edaad2a5ae7ceaa3395` | 47.806.372 | 348.521 |
| `avolcellpoi2_v23_6E_0626_time1_100d.csv` | `5683d2e3286a07da7cac4ca2fb3da6a17d4ed2ecd3a425ec66cec06dffa516dd` | 3.305.472 | 33.975 |

## 2. Ventana, params y timezone

Instrumento **6E 06-26** (no 09-26). El motivo es de warmup, no de comodidad: 09-26
sólo tiene **17 sesiones** en el árbol limpio (08/06 → 30/06) y `aVolCellPOI2` declara
`LookbackSessions=20`, así que el perfil nunca se forma. 06-26 tiene **71 sesiones**
(09/03 → 15/06) y además termina **antes del sello del holdout**, así que no hay cola
que declarar ni recortar. Su parquet (`124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1`)
es uno de los cuatro canónicos del acta de cierre F2.7–F2.10.

Chart: **Minute/1**; los dos `.cs` agregan por su cuenta la subserie `Tick 1`
(`AddDataSeries(BarsPeriodType.Tick, 1)`) y fijan `Calculate = OnBarClose`.

**Timezone verificada por medición, no por declaración.** `HFTZones2` exporta `ts`
(chart local) y `unix_ms` (epoch UTC) en la misma fila. Sobre el primer evento:

```
ts declarado (chart local) : 2026-03-08 19:00:00.104
unix_ms -> UTC             : 2026-03-08 22:00:00.104
offset                     : UTC-3   (ART, coincide con lo declarado)
```

Cobertura observada: `HFTZones2` 08/03 → 15/06; `aVolCellPOI2` 22/03 → 11/06, con
primer evento en `session_index=10` y `sample_count=1029` — consistente con
`MinSessions=10`. El corte del 11/06 (cuatro días antes del fin del contrato) es
compatible con la caída de liquidez del roll: sin celdas que superen
`MinCellSamples=1000` no hay emisión. **No verificado**; queda como observación.

Params de los dos CSV: coinciden con los defaults declarados en los `.cs`.

## 3. Cuarentena abierta y levantada con prueba

Los tres artefactos de `HFTZones2` declaraban versiones distintas, así que el intake
**paró antes de correr gates** (fail-closed). La investigación mostró que las tres
etiquetas describen **el mismo comportamiento**. Detalle completo y prueba en
`PENDIENTE.md` **P-34**; resumen:

- Quitando las 53 líneas de `#region NinjaScript generated code` que NT8 autogenera, el
  `.cs` del repo y el instalado difieren en **un solo bloque**: el repo saca
  `long priceTick = PriceToTick(price);` fuera del `for` sobre zonas y el de NT8 lo
  calcula adentro. `price` es invariante en el loop y `PriceToTick` es pura → **hoist
  de invariante**, mismo valor y mismas comparaciones enteras.
- El kernel Python hace lo mismo que el repo (`hftzones2.py:365-369`); su docstring
  «v2.1» es etiqueta vieja, no código viejo.
- `aVolCellPOI2`: el `.cs` del repo y el instalado **no tienen ninguna diferencia real**.

**Veredicto del intake: oráculos HABILITADOS** para correr paridad.

## 4. Lo que el intake NO establece

La equivalencia probada es `.cs` ↔ `.cs` y la estructura del kernel Python. La
equivalencia **numérica** kernel ↔ oráculo es justamente lo que la corrida de paridad
mide: no se anticipa acá.

Requisito que la corrida debe respetar (contrato de paridad §5, citado en el docstring
del propio kernel): la ventana de comparación arranca en **borde de sesión con al menos
una sesión completa previa**, para que exista calibración congelada antes de las
detecciones comparadas. Para `aVolCellPOI2` hay que entrar además replicando el arranque
declarado por el oráculo (`session_index=10`, `sample_count=1029`).

## 5. Nota de tamaño

`hftzones2_v23_...csv` pesa **47,8 MB**, cinco veces más que el oráculo más grande ya
versionado (`Gaps2_events_nt8_6E_0926_90d.csv`, 9,1 MB). Commitearlo es permanente:
git lo conserva en toda clonación para siempre. Queda **fuera del repo** hasta que Nico
decida, con su sha256 registrado arriba y el archivo íntegro en `E:\EdgeLab\oracles\`.
`avolcellpoi2_v23_...csv` (3,3 MB) sí entra, en línea con lo ya versionado.
