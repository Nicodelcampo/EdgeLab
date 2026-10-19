# Enmienda pre-outcome — espacio de reglas de entrada (EXPLORE-001)

> **ESTADO: DRAFT v0.2 — 2026-08-06. NO SELLADO.**
>
> **Decisión de Nico registrada:** devolver la v0.1 a DRAFT v0.2 tras una segunda
> auditoría. Esto **no adopta** ninguna opción técnica S1–S6, no autoriza corridas
> y no abre outcomes, holdout ni oráculos económicos.
>
> Referente: `docs/NORTH_STAR.md` sha256 `21bb3b01a33e2b373859a38ac4615de376a6262f0aa7ced0e8f5dec33b5256a8`
> Gates: `docs/edge_validation_contract.md`
> ESPEC: `docs/ESPEC_TEST_EXPLORE-001.md`
> Decongestión previa: `docs/amendments/EXPLORE-001-2026-08-04_first_touch_decongestion.md`
> Contrato histórico del censo: `docs/D3_CENSO_AUTORITATIVO_PRIMEROS_TOQUES.md`
>
> **SELLADO ≠ AUTORIZACIÓN DE CORRIDA.** Antes de un SEALED v1.0 faltan un
> contrato ejecutable por arquetipo, la curva completa outcome-free, las
> decisiones de Nico y un método único de multiplicidad.

## 0. Por qué la v0.1 fue devuelta

La v0.1 no era sellable. La segunda auditoría encontró cinco defectos materiales:

1. copiaba un estado de elegibilidad anterior a la normalización de eventos;
2. decía a la vez que `AACloseOpenDiffs` tenía toque de misma barra y que no
   emitía ningún `ZONE_TOUCHED`;
3. trataba retorno y ruptura como si compartieran el mismo instante de entrada;
4. proponía `T=1,2,3,5,8,13,21` sin una regla documentada y retiraba `T=34`, que
   sí estaba en el piloto outcome-free;
5. publicaba un conteo nominal de 168 celdas que mezclaba `kind`, la familia tick
   y el control `time:1`, sin un procedimiento de multiplicidad elegido.

También se retira esta frase de la v0.1: «cada vecino es réplica». Las celdas de
T y resolución son anidadas y dependientes; una banda contigua puede ser un gate
de robustez, **no evidencia independiente**.

---

## 1. Frontera epistemológica

### 1.1 Lo permitido antes del sello

- contar zonas y eventos;
- reconstruir el orden temporal previo a una entrada candidata;
- medir frecuencia, cobertura de sesiones y supervivencia a T;
- verificar contratos, tipos, paridad e invariantes;
- reemitir MDE/geometrías usando datos nulos o placebo.

### 1.2 Lo prohibido

- retornos después del instante de entrada candidato;
- PnL, TP/SL, expectativa económica o selección del ganador;
- abrir holdout o correr P5 sin autorización y log;
- modificar la grilla después de mirar outcomes;
- correr `time:1` como adelanto económico de H1 tick.

La curva de diseño es outcome-free sólo si termina su lectura en el instante de
entrada candidato. Esa curva **sí puede y debe informar** la grilla final: fue
construida justamente para evitar que Nico tenga que adivinar T.

---

## 2. Estado real del contrato de eventos en el tip de devolución

`docs/D3_CENSO_AUTORITATIVO_PRIMEROS_TOQUES.md` describe correctamente el estado
**anterior** a los commits de normalización `1f0f62d` y `ff59472`; no es una foto
suficiente del tip actual.

| Indicador | Campos básicos del censo | Invariante temporal actual | Estado para censo básico |
|---|---|---|---|
| `BigTrap2` | completos | pasa | **elegible** |
| `VolTicksPOC2` | completos tras `1f0f62d` | la barra creadora no interactúa | **elegible** |
| `aVolCellPOI2` | completos tras `1f0f62d` | lifecycle empieza en barras posteriores | **elegible** |
| `Gaps2` | completos tras `1f0f62d` + `ff59472` | puede emitir `touch_count=1` en barra creadora | **rechazado por el extractor actual** |
| `HFTZones2` | completos tras `1f0f62d` + `ff59472` | puede emitir `touch_count=1` en barra creadora | **rechazado por el extractor actual** |
| `AACloseOpenDiffs` | no tiene lifecycle de toque | emite `ZONE_CREATED`, cero `ZONE_TOUCHED` | **sin población de primer toque** |

Consecuencia: hoy hay **tres**, no uno, candidatos para el censo básico. Pero el
censo básico de `touch_count==1` todavía **no es** el censo autoritativo de una
regla T-qualified; primero hay que definir y materializar los dos relojes de §3.

---

## 3. Dos arquetipos, dos relojes de entrada

La creación de una zona nunca es por sí sola una entrada.

### 3.1 Retorno

