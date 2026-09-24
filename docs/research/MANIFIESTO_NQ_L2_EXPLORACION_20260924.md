# Manifiesto: exploración L2 de NQ (desarrollo jul–oct 2026), 2026-09-24

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** PROPUESTO. Requiere OK explícito de Nico (regla STOP): mira el precio después de los eventos.
**Marco:** capa descriptiva del atlas (`ATLAS_CAPA_DESCRIPTIVA_20260924.md`). Ninguna prueba de P&L. Solo perfiles de respuesta en la partición de exploración.

## Datos

L2 de NQ del período de desarrollo de la enmienda L2:
- NQ 09-26 del 01/07 al 11/09 (contrato principal);
- NQ 12-26 desde el 11/09 hasta el 31/10 (octubre se baja a medida que pase).

El L2 está validado contra Tradovate: 20/20 niveles (P-76). Se excluyen los archivos con el reloj no certificado (P-84, escaneo de pausa y apertura) y los días con defectos (`defect_reasons`).

## Particiones (se declaran en el Brain antes de calcular nada)

| Partición | Rol | Días |
|---|---|---|
| `P-NQL2-EXP` | EXPLORATION | 01/07–21/08 (~36 sesiones) |
| `P-NQL2-CONF` | CONFIRMATION_RESERVED | 24/08–31/10 (~12 hoy, ~34 al cerrar octubre) |

## Qué se mide (dos familias, cada una por separado)

**A. Absorción L2** (detector causal, con nulo propio):
- respuesta a 10, 30, 60 y 300 s en tres canales: fade con signo, \|movimiento\| y ruptura del nivel;
- 12 celdas en total;
- **Controles corregidos:** a la **misma distancia del precio** (la lección de geometría del 24/09) **y** con la **misma actividad reciente** (volumen de los 60 s previos, en terciles). Así el "más volatilidad" no se confunde con "hubo mucho volumen".

**B. Desequilibrio de filas del libro** (QI = (bid₀ − ask₀)/(bid₀ + ask₀)):
- dirección del próximo cambio del precio medio y movimiento a 1, 10 y 60 s, por decil de QI;
- canal con dirección y sin dirección: 6 celdas;
- es la variable con más respaldo en la literatura (Gould y Bonart).

**Número de miradas:** 18 celdas descriptivas. Ninguna se usa como prueba. Las sugerencias salen por reglas escritas en el código y solo se confirman en `P-NQL2-CONF` o en el holdout L2 (nov–dic).

## Riesgos

- **Miradas múltiples:** mitigado porque todo es descriptivo y la reserva queda intacta.
- **Costo:** el spread de NQ es ~4,6 ticks en RTH (real, validado). Un efecto de 1–2 ticks no paga la ida y vuelta, y se reporta así.
- **Relojes por archivo** (P-84): los días no certificados se excluyen, no se corrigen a mano.
- **NQ es de tick chico relativo:** el desequilibrio de filas predice menos que en contratos de tick grande. Un nulo en B no se extiende a ZB ni a 6E.

## Qué falta

- Octubre (se baja mensualmente).
- Adaptar la herramienta del atlas: rutas, controles corregidos e ids de NQ. Se hace después del OK.
