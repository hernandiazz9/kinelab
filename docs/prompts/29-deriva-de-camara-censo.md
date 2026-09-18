# 29 — La deriva de la cámara, medida: herramienta y censo de los ocho clips reales

Para correr: `/encargo 29` en una sesión nueva, **solo, después de que
cierren el 30 y el 17** (los dos editan `kinelab/perception/`, que vos
importás para leer material). Leé antes
`docs/informes/2026-09-16-auditoria-primer-juicio.md` §1 («La cámara», «Lo
que no lo detecta») y `docs/informes/auditoria-2026-09-16/reproduccion.md`.

## Contexto

La auditoría del 16/9 midió, con tres métodos independientes, que en
`cortado3-lento.mp4` la imagen se corre entre el address y el top o el
impacto: **+14 a +23 px en x en la repetición 1, −8 a −25 px en la 2**, y
unos 10 px en y. Eso entra derecho en los desplazamientos en cm, por encima
de su MDC (2,4–4,5 cm), y el motor no lo ve: `quality.camera_motion_px` da
1,35 porque `camera_motion_px` (`kinelab/perception/video.py:138`) es la
mediana del corrimiento entre muestras tomadas cada 120 cuadros reducidas a
320 px, que no ve una deriva lenta. Los tres métodos de la auditoría difieren
entre sí 3–6 px, y en la repetición 2 queda un residuo no rígido de 10–12 px.
No se sabe la causa (estabilización electrónica del modo Slow motion,
trípode, suelo): la sesión de validación la va a separar; **este encargo la
mide**, no la compensa (decisión del orquestador: nada de compensar dentro
de las métricas sin validación).

Leer: `kinelab/perception/video.py` (`open_capture`, `iter_frames`,
`rotate_frame`, `sample_gray`, `camera_motion_px`), `kinelab/perception/
posestore.py` (`load_pose`, qué trae `pose.npz`: `keypoints`, `bbox`,
`timestamps_s`), `kinelab/tools/interpolar.py` (cómo lee cuadros por índice
del motor respetando la edit list; el 05 lo midió), `kinelab/tools/
fps_truth.py` (la forma de un tool con CLI y `to_dict()`), `tests/
test_interpolar.py` (tests de un tool con clip sintético), `tests/conftest.py`,
`CONTEXTO.md` §piso de ruido e invariante 5.

## Qué existe ya

- OpenCV 4.14 con SIFT y ORB (`cv2.SIFT_create` disponible; verificado). Sin
  dependencias nuevas.
- Ocho clips reales con su `pose.npz` ya calculada: `data/incoming/
  {Cortado-lenta,cartado2-lenta,cortado3-lento,vid1,vid2,vid3}.mp4` con sus
  `<clip>.kinelab/` (cartado2 puede no tener: corré `datos` si falta), y
  `~/Desktop/cortado.mp4` y `~/Desktop/20260907_170638.mp4` con los suyos.
  Más la toma definitiva `data/sessions/hernan/2026-09-15/driver/face_on/
  take-01/` (cortado3, con `analysis.json` y sus eventos: address 1052, top
  1284, impacto 1364, follow_end 1978 en la rep 1; 2322, 2548, 2624 en la 2).
- Los rangos de la auditoría, por repetición y por eje, en `reproduccion.md`.

## Encargo

Una herramienta nueva, agnóstica al deporte: `kinelab/tools/camera_drift.py`.

```
python -m kinelab.tools.camera_drift VIDEO --pose POSE.npz [--cada 10] [--ref FRAME] [--out camera-drift.json]
```