Definición propuesta:

1. la zona se crea en `created_ms`;
2. después de la creación, el precio alcanza una distancia ≥ T desde el borde
   relevante;
3. sólo después de (2), el precio reingresa a la banda;
4. `entry_ms_retorno` es el primer reingreso que satisface ese orden.

Orden exigido:

```text
created_ms < reached_T_ms < entry_ms_retorno
```

### 3.2 Ruptura

Definición propuesta:

1. la zona se crea en `created_ms`;
2. se fija **antes de outcomes** una dirección de break a partir de información
   nativa del indicador o un régimen bilateral ya declarado;
3. `entry_ms_ruptura` es el primer cruce de distancia ≥ T desde el borde
   relevante en esa dirección.

Orden exigido:

```text
created_ms < entry_ms_ruptura
```

Ruptura no exige volver a la zona. Retorno sí. Por eso no se permite usar
`first_touch_ms` como ancla universal.

### 3.3 Misma barra e intrabar

Propuesta revisada, todavía no sellada:

- un contacto simultáneo a la creación no cuenta como entrada;
- ese contacto tampoco descalifica automáticamente la zona para siempre;
- si el feed permite demostrar el orden temporal completo, puede existir una
  entrada posterior en la misma barra;
- si sólo hay OHLC y no puede probarse el orden `creación → alcanza T → entrada`,
  la observación es **ABSTAIN/ineligible**, no se infiere el camino intrabar;
- el evento de entrada final se reconstruye desde geometría + camino canónico de
  precios; `touch_count==1` queda como diagnóstico de lifecycle, no como autoridad
  suficiente para las reglas T-qualified.

Esto evita dos errores opuestos: aceptar la barra creadora por construcción y
matar una zona aunque luego produzca un evento temporalmente demostrable.

---

## 4. Decongestión

Se conserva lo ya congelado:

- separación: **120 minutos**;
- alcance: fecha de sesión `America/Chicago`;
- algoritmo: greedy cronológico;
- frontera de sesión reinicia la separación;
- empate: creación más antigua y luego `zone_id`;
- outcomes prohibidos.

Corrección necesaria para una futura v1.0:

```text
ancla retorno  = entry_ms_retorno
ancla ruptura  = entry_ms_ruptura
```

La frase previa `ancla = first_touch_ms` sólo puede conservarse como alias si el
artefacto define de forma inequívoca cuál de estos dos eventos representa. Esta
re-vinculación es una enmienda semántica y necesita sello de Nico.

---

## 5. Diseño de T: todavía no sellado

### 5.1 Grilla de medición outcome-free propuesta

Para terminar la curva de diseño, no para correr outcomes:

```text
T_design = {1, 2, 3, 5, 8, 13, 21, 34}
```

- T=0 se excluye: no exige alejamiento;
- 34 se conserva porque estaba en el piloto outcome-free y no hay razón
  documentada para retirarlo;
- agregar o retirar valores de la **grilla confirmatoria** se decide después de
  la curva de frecuencia, pero antes de cualquier retorno económico.

### 5.2 Qué puede decidir la curva

Sólo puede usarse para:

- frecuencia por sesión;
- cobertura de sesiones;
- cantidad de eventos elegibles;
- capacidad de formar una banda de especificaciones;
- factibilidad computacional y operativa.

No puede usarse para elegir el T con mejor retorno, expectativa o win rate.

### 5.3 Qué falta antes de cerrar S1

1. terminar la curva outcome-free en el universo research autorizado;
2. reemitir la tabla de 40 geometrías con fricción 2,768;
3. resolver el MDE 1,14 no reproducible;
4. escribir una regla mecánica de recorte basada sólo en frecuencia/cobertura.

Por lo tanto, **S1 queda PENDIENTE**. La lista `T_design` no es todavía la grilla
confirmatoria sellada.

---

## 6. Arquetipo y `kind`

### 6.1 Arquetipos

Ambos arquetipos pueden medirse en la etapa outcome-free. En la etapa
confirmatoria:

- cada hipótesis H1–H3 debe fijar retorno, ruptura o una familia que cobre ambas;
- evaluar ambas políticas cuenta como dos especificaciones económicas;
- está prohibido elegir el arquetipo después de ver cuál gana.

### 6.2 `kind`

`kind` es desglose obligatorio. No multiplica automáticamente la cantidad de
hipótesis si sólo se usa para diagnóstico y se emite un único veredicto agregado.

Sí cuenta por separado cuando:

- existe un veredicto por kind;
- cambia la dirección o regla de entrada;
- se permite promover un kind y matar otro;
- se reporta como candidato independiente.

La v0.1 multiplicaba por dos los kinds de BigTrap2 sin declarar cuál de estos
usos aplicaba; ese conteo queda retirado.

---

## 7. Barras tick y control `time:1`

