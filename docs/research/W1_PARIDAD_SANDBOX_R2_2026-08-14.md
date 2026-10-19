# W1 Ronda 2 — Fix de frontera en time:1, comparación 1:1 de junio y veredicto sobre el parquet 06-26 — 2026-08-14

**Etiqueta: RÉPLICA DIAGNÓSTICA NO ADJUDICADORA** (sandbox del auditor externo; la etiqueta formal PASS/FAIL la emite la corrida local gobernada). Continuación de `W1_PARIDAD_SANDBOX_2026-08-14.md`. No abrió outcomes, P&L ni holdout.

---

## 1. P-13 — raíz confirmada, fix verificado, paridad medida

**Raíz (lectura del `.cs` blob `ee984f6e`)**: en `AccumulateTick()`, el bloque `if (fpTicksPerBar <= 0) { curBlock.Add(ev); return; }` cortaba ANTES del bloque de frontera de sesión. Consecuencia: en time:1 el reset de `sesionNoConfiable` era **inalcanzable** → supresión permanente tras el primer `FOOTPRINT_MISMATCH` (17-abr). El oráculo viejo (9 TRAPs, todos ≤ 16-abr) era el registro fiel de un indicador suprimido, no de ausencia de detecciones. Los eventos de control (`ANCLAJE_*`, `BARRA_PROCESADA`, `SESION_RESINCRONIZADA`) viven en el camino de ticks (`DrenarPorOHLCV`, `fpTicksPerBar > 0`) o detrás de ese return: su ausencia en time:1 era estructural, no un filtrado del operador (aclaración del equipo, verificada línea por línea).

**Fix (`f77a3be`, `.cs` blob `62b0c951`)**: la detección de frontera se reubicó antes del `return` de tiempo; el guard `fpTicksPerBar > 0 &&` en `pendCutAt` es correcto (el marcador de corte residual solo aplica a barras por ticks); el resto del diff es el bloque "NinjaScript generated" que NT8 regenera. Verificado sobre el patch: el cambio semántico es exactamente el diagnosticado.

**Oráculo nuevo** (`BigTrap2_v252_6E_0926_time1_90d_completo.csv`, blob `0837ef7e`, sha256 `4c76a0f2…` — ambos recomputados y coincidentes): 9.709 eventos = 3.807 TRAPs + 1.167 ZONE_CREATED + 1.121 INVALIDATED + 3.558 TOUCHED + 36 EXPIRED + 11 FOOTPRINT_MISMATCH + **9 SESION_RESINCRONIZADA con contadores**. Los 9 resyncs corresponden 1:1 a las 9 sesiones marcadas del oráculo viejo; los contadores `zonas_suprimidas` (6, 0, 8, 9, 14, 21, 373, 118, 307) cuantifican la supresión por sesión.

### Comparación 1:1 en la ventana del parquet (junio, 6E 09-26)

Diseño declarado antes de correr: el oráculo de junio debe ser ~subconjunto del kernel (que no implementa supresión, por desviación declarada), faltándole las colas suprimidas de las sesiones con mismatch.

| clase | cantidad | lectura |
|---|---:|---|
| EXACT (side, vol, geometría, close, bar_vol, fp_vol, n_quote/n_rule) | **3.628 / 3.638 = 99,73 %** | paridad del kernel medida al nivel más fino |
| field_diff | 2 | la misma barra (06-26 18:00 ART, ambos lados): `bar_vol`/`fp_vol` 154 vs 153, `n_quote` 91 vs 90 → 1 tick de diferencia entre las dos rutas de datos de NT8 en la barra de cierre de sesión; geometría idéntica |
| MISSING_IN_NT8 | 129 | 128 = colas suprimidas documentadas (06-11/06-12/06-25: el `.cs` declara 798 barras suprimidas en junio; a la tasa medida de ~0,15 traps/barra predicen ~119 — cuadra) + 1 = última barra de la ventana (06-30 18:00 ART: la serie nativa de NT8 termina una barra antes — efecto de borde) |
| MISSING_IN_PYTHON | 8 | 7 = defecto de datos del parquet de junio (→ P-14); 1 = anomalía con barra idéntica (06-24 08:56: OHLCV igual en ambas rutas y aun así el oráculo emite y el kernel no → divergencia a nivel de clasificación de ticks por bid/ask o de estado; tasa 1/3.638; investigar local) |
| ZONE_CREATED (vol≥30) | oráculo 1.152 / kernel 1.191 | la diferencia (39) = colas suprimidas; consistente |

