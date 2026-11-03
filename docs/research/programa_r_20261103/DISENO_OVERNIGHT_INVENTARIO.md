# OVERNIGHT-INVENTARIO: Desequilibrio de Inventario Globex (18:00–09:29 ET) en la Apertura RTH

Estado: VIGENTE, pre-registrado antes de correr (2026-11-03). Referente: `docs/NORTH_STAR.md`. Programa: `docs/research/programa_r_20261103/PROGRAMA_R.md`.

## 1. Mecanismo económico y fuente
- **Fuente académica / empírica:** Lou, Polk y Skouras (2019), «A Tug of War: Overnight vs. Intraday Expected Returns», Journal of Financial Economics; Dalton, Jones y Dalton (1990), «Mind Over Markets».
- **Hipótesis económica:** La sesión overnight de Globex (18:00–09:29 ET) opera con una fracción de la liquidez del horario regular. Cuando el flujo overnight desplaza el precio de forma persistente hacia un extremo del rango nocturno (alto desequilibrio neto y alta fracción de tiempo de un lado del punto medio), la entrada de participantes institucionales a las 09:30 ET corrige el inventario acumulado (regla 0: liquidación) o lo valida como nuevo equilibrio (regla 1: continuación).
- **Módulo:** `edgelab/research/overnight_inventario.py` (`NOMBRE = "OVERNIGHT-INVENTARIO"`, `NATIVO_AGENTE`).
- **Campañas registradas (`activa: false`, `estadistico: "R"`, `conductor: "local"`):** `OVERNIGHT-INV-ES-R` (ES→ES), `OVERNIGHT-INV-NQ-R` (NQ→NQ), `OVERNIGHT-INV-YM-R` (YM→YM), `OVERNIGHT-INV-GC-R` (GC→GC).

## 2. Por qué aporta baja correlación con la canasta actual (v5)
A diferencia de GAP-RTH (que mide el salto respecto al cierre de las 15:59 del día anterior), OVERNIGHT-INVENTARIO mide la trayectoria interna de la sesión Globex 18:00–09:29 ET (desplazamiento sobre rango nocturno y tiempo en el extremo) en ES, NQ, YM y GC.

## 3. Población (evento contra estado) y alternativas descartadas
- **Definición de la población (evento):** Evento diario único por regla: el cierre de la primera vela RTH (09:30 ET, m == 570) en toda sesión con al menos 120 velas overnight previas.
- **Alternativas descartadas antes de medir:** Se descartaron stops basados sólo en la vela de las 09:30 ET (demasiado ruidosa); el stop se escala al 35 % o 50 % del rango overnight completo, garantizando un denominador R estable.

## 4. Estructura de la grilla (108 celdas por canal)
| Perilla | Columna en `disparos` | Modo | Niveles | Parámetro (`cortes` / `cuantiles` / `categoria`) |
|---|---|---|---|---|
| `regla` | `regla` | `grupo` | 2 | `2` |
| `desequilibrio_on` | `imb_on` | `ge` | 3 | `(0.3, 0.55)` |
| `tiempo_en_extremo` | `frac_ext` | `ge` | 3 | `(0.52, 0.65)` |
| `apertura_rth` | `empuje_930` | `extremos` | 1 | `3` |

- **Ejecuciones (2):** `('ON', 0.35, 2.5)`, `('ON', 0.5, 3.5)` (triple barrera: objetivo amplio en múltiplos de R, stop estructural con piso de 4 ticks, sin break-even ni trailing, y cierre por tiempo).
- **Total de celdas por canal (`grilla_generica.n_celdas`):** **108** (dentro del rango objetivo de 50 a 250 celdas).

## 5. Criterios de refutación y riesgos
- **Cómo podría refutarse:** Si ni la liquidación (regla 0) ni la continuación (regla 1) nominan celdas en DESC y confirman en réplica OOS, o si los días con inventario extremo (imb_on >= 0,55) no difieren del resto.
- **Riesgos operativos y estructurales:** Anuncios macro de las 08:30 ET que redefinen el rango overnight en los últimos 60 minutos antes de las 09:30 ET.
