# 32 — La máscara del sujeto: qué compra y qué cuesta, medido (experimento, no producto)

Para correr: `/encargo 32` en una sesión nueva, en paralelo con el 31. Leé
antes los informes del 29, 14 (§2, el +4,4 % residual) y 15 (§"Queda
abierto" 1: manos contra palo), y la auditoría del 16/9 §1 (eventos de manos
contra palo, 4–16 cuadros).

## Contexto

Hernán pregunta si conviene sacar el fondo del video, o quedarse con la
silueta del sujeto en vez de los palitos. La respuesta del orquestador, que
este encargo mide en vez de discutir: **para la pose, no** (el modelo se
entrenó con fondos; un recorte enmascarado está fuera de su distribución, y
lo medido dice que el error va por el bbox y la plausibilidad, no por la
entrada: `AGENTS.md` §Cosas que muerden). **Y el fondo es lo que usamos
para medir la deriva** (29): no se tira. Donde una máscara del sujeto sí
podría comprar algo, y hay que medirlo:

1. **El palo.** El error de eventos más grande medido es manos contra palo:
   4–16 cuadros. El motor mide manos porque no ve el palo. Una máscara de
   primer plano (persona + palo contra el fondo quieto, después de
   estabilizar con las homografías del 29) aísla el shaft como un componente
   fino y largo pegado a las manos. Si se puede ajustar una recta por cuadro,
   el top y el impacto **del palo** están al alcance (ESPECIFICACION 3.2,
   «geometría del shaft por evento», sin hacer).
2. **La escala.** El 14 dejó un +4,4 % residual porque la cadena arranca en
   el tobillo y la estatura en el piso, y la «cabeza» de Halpe es la cara,
   no la coronilla. La extensión vertical de la máscara en el cuadro más
   extendido da coronilla y suela.
3. **Etiquetas.** Para medir el error de eventos contra el palo (la ronda
   R8) hacen falta etiquetas humanas a 240 fps; una máscara del palo por
   cuadro las abarata.

Lo que no compra: ángulos articulares (una silueta no tiene articulaciones)
ni una vista «linda» (invariante 10: se dibuja desde datos; una capa de
silueta sería eso, una capa, y viene después si sirve).

Leer: `kinelab/tools/camera_drift.py` (cómo estabiliza: la homografía por
cuadro y la máscara del sujeto), `kinelab/perception/video.py`
(`iter_frames`), `kinelab/perception/posestore.py` (`load_pose`),
`banco/README.md` o los scripts de `banco/` (la forma de un script de
medición), `DECISIONES.md` ADR-010 y ADR-015, `HERENCIA.md` §Prohibido (el
centro de pala extrapolado del prototipo anterior: por qué no se estima).

## Encargo

Todo en `banco/mascara_sujeto.py` (script de medición, no módulo del motor)
y un informe con números. Sin dependencias nuevas: OpenCV 4.14 con
`createBackgroundSubtractorMOG2/KNN`, morfología y `fitLine` alcanza.

1. **Máscara clásica sobre `cortado3-lento`** (2977 cuadros, 240 fps, la
   toma de `data/sessions/…/take-01`): estabilizar cada cuadro contra la
   referencia con la homografía del 29 (reusá sus funciones, no las copies),
   modelo de fondo por mediana temporal de los cuadros donde el sujeto no
   está (la escena antes del address y después del finish, o los bordes
   fuera del bbox), y primer plano = diferencia contra el fondo, umbral y
   morfología. Reportá: cobertura de la máscara sobre el bbox de la pose por
   cuadro (mediana y mínimo), agujeros, y tiempo por cuadro.
2. **El palo.** En 20 cuadros de la rep 1 —10 alrededor del top (1284) y 10
   alrededor del impacto (1364)— buscá en la máscara el componente fino y
   largo conectado a la región de las muñecas, ajustá una recta (`fitLine`
   o PCA sobre sus píxeles) y reportá ángulo y largo en px por cuadro. Contra
   **etiquetas a ojo**: extraé los mismos 20 cuadros como PNG, marcá vos los
   dos extremos del shaft mirándolos (`Read` de la imagen; procedencia
   `estimacion`, hecha por la sesión) y dá el error en grados y en px, con
   su mediana y su máximo. Si el shaft no se separa del fondo o del cuerpo,
   decilo con las imágenes y en qué cuadros.
3. **La escala.** En el cuadro de `quality.scale_px` de esa toma (1594) y en
   dos vecinos: extensión vertical de la máscara (coronilla a suela) contra
   la cadena del 14 (783,9 px). Reportá el cociente y si coincide con el
   +4,4 % que el 14 dejó como residual geométrico.
4. **Robustez, dos clips más**: `data/incoming/vid1.mp4` (UHD 60, deriva
   +119 px según el 29) y `~/Desktop/cortado.mp4` (30 fps, 76 cuadros). Los
   mismos indicadores del punto 1; para el palo, 5 cuadros alrededor del
   impacto de cada uno.
5. **Sólo si lo clásico no separa el palo**: una tabla de modelos de
   segmentación con las tres preguntas de ADR-010 por fila (código, pesos,
   datos de entrenamiento), sin instalar nada: U²-Net vía `rembg`, MediaPipe
   Selfie/Multiclass, RTMDet-Ins (COCO), SAM 2, y los que descartan
   (YOLO-seg es AGPL; Human-Art es CC BY-NC). Con una línea de cuál correría
   en CoreML/onnxruntime y cuál sólo en `truth/` (torch).
6. Cerrá con tres líneas: qué compra la máscara (con números), qué cuesta,
   y si vale un encargo de producto (el shaft como evento) o no.

NO: no tocar `kinelab/`, `sports/`, `service/`, `web/`, `truth/`; no correr
pose sobre cuadros enmascarados; no instalar nada; no estimar el palo a
partir del antebrazo ni de un factor (HERENCIA §Prohibido); no compensar la
deriva en ninguna métrica; no llamar «medición» a las etiquetas a ojo.

## Cómo se prueba

El script corre de punta a punta con un comando por clip y deja en
`data/incoming/<clip>.kinelab/mascara/` las máscaras de los cuadros
etiquetados, la recta ajustada dibujada y las etiquetas a ojo en un JSON. El
informe lleva las tablas de los puntos 1–4 con el comando de cada una.
`.venv/bin/pytest` sin cambios (381). Para Hernán: nada de front; abrir las
imágenes de los 20 cuadros con la recta dibujada, y decir si el palo que ve
él es el que ajustó el script.

## En paralelo

El 31 edita `sports/golf/events.py`, `kinelab/events/`, `kinelab/analysis.py`,
`kinelab/explore.py`, `kinelab/ingest/gate.py`, `DECISIONES.md`, `web/` y
`tests/test_fase2.py`, `tests/test_eventos_senal.py`. Vos no importás nada de
eso: usás `kinelab.tools.camera_drift` y `kinelab.perception` (video,
posestore), que nadie edita. Tus archivos: `banco/mascara_sujeto.py`, lo que
escribas bajo `data/incoming/*/` (ignorado por git), `ESTADO.md` (tu sección)
y tu informe.
