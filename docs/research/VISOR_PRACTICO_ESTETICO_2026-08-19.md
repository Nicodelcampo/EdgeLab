# Visor práctico y estético — spec (2026-08-19)

- **Para qué:** tener un visor *listo* cuando haya que revisar un caso, no un dashboard
  de investigación. Nico: «no para algo en particular, pero si surge algo a revisar».
- **No rehacer** `viewer/nt8_bridge/store_viewer.html`. Ese ya es el idioma visual.
  El visor de corredores H-Z2A **hereda** paleta, tipografía, grid y teclado.
- **Firewall:** sin MAE/MFE, sin P&L, sin holdout. Marcas = conteos de `censar_zona`
  sobre prefijos (propiedad C-A). No copiar la máquina de estados.

## 1. Qué tipo de pantalla es

Carbon distingue dos dashboards. Este es **exploración**, no presentación:
buscar, filtrar, saltar al siguiente caso, anotar. No KPIs ni «22 vivas».

Fuentes: [Carbon Dashboards](https://v10.carbondesignsystem.com/data-visualization/dashboards)
· Tufte (data-ink, small multiples, nada de chartjunk) · Grafana annotations ·
TradingView replay (teclado, no el producto).

## 2. Layout (posiciones fijas — no se improvisan)

Patrón F. Una sola página, 100 vh, sin scroll de documento.

```
┌ header 46 px ──────────────────────────────────────────┐
│ marca · caso actual · chips de estado · tabs           │
├──────────┬─────────────────────────────────────────────┤
│ sidebar  │  chart (ocupa todo)                         │
│ 260–290  │  leyenda arriba-derecha, no tapa el precio  │
│ lista de │  overlay de zonas / bandas δ                │
│ casos    │                                             │
│          ├─────────────────────────────────────────────┤
│          │  drawer 28–34 vh  (tabla / detalle / json)  │
└──────────┴─────────────────────────────────────────────┘
```

- **Header:** marca a la izquierda; contexto (instrumento, D/δ/R, n) al centro;
  tabs a la derecha. Altura 46 px — ya está en el store viewer.
- **Sidebar izquierda:** árbol o lista de corredores. Colapsable. Filtro arriba.
- **Chart al centro:** el objeto. Máximo contraste, máximo área.
- **Leyenda:** esquina superior derecha, fondo semitransparente, no sobre el
  último precio.
- **Drawer abajo:** discrepancias / marcas / params. No un modal.
- **No** meter un panel de métricas arriba del chart. Eso es presentación.

Si hay que comparar dos δ: **small multiples verticales** (mismo eje X, zoom
linkeado). No dos colores superpuestos en el mismo precio si se pisan.
Carbon: charts linkeados — zoom/filtro se espejan.

## 3. Elementos que sí, y los que no

| Sí | No |
|---|---|
| Línea de distancia `d` en ticks enteros | Velas como vista primaria del episodio |
| Banda de zona `[L,U]` relleno 15–20 % opacidad | Arcoíris por cada estado |
| Bandas δ como **región** (Grafana), hover para texto | Etiquetas permanentes sobre la serie |
| Marca vertical en A1 / NM / A2 / salida de banda | MAE/MFE, flechas de “fuerza”, P&L |
| Chips de estado (ok / warn / err) ya definidos | Semáforo de “vive” |
| Teclado: ← → caso; j/k paso; `f` fit; `/` filtro | Gestos solo-mouse |
| Una pregunta por vista (Metabase) | 8 series en un chart |

Color: **una semántica, un color**, en todos los visores.
Ya existe: Python `#3fb950`, NT8 dashed gris, missing `#f0616d`,
warn `#d9a441`, accent `#3b82f6`, fondo `#0b0e14`.
δ=5 y δ=8: dos tonos del **mismo** accent, no verde vs rojo
(rojo = error, no “más ancho”).

Tipografía: `system-ui` UI · `ui-monospace` números y IDs.
Números tabulares. Sin sombras, sin gradientes, sin iconos decorativos.

## 4. Interacción (lo que lo hace práctico)

1. Abrir y **ver un caso en < 2 s**. Lista precargada (3–20 corredores), no
   575 zonas en un JSON de 80 MB.
2. **Siguiente / anterior** con teclado. El trabajo es revisar una cola.
3. Click en fila del drawer → el chart **encuadra** ese evento (ya lo hace el
   store viewer).
4. Export CSV del caso visible. Para pegar en una entrada del canal.
5. Empty state honesto: «no hay corredores que cumplan el filtro» — no un
   spinner eterno. Claude ya se comió esto con δ=3 vs 8.

## 5. Dónde vive

`viewer/hz2a/` al lado de `viewer/nt8_bridge/`. Mismos tokens CSS
(copiar `:root`, no reinventar). HTML estático + JSON chico. Sin servidor.
Sin MAE. Sin holdout.

**Aporte al referente:** un visor sirve si acorta el tiempo entre “esto huele
mal” y “acá está el corredor”. La estética es no tapar los datos.
