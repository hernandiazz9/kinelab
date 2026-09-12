# kinelab

Motor de medición del movimiento humano a partir de video de celular. Para un
entrenador, en su Mac, sin nube. Agnóstico al deporte: el motor no conoce la
palabra "golf". Primer deporte: golf. Segundo: pádel, sólo cuando golf tenga
números de error medidos.

> `kinelab` es nombre provisorio. Cambiarlo es un `sed`; no hace falta decidirlo hoy.

## Leé primero, en este orden

1. `CONTEXTO.md` — vocabulario y reglas invariantes. Antes de tocar nada.
2. `DECISIONES.md` — lo que ya está decidido y por qué. Se reabre con una
   decisión nueva, nunca con un rodeo.
3. `ESPECIFICACION.md` — las fases, en orden fijo, con su criterio de aceptación.
4. `CONTRATO.md` — el contrato de datos. Es el artefacto central del proyecto.
5. `CAPTURA.md` — el protocolo de filmación y el gate de ingesta.
6. `HERENCIA.md` — qué se porta de los dos prototipos anteriores, archivo por
   archivo, y qué está prohibido portar. Incluye el cementerio.

Esos seis son la fuente de verdad. Este archivo no los repite ni los resume.

Después de los seis, `ESTADO.md`: dice dónde quedó el trabajo al cerrar la
última sesión y qué está escrito pero sin probar. Se actualiza al cerrar cada
sesión.

## Acuerdo de trabajo

- **Una fase por vez, en el orden que fija la spec.** No se adelanta trabajo
  de una fase posterior. Los dos prototipos anteriores construyeron pantallas
  enteras sobre métricas que nunca se validaron; esta regla existe para eso.
- **Material antes que código.** Si una tarea necesita un clip real y no lo hay,
  la tarea pasa a ser escribir la herramienta para conseguirlo, y parar.
- **Ninguna métrica entra sin sus seis cosas:** cómo se calcula, unidad, vistas
  desde las que es válida, fps mínimo, MDC medido en el arnés, y un test con un
  ángulo no trivial. Sin las seis no existe. Ver `CONTRATO.md` §Registro.
- **Sin dependencias fuera del stack de `DECISIONES.md` sin preguntar.** Y antes
  de proponer una, leer ADR-010: código, pesos y datos de entrenamiento son
  tres licencias distintas.
- **Commit al cerrar cada bloque de trabajo.** La mitad de `padel-coach` —
  incluidas sus dos mejores correcciones — quedó sin commitear.
- **Cuando algo de estos documentos resulte inviable, avisar. No improvisar.**
  Un apartamiento se anota en `CONTRATO.md` §Desviaciones con fecha y razón.
- Prosa de documentos, comentarios y mensajes de commit en español;
  identificadores de código en inglés.

## Sesiones: orquestador y encargos

El trabajo se reparte en sesiones de Claude Code. Una **orquestadora**
(`/orquestador`) lee los informes, mantiene el backlog en `docs/PLAN.md` y
escribe encargos numerados en `docs/prompts/NN-<slug>.md`. Las sesiones de
**trabajo** (`/encargo NN`) ejecutan uno, commitean y dejan un informe corto en
`docs/informes/`. Las reglas fijas de cada rol viven en `.claude/skills/`; los
prompts sólo llevan lo específico de cada encargo.

## Estructura del repo

```
kinelab/          paquete Python del motor — puro, sin UI, sin servidor
  ingest/         gate de entrada, capture.json
  perception/     pose, tracking de un sujeto, relleno de huecos, posestore
  events/         address, top, impact, segmentación de repeticiones
  metrics/        registro declarativo + implementaciones por nivel
  contract/       schema.json + validador
  tools/          fps_truth, calibración de cámara
sports/golf/      config del deporte: gestos, vistas, eventos, métricas permitidas, gates
truth/            arnés de verdad — con SU PROPIO entorno virtual
banco/            scripts de medición de rendimiento (heredados, ver HERENCIA)
service/          FastAPI local — Fase 4
web/              Next.js — Fase 4
data/             ignorado por git salvo schemas y ejemplos
docs/
tests/
```

