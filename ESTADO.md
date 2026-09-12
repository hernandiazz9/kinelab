# Estado del trabajo

Dónde quedó el repo al cerrar la última sesión. Se lee **después** de los seis
documentos de `AGENTS.md` y se actualiza al cerrar cada sesión.

## 12 de septiembre de 2026 — cuarta sesión: interfaz de exploración (`web/` + `/api/datos`)

Una pantalla: subir un video → el `overlay.mp4` con los palitos en un
reproductor con cámara lenta, cuadro a cuadro y zoom, las fotos por evento y
toda la data en tablas. Prompt de origen: `docs/prompts/interfaz-exploracion.md`.
Los comandos y qué esperar están en `README.md`.

### Qué existe

| Pieza | Dónde | Probado con |
|---|---|---|
| Cola de exploración: un trabajo por vez, estimador CoreML creado una vez y compartido, `trabajo.json` por trabajo en `data/exploracion/<id>/` (sobrevive al reinicio) | `service/exploracion.py` | 7 tests nuevos en `tests/test_service.py` con estimador falso (173 en total, ~40 s) |
| `PUT /api/datos?filename=&altura_m=` (cuerpo crudo → 202 con id) · `GET /api/datos/{id}` (estado, progreso, `datos-eventos.json` cuando está listo, URLs de archivos) · `GET /api/datos/{id}/archivos/{nombre}` (lista blanca; `?descargar=true` → attachment) | `service/app.py` | TestClient + estimador real con `~/Desktop/cortado.mp4`: listo en 9,6 s |
| `Range`/206 para arrastrar el video | `FileResponse` de Starlette 1.6.0 lo hace solo (verificado: 206, `Content-Range`, bytes correctos). **No se portó** el `route.ts` de `padel-coach` | test + curl |
| `explore()` avisa la etapa (`stage`) y el progreso también al dibujar; el overlay sale con `-g 12` (GOP corto: retroceder un cuadro no decodifica 250) | `kinelab/explore.py` | test de explore + corrida real |
| App Next.js 16.3.4 (`--webpack`, ADR-015), React 19, Tailwind 4, pnpm. Una página. Proxy `/api/*` → 8765 (`KINELAB_API` para cambiarlo), `proxyTimeout` 600 s | `web/` | `pnpm lint` y `pnpm build` limpios; el flujo entero por el proxy con `curl` (202, etapas, 206 byte a byte igual al backend, CSV, attachment, PNGs) |
| Reproductor propio: `<video>` + `requestVideoFrameCallback`, seek a `(n + 0,5) / fps`, verificación del cuadro llegado por `mediaTime` (aviso si no coincide), 0,1×–1×, ◀ ▶ y flechas (shift = 10), marcas de evento en la línea de tiempo, **zoom 1–4× con la rueda o botones y paneo arrastrando** (pedido de Hernán durante la sesión) | `web/src/components/Reproductor.tsx` | **nunca abierto en un navegador** |
| Subida con progreso (XHR), sondeo cada 0,5 s, el último trabajo vuelve al recargar (localStorage) | `web/src/app/page.tsx`, `lib/api.ts` | idem |
| Tabla por evento (codos, rodillas, caderas, hombros, líneas, tronco, brazos, altura de manos, pelvis/tórax/cabeza/manos vs address en cm y %, velocidades, rotaciones aparentes), duraciones y tempo, picos, diferencias vs address, TODAS las columnas por evento, calidad del motor | `web/src/components/TablaEventos.tsx` | idem |
| Tabla por cuadro entera (118 columnas), virtualizada, filtro de columnas, clic en fila → cuadro, fila actual resaltada, descargas de CSV/JSON/analysis/capture/overlay | `web/src/components/TablaCuadros.tsx` | idem |

### Reproductor: lo evaluado y por qué no hay librería

Datos del registro de npm (`pnpm view`, 12/9/2026):

| Candidata | Versión | Licencia | Peso (unpacked) | Cuadro a cuadro | H.264 en Chrome |
|---|---|---|---|---|---|
| Video.js | 8.24.0 | Apache-2.0 | 18 MB | no; seek a `(n+0,5)/fps` a mano | sí |
| Plyr | 3.8.4 | MIT | 5,3 MB | no; idem | sí |
| Vidstack / `@vidstack/react` | 0.6.15 (tag `latest`) | MIT | 2 MB / 125 kB | no; idem | sí |
| react-player | 3.4.0 | MIT | 40 kB | no; idem (envuelve `<video>`) | sí |
| Propio: `<video>` + `requestVideoFrameCallback` | — | — | 0 | seek a `(n+0,5)/fps` **con verificación del cuadro presentado** | sí |

