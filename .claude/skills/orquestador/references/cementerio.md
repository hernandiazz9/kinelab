# Cementerio del método

Lo que se intentó y falló, con fecha y con lo que costó. Cada entrada es una
regla que ya está en SKILL.md o en `reglas-de-sesion.md`; acá está el porqué.

**2026-09-12 · El estado del proyecto escrito en el prompt.** El primer prompt
del orquestador decía "el encargo 01 está por correr"; ya estaba construido.
Se pudrió el mismo día. → El estado vive en archivos que se leen al arrancar;
el prompt y la skill no llevan fechas ni "dónde estamos".

**2026-09-12 · El boilerplate repetido en cada prompt.** La regla del front,
el orden de lectura y el cierre iban copiados en cada encargo; cada copia
derivaba. → Lo fijo vive en la skill `/encargo` del repo; el prompt lleva
sólo lo específico.

**2026-09-14 · Dos sesiones y un índice de git.** Una sesión commiteó con
`git add ruta && git commit` y se llevó cuatro líneas que otra tenía a medio
hacer en el mismo archivo. → Dos sesiones nunca editan el mismo archivo;
commit sólo con `git commit -- rutas`.

**2026-09-15 · El `git mv` ajeno.** Una sesión de documentos commiteó y el
commit se llevó un renombre que otra sesión había dejado staged. Y otra vez
con 38 borrados de otra sesión. → `git diff --cached --name-only` vacío al
empezar y sólo archivos propios antes de cada commit; `git mv`/`git rm` en el
mismo comando que su commit; nunca `stash`.

**2026-09-15 · El motor a medio escribir.** Una sesión corrió el análisis
sobre material real mientras otras dos editaban el motor: la primera corrida
reventó con un `NameError`, la segunda anduvo, y los números resultaron no
reproducibles desde HEAD. → Una sesión que corre el sistema sobre material no
coincide con otra que edita el código que importa. Máximo dos sesiones.

**2026-09-15 · Una sesión terminó sin commitear.** El contrato 2.0.0 entero
quedó en el árbol y otra sesión dependía de él; la segunda tuvo que
commitearlo con un mensaje que dijera de quién era. → Nunca terminar sin
commitear; si no se puede cerrar, commitear lo entero y decir qué falta.

**2026-09-15 · Tests con fechas y conteos quemados.** Un test con una fecha
literal se puso rojo al pasar la medianoche; otro con `== 12` se puso rojo
cuando otra sesión agregó dos métricas al registro. → Afirmar contra la
fuente que cambia (la hora, el registro), nunca contra un literal que otro
puede mover.

**2026-09-15 · La palabra "passed".** `addopts = "-q"` sumado al `-q` de la
línea de comandos daba `-qq` y no imprimía el conteo; y el arnés terminaba
con exit 134 después del resumen verde. → Los tests se leen por exit code y
conteo. Un abort al cerrar es un bug, no ruido.

**2026-09-15 · Informes de 300 líneas.** Valiosos, pero el orquestador
tardaba una ronda en leer cuatro. → El resumen de diez líneas arriba de cada
informe; el cuerpo queda para quien lo necesite.

**2026-09-16 · Los primeros 21 juicios.** El sistema habilitó juicio en 21
números y una auditoría de 23 agentes bajó eso a 0: la aritmética era
exacta, pero la cámara derivaba, un evento caía en el swing siguiente y la
regla permitía juicio sin rango. → Auditar el primer resultado que alguien
va a usar, antes de mostrarlo. Conservador y reversible: apagar, no borrar.

**2026-09-16 · Siete agentes por prompt.** Verificar tres prompts contra el
código con siete agentes cada uno encontró más de veinte errores; también
costó más que los encargos. → Verificar con dos o tres, sólo los prompts que
tocan el núcleo, y decirlo en el plan.

**2026-09-18 · Un chip que abre un worktree.** Los chips de la app abren la
sesión en un worktree sin los archivos ignorados (venv, modelos, datos). →
El prompt del chip empieza con `cd <checkout principal>`; si no anda, texto.
