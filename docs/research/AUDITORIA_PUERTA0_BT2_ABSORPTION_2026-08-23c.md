# Auditoria Puerta 0 (tercera) — 2026-08-23

**Commit auditado**: `e142827` · **files[]**: 3 (JSON, harness, visor).
**Resultado declarado**: `PASSED_PUERTA_0`.
**Veredicto del auditor**: **NO FIRMADO**. La aritmetica comun da EXACT, pero el
artefacto no satisface su propia regla de conjuntos y no prueba el headline confirmado.

## 1. Hallazgo bueno: la aritmetica vuelve a cerrar

Ancla dinamica: NT8 bar 715, `t_start=2026-08-17T00:00:09.788 ART`,
`03:00:09.788 UTC`, tape index 12. Sobre las claves comunes que sobrevivieron al
mapa: `signed_flow`, `d_ticks` y `a_score` = **26.817/26.817 EXACT**.
Esto confirma que el 2,39 % de `71c80bd` era desalineacion, no aritmetica.

## 2. `t_start` no es clave unica: el `dict` pierde cientos de cubetas

El harness hace:

```python
py_scores_by_tstart[t_start] = score
nt8_scores_by_tstart[t_start_utc] = score
```

Varios ticks y, por tanto, varias cubetas pueden empezar en el mismo nanosegundo.
El ultimo evento pisa a los anteriores.

Prueba interna del JSON:

- `nt8_total = 28.042`
- `common_t_start_count = 26.817`
- `only_nt8_count = 707`
- 26.817 + 707 = **27.524**, no 28.042: **518 eventos NT8 desaparecen** por
  colision de clave.
- `python_total = 26.818` es el numero de claves unicas, no el numero de
  `ABS_SCORE` emitidos.
- `post_burn_in_total = 26.824` es mayor que las 26.817 claves comunes. El loop
  recorre duplicados de `py_scores_list`, pero para compararlos recupera siempre
  el ultimo valor del `dict`. Por eso puede contar la misma pareja colapsada mas
  de una vez.

Solucion: multimap con ordinal estable por timestamp, o clave compuesta derivada
del ancla (`global_bar = first_matched_bar + local_bar - 1`, mas `t_start`).
Nunca un `dict[t_start]` simple.

## 3. Zonas/fills: EXACT ignora conjuntos faltantes

El JSON dice:

- zonas: 628/628 comunes, `only_python=0`, **`only_nt8=18`**, verdict EXACT;
- fills: 628/628 comunes, `only_python=0`, **`only_nt8=18`**, verdict EXACT.

Pero la regla escrita en el prompt era EXACT solo si `matched == total`,
`only_nt8 == 0` y `only_python == 0`. El codigo deriva el verdict usando solo
`matched/common`; ignora los conjuntos laterales.

Si esas 18 son previas al ancla, deben filtrarse por una ventana comparable y
publicarse como `excluded_before_anchor=18`, no como `only_nt8=18` bajo EXACT.
Ademas `run()` informo 629 zonas y el mapa tiene 628 claves comunes: al menos
una clave `available_at + side` tambien colisiono y fue pisada.

Solucion: multimap/ordinal tambien para `available_at+side` y `signal_at+side`.
Comparar igualdad de multisets dentro de la ventana comparable.

## 4. La capa causal no participa del PASS general

El codigo calcula `apass_verdict`, `nhist_verdict`, `athr_verdict`, pero luego:

```python
is_all_exact = all(v == "EXACT" for v in [
    flow_verdict, dticks_verdict, score_verdict,
    zones_verdict, fills_verdict
])
```

La capa causal no esta en la lista. Podria fallar y `PASSED_PUERTA_0` seguiria
saliendo. Deben entrar los tres verdicts, junto con la igualdad de conjuntos.

## 5. El headline confirmado no fue probado

El JSON declara:

- `headline_params.ScoreMode = AbsMagnitude`
- `tested_params.ScoreMode = AbsDirectional`

Eso es correcto para reproducir el CSV viejo, pero no prueba la rama que Nico
confirmo para junio. Puerta 0 del headline requiere un export NT8 con
`ScoreMode=AbsMagnitude` sobre esta misma ventana target-free, o un artefacto
separado que pruebe explicitamente esa rama sin relabeling.

## Estado

- Semantica/arimetica de `AbsDirectional` en cubetas alineadas: **evidencia fuerte
  de EXACT**, pendiente de preservar duplicados.
- Igualdad completa de eventos: **no medida correctamente**.
- `AbsMagnitude` (headline): **no probado contra una corrida NT8**.
- Puerta 0: **no firmada**. No abrir junio.
