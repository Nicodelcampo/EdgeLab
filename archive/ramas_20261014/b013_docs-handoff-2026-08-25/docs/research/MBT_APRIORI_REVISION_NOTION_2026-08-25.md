# MBT a-priori — nota de auditoría (Notion AI) — 2026-08-25

**Qué es esto:** registro de auditoría sobre la corrida liviana de Antigravity
(configuración a-priori de BigTrap2Absorption para MBT). El documento original
de Antigravity es `docs/research/MBT_APRIORI_CONFIG_2026-08-25.md` en la rama
`docs/mbt-apriori-2026-08-25`, que al momento de esta nota **existe sólo en la
máquina local, sin pushear**. Esta nota deja el resultado, la verificación y
las decisiones pendientes en el repo aunque aquella rama tarde en subir.

**Firewall:** todo lo medido es estructural (cubetas, zonas, tasas). Sin
outcomes, retornos, P&L, MAE/MFE ni holdout. `CAMPAIGN_OUTCOMES_OPENED=false`.
Esto NO es la prueba de las 3 puertas: la config es sólo el input candidato.

---

## 1. Reportado por Antigravity (no re-medido por este auditor)

Indicador v1.1.1 sobre `MBT 08-26.Last.txt` (555.014 ticks, 97 sesiones),
4 corridas en NT8 con export completo:

| TW | archivo | sha256 (prefijo) | cubetas | zonas/fills |
|---|---|---|---|---|
| 10 | `mbt_export__TW10.csv` | `b88ed81e…` | 55.547 | 728 |
| 15 | `mbt_export__TW15.csv` | `1f217ad2…` | 37.053 | 836 |
| 25 | `mbt_export__TW25.csv` | `14cf8ca6…` | 22.260 | 688 |
| 50 | `mbt_export__TW50.csv` | `55336f11…` | 11.160 | 373 |

- Mediana front-month (TW=25): **760 cubetas/sesión**.
- q=95 → **1,74 %** de cubetas (12 zonas/sesión); q=97.5 → **0,91 %**
  (6 zonas/sesión).
- TW=50 colapsa a 3 zonas/sesión en q=97.5.
- MinStackedRows 2 vs 1: idéntico (372 vs 372 zonas).
- MinTrapFrac 0.1/0.3: ratio 1,23× (estable, muy por debajo del umbral 2×).
- MinHistoryBuckets=100: burn-in superado en la cubeta 147 (~19 % de la primera
  sesión front-month), cobertura causal 99,3 %.
- Régimen: variación intradiaria p90/p10 ≈ **11,7×** → la evaluación formal
  queda circunscripta estrictamente a front-month.

## 2. Verificado por este auditor

- **Aritmética de cubetas consistente**: ticks ÷ TW ≈ cubetas reportadas
  (555.014/25 = 22.201 ≈ 22.260; ídem para 10, 15 y 50). El excedente son las
  cubetas residuales de cierre de sesión, que existen por diseño.
- **Validación cruzada externa**: 760 cubetas/sesión front-month coincide con
  la estimación previa de Claude (480–800), medida por otro camino (L2 y ticks,
  canal Notion, entrada 2026-08-24 19:40 ART).
- **La regla se aplicó como fue pre-declarada**: TW=50 rechazado por el piso de
  5 zonas/sesión, no a ojo después de ver resultados; q evaluado contra la
  referencia GC headline (122 zonas / 24.093 cubetas ≈ 1,02 %).
- **Firewall intacto**: ninguna métrica económica en el resumen.

## 3. Configuración recomendada resultante

`TapeWindowTicks=25` · `AbsorptionPct=97.5` (ver §4) · `MinStackedRows=2` ·
`MinTrapFrac=0.20` · `MinHistoryBuckets=100` · `AbsorptionLookback=500` ·
resto en default v1.1.1.

## 4. Decisión pendiente: q=95 vs q=97.5

El resumen de Antigravity dejó ambas. Criterio del auditor: **97.5**, porque la
regla pre-declarada anclaba a la tasa de referencia de GC (≈1,0 %) y 97.5 da
0,91 % — el ancla exacta. q=95 da 1,74 %: dentro de la banda aceptable
(0,5–2 %) pero más laxo. Si se privilegia muestra sobre fidelidad al ancla, 95;
si se privilegia el ancla, 97.5. **La decisión final es de Nico.**

## 5. Pendientes

1. Pushear `docs/mbt-apriori-2026-08-25` (hoy sólo local en la máquina).
2. Confirmar si Antigravity verificó paridad `.cs` ↔ kernel Python (no aparece
   en el resumen).
3. Re-correr el procedimiento sobre **MBT SEP26** cuando pase a ser front month
   (AUG26 vence a fin de agosto). Mismo procedimiento, minutos.
4. Las 3 puertas pre-registradas siguen siendo la prueba real. Nada de esto
   declara edge.

## Procedencia

Exports en `$DATA/mbt_apriori/` en la máquina del usuario; los sha256 completos
están en el manifiesto local de Antigravity (acá se citan prefijos). Resumen
recibido por chat y asentado aquí tal cual, marcado como reportado. Rama de
esta nota: `docs/handoff-2026-08-25` (no `foundation`: hay un sweep corriendo
desde `7fbab53` y commitear ahí lo invalidaría).
