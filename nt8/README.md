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
| `HFTZones2.cs` | v2.1 | `b8c8214cb1bbd203876886efd325e23617ec99202576dbb590091e80c77a5c6e` |
| `BigTrap2.cs` | v2.1 | `77af06eed2bba5d5367ef41a68476d04b295039411ac124492d918c0a557fbf5` |
| `TickBarDiag.cs` | v1.1 | *(instrumental de diagnóstico, no de trading)* |
| `VolTicksPOC2.cs` | v2.1 | `a7fbdd5bfb0efcb4003b60e18c2865b8825abeb5e9ca9ab9131b4f45423c19ff` |

Falta versionar `aVolCellPOI2`. **`Gaps2.cs` no se toca**: es la referencia que dio
paridad 1316/1316; cualquier cambio exige digest nuevo y oráculo nuevo.
