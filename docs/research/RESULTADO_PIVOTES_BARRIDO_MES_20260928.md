# PIVOTES-BARRIDO-MES — resultado del censo (2026-09-28)

**Veredicto: el censo NO confirma que un pivote se barra más que el azar.** OK de Nico. `tools/pivotes_barrido.py`,
commit `0f148a94`, árbol limpio. MES 25t (Lucid, precio de trade), 171 sesiones, **272.331 pivotes** (12.237 en niveles
IPC), evento en la confirmación del pivote. Artefacto: `artifacts/pivotes_barrido/reporte.json`.

| Prueba | Techo | Piso |
|---|---|---|
| P0 global (barre − p0) | **−0,008** [−0,012; −0,004] (sobrevive, en contra) | +0,002 [−0,002; +0,006] |
| F1 tramo alto − bajo | 0,000 | +0,007 (p 0,04, no pasa BH) |
| F2 velocidad | −0,001 | −0,002 |
| F3 distancia alto − bajo | **+0,026** [+0,019; +0,034] (sobrevive) | **+0,017** [+0,010; +0,024] (sobrevive) |
| F4 volumen | +0,001 | −0,005 |
| F5 RTH − ETH | −0,003 | +0,002 |
Barre: 0,419 / 0,423; p0: 0,427 / 0,421.

## Lectura
- **El «pivote suelto se barre ~5 pp más que el azar» del IPC-NIVEL no es una propiedad de los pivotes.** En el censo,
  en la confirmación, se barren igual que el azar (techos incluso 0,8 pp menos). Aquel +5 pp venía de **cómo se eligió el
  control**: pivotes emparejados en distancia y edad, medidos en un instante posterior a su confirmación. Es un efecto de
  selección del evento de control, no de los pivotes.
- Consecuencia para IPC-NIVEL: «la zona se barre menos que un pivote suelto» sigue siendo una comparación válida **contra
  ese control**, pero no quiere decir «la zona resiste más que un extremo cualquiera»; contra el azar, la zona tampoco se
  apartaba (P1 ≈ 0). El candidato a confirmación queda más débil: vale como contraste emparejado, no como resistencia.
- Lo único que sobrevive con tamaño: los pivotes con **más distancia** en la confirmación se barren 1,7–2,6 pp más que los
  cercanos. Con 270 mil eventos cualquier efecto sale significativo; 2 pp está lejos de pagar fricción (umbral ≈ fricción
  MES / d). Descriptivo, no candidato.
- Registrado para el L2: la distinción defendido / vacío no se puede apoyar en un exceso global de los pivotes, porque no lo hay.