La familia confirmatoria preexistente de BigTrap2 es:

```text
tick:{10,15,25,50,100}
```

`time:1` sigue siendo control fuera de esa familia. Política propuesta:

- puede usarse antes para ingeniería, paridad ya acreditada y censos target-free;
- **no** puede mirarse como campaña económica formal antes de H1 tick;
- si se decide evaluar económicamente `time:1`, se preregistra como test separado,
  se corre en la misma pasada y entra a la familia de multiplicidad de campaña.

PRED-004, por lo tanto, bloquea H1 tick y también bloquea usar `time:1` como
adelanto económico de la misma tesis. No bloquea trabajo target-free.

---

## 8. Multiplicidad y robustez

### 8.1 Retirado

Se retira el conteo `≈168` de la v0.1 y no se publica un `M_eff` numérico sin
método reproducible.

### 8.2 Método recomendado para decisión de Nico

Propuesta del auditor, todavía pendiente de Nico:

- FWER de campaña = 0,05;
- Romano–Wolf stepdown / max-T;
- remuestreo por bloques de fecha de sesión, preservando dependencia diaria;
- familia = todas las especificaciones económicas realmente evaluadas en la
  pasada confirmatoria, incluido `time:1` si se mira económicamente;
- código y tests del ajuste listos antes del manifiesto SEALED.

No se deja «autovalores / Romano–Wolf» como menú para elegir después de ver
resultados. Si Nico prefiere otro método, debe quedar fijado antes de la corrida.

### 8.3 Banda contigua

Puede conservarse como gate adicional:

> una tesis sobre un eje ordenado sólo puede VIVIR si existe una banda de al
> menos tres valores adyacentes cuyos IC ajustados cumplen el criterio.

Pero:

- la banda no reemplaza el ajuste de multiplicidad;
- sus miembros son dependientes y no se llaman réplicas;
- un pico aislado muere aunque pase individualmente;
- se entrega la curva completa, nunca sólo el argmax.

---

## 9. Qué puede ejecutarse mientras sigue DRAFT

Permitido, sin outcomes:

1. instrumentar y terminar la curva `T_design` con progreso visible;
2. implementar un extractor de eventos candidatos separado por arquetipo;
3. probar orden temporal y ABSTAIN intrabar con fixtures sintéticos;
4. correr un censo **diagnóstico** de contrato en BigTrap2, VolTicksPOC2 y
   aVolCellPOI2;
5. reemitir MDE/geometrías con fricción 2,768;
6. verificar G4/PRED-004 sin consumir P5 económico.

No permitido:

- llamar “autoritativo” al censo T-qualified hasta que §3 esté implementado;
- llenar H1–H3 con retornos;
- correr una campaña económica;
- sellar automáticamente esta v0.2.

---

## 10. Decisiones de Nico que siguen abiertas

La devolución a v0.2 **no responde** estas filas:

| # | Decisión pendiente | Recomendación auditada, no sellada |
|---|---|---|
| S1 | grilla confirmatoria T | terminar curva outcome-free; usar `T_design` sólo para diseño |
| S2 | uso de ambos arquetipos | ambos en diseño; uno por hipótesis, o cobrar ambos explícitamente |
| S3 | misma barra / orden | aceptar sólo orden demostrable; ambigüedad intrabar = ABSTAIN |
| S4 | multiplicidad | Romano–Wolf/max-T por bloques de sesión |
| S5 | primer censo | diagnóstico en los tres elegibles; autoritativo tras extractor T-qualified |
| S6 | `time:1` económico antes de tick | no; sólo trabajo target-free hasta PRED-004 |

Próxima instancia de decisión: v0.3 con evidencia outcome-free y diff explícito
contra esta v0.2. Recién entonces Nico puede sellar v1.0.

---

## 11. Checklist para una futura v1.0

- [ ] Curva outcome-free completa y huellada
- [ ] Dos relojes de entrada implementados y testeados
- [ ] Política intrabar decidida
- [ ] Grilla T confirmatoria cerrada
- [ ] Arquetipo por hipótesis o familia cobrada explícitamente
- [ ] Método único de multiplicidad fijado
- [ ] Tabla de elegibilidad actualizada
- [ ] H1–H3 escritas sin outcomes
- [ ] Manifiesto cita el hash del cuerpo sellado
- [ ] Firma y fecha UTC de Nico

```text
SELLADO POR: —
FECHA (UTC): —
```

## STOP

Esta v0.2 documenta una devolución, no un permiso. No hay grilla confirmatoria,
hipótesis ni campaña autorizadas.

<!-- SHA256-BODY-ABOVE -->

**sha256 del cuerpo:** no aplica mientras sea DRAFT.

**Estado:** DRAFT v0.2 — 2026-08-06 — v0.1 devuelta por decisión de Nico.
