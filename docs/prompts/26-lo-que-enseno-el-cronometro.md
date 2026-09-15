# 26 — Lo que enseñó el cronómetro: la guía de filmación, el segundo clip y el camino fijado por un test

Para correr: `/encargo 26` en una sesión nueva. Leé antes el informe del 24
completo, y el del 12 (que escribió la guía que vas a corregir).

## Contexto

El encargo 24 leyó el cronómetro filmado dentro de `Cortado-lenta.mp4` y midió
la primera tasa de captura real del proyecto: **240,15 fps ± 0,60, uniforme,
estirada ×8,0005**. Escribió el primer camino calibrado. El gate pasa 8 de 9
chequeos y falla uno solo: la toma dura **2,49 s reales** y pide 3.

De ahí salieron nueve lecciones sobre cómo filmar, listadas al final de ese
informe en §«Lo que este clip enseña». La sesión no podía tocar los documentos
de captura. Este encargo las escribe, mide el segundo clip que apareció, y fija
el camino calibrado con un test.

Leer: el informe del 24 §«Lo que este clip enseña» y §4 y §5,
`docs/filmacion-s22.md`, `CAPTURA.md` (§Calibración con cronómetro,
§Encuadre, §Transferencia, §Lo que queda por verificar),
`data/capture-paths.yaml`, `tests/test_capture_paths.py` (el test
`test_repo_has_the_declared_paths_of_adr_016`, que es el hermano del que hay
que escribir), `kinelab/tools/fps_truth.py`.

## Encargo

1. **`docs/filmacion-s22.md`**, que es la hoja que recibe quien filma. Los
   cambios que el 24 midió, con el porqué en una línea cada uno:
   - **Mínimo 25 segundos de grabación** en cámara lenta. En ×8, los 3 s
     reales que pide el programa son 24 s de grabación. Es el único motivo
     por el que el clip del 15/9 no pasó.
   - **El cronómetro va dentro del mismo cuadro que el swing**, y pasa a ser
     la regla del modo lento, no una toma aparte. Es lo que hizo que ese clip
     se calibrara a sí mismo.
   - **El cronómetro, a la distancia del golfista, plano y encarado**, con el
     brillo al máximo, fuera de la línea de tiro. En el clip del 15/9 estaba a
     20 cm del lente, desenfocado y girado 23°.
   - **No recortar en la Mac**: el archivo entero de `DCIM/Camera` por cable.
     El recorte se llevó las etiquetas del fabricante y escondió 14 cuadros.
   - **Acercar el trípode**: ese clip dio 21,6 % del alto, el peor de los cinco
     clips reales.
   - **Nada más en el cuadro**: el carrito de golf se detectó como persona en
     8 cuadros.
   - Y lo que salió bien y hay que repetir: el modo *Slow motion* FHD (no
     *Super slow motion*), y el sol.
2. **`CAPTURA.md`**: en §Calibración con cronómetro, que el cronómetro dentro
   del cuadro del gesto es el método preferido, con el resultado medido
   (240,15 fps, ratio 1,0027, factor 8,0005) y su procedencia. En §Lo que queda
   por verificar, sacar lo que este clip ya contestó y dejar lo que falta: el
   original sin recortar, el delta de arranque de este modo, y los cronómetros
   de Video FHD 60 y 30. Agregá una nota en §Encuadre con el quinto punto de la
   serie (21,6 %).
3. **El segundo clip.** `~/Desktop/cartado2-lenta.mp4` apareció después del
   prompt del 24: mismo modo, mismo lugar, 292 cuadros, creado 5 minutos
   después. Medile la tasa con **el mismo método** del 24 (lecturas del
   cronómetro a ojo con `Read`, ajuste sobre todas las lecturas, tramos) y
   comparala contra los 240,15 ± 0,60. **Es la primera verificación
   independiente de una tasa calibrada del proyecto**: si coincide, el camino
   se sostiene en dos clips; si no, hay que entender por qué antes de confiar
   en él. Reportalo pase lo que pase. Con 292 cuadros son 1,22 s reales, así
   que tampoco va a pasar `duration_plausible`: no lo ingestes, alcanza con la
   tasa.
4. **El test que faltaba.** En `tests/test_capture_paths.py`, el hermano de
   `test_repo_has_the_declared_paths_of_adr_016` para el camino calibrado:
   que exista, que sea `mode: slomo`, su `fps_real`, su `stretch_factor`
   consistente con `fps_real / fps_playback`, y que los seis campos del
   cronómetro estén llenos. Si el 3 mueve el número, el test lleva el que
   quede y el informe lo dice.

NO: no tocar `kinelab/`, `sports/`, `service/`, `web/`, `truth/`; no cambiar
ningún umbral del gate (la decisión sobre `duration_plausible` está tomada:
se filma más largo, no se baja el número); no escribir un camino nuevo salvo
que el punto 3 obligue, y en ese caso preguntá antes en el informe.

## Cómo se prueba

`.venv/bin/pytest -q` en verde con el test nuevo. La tabla del segundo clip
con sus lecturas y su cuadro al lado, como hizo el 24. Los tres documentos
leídos de punta a punta al terminar, y en el informe cinco líneas de qué dice
ahora la guía.

## En paralelo

El 16 toca `kinelab/` y el contrato; el 18 `kinelab/events/`; el 21 y el 17
están pendientes. Vos: `docs/filmacion-s22.md`, `CAPTURA.md`,
`docs/checklist-captura.md` si hace falta, `tests/test_capture_paths.py`,
`data/incoming/`. Ningún archivo de código del motor.
