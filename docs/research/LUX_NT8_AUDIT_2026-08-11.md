# LUX-IMB — auditoría estática del NT8 recibido

**Archivo:** `ImbalanceDetectorLuxAlgoMTF.cs`  
**Tamaño:** 34.582 bytes; 629 líneas  
**SHA-256 crudo:** `bff0e66242d055152f891c9fcb2e04b3890346a1cf6b88311607e4645350c533`  
**SHA-256 normalizado LF:** `f13576008bd3caecacc0ace6602fe43460508ab57e93afe080b658a7cacbbdd0`  
**Estado:** referencia útil, no oráculo de paridad todavía.

## Lo que sí resuelve

- usa una serie M1 secundaria y `Calculate.OnBarClose`;
- FVG apagado, OG y VI activos por defecto;
- conserva puntos, porcentaje y ATR(200);
- proyecta 500 minutos/barras M1 por defecto;
- no elimina cajas por `Mitigation Method`;
- implementa desigualdades VI explícitas.

## Hallazgos bloqueantes

### 1. La geometría OG no coincide con su condición

Detecta OG alcista con `Low[0] > High[1]` y bajista con `High[0] < Low[1]`, pero guarda, filtra y dibuja el intervalo body-a-body calculado para VI. La zona coherente es wick-a-wick:

```text
alcista: [High[1], Low[0]]
bajista: [High[0], Low[1]]
```

El archivo recibido puede ampliar OG hacia precios donde sí hubo negociación y fabricar contactos inexistentes.

### 2. El near-miss mezcla detector y outcome

`ShowNearMissDiamonds=true` por defecto y usa mecha/cierre de la misma barra o de la siguiente. Es clasificación retrospectiva, no señal disponible al crear la zona. También prueba ambos lados sin usar `IsBull`, reutiliza tags sin ID de zona y fija umbrales `2/10/5` ticks no preregistrados.

### 3. No es autónomo

- `ImbalanceWidthMethod` no está definido en el archivo;
- requiere `System.Data.SQLite`;
- fija `DbPath = D:\\AlgoProject\\data\\algo_features.sqlite`;
- incluye código autogenerado que puede quedar obsoleto.

### 4. El ledger SQLite no alcanza

Omite `zone_id`, `created_at`, `available_at`, barra fuente, expiración, configuración, hashes, calendario y versión. Usa `ToUniversalTime()` sin demostrar timezone/Kind de `Time[0]`.

### 5. MTF y Extend requieren paridad

El encabezado promete DateTime, pero dibuja con `barsAgo` negativos desde la serie secundaria. `Extend` equivale a minutos sólo porque la fuente es M1. Faltan pruebas en gráficos no M1, DST y orden de `BarsInProgress`.

## Decisión

No se descarta: se fija su SHA y se usa para una semántica candidata. No se lo declara equivalente a Pine ni listo para outcomes.

`edgelab/research/lux_imb.py` replica VI, corrige OG a wick-a-wick, exige timestamps con zona horaria y separa detección de reacción.

## Gate restante

1. hardenizar el `.cs`;
2. compilarlo en NT8 con dependencias declaradas;
3. exportar 50+ zonas OG/VI;
4. comparar bordes, dirección y `available_at` contra Python;
5. recién después ejecutar H-COND-1.
