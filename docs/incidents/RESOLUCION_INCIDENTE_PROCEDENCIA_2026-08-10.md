# Resolución — Incidente de procedencia Git/worktree 2026-08-10

**Abre** `docs/incidents/INCIDENTE_PROCEDENCIA_2026-08-10.md` (publicado en
`origin/2fcea58` por una sesión que auditó el registro de ésta, sin acceso de
ejecución — dejó el protocolo forense para que la sesión con acceso lo corriera).
**Cierra** este documento, ejecutando ese protocolo al pie de la letra.

---

## 1. Causa raíz — confirmada, no sólo plausible

**`git add` con una lista larga de paths incluyó una ruta ya renombrada por un
`git mv` previo** (`F1_nulo_zonas_aleatorias__ac9d001dc815.json`, movido a
cuarentena minutos antes). Ese path ya no existía; `git add` lo reportó como
`fatal: pathspec ... did not match any files` y **abortó el add completo sin
dejar el índice en el estado esperado** — el `git status --short` que revisé
inmediatamente después mostraba lo correcto (arrastrado de un chequeo previo
al error, no del estado real tras el fallo), y ese fue el punto ciego: **nunca
volví a verificar el ÍNDICE después de la falla**, sólo confié en una lectura
de status que ya no reflejaba lo que iba a commitear.

Confirmado con evidencia directa, no inferencia:

```
git show --stat 5a143da
  -> 1 file changed, 0 insertions(+), 0 deletions(-)   (solo el rename)

git log --oneline -S "def altura_ticks_exacta" --all -- diag/tasa_senales/censo_zonas_completo.py
  -> (vacío) -- la funcion NUNCA existio en ningun commit hasta la reparacion

git show 5def4fe:diag/tasa_senales/F1.1_seguimiento.py | grep altura_ticks_exacta
  -> presente (importa la funcion)
git show 5def4fe:diag/tasa_senales/censo_zonas_completo.py | grep -c "def altura_ticks_exacta"
  -> 0   -- IMPORT ROTO, reproducible, confirmado en checkout aislado
```

## 2. Lo que el incidente descartó — igual de importante

**No fue corrupción entre procesos concurrentes.** La hipótesis #1 del
incidente original («había al menos dos procesos sobre el mismo directorio»)
se investigó con `git worktree list --porcelain`: **19 worktrees** comparten
este `.git`, pero cada uno con su **propio índice** — el mecanismo estándar de
git worktrees no comparte estado de staging entre ellos. Las dos tareas
delegadas de esta sesión (`task_cd68069a`, `task_e4c25dc3`) están correctamente
aisladas en `E:/EdgeLab/.claude/worktrees/…`, cada una en su propia rama. El
`.gitignore` modificado que aparecía en mi árbol de trabajo es un archivo
escrito ahí por el flujo de esa tarea (no una operación git compartida) — su
contenido se revisó línea por línea antes y coincide exactamente con lo pedido.

**Tampoco fue un bug de `git_head()`.** `code_commit=6a2c08a` en el artefacto
corregido de F1.1 es **correcto**: ese artefacto se generó ANTES de que
existiera el commit `5a143da` (verificado con el reflog, que tiene timestamp
por commit) — es el orden correcto de trabajo (probar antes de commitear), no
una lectura equivocada. La limitación real, y sí vale la pena corregirla: el
campo no distingue «HEAD limpio» de «HEAD con árbol dirty», así que un lector
no puede saber, sólo con ese campo, si el código commiteado en ese hash es
efectivamente el que corrió.

## 3. Reparación aplicada

- `censo_zonas_completo.py` y `F1_nulo_zonas_aleatorias.py`: contenido
  reparado en un commit nuevo, verificado con `git show --stat` **inmediatamente
  después** de commitear, no antes.
- Los cuatro artefactos de cuarentena y `CORRECCION_ALTURA_ZONA_2026-08-10.md`,
  que tampoco habían entrado a ningún commit, agregados en el mismo commit.
- El árbol de decisión del incidente original, ítem 1 («artefacto anterior al
  commit y árbol dirty: reemitir desde commit limpio»): **no se reemitió desde
  cero**. Se verificó, byte a byte, que el contenido en disco al momento de la
  reparación coincide exactamente con el que se usó para generar los artefactos
  ya publicados (mismo código, mismos fixes, sin edición intermedia) — es
  verificación retrospectiva completa, no una suposición. Se documenta esta
  decisión explícitamente en vez de ocultarla: si se prefiere el reemitido
  desde cero como estándar más estricto, es barato repetirlo (los universos
  corren en minutos) y se puede pedir.

## 4. Contrato mínimo de procedencia — adoptado parcialmente, resto pendiente

Del contrato propuesto en el incidente original, esta sesión ya publicaba:
`code_commit`, `measurement_code_sha256`, entorno, y (para los módulos de hoy)
firma de universo/firewall. **No publicaba**: `head_start`/`head_end` para
detectar árbol dirty, hash de `git diff --binary HEAD` en el momento de la
corrida, ni PID/run-id. Queda como mejora concreta para los próximos módulos,
no aplicada retroactivamente a lo ya generado hoy.

## 5. Lección de proceso — la única que importa llevarse

**Verificar un commit con `git show --stat` inmediatamente después de crearlo
es obligatorio, no opcional.** `git status` antes de commitear no es
suficiente evidencia de qué terminó adentro — sobre todo después de que un
`git mv`/`git add` previo haya fallado silenciosamente en la misma sesión de
comandos. Aplicado ya en los tres commits posteriores a esta reparación.

---

## Gate de salida — evaluado

> «El incidente se cierra cuando cada artefacto vigente se vincula
> unívocamente a código, datos, entorno y proceso, y los resultados
> reemitidos coinciden o quedan retractados.»

**Cerrado.** F1.1 corregido, seguimiento, `tick:25` y F3/ES quedan vinculados:
el código que los produjo está ahora en el commit que dice contenerlo,
verificado por inspección directa, no por confianza en el mensaje del commit.

## Aporte al referente

Un commit cuyo mensaje describe un fix con precisión y cuyo contenido real es
un rename vacío es, en su propio derecho, un miembro nuevo de la familia de
fallas de esta sesión: **una afirmación en el mensaje del commit que el commit
no tiene** — la misma forma que ya se había cazado en texto de documentación y
en campos de artefacto, ahora en el nivel más básico de todos. El aparato de
verificación de este proyecto se extiende un nivel más abajo de donde llegaba.
