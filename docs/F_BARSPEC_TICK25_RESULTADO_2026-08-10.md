# `bar_spec` — replicación bajo `tick:25` · RESULTADO

**Fecha** 2026-08-10 · **Artefacto** `F_barspec_tick25__676bde88efad.json`
**Módulo** `diag/tasa_senales/F_barspec_tick25.py`
**Outcomes** `false` · **Multiplicidad gastada** cero · **Holdout** intacto
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

Corrido **después** de corregir los dos defectos de geometría documentados en
`CORRECCION_ALTURA_ZONA_2026-08-10.md`; el número aquí citado es el final.

---

## 0. Por qué esta dimensión

`time:1` está hardcodeado en siete módulos de research y nunca se justificó
por escrito — la dimensión más grande sin explorar de todo el programa
(`REGISTRO_NO_MEDIDO_2026-08-10.md` §2.1). `tick:25` no es un valor arbitrario:
`docs/nt8_bridge.md` documenta que BigTrap2 corre históricamente sobre charts
de 5t/25t en NT8, y hay un oráculo sellado a `tick:25` (aunque con
`ImbalanceMode=SameLevel`, no defaults — ver el caveat de paridad en el
módulo). Este resultado es evidencia interna Python, no reemplaza un oráculo
de esa combinación exacta.

---

## 1. El censo replica, número por número

| | `time:1` (F0.2) | `tick:25` |
|---|---|---|
| zonas / sesión | 79,3 | 101,5 |
| tocadas alguna vez | 97,9 % | 98,8 % |
| altura (ticks, mediana / p90) | 1,00 / 2,00 | **1,00 / 1,00** |
| vida (barras, mediana) | 7,0 | 7,0 |
| `close_through`+`gap` | 96,1 % | 97,2 % |

La cuenta de zonas por sesión cambia (más barras, más oportunidades de
formación) y bajo `tick:25` las zonas son geométricamente **más consistentes**
(p90 de altura = 1,00, no 2,00 — casi todas miden exactamente un tick). Pero
las cifras que importan —tocada, vida, tasa de ruptura— son **prácticamente
las mismas**.

---

## 2. El hallazgo central de F1.1 replica, también número por número

| | `time:1` (corregido) | `tick:25` |
|---|---|---|
| REAL tocada | 97,9 % | 98,81 % |
| NULO-B tocada | 50,6 % | 51,94 % |
| REAL rota | 96,1 % | 97,17 % |
| NULO-B rota | 95,4 % | 96,65 % |
| brecha tocar (pareada, media) | +47,07 pp | +46,77 pp |
| sesiones REAL>NULO (tocar) | 201/201 | 201/201 |
| sesiones REAL>NULO (rota) | 80/201 | 103/201 |

**El hallazgo no depende de la resolución de barra elegida.** Bajo una
construcción de barra completamente distinta —25 ticks de actividad en vez de
1 minuto de reloj, con una agregación de footprint totalmente distinta por
detrás— BigTrap2 sigue distinguiéndose del azar en la misma dimensión (tocar,
no romper) y con una magnitud casi idéntica.

*Nota sobre `rota`*: bajo `tick:25` el empate está más parejo (103/201, más
cerca de 50/50 que el 80/201 de `time:1`), consistente con que, bajo ambas
resoluciones, romper sigue sin discriminar real de nulo.

---

## 3. Por qué esto importa más de lo que parece

`time:1` fue una elección heredada, nunca comparada contra la resolución con
la que el indicador se usa de hecho en NT8. Si el hallazgo de F1.1 hubiera
sido un artefacto de esa elección —por ejemplo, si la agregación de un minuto
de footprint produjera algún patrón espurio de "atracción" que una agregación
de 25 ticks no reprodujera— esta corrida lo habría revelado. **No lo reveló.**
Eso mueve la confianza en el hallazgo de "cierto bajo una configuración
elegida sin justificar" a "cierto bajo dos configuraciones estructuralmente
distintas, una de las cuales tiene precedente histórico real de uso".

---

## 4. Lo que esto NO establece

- **No es paridad NT8 confirmada** para "BigTrap2 defaults + tick:25" — sigue
  siendo evidencia interna Python (§0). Si este resultado va a sostener una
  hipótesis de outcomes más adelante, conviene pedir el oráculo de esa
  combinación exacta antes, no asumirlo.
- **No se probó `tick:5`**, la otra resolución histórica mencionada. Queda
  registrado como abierto — el costo computacional es mayor (más barras por
  sesión) y no se justificó gastarlo todavía dado que `tick:25` ya contestó la
  pregunta de robustez.

---

## Aporte al referente

La dimensión más grande sin explorar del programa deja de ser un supuesto sin
examinar: se comparó explícitamente contra la resolución histórica del
indicador, y el hallazgo central de la sesión —BigTrap2 atrae, no resiste— es
invariante al cambio. Reduce sustancialmente el riesgo de que todo lo
construido hoy sobre F1.1 dependiera de una elección de `bar_spec` nunca
justificada por escrito.