1. **Método.** Para cada cuadro muestreado (cada `--cada`, en índices del
   motor), estimar el movimiento del **fondo** respecto del cuadro de
   referencia (`--ref`, default el primer cuadro con pose): puntos SIFT en las
   dos imágenes con el sujeto **enmascarado** (el `bbox` de `pose.npz`
   dilatado un 20 %, y también un margen alrededor del palo si el bbox no lo
   cubre: la caja de las muñecas al pico de velocidad), emparejamiento con
   ratio test, homografía por RANSAC. Del modelo, reportar el desplazamiento
   que induce en cuatro filas de la imagen: la de las caderas, la de los
   hombros, la de la cabeza y la de los pies del sujeto en el cuadro de
   referencia (keypoints de `pose.npz`), evaluado en la columna del sujeto.
   Y el residuo: mediana del error de reproyección de los inliers, número de
   inliers, y una bandera `no_rigido` cuando el residuo supera un umbral
   parametrizado (procedencia `estimacion`).
2. **Salida** (`to_dict()` y JSON): por cuadro muestreado `frame`, `dx_px` y
   `dy_px` por fila, `residuo_px`, `inliers`; y un resumen: máximo absoluto
   por eje, y si el JSON de análisis del take existe, el desplazamiento
   address→top y address→impacto por repetición y por fila. **No** escribe en
   `analysis.json` ni en `pose.npz` (eso es un encargo aparte, con contrato
   2.2.0). Un archivo `camera-drift.json` al lado de la pose.
3. **Censo.** Correrla sobre los ocho clips (y la toma de `data/sessions/`,
   que es cortado3 con eventos). Tabla en el informe: por clip, máximo
   absoluto de dx y dy, residuo mediano, `no_rigido`, y para los que tienen
   eventos, address→top y address→impacto por repetición. Contra la
   auditoría, en cortado3: la aceptación es **estar dentro de ±3 px de sus
   rangos** (rep 1: +14 a +23 px en x; rep 2: −8 a −25 px). Si no entra,
   decilo con los números y no ajustes el método hasta que entre: la
   auditoría también puede estar mal, y las diferencias entre sus métodos
   eran 3–6 px.
4. **Dos controles que separan causas**, sobre cortado3: (a) la deriva
   medida sólo en la mitad inferior de la imagen (suelo y pies) contra la
   mitad superior (fondo lejano): si difieren, hay paralaje o rolling, no un
   corrimiento rígido; (b) la deriva en los cuadros de address, donde el
   sujeto está quieto, contra la de los cuadros del downswing: si crece con
   el movimiento del sujeto, la máscara está dejando pasar al sujeto.
5. **Tests** (`tests/test_camera_drift.py`), con clips sintéticos de
   `conftest.py` o generados en el test: fondo con textura desplazado una
   cantidad conocida (3,0 px en x, 1,5 px en y) con un "sujeto" enmascarado
   → recupera el desplazamiento a ±0,3 px; sin desplazamiento → |d| < 0,3 px;
   un sujeto que se mueve sobre fondo fijo → deriva < 0,3 px (la máscara
   funciona); un cuadro sin inliers suficientes → `null` con razón. Bugs
   inyectados: máscara invertida, y homografía evaluada en la fila
   equivocada.

NO: no tocar `kinelab/perception/`, `kinelab/analysis.py`, `kinelab/
metrics/`, `sports/`, `service/`, `web/`, `truth/`, ni ningún
`analysis.json`; no compensar nada en ninguna métrica; no cambiar
`camera_motion_px` (si tiene que morir o cambiar, va en el informe); no
correr el modelo de pose de nuevo (invariante 1: las poses ya están).

## Cómo se prueba

`.venv/bin/pytest` en verde por exit code y conteo (hoy 357). La tabla del
censo con el comando de cada corrida. Tiempo por clip. Para Hernán: nada de
front; si querés mirar, la sesión deja para cortado3 una imagen con el fondo
enmascarado y los inliers dibujados en dos cuadros (address e impacto).

## En paralelo

Ninguno. Vos: `kinelab/tools/camera_drift.py`
(nuevo), `tests/test_camera_drift.py` (nuevo), `ESTADO.md` (tu sección) y
tu informe. Nada más.
