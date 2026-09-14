# 05 — Lámina de cuadros interpolados entre dos cuadros medidos (para mirar)

Para correr: `/encargo 05` en una sesión nueva.

## Contexto

Paso 3 del pedido de Hernán (`ESTADO.md`, quinta sesión): entre el cuadro 44
y el 45 de `~/Desktop/cortado.mp4` nunca hubo cuadros, y el encargo 02
estimó que las manos cruzan su posición de address en 44,44 ± 0,11
(`docs/informes/2026-09-14-02-impacto-subcuadro.md`). Falta ver si
`minterpolate` de ffmpeg fabrica cuadros intermedios que sirvan para MIRAR el
contacto, o si el shaft sale fantasma. Es un experimento etiquetado, no una
medición: ninguna métrica lee lo que produce, y lo decide Hernán mirando.

Leer: `kinelab/explore.py` (sólo para saber cómo nombra `<video>.kinelab/` y
qué hay en `datos-eventos.json`; no se modifica), `kinelab/tools/fps_truth.py`
(cómo se decodifica y se cuentan cuadros con ffmpeg/ffprobe),
`HERENCIA.md` §"Se porta" (escritura de video por pipe a ffmpeg) y
§Prohibido (video anotado como única vista: acá es un archivo aparte, a
propósito), ADR-010 (sin RIFE ni FILM: sólo ffmpeg).

## Qué existe ya

- ffmpeg 9 con `minterpolate`. `cortado.mp4`: 76 cuadros, 29,999 fps,
  1080×2320 con rotación 90.
- `~/Desktop/cortado.kinelab/datos-eventos.json` con
  `eventos_subcuadro.impact` (frame_before 44, frame_after 45, fraction
  0,4404) y `overlay.mp4`, cuyo cuadro 44 lleva el rótulo IMPACT.
- `tests/conftest.py`: clips sintéticos generados con ffmpeg en el propio
  test.

## Encargo

Una herramienta nueva, `kinelab/tools/interpolar.py`, agnóstica al deporte
(recibe índices de cuadro, no "impacto"):

```
python -m kinelab.tools.interpolar VIDEO --entre A B [--factor 4] [--marca 44.44] [--contexto 2]
```

1. Recorta el tramo `[A − contexto, B + contexto]` del video original
   (rotación aplicada, mismo tamaño), lo pasa por `minterpolate` a
   `fps × factor` (probar `mi_mode=mci`, `mc_mode=aobmc`, `me_mode=bidir`,
   `vsbmc=1`; anotar en el informe con qué se quedó y por qué) y escribe
   `<video>.kinelab/interpolado-A-B-x<factor>.mp4` (H.264, `-g 12`) donde
   **cada cuadro sintético lleva quemado** "cuadro interpolado, no medido" y
   su índice fraccional (44,25, 44,50…); los medidos llevan "medido · 44".
2. Escribe `<video>.kinelab/lamina-A-B-x<factor>.png`: el cuadro A medido,
   los intermedios interpolados y el B medido, en fila, cada uno con su
   rótulo, y una marca vertical donde cae `--marca` (44,44) con el texto
   "estimación del encargo 02: 44,44 ± 0,11". Recortá al bbox de la persona
   (o a un recorte fijo alrededor de las manos) para que se vea algo a 2320
   de alto.
3. Correrla sobre `cortado.mp4` con factor 4 (120 fps: 3 intermedios) y 8
   (240 fps: 7 intermedios).
4. Que nada lo lea: el nombre no entra en la lista blanca de `service/` ni en
   `explore.py`. Se verifica con un `grep` y se dice en el informe.

NO: no tocar `explore.py`, `service/`, `web/`, `sports/`, ni ningún evento.
No correr pose sobre los cuadros interpolados. No RIFE, FILM ni ningún modelo.
No agregar dependencias (Pillow o OpenCV, que ya están, alcanzan para el PNG).

## Cómo se prueba

- `tests/test_interpolar.py` con un clip sintético de `conftest.py`: la
  salida tiene `(n − 1) × factor + 1` cuadros para el tramo; los cuadros en
  posiciones múltiplo de `factor` son iguales al original salvo la franja del
  rótulo (PSNR alto fuera de ella) y los intermedios difieren de sus dos
  vecinos; el PNG existe con el ancho esperado.
- `.venv/bin/pytest -q` en verde.
- Sobre `cortado.mp4`, factor 4 y 8: rutas de las dos láminas y los dos
  `.mp4`, tiempo de ffmpeg de cada corrida, y una frase honesta de la sesión
  sobre lo que se ve en la lámina (shaft entero, fantasma o doble), sin
  decidir por Hernán.

## Para Hernán

Abrir las dos láminas (`open ~/Desktop/cortado.kinelab/lamina-44-45-x*.png`)
y decir si el shaft se ve o sale fantasma. Nada de front.

## En paralelo

El encargo 04 toca `kinelab/ingest/`, `kinelab/contract/`, `kinelab/explore.py`
(dos líneas), `tests/test_gate.py`, `CAPTURA.md` y `CONTRATO.md`. No toques
nada de eso.
