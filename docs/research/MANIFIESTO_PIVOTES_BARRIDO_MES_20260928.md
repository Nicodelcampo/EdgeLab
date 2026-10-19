# Manifiesto PIVOTES-BARRIDO-MES: ¿qué pivotes se barren más que el azar? — PRE-REGISTRO (2026-09-28)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** OK de Nico (28/09: «escribí el pre-registro y corrélo»).
**Familia nueva: PIVOTES** (extremos recientes como objetivo de liquidez), presupuesto propio. Nace del control C-PIV del
IPC-NIVEL (un pivote suelto se barrió 0,49 contra 0,44 del azar), pero **la población es otra**: el censo completo, no los
pivotes emparejados con zonas.

## 1. Hipótesis y refutación
- **Hipótesis:** los extremos recientes (pivotes de un zigzag de 6 t) se barren más de lo que da un paseo sin memoria,
  y el exceso depende del tipo de pivote.
- **Justificación económica:** detrás de un máximo o mínimo reciente se juntan stops; es liquidez visible que el precio
  va a buscar. Cuanto más obvio el extremo, más liquidez.
- **Cómo podría refutarse:** el exceso global no supera al nulo, o ninguno de los rasgos separa pivotes que se barren
  más de los que se barren menos.

## 2. Población (regla de población)
Eventos enumerados del pivote: formación, **confirmación** (el zigzag revierte 6 t), primer toque, barrido, expiración,
estado continuo. **Se congela: la confirmación**, primer instante causal en que el pivote existe. Censo completo de
pivotes del zigzag R = 6 t en MES 25t; se marca (no se excluye) si pertenece a un nivel IPC-NIVEL.

## 3. Resultado y nulo
Carrera: barre (≥ 2 t más allá del pivote) antes de alejarse d (d = distancia del cierre de confirmación al pivote,
≥ 2 t); horizonte 200 velas o fin de sesión; censura aparte. Nulo `simulate_null`, ternas 25t estrictamente anteriores
a la vela de confirmación, sin agrupar. Exceso = barre − p0.

## 4. Rasgos (causales, en la confirmación) y pruebas
| Rasgo | Definición | Contraste |
|---|---|---|
| F1 tramo | tamaño en ticks del tramo que llevó al pivote (desde el pivote opuesto anterior) | tercil alto − bajo |
| F2 velocidad | velas entre el pivote y su confirmación (rechazo rápido o lento) | tercil alto − bajo |
| F3 distancia | d | tercil alto − bajo |
| F4 volumen | volumen de las 5 velas centradas en el pivote ÷ mediana de la sesión previa | tercil alto − bajo |
| F5 horario | RTH (08:30–15:00 CT) − fuera de RTH | RTH − ETH |
Más **P0 global** (exceso de todos los pivotes) por lado.
**12 pruebas** (2 globales + 5 rasgos × 2 lados), bilaterales, BH q = 0,10, bootstrap por sesión. Terciles fijados con
el rasgo solo, sobre todo el descubrimiento. Combinaciones entre rasgos: sólo descriptivas.

## 5. Datos
MES 25t (Lucid, precio de trade), ago-2025 → mar-2026, 171 sesiones. Confirmación única abr–jun 2026. Holdout oct+.

## 6. Riesgos
- Censo enorme (decenas de miles de pivotes): cualquier diferencia chica da significativa. Se publica el tamaño del
  efecto y el umbral económico (fricción MES propia / d), no sólo p.
- Precio de trade: barrido exige 2 t.
- Pivotes superpuestos en el tiempo: bootstrap por sesión.
