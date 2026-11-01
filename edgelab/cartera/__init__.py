"""Cartera viva (2026-10-31, pedido de Nico): EdgeLab se organiza alrededor de canastas que el agente del Debian mantiene al día con el
régimen del mercado, todos los días. Documento central: docs/CARTERA_VIVA.md.

Ciclo diario (`ciclo.py`, después del cierre de CME y antes de la apertura asiática): (1) operaciones forward nuevas de cada estrategia
(papel simulado con el motor de siempre y, cuando haya, fills de demo y de cuentas reales); (2) e-procesos y drawdown: retiro inmediato
de lo que dejó de funcionar; (3) régimen de mañana con datos hasta hoy; (4) afinidad de cada estrategia con ese régimen; (5) riesgo y
contratos por cuenta (prop firms, Axi, capital propio) dentro de sus reglas; (6) cola de investigación con plazos para cubrir los
huecos del régimen actual; (7) plan del día y alertas.

Módulos: `regimen` (régimen diario causal), `afinidad` (rendimiento por régimen con contracción), `ficha` (ciclo de vida de cada
estrategia: PAPEL -> REAL, SUSPENDIDA por régimen, RETIRADA), `asignacion` (contratos por cuenta), `investigacion` (cola con plazos),
`papel` (operaciones forward con el motor congelado), `ciclo` (orquestación con plazo y modo seguro).
"""
