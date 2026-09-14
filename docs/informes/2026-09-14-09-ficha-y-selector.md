# ficha-y-selector — 14 de septiembre de 2026

**Encargo:** que la pantalla deje de esconder lo que el motor ya calcula. Cinco
cosas: elegir **con qué se filmó** antes de subir; `PUT /api/datos?camino=ID`
con sus 400; la **ficha del archivo** como primera etapa del trabajo, visible
mientras corre la pose; los **avisos** (`fps_aviso` del camino declarado y
`fps_note` de la corrección del primer delta) arriba de todo; y un bloque con
las **12 métricas** del registro, cada una calculada o con su razón.

## Hecho

- `b0b46c9` — backend, front y tests. Sin tocar `kinelab/`.
- **`PUT /api/datos?camino=ID`**, default `desconocido-video`. Va a
  `explore(camino=…)` y queda en `trabajo.json`. Se valida **antes** de recibir
  el archivo: id inexistente → 400 con la lista; `slomo` sin calibrar → 400 con
  la misma frase que da el gate (`slomo_declared_reason`, comparada literal en
  un test).
- **La cola resuelve los caminos del mismo `data/` que los trabajos.** Antes
  `explore()` caía en `default_capture_paths_file()`: en los tests eso leía el
  YAML **del repo**, no el del `tmp_path`. Es el bug que destapó el octavo
  camino del fixture (ver Queda abierto).
- **Bloque `archivo` en `GET /api/datos/{id}`** (`ficha_de_captura`): codec,
  tamaño y rotación, cuadros, duración real y de reproducción, fps efectivo y
  bruto, tasa variable sí/no con su ratio y el umbral del motor, primer delta,
  `fps_note`, camino, si está calibrado y la procedencia. Sale del
  `capture.json` que `prepare_take` escribe **antes** del modelo, así que está
  con el trabajo en `detectando_pose`. No se copia al `trabajo.json`.
- **`GET /api/datos` lleva `camino` y `fps_provenance` en cada fila**, siempre,
  también mientras el trabajo corre.
- **Front**, en este orden: selector «¿con qué se filmó?» (recordado en
  `localStorage`, **confirmado contra la lista del backend** —un camino que ya
  no existe cae al genérico en vez de dar 400—, con los `slomo` sin calibrar
  listados y deshabilitados); `Avisos.tsx`; `FichaArchivo.tsx`; y, bajo el
  reproductor y las fotos, `Metricas.tsx` («Con este archivo»). La procedencia
  va al lado del fps en la ficha, en la cabecera del trabajo y en la fila de la
  lista.
- Ninguna frase de aviso se compone en la pantalla: `fps_aviso` y `fps_note`
  viajan tal cual los escribe el motor.

## Probado

Backend de esta sesión en el 8765, con `curl` directo.

**`~/Desktop/20260907_170638.mp4` con `s22ultra-video-fhd30-cable`** (265
cuadros, 17,3 s):

| | |
|---|---|
| la ficha aparece | con `detectando_pose`, **~4,8 s antes** del `listo`, con `resumen` en `null` |
| ficha | h264 · 1080×2320 · rot 90° · 265 cuadros · 8,834 s (repr. 8,969 s) |
| fps | **29,998 efectivo · 29,436 bruto** · `sin_verificar` |
| tasa variable | **no** — ratio 1,000, bruto 6,044, umbral 1,10 |
| primer delta | **0,201478 s**, con su `fps_note` completa |
| eventos | 111 / 141 / 147 / 219 |

**`~/Desktop/cortado.mp4` con "No sé"** (`desconocido-video`, 4,2 s): ficha a
los ~3 s del final; 76 cuadros, 2,533 s, 29,999 fps, primer delta 0,0333 s,
`fps_note` en `null`. Eventos 7 / 39 / 44.

