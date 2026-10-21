# Manifiesto — ORB0100 en NQ con franjas de zonas OG/VI como filtro (escrito ANTES de correr)

Pedido de Nico 2026-10-21: "al nq agregale como filtro las franjas de OG y VI y determina si alguna disposicion concreta de
estas zonas por encima y por debajo suman o restan a la estrategia". Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

Base: celda congelada de ORB0100 en NQ (01:00-01:15 ET, VWAP a favor, mercado, SL otro lado del rango, TP 1,5R, 16:00 ET,
costos MNQ). Las operaciones ya se miraron (descubrimiento y abr-sep); lo NUEVO es la particion por zonas, nunca mirada.
Zonas: LUX-IMB OG+VI en M1 (detector con paridad NT8), vivas al momento de la entrada (creadas antes, vida 500 min).
- **Camino**: zonas que se superponen con el tramo entrada -> TP. **Respaldo**: zonas que se superponen con entrada -> SL.
- H1: P&L (R/op) con camino >= 1 menos camino = 0 (se espera < 0).
- H2: con respaldo >= 1 menos respaldo = 0 (se espera > 0).
- H3: desbalance D = (respaldo - camino)/(total + 1): D > 0 menos D < 0 (se espera > 0).
Inferencia: diferencia ajustada por terciles de volatilidad previa (rango de los 60 min previos) y bootstrap por dia;
Holm sobre 3 en DESCUBRIMIENTO (ago-2025 .. mar-2026). Confirmacion: mismo signo en abr-sep 2026 (descriptivo, n chico).
Un filtro "suma" solo si pasa Holm en descubrimiento **y** mantiene el signo en abr-sep. Se publica todo y el MDE.
Riesgo: n ~ 160 + 90 operaciones; MDE grande. Como podria refutarse: H1-H3 sin efecto o signo distinto en abr-sep.
