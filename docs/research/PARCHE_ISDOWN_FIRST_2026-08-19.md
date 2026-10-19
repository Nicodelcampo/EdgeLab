# Parche del `isDown`-first — `HFTZonesESPureV2Flat`

- **2026-08-19** · archivo: `docs/research/parches/HFTZonesESPureV2Flat.cs`
- Original `HFTZonesESPureV2.cs` · `sha256 dc114e6d0b2507de001f1616a398421e474af9fee367c8598f0c0705b6501678`
- Parcheado · `sha256 4e80c24d873cd9009850e55d3e3b4a7492a77608e47dc8a41f0294cb226824e5`

## El bug

Con el precio **plano** (`cl == clP == op`) las dos condiciones son verdaderas y
`isDown` se evalúa primero, así que **todo tick plano abre una racha bajista**.

Medido: **92 % de las zonas con `dir = −1`**, idéntico en los tres buckets y los tres
contratos. Y el diagnóstico v2.3 ya había medido que entre el 41 % y el 86 % de los
intervalos son `dt = 0`: los ticks planos abundan.

## El cambio — sólo el inicio

```csharp
bool plano = isDown && isUp;
if (plano) { /* sin direccion: no inicia racha */ }
else if (isDown) { dir = -1; Iniciar(...); }
else if (isUp)   { dir =  1; Iniciar(...); }
```

**La continuación no se toca**: un tick plano durante una racha no la contradice. Sólo
deja de *iniciarla*, que es la regla que las notas de `HFTZones2` ya piden — *«no
arrancar en plano ni `isDown`-first»*.

## Por qué es un indicador nuevo y no una edición

`HFTZonesESPureV2` **queda intacto**. Cambiar el `.cs` original destruiría el objeto que
se está validando y haría imposible medir el tamaño del sesgo.

- clase y `Name` → `HFTZonesESPureV2Flat` (59 ocurrencias, **0** referencias al nombre viejo)
- `DbPath` → base aparte: `oraculo_espurev2flat_ES.sqlite`
- todo lo demás, idéntico

## Cómo usarlo

1. Copiar el `.cs` a la carpeta de indicadores de NT8
2. Compilar (F5)
3. Correrlo con **la misma configuración** de la corrida controlada: mismos contratos,
   mismos `End date`, `EnableFlowLog` off, defaults sin tocar

## Qué mide la comparación

Corriendo los dos sobre la misma ventana y comparando zona a zona sale el **tamaño
exacto del sesgo**: cuántas bajistas desaparecen, cuántas alcistas aparecen, y si la
geometría de las que sobreviven cambia.

Es un resultado en sí mismo, y es **target-free**.
