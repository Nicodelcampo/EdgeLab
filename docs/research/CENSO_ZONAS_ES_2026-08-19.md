# Censo descriptivo de las zonas de HFTZonesESPureV2 — ES

- **2026-08-19** · artefacto `docs/research/censo_zonas_es.json`
- Fuente: `runs/oraculo_espurev2_ES_snapshot.sqlite` (`ORACULO_CONTROLADO`)
- **23.863 zonas · 120 sesiones** · 2025-12-22 → 2026-06-30 · sólo pre-firewall
- Target-free: **sin toques, sin rechazo, sin MFE/MAE, sin P&L**

---

## El hallazgo: **el 92 % de las zonas son bajistas, y es un bug**

| | dir −1 | dir +1 | % alcista |
|---|---|---|---|
| Absorb | 14.688 | 1.289 | 8,1 % |
| Predator | 7.227 | 652 | 8,3 % |
| Ultra | 6 | 1 | 14 % |
| ES 03-26 | 9.528 | 850 | 8,2 % |
| ES 06-26 | 10.717 | 936 | 8,0 % |
| ES 09-26 | 1.676 | 156 | 8,5 % |

**Idéntico en los tres buckets y los tres contratos.** No es el mercado ni el período:
es el detector.

### La causa, en el `.cs`

```csharp
// l.215-216
isDown = small && cl <= clP && cl <= op;
isUp   = small && cl >= clP && cl >= op;

// l.233-234
if (isDown)    { dir = -1; Iniciar(...); }
else if (isUp) { dir =  1; Iniciar(...); }
```

Con el precio **plano** (`cl == clP == op`) **las dos condiciones son verdaderas**, y
`isDown` se evalúa primero. **Todo tick plano abre una racha bajista.**

Y el diagnóstico v2.3 ya había medido que en este store entre el **41 % y el 86 %** de
los intervalos son `dt = 0`, con hasta 14.837 trades compartiendo timestamp: los ticks
planos son abundantísimos.

Es exactamente el defecto que las notas de ingeniería de `HFTZones2` mandan evitar —
*«no arrancar en plano ni `isDown`-first»*—. `HFTZones2` lo corrigió;
**`HFTZonesESPureV2` no.**

**Consecuencia:** la población está sesgada por construcción. Cualquier medida
direccional sobre estas zonas mide el orden de dos `if`, no el mercado.

## Segundo hallazgo: la ocupación está saturada

`no_move_vol / total_vol`:

| p05 | p25 | p50 | p75 | p95 |
|---|---|---|---|---|
| 0,798 | 0,913 | **0,946** | 0,968 | 0,989 |

**94,9 % de las zonas superan 0,8** y el 45,4 % superan 0,95.

La spec de `HFTZonesRange` (§2) propone `occ >= eff_absorb_occ` con `Q_OCC = 0,80` para
definir ABSORB. **Con esta distribución clasificaría casi todo como absorb.** Es la
segunda vez que un estadístico que propuse sale degenerado, después de
`3 × mediana(volume) × 8`.

**No se baja `Q_OCC` para arreglarlo** — sería elegir el umbral después de ver el
resultado. Lo que hay que revisar es si la ocupación, medida así, separa algo.

## Estructura

| | mediana | p05 | p95 |
|---|---|---|---|
| zonas por sesión | **202** | 3 | 366 |
| altura (ticks) | **3,0** | 1,0 | 11,0 |
| duración (ms) | **108** | 8 | 272 |
| pasos | 171 | | 419 |
| volumen | 280 | | 768 |

- **Buckets:** Absorb 15.977 (67 %) · Predator 7.879 (33 %) · **Ultra 7** (0,03 %) — el
  bucket Ultra prácticamente no se dispara.
- **Solape:** sólo **1,6 %** de las zonas se pisan con la siguiente en tiempo y precio.
  No se apilan.
- **Concentración horaria:** los 3 bloques más cargados —21, 16 y 15 horas desde la
  apertura de las 17:00 CT— concentran el **54,4 %** de todas las zonas. Corresponden a
  la apertura y el cierre del cash americano.
- **`p05 = 3` zonas por sesión:** hay sesiones casi vacías. La dispersión entre sesiones
  es enorme y ninguna mediana se publica sin sus cuantiles.

## Contexto guardado, sin usar (P-55)

Por sesión: número de zonas, rango de precios cubierto, volumen total, minuto mediano,
fracción Absorb y fracción alcista. **Este censo no condiciona nada con eso** — se
guarda para que preguntar por contexto más adelante no obligue a re-correr.

## Qué queda

**El sesgo direccional bloquea cualquier análisis direccional** sobre esta población.
Antes de medir «rechazo» hay que decidir qué hacer con el `isDown`-first: corregirlo en
el `.cs` y regenerar el oráculo, o medir sólo lo no direccional.

**Es decisión de Nico y del auditor.** Corregir el `.cs` cambia el objeto que se está
validando.

**Aporte al referente:** el censo descriptivo —sin tocar un solo resultado— encontró que
la población está sesgada por el orden de dos condicionales. Medir rechazo sobre ella
habría dado un efecto direccional espurio del tamaño del sesgo.
