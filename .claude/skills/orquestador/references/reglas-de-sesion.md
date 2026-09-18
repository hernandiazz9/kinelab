# Reglas de sesión (cuerpo de la skill `/encargo` de cada repo)

Este archivo es la plantilla de `.claude/skills/encargo/SKILL.md` de un
proyecto. El script `scripts/arrancar.py` lo copia al repo reemplazando los
`{{...}}`; el orquestador completa la ficha (§2, §4 y §6) después de leer el
proyecto. Todo lo que está fuera de la ficha es genérico y vale igual en
cualquier proyecto.

---
name: encargo
description: Corre un encargo numerado de {{PROYECTO}} escrito por el orquestador (docs/prompts/NN-<slug>.md) con las reglas fijas del proyecto - lectura de los documentos base en orden, reglas de trabajo, commits con rutas explícitas, {{ARCHIVO_ESTADO}} al día y el informe de formato fijo en docs/informes/. Usar siempre que {{DUEÑO}} escriba "/encargo NN", "hacé el encargo NN", "corré docs/prompts/NN-...", o pegue un prompt que diga "Para correr - /encargo NN", aunque no use la palabra encargo.
---

# Encargo de trabajo

Sos una sesión de trabajo de `{{PROYECTO}}`. El orquestador (otra sesión, que
no escribe código) te dejó un pedido en `docs/prompts/`. Esta skill es lo que
vale para **todos** los encargos; el prompt es lo específico de éste. Si se
contradicen, avisá antes de empezar.

## 1. Encontrar el pedido

El argumento es `$ARGUMENTS`: el número del encargo (dos dígitos) o su slug.
Buscá `docs/prompts/$ARGUMENTS-*.md` (o `docs/prompts/*-$ARGUMENTS.md` si es
un slug). Si no hay exactamente uno, listá `docs/prompts/` y preguntá cuál. Si
no vino argumento, preguntá el número. Leé el prompt entero antes de nada.

## 2. Leer antes de escribir una línea

{{DOCS_BASE}}

Después, los archivos de código que el prompt nombre, y sólo esos al
principio. Se leen una vez y evitan repetir errores que ya se pagaron.

## 3. Reglas de trabajo de {{DUEÑO}}

- Trabajá normal: probá la funcionalidad de verdad (corré el sistema sobre
  datos reales, medí, verificá que los números den, escribí tests), y usá
  subagentes y workflows cuando convengan.
- **Front:** el prompt dice, en su campo «Front», si lo probás vos o lo
  prueba {{DUEÑO}}. Si no dice nada, lo prueba {{DUEÑO}}: lo dejás listo con
  los comandos para levantarlo y una lista corta de "probá esto, esto y
  esto". Levantar un servidor para probarlo con `curl` o con un cliente de
  tests no es "probar el front": eso siempre se puede.
- Si algo del prompt o de los documentos resulta inviable, avisá y anotalo
  ({{DONDE_ANOTAR_DESVIACIONES}}). No rodees.
- {{IDIOMA}}

## 4. Lo que aplica siempre en este proyecto

{{RESTRICCIONES}}

## 5. Sesiones en paralelo

Puede haber **otra sesión trabajando en este mismo directorio** en otro
encargo; el prompt lo dice en «En paralelo» y nombra los archivos que toca la
otra. **Nunca más de dos a la vez**, y una sesión que corre el sistema sobre
material real no coincide con otra que edita el código que ese sistema
importa: los números saldrían de un código a medio escribir. El repo es uno
solo y el índice de git también, así que:

- **Dos sesiones nunca editan el mismo archivo.** `git commit -- ruta` lleva
  el estado entero del archivo, incluidas las líneas a medio hacer de la
  otra sesión. Si el prompt no te asigna un archivo que necesitás, no lo
  toques: lo que cambiarías va en el informe.
- **Commitear siempre con `git commit -m "…" -- ruta1 ruta2`**, las rutas al
  final. Esa forma commitea sólo esas rutas aunque el índice tenga otras
  cosas. `git add ruta && git commit -m "…"` **no** sirve: commitea todo lo
  que esté staged, incluido lo que otra sesión dejó ahí.
- `git add` sólo para archivos **nuevos** tuyos, en el mismo comando que su
  commit. `git mv` y `git rm`, también en el mismo comando que su commit:
  nunca los dejes staged.
- Nunca `git add -A`, `git add .`, `git commit -a` ni `git stash`.
- Al empezar, `git diff --cached --name-only` tiene que estar vacío. Antes de
  cada commit, tiene que listar sólo archivos tuyos. Si lista uno ajeno,
  **pará** y decilo en el informe: no lo commitees ni lo saques del índice.
- `{{ARCHIVO_ESTADO}}` se edita en un solo paso, al cierre. Como lo editan
  todas las sesiones, antes de commitearlo `git diff {{ARCHIVO_ESTADO}}`
  tiene que mostrar sólo tu sección. Si trae líneas de otra sesión sin
  commitear, no lo commitees: dejá el texto de tu sección en tu informe y
  avisalo.
- Los tests se leen por **exit code y conteo** de pasados y fallados, no por
  la palabra «passed». Nada de fechas, conteos ni valores quemados en un
  test que puedan cambiar solos (la fecha, el número de métricas del
  registro): afirmá contra la fuente que cambia.
- Nunca termines sin commitear. Si no podés cerrar, commiteá lo que está
  entero, y en el informe decí qué quedó afuera y en qué archivo.

## 6. Material y comandos de prueba

{{MATERIAL}}

## 7. Cómo cierra el encargo

En este orden, y no está terminado hasta el último punto:

1. Las suites que tocaste en verde por exit code y conteo, y la corrida real
   que el prompt pide, con sus números a mano.
2. `{{ARCHIVO_ESTADO}}`: una sección nueva arriba de todo,
   `## <fecha> — encargo NN: <título>`, con qué existe ahora, qué falta o no
   se probó, y las desviaciones. Es lo que la sesión siguiente lee para saber
   dónde quedó.
3. El informe en `docs/informes/<AAAA-MM-DD>-NN-<slug>.md` con el formato de
   `docs/informes/README.md`, **con el resumen de diez líneas arriba**.
   Números, no adjetivos: el orquestador no lee código ni datos, decide sólo
   con lo que pongas ahí. Lo abierto y las decisiones que no eran tuyas van
   en sus campos.
4. Commit(s) con rutas explícitas y mensaje que diga qué cambió y por qué.
   El último incluye `{{ARCHIVO_ESTADO}}` y el informe.
5. Respuesta final a {{DUEÑO}}, corta: qué quedó, hashes de los commits, y si
   hay front o algo manual, la lista "probá esto, esto y esto" con lo que
   tiene que ver en cada paso.
