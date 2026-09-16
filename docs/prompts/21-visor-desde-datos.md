# 21 — El visor definitivo: el esqueleto dibujado desde datos, con capas que se apagan

> **POSTERGADO el 16/9/2026 por la auditoría del primer juicio**
> (`docs/informes/2026-09-16-auditoria-primer-juicio.md` §4). **No correr
> todavía.** Va después de: el 28 (pantalla sin falsedades), el encargo que
> acote `follow_end` a su repetición, y la sesión de validación filmada; y sin
> ninguna sesión abierta que edite `kinelab/analysis.py` o `kinelab/explore.py`.
> El orquestador lo re-emite con estos cinco ajustes incorporados:
>
> 1. **Dependencias:** las de arriba, no «16, 19 y 20».
> 2. **Cuadro y tiempo:** el número de cuadro sale del fps de **reproducción**
>    del archivo servido (30,0169 en el Slow motion del S22, estirado ×8,0005),
>    nunca de `timestamps_s` de `pose.npz`, que es n / 240,15.
> 3. **Material de prueba:** además del cuadro 741 de `vid1`, `cortado3-lento`
>    (HEVC, 2977 cuadros) y una toma de la sesión de validación.
> 4. **Hash del master:** va en `header.source.master_sha256`, que ya existe en
>    el schema 2.0.0 (hoy `null`). No hace falta cambiar el contrato.
> 5. **Juicio:** el front no calcula ni muestra juicio; pinta lo que manda el
>    motor: `uncertainty.method`, `null_reason` y `warnings`.

Para correr: ver el recuadro de arriba.

## Contexto

Hernán quiere un botón para apagar y prender el esqueleto y los ángulos, y
ver el video limpio. Hoy no se puede: el reproductor muestra un
`overlay.mp4` con los palitos **quemados**, que además es una recompresión
del original. Es la desviación de la **invariante 10** que el proyecto
arrastra desde la cuarta sesión y que está anotada en `ESTADO.md`: "nunca
video anotado pre-renderizado como única vista; se dibuja desde datos, en
vivo, sobre el master".

ADR-014 ya fija cómo: canvas sobre el video, dibujando **sólo** dentro de
`requestVideoFrameCallback`, con el `mediaTime` del cuadro presentado, seek a
`(n + 0,5) / fps` con verificación, video y canvas dentro del mismo
contenedor que se transforma para el zoom, y capas conmutables. El
reproductor actual ya tiene todo eso salvo el dibujo: fue escrito como base
de esto, no como otra cosa (informe de la cuarta sesión).

Un cambio resuelve tres pedidos a la vez: el switch, el zoom sin ampliar
compresión, y la invariante 10.

Leer: `web/src/components/Reproductor.tsx` (el rVFC, el seek verificado, el
zoom y el paneo, `marcoRef`), `web/src/components/Visor3D.tsx` (lo que dejó
el 19: cómo dibuja huesos en canvas y cómo se conmuta), `web/src/lib/api.ts`,
`web/src/app/page.tsx`, `service/app.py` y `service/exploracion.py` (cómo se
sirven los archivos de un trabajo y la lista blanca), `kinelab/explore.py`
(qué escribe, y el informe del 20 sobre la calidad del video),
`kinelab/contract/` y `CONTRATO.md` §pose.npz (qué hay adentro: keypoints,
scores, bbox, plausibilidad), ADR-014, `HERENCIA.md` §Se porta (los tres
defectos del `PoseViewer` heredado: dibujaba el cuadro pedido y no el
presentado, `setTimeout` fijo, un `setState` por cuadro).

## Qué existe ya

- `pose.npz` por trabajo con los 26 puntos por cuadro, sus scores, el bbox y
  la máscara de plausibilidad.
- `datos-eventos.json` con los eventos, el sub-cuadro del impacto y los
  ángulos por evento; `datos-por-cuadro.csv` con los ángulos por cuadro.
- El reproductor con cuadro a cuadro verificado, cámara lenta, zoom y paneo.
- `GET /api/datos/{id}/archivos/{nombre}` con lista blanca y Range/206.

## Encargo

1. **Servir la pose al front.** `GET /api/datos/{id}/pose` lee el `pose.npz`
   y devuelve JSON: keypoints por cuadro, scores, los pares de huesos, los
   ángulos por cuadro que hoy van al CSV, los eventos, y el tamaño del video
   en el que están esas coordenadas. `NaN` a `null` en la frontera, en un
   solo lugar. Pensá el peso: 1066 cuadros × 26 puntos son ~300 KB con 1
   decimal; si hace falta, comprimí o paginá, y decí por qué.
2. **Dibujar desde datos** en un canvas sobre el video, dentro del mismo
   contenedor que ya se transforma para el zoom, sólo dentro de
   `requestVideoFrameCallback` y con el cuadro que dice `mediaTime`. El aviso
   ámbar de "pedí el cuadro n y mostró m" que ya existe se conserva.
3. **Las capas, cada una con su interruptor**, y el estado recordado en
   `localStorage`: esqueleto, ángulos, eventos, y el rótulo del camino. Todas
   prendidas por defecto. Un botón "ver el video limpio" que apaga todas de
   una.
4. **El video que se ve deja de ser el `overlay.mp4`.** Sobre qué archivo se
   dibuja lo decide el informe del 20: si el original se puede reproducir en
   Chrome, se sirve el original; si no (HEVC no es portable, ADR-014), hace
   falta el `master.mp4` de ESPECIFICACION 4.2, H.264 CFR con GOP corto y
   rotación aplicada, escrito con la calidad que el 20 haya fijado. Elegí con
   los números del 20 y decilo en el informe. Los índices de cuadro se
   refieren a ese archivo y su hash va en el análisis.
5. **El `overlay.mp4` deja de ser la vista principal.** No lo borres todavía
   (las descargas lo usan), pero el reproductor ya no lo abre. Anotá en
   `ESTADO.md` que la desviación de la invariante 10 **queda cerrada**, con
   la fecha.

NO: no escribir un segundo visor (`HERENCIA.md` lo prohíbe explícitamente:
se extiende el que tiene cuadro a cuadro); no tocar `kinelab/events/` ni
`sports/`; no agregar dependencias; no dibujar nada que no salga de
`pose.npz` o del análisis; no abrir el navegador.

## Cómo se prueba

- `tests/test_service.py`: el endpoint de pose sobre un trabajo con pose
  sintética, sin `NaN` en el JSON, y 404 para un trabajo sin `pose.npz`.
- `.venv/bin/pytest -q` y `cd web && pnpm lint && pnpm build` limpios.
- Por `curl`: el JSON de pose de `vid1` con el keypoint de la muñeca derecha
  en el cuadro 741 comparado contra el `pose.npz` leído con numpy, valor por
  valor. Si el front dibuja otra cosa que el motor midió, es un bug.
- Para Hernán: qué mirar, con énfasis en apagar todas las capas sobre el
  cuadro 741 de `vid1` y ver el video limpio, y en que el zoom a 4× ya no
  amplía compresión sino el archivo servido.

## En paralelo

Ninguno si esperás al 16, 19 y 20 como dice arriba. Si algo sigue abierto,
avisá antes de empezar.
