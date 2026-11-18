# Papel M1 — validación de la fuente (2026-11-15)
Estado: DESCARTADA (2026-11-18, K40) — medida con el motor de la grilla, que cobraba el stop en el extremo de la vela M1 (pesimista con stops chicos; TORI «signo opuesto» es candidato a este sesgo). Se relanza con el motor corregido; resultados viejos en `descartada_v1/`. Antes:  RESULTADO. Criterio (PREREGISTRO punto 1): media y signo dentro de ~1 error estándar y correlación del P&L por sesión > 0,5,
M1DK:NQ_M1_dukas (CFD USATECH, 4 ticks por barra) contra ticks reales de NQ (`ops_desarrollo` de cada ficha), ago-2025 → sep-2026.
| Regla | M1 (pts/sesión, ee, n) | Ticks NQ (pts/sesión, ee, n) | Sesiones comunes | Corr | Veredicto |
|---|---|---|---|---|---|
| ASIA-NQ | +10,20 (4,23; 235) | +5,39 (1,79; 247) | 214 | 0,74 | PASA (≈ 1 ee, mismo signo) |
| OTR930-NQ | +6,21 (5,61; 243) | +7,07 (2,14; 225) | 214 | 0,63 | PASA |
| RANGO0100-NQ | +2,49 (8,65; 27) | +13,61 (6,42; 58) | 18 | 0,95 | NO PASA: la M1 genera la mitad de las operaciones (cobertura de la sesión asiática en el CFD) |
| TORI-NQ | −3,04 (4,67; 88) | +10,71 (3,82; 70) | 34 | 0,64 | NO PASA: signo opuesto a 2,3 ee (probable orden dentro de la barra / cortes de ángulo) |
El error por sesión en M1 es mayor que en ticks (el orden conservador dentro de la barra agrega dispersión). ASIA y OTR930 pasan al
largo (2012 → 2025-07) con el uso de la enmienda 1 (mapa y encendido por régimen; el largo no da de baja). RANGO0100 y TORI no se miden en M1.
