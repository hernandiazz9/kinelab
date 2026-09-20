# interfaz-exploracion — 2026-09-12

> **Reconstrucción, no informe de sesión.** Lo escribió el orquestador el
> 20/9/2026 leyendo el historial, porque el 01 nunca dejó informe y el tablero
> lo marcaba abierto para siempre. Los commits son verificables; lo que no
> consta se dice que no consta.

Resumen: el 01 se hizo el mismo 12/9 y está en `main`. Es el primer encargo del
proyecto y es anterior al método: el formato de informes se escribió ese mismo
día, en `27fe21f`, después de que el 01 ya estuviera corriendo. Por eso no hay
informe, no porque haya quedado. La pantalla que pedía existe (`web/`, Next 16,
más `PUT /api/datos` en `service/`) y de ella salió una de las lecciones que
hoy están en `AGENTS.md` §Cosas que muerden: el proxy de `next dev` cortaba el
cuerpo a 10 MiB sin avisar. Lo que sigue abierto de esa pantalla no es del 01:
son el 21 (visor desde datos, postergado), el 28 (ya cerrado) y el inventario
de «una sola escala en la pantalla» del 16/9.

Encargo: una pantalla para subir un video y ver los palitos y toda la data del
modo exploración, sin gate, sin puntaje y sin nada del deporte.

Hecho (commits del 12/9, en `main`):
- `c79dd43` — interfaz de exploración: `web/` (Next 16) + `PUT /api/datos` en
  `service/`.
- `2725e01` — proxy de `next dev`, límite de cuerpo a 2 GB: cortaba los videos
  a 10 MiB sin avisar y la conexión quedaba colgada. Está en `AGENTS.md`.
- `45809a2` — la fuente del overlay se escala también por el ancho; en video
  vertical la tercera línea se salía por la derecha.
- `38ed3af` — el prompt del encargo y `ESTADO.md`.

Probado: no consta. La sesión no dejó números y este informe no los inventa.
Lo que sí consta es que la pantalla se siguió usando y modificando en los
encargos 20, 21, 27 y 28, así que funcionaba.

Queda abierto: nada atribuible al 01.

Preguntas para el orquestador: ninguna. Si algún día hace falta el detalle,
está en `git show c79dd43`.