**Nota semántica para la campaña**: los 128 traps de las colas suprimidas son detecciones reales sobre datos verificados que el oráculo no emite por diseño (supresión post-mismatch). El universo de traps de junio difiere 3,4 % entre NT8 y Python por esta política, no por la lógica de detección. Decisión de Nico registrada: en futuras versión `sesionNoConfiable` debe MARCAR los eventos en el log en vez de suprimirlos. Pendiente menor: el meta del oráculo sigue declarando `version=2.5.2` con el código ya cambiado (blob `62b0c951`); subir el string en la próxima edición.

**Estado P-13**: RESUELTA a nivel diagnóstico — causa medida, fix verificado correcto, paridad 99,73 % exacta con el 100 % del resto atribuido a causas medidas. La etiqueta formal la pone la corrida local gobernada con este mismo arnés.

## 2. P-11 — RESUELTA (verificada)

`avolcluster_v05_ES_0926.csv` (blob `bd8b7265`, 150.734 bytes): meta `instrument=ES 09-26` ✓, 1.066 eventos, ventana 01-may→30-jun, `session_index` arranca en 22 (la instancia cargó ~01-abr: 21 sesiones completas antes del primer evento → perfil caliente, sin el defecto H3). El duplicado viejo quedó atrás.
**Bloqueo residual para el replay ES**: falta el parquet ES 09-26 en el sandbox (453 MB no entra como adjunto; ventanear abr→jun + warmup, o por meses).

## 3. P-12 — sigue ABIERTA: el parquet 06-26 NO valida los TRAPs de abril del oráculo 09-26

Veredicto medido sobre el paquete `paquete_6E_0626_abril_mayo_auditor.zip` (contiene el mismo `becc5625…` ya verificado + una copia del oráculo PRE-fix):

1. **Nivel de precio**: el 06-26 en abril opera 40–48 ticks por debajo de las zonas del oráculo. El 01-abr 11:00–13:00 ART el 06-26 operó en [1,1643; 1,1666]; la zona del TRAP#0 es [1,170025; 1,170075] — **34+ ticks por encima de todo el rango operado**: esa zona no existió nunca en el 06-26. Mismo resultado el 10-abr y el 16-abr (spread constante = forward points jun→sep).
2. **Control negativo**: el kernel byte-verificado sobre abril del 06-26 emite 2.985 TRAPs (P1A PASS, 17.236 barras) y **ninguno** coincide con los 9 del oráculo en tiempo + geometría.

El oráculo se generó con `instrument=6E 09-26` (back-month ilquido en abril — de ahí sus traps diminutos de vol 3–8). La paridad exige mismo contrato + misma ventana (H2 del dictamen AVOLT); "front-month natural de abril" no es el contrato del oráculo. **Lo que cierra P-12 es el parquet 09-26 de 90 días**: el primer manifiesto recibido declaraba 3.182.270 filas / hash `2377b076…` — casi seguro es el build completo 04-01→06-30 antes del recorte a junio; si existe local, empaquetarlo (partido por mes) con manifiesto regenerado desde el archivo final.

El parquet 06-26 quedó verificado estructuralmente (5.550.120 filas ✓, monótono ✓, contrato único ✓, 27 unclassified declarados ✓, sin firma D1 ✓, ventana 08-mar→15-jun) y sirve para el universo 6E — pero no para este propósito. Nota de higiene: no es el canónico `124b3750…` de `datos_manifiesto.json`; declarar la diferencia (¿ventana o compresión?).

## 4. P-14 (nueva, abierta) — defecto del 25-jun en el parquet de junio (`46413432…`)

Detectado por la comparación (los MISSING_IN_PYTHON): al parquet le **faltan los minutos 11:02–11:10 ART del 25-jun** (el nativo NT8 tiene barras activas de 314 a 1.893 de volumen ahí) y la barra 12:48 ART aparece **inflada (vol 227 vs 37)**. Escapó a la batería estructural (que miraba duplicados en la ventana de mantenimiento, no minutos faltantes intra-sesión). Criterio de cierre propuesto: regenerar el parquet desde el `.Last.txt` exigiendo cobertura por minuto contra la serie nativa (el chequeo ya existe — barras propias vs `6E_1min.csv` — extenderlo a "0 minutos faltantes en horario activo"), o auditar la fuente.

---

Aporte al referente: la política de supresión quedó medida de punta a punta (cuándo se arma, cuánto suprime por sesión, y su efecto neto en el universo de traps: 3,4 % de junio), la paridad del kernel BigTrap2 en time:1 quedó en 99,73 % exacto con el resto atribuido a causas medidas, y la premisa "front-month valida al back-month" quedó refutada con números antes de que costara una corrida entera. Nada acá emite etiqueta de efecto: es paridad y estructura, nunca outcomes.