Ninguna da cuadro a cuadro real: el navegador no tiene API para eso, todas
terminan en un seek, y la única forma de saber **qué cuadro se mostró** es el
`mediaTime` de `requestVideoFrameCallback`, que ninguna expone. Como ADR-014
ya fija ese enfoque para el visor definitivo, se escribió propio: cero
dependencias y nada que tirar después. Supuestos de Chrome: `playbackRate`
0,1 anda (mínimo 0,0625); Firefox lo limita a 0,25 y no tenía rVFC hasta
hace poco (hay caída a `timeupdate`, un cuadro desfasado posible).

### Desviación anotada: invariante 10 de `CONTEXTO.md`

Esta pantalla reproduce `overlay.mp4` **pre-renderizado como única vista**, lo
que la invariante 10 prohíbe ("se dibuja desde datos, en vivo, sobre el
master"). Es un paso provisorio a pedido, para mirar el resultado del motor
hoy. El visor definitivo (Fase 4.4) dibuja el esqueleto desde `pose.npz` en un
canvas dentro del mismo div que se transforma para el zoom (`marcoRef` en
`Reproductor.tsx`), sobre `master.mp4`; el reproductor de acá es la base de
eso, no un segundo visor. Mientras dure: no se puede apagar el dibujo, ni
ampliarlo sin pixelar, ni cambiar un evento sin volver a renderizar.

### Lo que falta o no está probado

- **El front nunca se vio en un navegador** (regla de trabajo): lo prueba
  Hernán con la lista de abajo. Lo que más puede fallar sin haberlo visto: el
  tamaño del recuadro del video (vertical 1080×2320: alto 78 % de la ventana),
  el aviso "pedí el cuadro n y mostró m" si el `mediaTime` no cae en `n/fps`,
  y el ancho de la tabla de 118 columnas.
- Un trabajo por vez, sin cancelación, sin borrar trabajos viejos:
  `data/exploracion/` crece ~20 MB por clip de 3 s (las tres fotos PNG pesan
  3,7 MB cada una; se podrían escribir como JPEG).
- El estimador se carga con el primer trabajo (3–4 s); no se precalienta al
  arrancar el servidor.
- La página vieja del gate sigue en `http://127.0.0.1:8765/` y no se usa.
- Al cerrar el servidor con Ctrl-C puede aparecer `recursive_mutex lock
  failed` de CoreML: es el teardown al salir del intérprete, ya con todo
  escrito; no afecta a los trabajos.

### Para que pruebes vos

0. En esta Mac el **8765 tiene un `python -m service` viejo** (PID 9363, de
   las 15:59, anterior a estos cambios) y el **3000 lo ocupa `work-hunter/web`**.
   Matá el viejo (`kill 9363` o `lsof -nP -iTCP:8765`) y levantá el nuevo:
   `.venv/bin/python -m service`. Después `cd web && pnpm install && pnpm dev`:
   si el 3000 está ocupado Next avisa y usa el 3001.
1. Subir `~/Desktop/cortado.mp4` con altura 1,75. Debería verse: barra de
   subida → "cargando el modelo" → "detectando la pose 40 / 76" →
   "dibujando 30 / 76" → resultado en ~10 s. Aviso amarillo arriba con "el gate
   diría: hay más de una persona en cuadro (59 %)".
2. Reproductor: el video vertical con los palitos; eventos en la línea de
   tiempo: address 7, top 39, impacto 44. Probar ◀ ▶ y las flechas (el
   contador y la imagen tienen que cambiar juntos, sin aviso amarillo),
   shift + flecha (10 cuadros), espacio y clic en el video (reproducir /
   pausar), velocidad 0,1× y 0,25×, arrastrar la línea de tiempo, los botones
   "ir a address / top / impacto", **zoom con la rueda sobre el video y con
   + − 1:1, y mover con arrastre**.
3. Fotos: clic en la de impacto → el reproductor salta al cuadro 44 y la
   página sube.
4. Tablas: en address codo izq/der 168° / 171°, rodillas 176° / 180°; tempo
   6,4 : 1 (backswing 1066,7 ms, downswing 166,7 ms). Filtrar columnas por
   "codo"; clic en una fila → ese cuadro; "ir al cuadro actual"; las cinco
   descargas.
5. Recargar la página: vuelve el último resultado sin subir de nuevo.
6. Subir un archivo que no es video: tiene que mostrar "No salió. …" con el
   error del motor, no colgarse.

### Siguiente

Con lo que digas del front: ajustes. Después, lo pendiente de las sesiones
anteriores (abajo): clips reales por percepción y análisis, umbral de
encuadre, calibración de cámara, y la Fase 4 propiamente dicha (`master.mp4`,
visor desde `pose.npz` sobre este reproductor, corrección de eventos).

---

## 12 de septiembre de 2026 — tercera sesión: Fases 1, 2 y 3 construidas sin material real

### Desviación de proceso, anotada

A pedido explícito del entrenador ("avanzá full en las fases"), se construyó
código de las Fases 1, 2 y 3 **sin clips reales que hayan pasado el gate**, contra
lo que fija `ESPECIFICACION.md` ("una fase por vez", "material antes que
código"). Se hizo con datos sintéticos y con un clip heredado de pádel para
probar la cadena de percepción. Todo criterio de aceptación que necesita
material real sigue **abierto** y está listado abajo. Regla de trabajo:
el agente trabaja normal (pruebas de funcionalidad con corridas reales, tests,
subagentes y workflows cuando convengan); lo único que NO hace es levantar el
front y verlo en el navegador con capturas, salvo pedido explícito. El front
lo prueba el entrenador.

### Commits de esta sesión

- `8ede11a` Fase 0 de agente cerrada (94 tests, fps_truth, gate, checklist).
- `e1b4b89` `service/`: página HTML local para pasar clips por el gate
  (adelanto de 4.3 a pedido). `python -m service` → http://127.0.0.1:8765.
- `ed2b865` Fase 1: `kinelab/perception/` completo, `python -m kinelab.perception`.
- `5f7efaa` Fase 2: `kinelab/events/`, `kinelab/contract/`,
  `kinelab/metrics/registry.py`, `sports/golf/events.py`, `python -m kinelab analyze|adjust`.
- Fase 3: `kinelab/metrics/` (sextuplo, ±1 cuadro, repetibilidad, ganancia),
  `sports/golf/metrics.py` + `sports/golf/mdc.yaml`, `truth/` (arnés con su venv),
  `truth/reports/mdc-2026-09-12.json`.

### Qué hay, qué prueba cada cosa

| Pieza | Comando | Probado con |
|---|---|---|
| Verdad del fps | `.venv/bin/python -m kinelab.tools.fps_truth CLIP --duracion-real S --nominal 120` | clips sintéticos (tests) |
| Gate de ingesta | `.venv/bin/python -m kinelab.ingest CLIP --atleta a --gesto driver --vista face_on --camino ID` | clips sintéticos (tests) |
| Página del gate | `.venv/bin/python -m service` (opcional `--data DIR --port N`) | TestClient (34 tests); **nunca abierta en un navegador** |
| Modelos | `.venv/bin/python -m kinelab.perception.models [--download]` | los dos verifican por hash en `models/` |
| Percepción | `.venv/bin/python -m kinelab.perception TAKE_DIR [--cpu] [--overwrite]` | estimador falso (tests) + **una corrida real** sobre `padel-coach/samples/demo_h264.mp4`: 230 cuadros en 10 s con CoreML, 82 % de detección, gate rechaza por varias personas (correcto) |
| Análisis | `.venv/bin/python -m kinelab analyze TAKE_DIR` | swing sintético (`tests/helpers/synth_swing.py`) |
| Corrección manual | `.venv/bin/python -m kinelab adjust TAKE_DIR --rep 1 --event top --frame F` | sintético; round-trip y colisión |
| Arnés de verdad | `cd truth && .venv/bin/python -m kinelab_truth` (12 s) | escribe `sports/golf/mdc.yaml` y `truth/reports/`; tests: `cd truth && .venv/bin/pytest -q` (4) |
| Calibrar la cámara real | `cd truth && .venv/bin/python -m kinelab_truth.calibrate FOTOS --cols 9 --rows 6 --square-mm 25 --id iphone17pro-1080p120 --out cameras/iphone17pro-1080p120.yaml` | sin correr: necesita fotos de un tablero con el teléfono |
| Modo exploración | `.venv/bin/python -m kinelab datos VIDEO --altura-m 1.75` | probado con dos clips reales de Hernán (WhatsApp 29 fps y un vertical de iPhone 30 fps): overlay, fotos por evento, CSV por cuadro y JSON por evento |
| Suite | `.venv/bin/pytest -q` | 166 tests en verde, ~9 s |

### Decisiones tomadas al codificar (no estaban en los documentos)

- **Señal maestra del swing: el centro de las dos muñecas** (las manos van
  juntas en el grip): independiente de la lateralidad, más estable que una
  muñeca sola. `sports/golf/events.py` lo documenta.
- **Impact** = cuadro más cercano a la posición de las manos en address, dentro
  de ±0,25 s del pico de velocidad de las manos (el palo vuelve a la pelota).
  **Top** = último cambio de signo de la velocidad de las manos proyectada
  sobre el eje principal de la trayectoria address→impact. **Address** =
  último cuadro de la ventana de quietud (< 0,15 alturas/s durante ≥ 0,5 s)
  antes del pico, refinado hacia atrás hasta donde la velocidad deja de bajar.
  Todos los umbrales son `estimacion` y viven en `GolfEventParams`.
- Ventana de agudeza de la segmentación en golf: 3 s (con 1 s, heredado de
  pádel, un swing continuo de ~2 s parece "sostenido" y se descarta).
- `pose.npz` guarda la pose CRUDA del sujeto elegido; relleno de huecos,
  filtrado y máscaras son derivados que se aplican al leer.
- `rotation_deg` horario; `iter_frames` no rota dos veces si OpenCV ya aplicó
  la rotación de metadatos (regla por tamaño y `CAP_PROP_ORIENTATION_AUTO`).
- Umbral de encuadre `body_height_frac_min = None` hasta medirlo: el chequeo
  se reporta `passed: null` con razón "umbral sin medir".
- Modelos: `rtmpose-m-halpe26` (OpenMMLab, sha256 `26f3a19e…`) y `yolox_m`
  0.1.1rc0 de Megvii entrenado en COCO (sha256 `21ff6cfd…`). Los YOLOX de
  Human-Art que rtmlib trae por defecto quedan fuera (ADR-010). **Pendiente de
  licencia:** los datos de entrenamiento "body7" de RTMPose incluyen Halpe;
  su licencia figura como `sin_verificar` en `models.py`.
- OpenCV: `opencv-python` y `opencv-contrib-python` fijados a 4.14.0.94 los
  dos (rtmlib exige ambos; instalan el mismo `cv2`).
- Medido: CoreML compila la sesión en 3,6 s y después tarda 4,7 ms por
  recorte (CPU: 15 ms). Con CoreML, una entrada sin normalizar da scores todos
  NaN: por eso `estimator.py` asierta el rango de entrada y chequea NaN.
- ffmpeg 9: aun con `-fps_mode passthrough`, redondea los PTS al time base del
  encoder (1/fps); `-enc_time_base 1/90000` los conserva. Importa para la
  Fase 4 (master.mp4) y para cualquier retiming.
- **Métricas en cm** necesitan la altura declarada del atleta
  (`data/athletes/<slug>.yaml` con `altura_m`, o `--altura-m`); sin ella
  quedan en `null` con razón. La conversión usa la altura del cuerpo en px del
  cuadro de address.
- **Tabla del arnés (nivel 0, cámara `sin_verificar`, ruido 0,6 % de la altura
  del cuerpo, 16 semillas):** duraciones MDC ≈ 13 ms a 240 fps y `fps_min`
  120; sway/lift/thrust MDC 2,5–4,5 cm por repetición; sway sólo `face_on`,
  thrust sólo `down_the_line`, lifts ambas; **las deltas de flexión de rodilla
  mueren** (declaradas en `face_on`, la flexión ocurre en profundidad). Las
  tolerancias de sesgo (2 cm, 25 ms, 5°) y de MDC (5 cm, 30 ms, 15°) son
  estimaciones declaradas en `truth/kinelab_truth/harness.py`. El arnés sólo
  puede quitar vistas de las que el deporte declara, nunca agregar.
- La ganancia de velocidad angular (pelvis→tórax→brazo) se calcula desde el
  giro aparente de las líneas de cadera/hombros en el plano de imagen; NO está
  validada por el arnés (no es una métrica registrada) y desde `face_on` la
  rotación axial se ve como escorzo, no como giro: sospechosa. Queda en
  `summary.gain` como descriptiva hasta que el arnés la evalúe.

### Lo que sólo material real puede cerrar (abierto)

- Fase 0: filmar cronómetro y sesión; `capture-paths.yaml` sigue vacío.
- Fase 1: umbral de encuadre medido; que la convención de rotación dé 90 en
  un `.MOV` real en vertical; `creation_time` de QuickTime; el determinismo
  CoreML sobre un clip de golf; reporte SynthPose vs RTMPose (1.5, no hecho:
  SynthPose necesita torch, fuera de ADR-015 salvo en `truth/`).
- Fase 2: error contra GolfDB (2.5): la herramienta existe
  (`kinelab.tools.golfdb_eval`), el dataset no está descargado; todos los
  parámetros de `GolfEventParams` y `GOLF_SEGMENTATION` son estimaciones.
- La página `service/` no se abrió en un navegador: **probarla vos** (abajo).
- Fase 3: intrínsecos reales del teléfono (tablero); nivel 1 de validación
  (movimiento humano real) y SynthPose; oclusión y desenfoque no están en el
  barrido; mutation manual de la invariante 15 no hecha sistemáticamente.

### Para que pruebes vos (cuando quieras)

1. `.venv/bin/python -m service` y abrir http://127.0.0.1:8765. Sección 1:
   subir cualquier `.mov`/`.mp4` y ver la tabla de fps; sección 2 se habilita
   cuando `data/capture-paths.yaml` tenga un camino.
2. Con un clip de golf real ingestado (`gate: OK`):
   `.venv/bin/python -m kinelab.perception data/sessions/.../take-01` y después
   `.venv/bin/python -m kinelab analyze data/sessions/.../take-01`. Mirar
   `analysis.json`: `events[]` por repetición y `quality.verdict`.
3. Si un evento está mal: `python -m kinelab adjust TAKE --rep N --event top --frame F`.

### Entorno verificado

`python3.12` = 3.12.14 · ffmpeg / ffprobe 9.0.1 · onnxruntime 1.30.0
(CoreMLExecutionProvider) · rtmlib 0.0.16 · OpenCV 4.14.0.94 · numpy 2.5.3 ·
scipy 1.18.1 · pydantic 2.13.5 · fastapi 0.141.1 · Mac Apple M3 Pro.

### Siguiente

**Interfaz de exploración** (pedido de Hernán): una pantalla con un botón para
subir un video, que corra `python -m kinelab datos` y muestre el `overlay.mp4`
con un reproductor con cámara lenta y cuadro a cuadro, las fotos por evento y
toda la data en tablas. El prompt completo para esa sesión está en
`docs/prompts/interfaz-exploracion.md`. La página actual de `service/` no le
sirve y se reemplaza por una app Next.js en `web/`.

Con clips reales: pasarlos por percepción y análisis, medir el umbral de
encuadre, calibrar la cámara con tablero y re-correr el arnés. Sin clips: Fase 4
(servicio con jobs, `master.mp4` H.264 CFR, visor desde datos sobre
`service/`), y evaluar la ganancia en el arnés.

---

## Mensaje de arranque para la próxima sesión

> Estás en `/Users/heralc/Desktop/HDDev/kinelab`. Leé `AGENTS.md`, `CONTEXTO.md`,
> `DECISIONES.md`, `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`,
> `HERENCIA.md` y por último `ESTADO.md`. Regla de trabajo: trabajá normal
> (probá la funcionalidad, usá subagentes y workflows si convienen); lo único
> que no hacés es levantar el front y verlo en el navegador con capturas,
> salvo que yo lo pida: el front lo pruebo yo. La interfaz de exploración
> (`web/` + `service/`) está hecha y sin ver en un navegador: empezá por lo que
> yo te diga de ella. Si hay clips reales en `data/sessions/`, pasalos por
> percepción y análisis y decime qué sale. Commit al cerrar cada bloque;
> `ESTADO.md` al cerrar.
