# `nt8/` — copias canónicas de los `.cs` de NinjaTrader

Fuente de verdad **versionada** del código NinjaScript que genera los oráculos.
Lo que corre es la copia instalada en
`%USERPROFILE%\Documents\NinjaTrader 8\bin\Custom\Indicators\`; esta carpeta
existe para que un cambio en un `.cs` quede en la historia de git junto al fix
del kernel Python que lo espeja.

## Regla operativa (incidente 2026-07-25)

**Los `.cs` se REEMPLAZAN in place. Nunca se guardan copias dentro de
`bin\Custom`** — NT8 compila **todo** el árbol y dos definiciones de la misma
clase producen `CS0111` / `CS0102` / `CS0121` / `CS0229`. Los respaldos van a
`archive/nt8_cs_backup/` con timestamp, **fuera** de `bin\Custom`.

**Las copias canónicas de acá NO llevan el bloque
`#region NinjaScript generated code`.** Ese bloque es *salida de build*: lo
genera NT8 al compilar. Si un archivo ya lo trae y NT8 genera otro, quedan dos y
la compilación falla.

**Terminadores CRLF.** Un `.cs` con LF hace que NT8 no reconozca su propia
región generada y **anexe una segunda** en vez de reemplazarla — que es
exactamente cómo se rompió la compilación el 2026-07-25 al instalar un archivo
revisado fuera del repo.

## Verificación antes de entregar un `.cs` a NT8

```bash
python tools/check_nt8_cs.py nt8/HFTZones2.cs
```

Debe dar: 1 sola `class X : Indicator`, **0** regiones generadas, meta con la
versión esperada, llaves y paréntesis balanceados, y CRLF sin LF sueltos.

## Inventario

| archivo | versión | sha256 (canónico, sin región generada) |
|---|---|---|
| `HFTZones2.cs` | **v2.3** | `9bdbcc8108d8dc3248bf0b23b18e2bbf53765a8a7fdfbb86ebf9f0e35f04fd32` |
| `BigTrap2.cs` | v2.1 | `77af06eed2bba5d5367ef41a68476d04b295039411ac124492d918c0a557fbf5` |
| `TickBarDiag.cs` | v1.1 | *(instrumental de diagnóstico, no de trading)* |
| `VolTicksPOC2.cs` | v2.1 | `48e0718a055958f0b2a325cdee53517e449989c6b43ecfe50e7b4d634278845d` |
| `aVolCellPOI2.cs` | v2.0 | `4ad4c671333c0b5c214d3d2c3d4c75a6a7dd4f616ee26bc8aaa7d31bb0ead6ed` |
| `AACloseOpenDiffs.cs` | **v1.2** | `e4f5f17b7a2f29fe85299575a4c4ab45b88b29414cb3ef7547d9616775ed2557` |

### Cambios del 2026-07-26 (barrido ULP, AUDIT-003)

| archivo | de → a | qué cambió | por qué |
|---|---|---|---|
| `HFTZones2.cs` | v2.2 → **v2.3** | `inside` pasa a comparar `priceTick` contra `LowerTick`/`UpperTick`; el precio se convierte **una vez por llamada** | el `.cs` había quedado en v2.2 mientras `hftzones2.py` ya era v2.3 — los dos lados estaban desalineados **por construcción**. Exposición medida antes 24,30 %, después **0,00 %** |
| `AACloseOpenDiffs.cs` | v1.0 → **v1.2** | `MinDiffTicks` se compara en enteros (`gapTicks`), no en points; se agrega el helper `PriceToTick` | v1.0 descartaba el **47,5 %** de los gaps de 1 tick (43,5 % observado). Aprobado por Nico. **v1.2** agrega `ind_version` por FILA al logger de research (Decisión B): ese archivo mergea corridas, así que una versión a nivel de archivo sería falsa |

Verificación de los dos: `python tools/check_nt8_cs.py --ulp nt8/*.cs`.

**`Gaps2.cs` no se toca**: es la referencia que dio
paridad 1316/1316; cualquier cambio exige digest nuevo y oráculo nuevo.
