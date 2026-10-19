# GEX-M0 — mapa de columnas 01B sellado (2026-08-13)

Estado: `COLUMNS_SEALED_PENDING_D1_CROSSCHECK`
Fixture: `edgelab/research/gex/fixtures/bulletin_2026-08-12.json` (boletín #154, FINAL).
Fuente del layout: header del propio PDF 01B + glosario oficial CME
(`CME-Group-Daily-Bulletin-Glossary.pdf`).

## Fila de referencia

```text
EC  803339  EURO FX FUTURES  127840  + 1455  125584  819728  135019  2256  EC
```

## Mapa

| Campo | Valor EC | Significado |
|---|---|---|
| col 0 (izquierda) | 803339 | **OPEN INTEREST actual** (todos los meses del producto) |
| col 1 | 127840 | OVERALL COMBINED TOTAL VOLUME |
| col 2 | +1455 | OI NET CHANGE (día a día) |
| col 3 | 125584 | GLOBEX VOLUME |
| col 4 | 819728 | 52 WEEKS (364 DAYS) AGO — OPEN INTEREST |
| col 5 | 135019 | 52 WEEKS AGO — VOLUME |
| col 6 | 2256 | complemento de venue (open outcry/PNT) = total − Globex |

## Evidencia (no es adivinación)

Identidades aritméticas exactas, tres productos:

```text
EC : 125584 + 2256 = 127840   (Globex + complemento = total)
NQ : 410608 + 2682 = 413290
ES :  940765 + 6867 = 947632
M6E: total == Globex (11239 == 11239) → sin complemento, columna ausente
```

Magnitudes conocidas: ES OI 2.103.868 (~2,1M), NQ OI 291.056 (~300k),
EC OI 803.339 — todas en rango de mercado conocido.

## Qué NO da este boletín

OI **por strike**. Gamma por strike necesita la cadena de opciones (settlement
por strike + vol). 01B da OI del **producto** (toda la curva). Para niveles GEX
hace falta una fuente por strike (GEX-M1), p.ej. los settlement files de
opciones CME o un dataset público documentado.

Lo que 01B sí da, gratis y diario: régimen de producto (OI, ΔOI, volumen,
comparación 52 semanas). Eso es un insumo diario target-free, no un nivel.

## Pendiente (un día más de boletín)

Cross-check D1: `OI(hoy) − OI(ayer)` debe igualar la columna ±CHGE. Confirma la
asignación izquierda = OI actual vs 52-semanas. El intento de bajar el boletín
archivado del 11-ago (`daily-bulletin_20260811153-finals.pdf`) devolvió una
landing, no el PDF; queda para mañana con el #155.