## Comandos

```bash
# motor
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q                         # tests del motor
.venv/bin/python -m kinelab.tools.fps_truth clip.mov --duracion-real 20.00

# arnés de verdad (entorno separado, a propósito)
cd truth && python3.12 -m venv .venv && .venv/bin/pip install -e .
cd truth && .venv/bin/pytest -q
```

Los comandos de `service/` y `web/` se agregan en la Fase 4.

## Cosas que muerden

Todas medidas, ninguna teórica. La fuente de cada una está en `HERENCIA.md`
§Cementerio.

- **El fps del archivo miente.** `r_frame_rate`, `avg_frame_rate` y el
  histograma de deltas de PTS no distinguen un clip de 240 fps estirado a 30
  de uno remuestreado a 30. Lo único que los separa es contar cuadros
  decodificados contra una duración real conocida. La tasa real es
  configuración del camino de captura, calibrada con un cronómetro filmado —
  nunca inferida del contenedor.
- **CoreML calcula en fp16 en silencio.** Entrada sin normalizar → salida toda
  `NaN`, sin error. Aserción de preprocesado y chequeo de `NaN` a la salida,
  siempre.
- **CoreML no es bit-idéntico a CPU** (0,23–0,32 px de media, hasta 1 px).
  "Determinista" significa "para un proveedor, checkpoint y versión dados", y
  los tres van dentro de `pose.npz`.
- **Más hilos es más lento.** onnxruntime satura en 5 hilos en el M3 Pro y
  empeora 15–35% de 6 a 11. `intra_op_num_threads=5`, siempre.
- **`rtmlib` descarga pesos en runtime por defecto**, y sus detectores por
  defecto están entrenados en Human-Art (CC BY-NC-SA 4.0). Pesos fijados por
  hash en local; detector entrenado en COCO.
- **ffmpeg 9 eliminó `-vsync`:** es `-fps_mode passthrough`. Y nunca `-r` para
  "arreglar" el fps: tira cuadros. `setpts` los conserva.
- **El punto `hip` de Halpe26 es predicho por la red**, no es un centro
  articular. Sirve como señal relativa de tronco; no alimenta nada que pretenda
  validez clínica.
- **`NaN` no es JSON.** Python lo escribe sin quejarse y `JSON.parse` lo
  rechaza. Se convierte a `null` en la frontera, en un solo lugar.
- **Un modelo más grande no arregla los ángulos imposibles.** Medido: el tamaño
  del sujeto mueve el codo −6/+9°; un bbox mal encuadrado lo mueve
  −14,5/+13,6°; tres modelos discrepan 13,6° entre sí en el mismo cuadro. El
  esfuerzo va a la calidad del bbox y al filtro de plausibilidad, no al
  checkpoint.
- **Address es el evento peor detectado del swing (31,7% de acierto)** y es el
  cero de todos los desplazamientos. Se define de forma determinista; nunca se
  detecta.
- **El wheel de OpenSim dice `universal2` y sus binarios son arm64.** Anda en
  el M3; rompe en una Mac Intel.
- **Mover el impacto dos cuadros a 60 fps cambia el codo hasta 25,6°.** Toda
  métrica anclada a un evento lleva la incertidumbre de ±1 cuadro propagada, o
  es ficción con decimales.
- **El proxy de `next dev` corta el cuerpo a 10 MiB y no avisa.** Next 16 trae
  `experimental.proxyClientMaxBodySize = 10mb`: un `.mp4` de 20 MB subido por
  un rewrite llegó truncado a 10 MiB y la conexión quedó colgada, sin error en
  ningún lado. Está subido a 2 GB en `web/next.config.ts`; si un video "carga
  al 100 % y no pasa nada", mirar ahí primero.
