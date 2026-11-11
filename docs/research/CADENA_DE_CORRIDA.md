# Cadena estándar de una corrida — guía de uso (para cualquier agente)

Estado: VIGENTE (2026-11-11). Detalle y origen: `docs/autopilot/AUTOMATIZACION_PROCESOS_20261111.md`. Directiva 20.
Regla: **una familia de reglas sobre eventos no escribe simulador, kernel, lanzador ni análisis propios.** Escribe un módulo con el
contrato de abajo y usa estos comandos. Lo que no esté acá (grillas masivas de miles de celdas) sigue en `GUIA_GRILLA_MASIVA.md`.

## 1. Diseño (antes de escribir nada)
`python tools/antecedentes.py "<idea en palabras>" --familia <FAMILIA>` → familias parecidas y su último desenlace, factores
(NO_REPETIR primero), documentos, código reutilizable, ventanas del holdout consumidas y **qué datos quedan sin mirar para el linaje**
(DESC, REP, spot 2023–2025, holdout). Lo que diga «mirada» no se usa para confirmar sin declararlo.
Pre-registro con: espacio de eventos y control, justificación económica, cómo podría refutarse, datos por uso, etapa EF, hash del
North Star y conteo (`tablas.conteo`). Registrar familia en `LINAJES.jsonl` y pruebas con `TrialRegistry.ensure` antes de lanzar.

## 2. Implementación: UN módulo (copiar `edgelab/research/plantilla_tabla.py`)
```
NOMBRE = "MI-FAMILIA"                       # slug: letras, números, «-»
EJECUCIONES = [("MERCADO", sl, tp, parcial, be), ("VUELTA", e, r, b, obj, c), ("LIMITE", x, sl, tp)]
def eventos(ctx) -> DataFrame               # k, lado (+1/−1), ref (objetivo), ext (extremo en contra), rg (escala) + rasgos, todo con velas ≤ k
DEFINICIONES = ["def_a", ...]               # opcional: columnas booleanas; CONTROL = {"def_a": "def_control"}
FILTROS = {"nombre": ("columna", ">=", 2.0)} # opcional: se aplican en el análisis; PERIODOS, FUENTE_COSTO, CARPETA opcionales
```
Motor único `edgelab/research/ejecucion.py`: stop a mercado al tick que lo cruza; objetivo/parcial límite en su nivel; tope 240
velas, fin de sesión o hueco; límite con fill «atraviesa». Salidas `r_<ejecución>` (R bruto) y `k_<ejecución>` (riesgo en precio).

## 3. Lanzar, traer, analizar
| paso | comando | qué hace solo |
|---|---|---|
| preflight | `python tools/tablas.py preflight <modulo>` | contrato, causalidad por disparo y por cortes, motor calibrado sin optimismo, kernel completo con datos sintéticos |
| lanzar | `python tools/tablas.py lanzar <modulo> NQ:20250805:20260331 DK:USATECHIDXUSD:20250805:20260331 …` | preflight, kernel con sus dependencias, datasets, falla si el push no sale, registra en `docs/research/tablas/LANZADAS.jsonl` |
| traer | `python tools/tablas.py traer` (el ciclo del Debian lo hace solo con `tablas.activo`) | baja lo terminado, rechaza lo corrido con código viejo |
| explorar | `python tools/tablas.py explorar <modulo>` | R neto con costos de `edgelab/costos.py`, DESC/REP por separado, control, fricción ≤ 0,08 R, estabilidad, **nulo de la búsqueda completa** |
| curva | `python tools/tablas.py curva <modulo> <definición> <ejecución> [filtro]` | IS / OOS / confirmación / holdout en R neto (SVG + JSON) |
| congelar | `python tools/tablas.py congelar <modulo> hip.json --familia F <ventanas de confirmación>` | ≤ 10 hipótesis con hash, registro global, lanza la confirmación |
| confirmar | `python tools/tablas.py confirmar <modulo> CONGELADAS_*.json` | UNA vez: BH q 0,10, sub-bloques, MDE, veredicto por regla |
| holdout | `python tools/tablas.py holdout <modulo> CONGELADAS_*.json NQ:20261023:20261231 --acta <md> --p p1,…` y `confirmar_holdout` | una apertura por familia, registrada antes; Fisher con las p de desarrollo |

## 4. Cierre
`python tools/cierre.py` antes de cada commit: regenera índices (catálogo, docs, familias, factores, remediciones, agentes) y corre
sus tests. Tests que vigilan la cadena: `test_ejecucion`, `test_tablas`, `test_dependencias_lock` (imports fuera del entorno),
`test_parametros_por_defecto` (parámetros atados a constantes).

## 5. Lo que la cadena ya impide (no hace falta acordarse)
Stop acreditado en su nivel (sesgo ≈ +0,3 R) · eventos que miran el futuro · kernel que falla en Kaggle por un import · slug con «_»
· tabla traída de código viejo · confirmación con hipótesis tocadas después (hash) · segunda confirmación · celda elegida por debajo
del nulo de la búsqueda presentada como hallazgo · import fuera del entorno · fricción mayor a 0,08 R elegida.
