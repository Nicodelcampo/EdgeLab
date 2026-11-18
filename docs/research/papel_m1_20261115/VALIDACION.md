# Papel M1 — validación de la fuente, v2 con el motor corregido (K40) (2026-11-18)

Estado: RESULTADO. Reemplaza a la v1 del 2026-11-15 (`descartada_v1/VALIDACION.md`), medida con el motor que cobraba el stop en el
extremo de la vela M1.
- **Criterio** (PREREGISTRO punto 1, sin cambios): diferencia de medias < 1 error estándar, mismo signo y correlación del P&L por sesión
  > 0,5.
- **Fuente:** M1DK:NQ_M1_dukas (CFD USATECH, 4 ticks por barra) contra ticks reales de NQ (`ops_desarrollo` de cada ficha), ago-2025 →
  sep-2026.
- **Unidad:** puntos por sesión; media de las celdas que operan esa sesión, igual que la v1.

| Regla | M1 (pts/sesión, ee, n) | Ticks NQ (pts/sesión, ee, n) | Sesiones comunes (M1 / ticks) | Corr | Veredicto |
|---|---|---|---|---|---|
| ASIA-NQ | +11,52 (4,15; 235) | +5,39 (1,79; 247) | 214 (+12,28 / +5,86) | 0,74 | **NO PASA**: diferencia 1,5 ee; M1 duplica |
| OTR930-NQ | +10,90 (5,61; 243) | +7,07 (2,14; 225) | 214 (+15,12 / +7,28) | 0,63 | PASA (0,7 ee) |
| RANGO0100-NQ | +5,20 (7,99; 27) | +13,61 (6,42; 58) | 18 (+6,82 / +10,11) | 0,95 | NO PASA: M1 genera la mitad de las operaciones |
| TORI-NQ | −0,88 (4,35; 88) | +10,71 (3,82; 70) | 34 (+8,69 / +9,41) | 0,65 | NO PASA: sólo 34 sesiones en común |

## Qué cambia respecto de la v1
- **ASIA-NQ pasa a NO PASA.** El veredicto ahora lo da el código (`python tools/papel_m1.py validacion` → `VALIDACION.json`, criterio
  único `a5.calibrar_por_sesion`: unión de sesiones con 0 donde una fuente no opera y EE combinado), no la tabla escrita a mano. Con ese
  criterio, ASIA da 1,28 EE en la v2 (NO) y daba 0,98 en la v1 (SÍ, por poco). La tabla de arriba usa el EE de M1 sobre las sesiones de
  cada fuente: 1,5 en la v2 y 1,14 en la v1, que la v1 dio por buena con «≈ 1 ee». Las dos lecturas coinciden en la v2.
- **Causa raíz:** el pre-registro decía «< 1 error estándar» sin decir cuál, y la tabla se armó a mano. Desde ahora el criterio es una
  sola función y el veredicto sale de su salida (K43). El largo v1 de ASIA (descartado por K40) no se relanza.
- **TORI no tenía signo opuesto por K40.** En las 34 sesiones comunes, M1 y ticks coinciden (+8,69 contra +9,41, corr 0,65). La
  diferencia del total es de cobertura: M1 genera operaciones en otras sesiones (88 contra 70 y sólo 34 en común), por los cortes de
  ángulo y el volumen proxy del CFD. Sigue sin medirse en M1.
- **M1 tiende a ser optimista.** En las sesiones comunes, M1 ≥ ticks en ASIA y OTR930. Es el sesgo conocido de los saltos dentro de la
  vela (`ejecucion.calibrar`, `m1_optimistas_con_saltos`). El largo de OTR930 se lee como cota optimista.

## Siguiente
Largo (enmienda 1: mapa y encendido por régimen; el largo no da de baja) **sólo para OTR930-NQ**.
