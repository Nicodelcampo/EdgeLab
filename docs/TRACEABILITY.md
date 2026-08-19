# TRACEABILITY — contrato Notion ↔ repo

> Decisión de diseño, no una moda de carpetas. Asentada 2026-08-17.
> **Aditiva:** no se mueven archivos existentes de `docs/`. Moverlos rompería
> las citas por path + blob que el canal ya selló (regla 3).
> **Enmienda 2026-08-19:** L3 es `docs/notion/CATALOG.md`. `catalog.json` y
> `docs/notion/snapshots/` **no existen** — no se citan como si existieran.

## 1 · El problema que esto cierra

Tres máquinas, dos canales (Notion + repo), cuatro versiones de una hipótesis
en un día, y un índice (`CANAL_AUDITOR.md`) que guardaba placeholders de una
sesión, no URLs. El auditor lo nombró en la 006 §6: el canal fuera de Notion
**no sobrevivía**. Las entradas 001–005 siguen sólo en Notion. Un zip de 12 PDF
del 16-ago **no incluye** v4, el handoff del 17, ni las entradas 003–005 / 008–014.

Eso es el capítulo 0 otra vez: dos verdades.

## 2 · Qué dice la evidencia externa (y qué no copiamos)

Wilson / Bryan / Cranston et al., *Good Enough Practices for Scientific
Computing* (Software Carpentry):

- un proyecto, un directorio;
- `doc/` para texto humano;
- **no reescribir lo crudo** — el zip/PDF es evidencia, se conserva hasheado;
- un `CHANGELOG` / punto de entrada;
- cambios chicos y frecuentes;
- **no reorganizar por estética** si eso rompe citas.

Audit trail cualitativo (Lincoln & Guba vía práctica contemporánea): decision
log + snapshots versionados + IDs estables ganan a un árbol de carpetas ingenioso.

Noble 2009 y el propio EdgeLab ya tienen la pieza que falta en esos papers:
**el registro no se limpia**. No se enmienda un commit para “ordenar”. Se asienta
el siguiente.

Lo que **no** hacemos: mover `docs/research/*` ni `docs/audits/*` a un árbol
nuevo. Cada path citado en un SHA dejaría de resolver. Eso es P-39 aplicado a
nosotros mismos — el nombre de la carpeta no es la identidad; el blob sí.

## 3 · Capas (quién manda)

```
L0  docs/CURRENT.md              ← una sesión nueva empieza acá
L1  PENDIENTE.md                 ← board = registro de decisiones
    docs/DECISIONES_*.md         ← actas
    docs/NORTH_STAR.md           ← referente (hasheado)
    docs/audits/CANAL_AUDITOR.md ← índice del canal
    docs/research/LEER.md        ← 8 paths de research, no el directorio
L2  docs/audits/ENTRADA_*.md     ← canal 006+ (texto canónico)
    docs/research/H_Z2A_V4_*.md  ← línea viva
L3  docs/notion/CATALOG.md       ← mapa Notion ↔ repo (markdown, no catalog.json)
L4  páginas Notion               ← timbre / redacción / lectura humana
```

Si L4 y L1 divergen, manda L1. Si L3 y L2 divergen, manda L2 (el markdown
commiteado). Un PDF de Notion **nunca** adjudica.

`catalog.json` y `docs/notion/snapshots/` se nombraron acá el 17-ago y **no se
crearon**. No se inventan para que el contrato cierre: el contrato se enmienda.

## 4 · Niveles de actualidad y relevancia

**Actualidad** (estado del objeto):

| valor | significa |
|---|---|
| `vigente` | manda hoy |
| `sustituida` | hay una versión posterior que manda (v1–v3 de H-Z2A) |
| `archivo` | cerrada o histórica; se conserva |

**Relevancia** (prioridad de lectura):

| valor | significa |
|---|---|
| `L0_entrada` | leer primero; cabe en una sentada |
| `L1_linea` | línea activa o asignación vigente |
| `L2_contexto` | hace falta para entender L0/L1 |
| `L3_archivo` | no leer primero; no borrar |

Una página puede ser `vigente` y `L2` (el mapa de 8 capítulos) o `sustituida`
y `L3` (H-Z2A v2). Son ejes distintos a propósito: “¿manda?” ≠ “¿la leo hoy?”.

## 5 · Reglas operativas

1. **Toda página nueva de Notion que gobierne trabajo entra al catálogo en el
   mismo turno** (`CATALOG.md` + fila). Si abre un `P-NN`, también
   `PENDIENTE.md` (regla 4 del canal).
2. **Entradas de canal 015+ nacen en `docs/audits/`**, no sólo en Notion.
   Notion puede espejar; el repo es la fuente.
3. **Snapshots:** si algún día hay export, se hashea. Hoy **no hay** carpeta
   `docs/notion/snapshots/`. No se cita como existente.
4. **No se commitean PDF binarios** si ya hay texto extraído + sha256 del PDF.
5. **URLs de Notion en el repo se escriben con el UUID vivo de la página**
   (`www.notion.so/` + uuid). Nunca placeholders de una sesión.
6. **No se mueven paths ya citados.** Si un documento cambia de rol, se le
   cambia la fila del catálogo (`currency` / `relevance`), no la ruta.
7. **Una sesión rezagada recibe `CURRENT.md` + `docs/research/LEER.md`**, no un
   tour de 40 páginas.
8. **`CURRENT.md` es manuscrito y eso se declara.** `tests/test_current_md.py`
   falla si cita un P-NN ausente del board, si su Fecha queda más de un día
   atrás del HEAD, o si un path entre backticks no existe. No convierte el
   archivo en computado: convierte «quedó viejo» de invisible en ruidoso.
   No relajar el test: actualizar CURRENT o asentar el P-NN.

## 6 · Qué queda para después (no bloquea esto)

- Snapshot de v4, handoff 17-ago, entradas 003–005 (faltan en el zip).
- Espejo markdown de 001–005 en `docs/audits/` (hoy sólo viven en Notion).
- Un chequeo mecánico que falle si `CANAL_AUDITOR.md` vuelve a guardar
  placeholders de sesión.

**Aporte al referente:** convierte “¿dónde está la verdad?” en un contrato
con capas, dos ejes (actualidad / relevancia) y una prohibición explícita de
reorganizar lo ya citado. Eso es distancia al edge porque deja de gastarse
turno en reconstruir el mapa.
