# Agentes del Debian — roles, modelos y tareas

Estado: VIGENTE (GENERADO de `config/autopilot/AGENTES.json` con `python tools/agentes.py --write`; no editar a mano). Actualizado: 2026-11-09.

## Agentes

| Agente | Modelo | Función | Contexto máx. (caracteres) | Roles |
|---|---|---|---|---|
| capataz | `python_determinista` | Capataz determinista: sincroniza con foundation, avanza el embudo, reparte Kaggle, corre los SLIs de alineación | — | — |
| arquitecto | `claude-fable-5-2` | Arquitecto cuantitativo y meta-analista: decide QUÉ vale la pena investigar | 200000 | proponente, abogado, meta_analista |
| ingeniero | `claude-opus-5-5` | Ingeniero de módulos y doctor autorreparador (worktree aislada) | 80000 | programador |
| juez | `claude-opus-5-5` | Revisor independiente del arquitecto: otro modelo que el que propone | 140000 | revisor |
| auditor | `claude-sonnet-5-5` | Auditor adversario, guardián de alineación | 140000 | revisor2, auditor |
| escribas | `claude-haiku-5-5` | Lectura, fichas y crónica en volumen | 30000 | lector, bibliotecario, cronista |

## Roles

| Rol | Agente | Modelo | Tope diario | Núcleo de contexto | Tarea |
|---|---|---|---|---|---|
| proponente | arquitecto | `claude-fable-5-2` | 24 | sí | Propone UNA familia falsable por ciclo, priorizando indagar lo que ya mostró ventaja (FACTORES_CON_VENTAJA) antes que abrir familias nuevas |
| abogado | arquitecto | `claude-fable-5-2` | 20 | sí | Sobre cada hallazgo: la explicación no-edge más plausible y la prueba que la refuta |
| meta_analista | arquitecto | `claude-fable-5-2` | 12 | sí | Tras cada campaña cerrada: qué factor aportó, cuánto, dónde, y qué indagar después; mantiene el registro de factores con ventaja |
| programador | ingeniero | `claude-opus-5-5` | 1 | sí | Escribe y repara código dentro de su perímetro, con tests y controles sintéticos |
| revisor | juez | `claude-opus-5-5` | 40 | sí | PROMOTE / KILL / DERIVE de un pre-registro contra antecedentes del proyecto |
| revisor2 | auditor | `claude-sonnet-5-5` | 40 | sí | Segunda opinión escéptica ante un PROMOTE, sin ver la razón del primero |
| auditor | auditor | `claude-sonnet-5-5` | 60 | sí | Compara lo corrido contra lo pre-registrado: CONFORME / DESVIO / SOSPECHA_FUGA |
| lector | escribas | `claude-haiku-5-5` | 200 | no | Resume resultados de corridas, sin juicio |
| bibliotecario | escribas | `claude-haiku-5-5` | 100 | no | Fichas de literatura con referencia |
| cronista | escribas | `claude-haiku-5-5` | 100 | no | Redacta el resumen del ciclo para la sala con los números tal cual |

## Modelos

| Alias | Identificador | USD por millón (entrada / salida) | Para qué |
|---|---|---|---|
| fable | `claude-fable-5-2` | 8.0 / 40.0 | criterio, síntesis y diseño: pocas llamadas, las que más pesan |
| opus | `claude-opus-5-5` | 4.0 / 20.0 | juicio independiente y código |
| sonnet | `claude-sonnet-5-5` | 2.0 / 10.0 | revisión adversaria y auditoría frecuentes |
| haiku | `claude-haiku-5-5` | 0.1 / 0.5 | resúmenes y fichas en volumen |

El que propone (arquitecto) y el que juzga (juez, auditor) son modelos distintos a propósito: separación de poderes.
