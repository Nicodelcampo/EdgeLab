# Prompt opcional — sello de F2.8, no redescubrimiento

Usar **sólo** si se quiere un JSON formal unívoco en origin. No reinterpretar labels. No abrir la cola. No implementar F2.9 en este prompt.

```text
Sos el sellador de F2.8, no un descubridor.

Rama: research/bigtrap2-local-displacement-null
Fetch primero. HEAD esperado incluye 9788ac7 o posterior.

No reescribas F2.9. No abras OPEN_FAR_ZONE_FAMILY. El dictamen auditor ya dijo que esa etiqueta no enciende.

Tres parches al runner F2.8_atlas_residuales.py, y nada más:
1. Incluir r_i=0 en el promedio por sesión, como F2.7.
2. No volcar empate/unexpected a double_censor. Publicar categorías por separado.
3. Contraste BT2-control PAREADO por sesión, no sqrt(se1^2+se2^2).

Después:
- un solo JSON formal commiteado;
- el informe debe listar labels con decide_labels, sin relajar la regla de la cola;
- OPEN_FAR_ZONE_FAMILY no se declara si el contraste de d>=6 cruza cero;
- no tocar kernel, holdout, P&L, Z2, F2.9.

Devolver: HEAD, path del JSON, labels emitidas por decide_labels, confirmación de los tres parches.
```