**Las 12 métricas: 7 con número y 5 con razón** en los dos clips — con el
`fps_min` tolerante del encargo 10 (`e2204ee`) ya commiteado; antes de ese
commit las 12 estaban en `null`. En `cortado.mp4`: pelvis sway top 0,8 cm ·
sway impacto 7,6 · lift top −4,2 · tórax sway 1,7 · lift −5,3 · cabeza sway
4,7 · lift −5,1, todas con su banda de ±1 cuadro. Sin número: las cuatro de
tiempo (`fps_min` 120 y 60 contra 29,999) y `pelvis_thrust_top_cm` por vista.
**Ningún `judgment_allowed` verdadero.**

Los 400 contra el `capture-paths.yaml` real: `camino de captura desconocido:
'iphone-que-no-tengo'. Los que hay: desconocido-video,
s22ultra-video-fhd60-cable, s22ultra-video-fhd30-cable` — y no queda carpeta.
`GET /api/datos`: 10 filas, 4182 bytes, 11 ms (lee además los 10
`capture.json`).

Suites: **261 en verde** en el motor, 39 s, con el trabajo sin commitear del 07
adentro (que sigue creciendo: eran 260 media hora antes);
`tests/test_service.py` pasa de **47 a 55**. Arnés: **4**.
`cd web && pnpm lint && pnpm build`, limpios.

Los 8 tests nuevos: camino declarado hasta `trabajo.json` y `capture.json`;
default genérico; 400 con la lista; 400 del `slomo` con la frase del gate
comparada literal; **la ficha con la pose frenada a mitad** (estimador falso
bloqueado en el primer cuadro por un `Event`, no por un `sleep`), y que no
cambia al terminar; la ficha del clip con el primer delta de arranque (efectivo
30,0 contra bruto 28,8, ratio bruto sobre el umbral); la fila con camino y
procedencia; y el `analysis.json` servido con las 12 métricas — o valor con
unidad y banda, o `null_reason`, nunca las dos, y nunca juicio. Ese último usa
un estimador nuevo que devuelve el **swing sintético** de
`tests/helpers/synth_swing.py` cuadro a cuadro: con el estimador quieto no hay
repeticiones y no hay ninguna métrica con número que mirar.

## Queda abierto

- **No se probó por el proxy de `next dev`**, que es lo que pedía el prompt. No
  había ninguno corriendo y levantarlo es exactamente lo que prohíbe la regla de
  trabajo (la skill del encargo manda sobre el prompt). Todo se midió contra el
  backend en el 8765. Lo único que el proxy agrega y acá no se ejercitó es el
  límite de cuerpo de 2 GB de `web/next.config.ts`; el camino del archivo en sí
  es el mismo.
- **La pantalla no se abrió.** Sin verla, lo que más puede fallar: el ancho del
  selector con etiquetas largas, y que la ficha más los avisos empujen el
  reproductor demasiado abajo.
- **El 400 del `slomo` declarado sólo vive en tests**: los tres caminos del
  `capture-paths.yaml` del repo son `video`. En la pantalla esa opción no
  aparece hasta que exista uno.
- El bloque de métricas muestra la **primera** repetición y lo dice cuando hay
  más de una. En exploración hoy siempre hay una.
- `confidence` sigue en `null` en todo el registro de golf (Fase 3): la pantalla
  lo aguanta sin inventar nada, pero esa columna no existe.
- **El test en rojo que el informe del 10 le atribuye al 07 era de este
  encargo.** El octavo camino del fixture (`desconocido-video` en
  `tests/conftest.py`) lo agregué yo, porque la cola ahora resuelve contra el
  `data/` del test y no contra el del repo; `test_load_fixture` pasa de 7 a 8 en
  `b0b46c9`. No hay nada que hacer del lado del 07.
- Se mató el backend del 8765 (PID 52416, de las 12:07, con código anterior a
  este encargo) y quedó corriendo el de esta sesión.

## Para que pruebe Hernán

El backend de esta sesión ya está corriendo; el front hay que levantarlo:

