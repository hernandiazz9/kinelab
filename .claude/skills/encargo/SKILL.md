---
name: encargo
description: Corre un encargo numerado de kinelab escrito por el orquestador (docs/prompts/NN-<slug>.md) con las reglas fijas del proyecto - lectura de los documentos base en orden, la regla del front de Hernán (nunca levantarlo ni abrirlo), commits con rutas explícitas, ESTADO.md al día y el informe corto en docs/informes/. Usar siempre que Hernán escriba "/encargo NN", "hacé el encargo NN", "corré docs/prompts/NN-...", o pegue un prompt que diga "Para correr - /encargo NN", aunque no use la palabra encargo.
---

# Encargo de trabajo

Sos una sesión de trabajo de `kinelab`. El orquestador (otra sesión, que no
escribe código) te dejó un pedido en `docs/prompts/`. Esta skill es lo que vale
para **todos** los encargos; el prompt es lo específico de éste. Si se
contradicen, avisá antes de empezar.

## 1. Encontrar el pedido

El argumento es `$ARGUMENTS`. Es el número del encargo (dos dígitos) o su slug.
Buscá `docs/prompts/$ARGUMENTS-*.md` (o `docs/prompts/*-$ARGUMENTS.md` si es un
slug). Si no hay exactamente uno, listá `docs/prompts/` y preguntá cuál. Si no
vino argumento, preguntá el número. Leé el prompt entero antes de nada.

## 2. Leer antes de escribir una línea

`AGENTS.md` ya está cargado. Leé completos y en este orden: `CONTEXTO.md`,
`DECISIONES.md`, `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`,
`HERENCIA.md` y por último `ESTADO.md` (su sección más reciente dice dónde
quedó todo). Después, los archivos de código que el prompt nombre, y sólo esos
al principio. Son unas 1.900 líneas; se leen una vez y evitan repetir errores
que ya se midieron (el cementerio de `HERENCIA.md` existe por eso).

## 3. La regla de trabajo de Hernán (no negociable)

Trabajá normal: probá la funcionalidad de verdad (corré videos por el pipeline,
medí, verificá que los números den, escribí tests), y usá subagentes y
workflows cuando convengan. Lo ÚNICO que no hacés es levantar el frontend,
abrirlo en el navegador, sacar capturas de pantalla o leer la página: eso quema
el contexto. El front lo prueba Hernán y va diciendo cómo está; vos lo dejás
listo con los comandos para levantarlo y una lista corta de "probá esto, esto
y esto". Excepción: sólo si él lo pide explícitamente. El backend
(`.venv/bin/python -m service`) sí se puede levantar para probar con `curl`
o con el TestClient: lo que no se levanta es `next dev` ni el navegador.

## 4. Lo que aplica siempre (además de `AGENTS.md`)

- El motor `kinelab/` no conoce ningún deporte; lo del deporte va en
  `sports/<deporte>/`.
- Ningún número sin unidad ni sin procedencia (`medido`, `estimacion`,
  `declarado`…; ver `CONTEXTO.md` y `CONTRATO.md`).
- Sin puntaje ni veredicto para el atleta (ADR-012). Se muestra la medición,
  no se califica.
- Stack cerrado (ADR-015). Nada nuevo sin preguntar; y antes de proponer algo,
  ADR-010: código, pesos y datos de entrenamiento son tres licencias distintas.
  En `web/`, sólo MIT/Apache/BSD, con la licencia anotada donde se agrega.
- Si algo del prompt o de los documentos resulta inviable, avisá y anotalo
  (`CONTRATO.md` §Desviaciones si es del contrato; `ESTADO.md` si es de
  proceso). No rodees.
- Prosa en español, identificadores en inglés.

## 5. Sesiones en paralelo

Puede haber **otra sesión trabajando en este mismo directorio** en otro
encargo; el prompt lo dice en "En paralelo" y nombra los archivos que toca la
otra. El repo es uno solo y el índice de git también, así que:

- **Dos sesiones nunca editan el mismo archivo.** `git commit -- ruta` lleva
  el estado entero del archivo, incluidas las líneas a medio hacer de la
  otra sesión. Si el prompt no te asigna un archivo que necesitás, no lo
  toques: lo que cambiarías va en el informe.
- Nunca `git add -A`, `git add .` ni `git commit -a`. Siempre rutas explícitas
  de lo que vos tocaste (`git add ruta1 ruta2 && git commit -m …`, o
  `git commit -m … -- ruta1 ruta2`).
- `git status` antes de cada commit. Si aparecen archivos que no son tuyos, ni
  los toques ni los commitees; si te estorban, decilo en el informe.
- En `ESTADO.md` tu sección lleva el número del encargo en el título. No
  edites secciones de otros encargos en curso.

## 6. Material de prueba que existe

- `~/Desktop/cortado.mp4`: swing real de Hernán, 3 s, 30 fps CFR, 76 cuadros,
  vertical (Samsung S22 Ultra). Hoy el motor da address 7, top 39, impacto 44;
  el contacto real cae entre el 44 y el 45. Original de 9 s del que salió
  (cuadros 103–178): `~/Desktop/20260907_170638.mp4`.
- `.venv/bin/python -m kinelab datos VIDEO --altura-m 1.75` corre todo sin gate
  y deja `<video>.kinelab/` con overlay, fotos por evento, CSV por cuadro y
  JSON por evento (~10 s por clip de 3 s).
- Clips sintéticos en `tests/conftest.py`; swing sintético con eventos
  conocidos en `tests/helpers/synth_swing.py`; arnés de verdad en `truth/`
  (entorno virtual propio, a propósito).
- Suites: `.venv/bin/pytest -q` (motor); `cd truth && .venv/bin/pytest -q`
  (arnés); `cd web && pnpm lint && pnpm build` (front, sin abrirlo).

## 7. Cómo cierra el encargo

En este orden, y no está terminado hasta el último punto:

1. Las suites que tocaste en verde, y la corrida real que el prompt pide, con
   sus números a mano.
2. `ESTADO.md`: una sección nueva arriba de todo, `## <fecha> — encargo NN:
   <título>`, con qué existe ahora, qué falta o no se probó, y las
   desviaciones. Es lo que la sesión siguiente lee para saber dónde quedó.
3. El informe en `docs/informes/<AAAA-MM-DD>-NN-<slug>.md` con el formato de
   `docs/informes/README.md`. Números, no adjetivos: el orquestador no lee
   código ni CSVs, decide sólo con lo que pongas ahí. Si algo quedó abierto o
   hay una decisión que no era tuya, va en su campo.
4. Commit(s) con rutas explícitas y mensaje en español que diga qué cambió y
   por qué. El último incluye `ESTADO.md` y el informe.
5. Respuesta final a Hernán, corta: qué quedó, hashes de los commits, y si
   hay front o algo manual, la lista "probá esto, esto y esto" con lo que
   tiene que ver en cada paso.
