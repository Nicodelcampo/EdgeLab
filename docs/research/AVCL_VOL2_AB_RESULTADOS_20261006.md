# AVCL-VOL-2 A+B — resultados MNQ — 2026-10-06

- Manifiesto: `AVCL_VOL2_AB_MANIFIESTO_20261006.md`.
- Kernels: etapa 1 `edgelab-avcl-cache-mnq-k1..k4`, unos 26 min en paralelo. Etapa 2 `edgelab-avcl-vol2-ab-20261006`,
  151 s. VOL-1 había tardado 3,5 h.
- JSON: `avcl_vol1_20261005/AVCL_VOL2_AB_RESULTADOS.json`. 8 pruebas más en el registro.
- Control de consistencia: A1 con FE sólo S0 da AT `y_rg` +0,082, igual que VOL-1 (+0,081).
- **Alcance:** información de expansión. No evalúa soporte/resistencia.

## A — formal (RTH, H10, Holm 8)
| tipo | contraste | canal | β | IC95 | Holm |
|---|---|---|---|---|---|
| AT | A1 (+ intensidad) | y_rg | **+0,081** | [0,075; 0,087] | <1e-15 |
| AT | A1 | y_rv | +0,042 | [0,031; 0,052] | 3e-15 |
| AT | **A2 (vol. alto sin zona)** | y_rg | **+0,054** | [0,037; 0,071] | 2e-9 |
| AT | A2 | y_rv | +0,003 | [−0,027; 0,033] | 0,86 |
| OFF | A1 | y_rg | +0,055 | [0,049; 0,060] | <1e-15 |
| OFF | A1 | y_rv | −0,003 | | 0,86 |
| OFF | A2 | y_rg | **+0,072** | [0,058; 0,087] | <1e-15 |
| OFF | A2 | y_rv | +0,028 | [0,005; 0,052] | 0,029 |

**Lectura pre-registrada: AT·y_rg sobrevive en A1 y en A2 → la zona agrega información de expansión de rango más
allá del pico de volumen y de la intensidad de flujo.** Contra el volumen alto sin zona, el efecto baja de +0,081 a
+0,054, es decir, un tercio del efecto era del volumen. En OFF el efecto es igual o mayor contra el volumen alto.
- La volatilidad realizada (`y_rv`) **no** sobrevive contra el volumen alto en AT: barra por barra, el ruido es igual
  que después de un pico de volumen cualquiera. Lo propio de la zona es el **rango**.
- H50 (descriptivo): ≈ 0 o negativo. El efecto se agota antes de las 50 barras.

## B — curva de respuesta (descriptiva)
- AT, rango por barra frente a las 20 barras previas: +3,5 % en h=1, +1,8 % en h=2, ≈0 desde h≈5. **El primer cruce
  de vida media cae en 3 barras.**
- OFF: plano (≈0–1 % por barra).
- Las curvas `VOL_ALTO_SIN_ZONA` y `AT_vs_VOL_ALTO` tienen sólo 495 bloques que cumplen la distancia > 400 barras, así
  que **no son interpretables**. El diseño de B era demasiado restrictivo para ese grupo.

## Lectura conjunta (lo importante)
**Las barras no se agrandan, pero la ventana de 10 barras recorre más.** Que el rango de la ventana crezca 5–8 % con
barras de tamaño casi normal implica que el precio **se desplaza**, es decir, que hay persistencia en un sentido,
más que agitación. Es una pista directa hacia la dirección: el siguiente paso natural es **C (delta de la zona →
sentido del desplazamiento)**, que además conecta con la función de soporte/resistencia que Nico ve en el chart.
Esto es una inferencia, no está medida.

## Estado
`INFORMACIÓN PROPIA DE LA ZONA (más allá del volumen) — AT/OFF H10 rango`. No es edge. Siguen C, con dirección, y el
protocolo de soporte/resistencia, ambos sobre el cache.