```bash
cd web && pnpm dev
```

Si hiciera falta el backend de nuevo:

```bash
.venv/bin/python -m service
```

1. **El selector.** Arriba, al lado de la altura: «¿con qué se filmó?», con
   tres opciones — *No sé con qué se filmó*, y los dos del S22 (`video 60 fps ·
   sin cronómetro` y `video 30 fps · sin cronómetro`). Abajo del formulario, la
   línea que explica qué implica un camino sin cronómetro. Elegí uno, recargá:
   tiene que seguir elegido.
2. **La ficha mientras carga.** Subí `~/Desktop/cortado.mp4` eligiendo
   *Galaxy S22 Ultra · video 30 fps · sin cronómetro*. Antes de que termine la
   pose ya tiene que estar «El archivo», con `ya se leyó; la pose sigue` en
   azul: h264, 1080×2320, rot 90°, 76 cuadros, 2,533 s, 29,999 fps y, al lado
   del fps con el que se midió, **sin verificar** en ámbar.
3. **Los avisos arriba.** Cuando termina, arriba de la ficha y del reproductor,
   el recuadro ámbar con el aviso de exploración y la frase del camino
   declarado. En `cortado.mp4` no hay corrección de fps; para verla, subí
   `~/Desktop/20260907_170638.mp4` (el original de 9 s) con el mismo camino:
   ahí aparece la línea extra —*el fps que se usó no es el que sale de contar
   todos los deltas*— y la ficha muestra **29,998** con **bruto 29,436** y
   primer delta **201,5 ms**.
4. **«Con este archivo».** Abajo del reproductor y las fotos: 12 filas. Siete
   con número (las de cm, con su banda de ±1 cuadro debajo) y cinco en gris con
   la razón en ámbar: cuatro *fps_real 29,999 por debajo de fps_min 120* (o 60)
   y una *vista face_on no válida para esta métrica*. A la derecha de cada una,
   la letra chica: nivel, MDC, fps mínimo, vista y **descriptiva, no es juicio**.
5. **La lista.** Cada fila ahora dice el camino al lado de la fecha, y el fps
   con `(sin verificar)` pegado. Los trabajos viejos del 12/9 dicen camino
   `exploracion`: es lo que tienen escrito en su `capture.json`, no se
   recalcula nada.
6. **Un camino que no existe.** `curl -s -X PUT
   "http://127.0.0.1:8765/api/datos?filename=x.mp4&camino=no-existe" --data-binary
   @~/Desktop/cortado.mp4` tiene que dar 400 con la lista de los tres caminos.

## Preguntas para el orquestador

1. **Los `slomo` declarados en el selector: ¿deshabilitados o escondidos?** Hoy
   se listan deshabilitados con «— hace falta el cronómetro», para que se vea
   que existen y por qué no sirven. La alternativa es no mostrarlos. No hay
   ninguno en el YAML del repo todavía, así que la decisión no aprieta.
2. **¿El bloque de métricas queda arriba o abajo del reproductor?** Lo puse
   abajo de las fotos y arriba de las tablas de exploración: el reproductor
   sigue siendo el producto (ADR-014) y las métricas son lo que se mira después.
   Si «con este archivo» es la respuesta a *¿esto sirve?*, tal vez vaya arriba
   de todo, pegado a los avisos.
3. **¿Alguien recalcula los trabajos viejos?** Los cinco del 12/9 tienen
   `capture_path_id: exploracion` y `analysis.json` 1.0.0, y la pantalla los
   muestra tal cual —incluidos los 29,436 fps brutos de antes del encargo 04—.
   Está bien que no se toquen, pero conviene decidir si se borran o se quedan
   como muestrario de "así se veía antes".
4. **`pnpm dev` no estaba corriendo y no lo levanté** (regla de trabajo). Si
   querés que las sesiones puedan medir por el proxy, hace falta o que quede
   uno corriendo, o autorizarlo explícito en el prompt.
