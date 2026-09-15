# 20 — Por qué la mano se ve borrosa: medirlo antes de arreglar nada

Para correr: `/encargo 20` en una sesión nueva. **La parte de medición se
puede hacer ya**; la de arreglo espera al 16 (ver §En paralelo).

## Contexto

Hernán mira el reproductor sobre `vid1.mp4` y ve las manos borrosas en el
backswing, cuando en el archivo original le parecen nítidas. Sospechó de la
interpolación del encargo 05: **no es eso**, ese experimento escribe archivos
aparte que nadie lee y está verificado con `grep` en el informe del 05.

Quedan dos causas posibles y hay que separarlas con números, no con
impresiones:

- **Desenfoque de movimiento real.** A 60 fps el obturador no puede ser más
  lento que 1/60 s, y la cámara elige según la luz. `CAPTURA.md` §Luz tiene
  la tabla: una mano a 10 m/s con buen encuadre barre 21 px a 1/240 s. Si el
  cuadro original ya está barrido, **ningún cambio de software lo arregla** y
  la respuesta es filmar distinto.
- **Nuestra recompresión.** El `overlay.mp4` se reescribe con H.264 desde los
  cuadros decodificados. Si el bitrate o el CRF que usa `explore.py` degradan
  frente al original (43 Mb/s HEVC en `vid1`), el borrón lo agregamos
  nosotros y se arregla en una línea.

Leer: `kinelab/explore.py` (cómo se escribe el `overlay.mp4`: códec, CRF o
bitrate, preset, escala, y si baja la resolución), `HERENCIA.md` §Se porta
(el pipe a ffmpeg, y por qué `mp4v` no sirve), `CAPTURA.md` §Luz y el
obturador, el informe del 11 (bitrates y bbox de los tres clips), el informe
del 05 (que la interpolación no la lee nadie).

## Qué existe ya

- `data/incoming/vid1.mp4`: 1066 cuadros, 2160×3840, HEVC 43,1 Mb/s, 60 fps.
  Impacto en el cuadro 741; el backswing va del 672 al 722.
- `data/incoming/vid1.kinelab/overlay.mp4` y su `pose.npz` con el bbox por
  cuadro.
- `ffmpeg -ss T -i CLIP -frames:v 1 -q:v 1 cuadro.png` extrae un cuadro sin
  recomprimir. Podés mirarlo con `Read`.

## Encargo

**Primera parte, medir. No toca ningún archivo del repo.**

1. Elegí cuatro o cinco cuadros del backswing y el downswing de `vid1` donde
   las manos se muevan rápido (por ejemplo 700, 710, 722, 735, 741) y uno de
   address como referencia quieta.
2. Para cada cuadro, tres versiones: el **original decodificado** a PNG sin
   recomprimir; el mismo cuadro del **`overlay.mp4`**; y, si la resolución
   difiere, el original escalado a la del overlay.
3. Medí la nitidez en una caja fija alrededor de las manos, con la misma caja
   en las tres versiones, con dos indicadores: varianza del laplaciano y
   energía de alta frecuencia. Medí también una caja sobre una zona quieta
   (el tronco, o un árbol del fondo) como control: si el control también cae,
   es compresión; si sólo caen las manos, es movimiento.
4. Contestá la pregunta con números: **cuánta nitidez pierde el overlay
   respecto del original**, y **cuánta nitidez le falta al original respecto
   de un cuadro quieto del mismo clip**. Mirá los PNG con `Read` y describí
   lo que ves.
5. Estimá el obturador que usó la cámara, si los metadatos lo traen
   (`ffprobe -show_frames`, etiquetas EXIF del `udta`). Si no está, estimalo
   del barrido: cuántos px se mueve la muñeca entre cuadros consecutivos
   según `pose.npz`, contra cuántos px mide el borrón.

**Segunda parte, arreglar lo que sea nuestro.** Sólo si la medición muestra
que el overlay pierde nitidez frente al original:

6. Subir la calidad del overlay en `explore.py`: CRF bajo o lossless,
   preset más lento, y sin reescalar. Medir de nuevo con los mismos números,
   y reportar cuánto pesa y cuánto tarda de más.
7. Si el overlay ya era fiel y el original está barrido, **no toques nada**:
   escribí en el informe qué haría falta para que no pase (más luz, o el modo
   de 240 fps que tiene el obturador topeado en 1/240 s) y que eso va a
   `CAPTURA.md`, que no es tuyo.

NO: no tocar `web/`, `service/`, `sports/`, `kinelab/` fuera del render de
`explore.py`, ni `CAPTURA.md`. No agregar dependencias: OpenCV y ffmpeg
alcanzan. No tocar la interpolación.

## Cómo se prueba

La medición **es** la prueba: la tabla con las tres versiones por cuadro y
los dos indicadores, más los PNG guardados en un directorio del scratchpad
cuyas rutas van en el informe, para que Hernán los abra. Si tocaste
`explore.py`, `.venv/bin/pytest -q` en verde y el antes/después de tamaño y
tiempo de `vid1`.

## En paralelo

El 16 toca `kinelab/explore.py` (borra las columnas de rotación aparente del
CSV). **Si el 16 no cerró cuando llegues al punto 6, no toques `explore.py`**:
dejá el arreglo escrito en el informe, con el diff exacto, y cerrá con la
medición. El 18 toca `kinelab/events/` y `sports/golf/events.py`; el 19 toca
`truth/`, `service/exploracion.py` y `web/`.
