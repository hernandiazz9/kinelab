# Arrancar un proyecto con el método

Tres pasos: entrevista corta, script, ficha. Después, el primer turno del
orquestador (SKILL.md, situación 2).

## 1. Entrevista al dueño (una sola vez, con `AskUserQuestion` si está)

Preguntá sólo lo que no se puede leer del repo:

1. **Nombre del proyecto y ruta del checkout principal** (la ruta importa
   para los chips: abren un worktree sin los archivos ignorados).
2. **Documentos base y orden de lectura.** Si el repo tiene `CLAUDE.md` o
   `AGENTS.md`, proponé lo que dicen; si no, preguntá cuáles son la fuente de
   verdad. Si no hay ninguno, el primer encargo es escribirlos, no código.
3. **Archivo de estado.** `ESTADO.md` por defecto: una sección por encargo,
   la más nueva arriba. Si el proyecto ya tiene otro, ése.
4. **Front.** ¿Hay algo que se vea en un navegador? Si sí: por defecto lo
   prueba el dueño, y cada encargo con front le pregunta si esa vez lo
   prueba la sesión.
5. **Idioma** de prosa, commits y documentos; identificadores en inglés salvo
   que diga otra cosa.
6. **Dónde se anotan las desviaciones** (un `§Desviaciones` de algún
   documento, o el archivo de estado).

## 2. El script

```bash
python3 ~/.claude/skills/orquestador/scripts/arrancar.py <ruta del repo> \
  --proyecto <nombre> --dueno <nombre> --estado ESTADO.md \
  --idioma "Prosa en español; identificadores de código en inglés." \
  --desviaciones "en ESTADO.md, con fecha y razón"
```

Crea, sin pisar lo que exista:

- `docs/PLAN.md` vacío con la plantilla.
- `docs/prompts/README.md` (qué es un encargo, numeración) y
  `docs/informes/README.md` (el formato del informe).
- `.claude/skills/encargo/SKILL.md` desde `reglas-de-sesion.md`, con los
  `{{...}}` de la entrevista reemplazados y los de la ficha (§2 documentos
  base, §4 restricciones, §6 material y comandos) marcados `PENDIENTE`.
- `.claude/skills/orquestador/` copiado entero al repo (SKILL.md y
  `references/`), para que el repo cuente su propio método sin depender de
  esta Mac.
- El archivo de estado, si no existe, con su cabecera.

Y una sección corta en `CLAUDE.md` o `AGENTS.md` (la que exista; si ninguna,
`CLAUDE.md` nuevo) que diga que el trabajo va por encargos y dónde viven las
reglas.

## 3. La ficha del proyecto (la completa el orquestador)

Después del script, leé los documentos base y completá en
`.claude/skills/encargo/SKILL.md`:

- **§2** la lista de documentos en orden, con una línea de por qué ese orden
  y cuántas líneas son.
- **§4** lo que aplica siempre y **no está** ya en `CLAUDE.md`/`AGENTS.md`
  (que las sesiones cargan solas): invariantes del dominio, stack cerrado,
  licencias, qué no se muestra nunca. Corto: cinco a ocho puntos.
- **§6** el material real y sintético que existe, los comandos de las suites
  y cómo se corre el sistema de punta a punta, con tiempos si se saben.

Commiteá todo con rutas explícitas y seguí con el primer turno.
