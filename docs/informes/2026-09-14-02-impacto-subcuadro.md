# impacto-subcuadro — 14 de septiembre de 2026

Encargo: estimar el instante del impacto ENTRE dos cuadros desde la señal de las
manos, sin tocar el cuadro entero, y mostrarlo en la pantalla de exploración.

## Hecho

Commits `5ec9c2e` (motor, contrato, front y tests) y el de cierre con
`ESTADO.md` y este informe.

- `kinelab/events/primitives.py`: primitiva genérica `subframe_crossing` —cruce
  de una señal 1-D por un nivel, interpolado entre los dos cuadros— y
  `still_run_start`. El motor no sabe qué señal es ni de qué deporte.
- `sports/golf/events.py`: la definición del deporte. Señal = centro de las dos
  muñecas **crudo** proyectado sobre su dirección de viaje alrededor del
  impacto; nivel = la misma proyección en el cuadro de address. Su cero es el
  instante de máximo acercamiento a la posición de address, que es la versión
  continua del criterio del cuadro entero (mínima distancia). **El cuadro entero
  y los umbrales no se tocaron**; address y top tampoco.
- Incertidumbre (invariante 8): el cruce recalculado extrapolando cada segmento
  vecino con su velocidad local (`curvature_frames`) ⊕ el ruido del clip
  propagado por la pendiente (`noise_frames`). Los sumandos van en el JSON.
- Sólo `face_on`; desde `down_the_line` devuelve `null` con razón (la dirección
  de viaje queda sobre el eje óptico). Sin cruce claro —no cruza, cruza más de
  una vez, o el cruce no es contiguo al cuadro del evento— también `null` con
  razón. Nunca un número forzado.
- Contrato: campo `subframe` opcional en cada evento; `schema_version` 1.1.0
  (un 1.0.0 sigue validando). Documentado en `CONTRATO.md` §events[].
- `datos-eventos.json`: clave `eventos_subcuadro`.
- Front (`web/`): el texto «entre el cuadro 44 y el 45 (0,44 ± 0,11)» en la
  tabla por evento, en la foto del impacto y debajo del reproductor, y un botón
  que muestra los dos cuadros lado a lado (`DosCuadros.tsx`), con la misma
  convención de seek del reproductor y el mismo aviso si el navegador muestra
  otro cuadro. Nada más: sin rediseño y sin interpolar video.

## Probado

Suite del motor: **193 tests en verde en 17 s** (180 antes, 13 nuevos), salida 0.
`cd web && pnpm lint && pnpm build`: limpios. No se tocó `service/`.

Los dos `impact` completos, con `python -m kinelab datos … --altura-m 1.75`:

| | `cortado.mp4` (76 cuadros, 29,999 fps) | original `20260907_170638.mp4` (265, 29,436 fps) |
|---|---|---|
| `frame` (cuadro entero, sin cambios) | 44 | 147 |
| `frame_before` → `frame_after` | 44 → 45 | 147 → 148 |
| `fraction` | **0,4404** | **0,4181** |
| `t_sub_s` | 1,481396 s | 5,008089 s |
| `uncertainty_frames` / `_s` | 0,1112 · 3,71 ms | 0,1361 · 4,62 ms |
| `components`: curvatura / ruido | 0,1104 / 0,0128 cuadros | 0,1154 / 0,0720 cuadros |
| `components`: pendiente / ruido | 115,4 px/cuadro / 1,20 px | 118,3 px/cuadro / 6,93 px |
| `method` | `hands_cross_address_linear_interp` | idem |

- **El recorte y el original coinciden en 0,022 cuadros (0,74 ms).** El original
  da el cruce en 147,418, que en la numeración del recorte (offset 103) es
  44,418, contra 44,440. Son cuadros bit a bit iguales pero con la pose estimada
  en dos corridas independientes: la diferencia entra en la banda de las dos.
- El instante cae **14,7 ms después** del cuadro 44 (`t_s` 1,4667 s). Entre el
  44 y el 45 las manos recorren 118 px, el 13,6 % de la altura del cuerpo: por
  eso un cuadro importa acá.
- Eventos del original: address 111, top 141, impacto 147. El recorte da 7, 39 y
  44; con el offset de 103 serían 110, 142 y 147. El impacto coincide exacto;
  address y top difieren un cuadro entre corridas.
- Tests nuevos (13): swing sintético con cruce conocido a 30 fps en 71,56
  (fracción 0,61) contra una verdad que **no sabe cómo se estima** —el mínimo de
  distancia sobre el modelo continuo, muestreado 200.000 veces—, con error de
  0,05 cuadros; lo mismo a 30/60/120/240 fps (≤ 0,1 cuadros); con 2 px de ruido
  la banda reportada cubre el error; los tres bugs inyectados de la invariante
  15 (eje sólo `y`, eje sólo `x`, signo de `y` mezclado entre el eje y las
  posiciones) dan otro número, y espejar el clip entero **no** mueve el
  instante; los cuatro nulos con razón; y uno de punta a punta que lee un video
  y verifica el `datos-eventos.json` escrito.
- Para el swing sintético hicieron falta dos parámetros nuevos (`hands_tilt`,
  `hands_miss_px`, ambos 0 por defecto): si el arco de bajada pasa **exacto**
  por el punto de address, cualquier eje cruza en el mismo instante y el test no
  distingue ningún bug. En el clip real las manos pasan a 66 px.
- El `overlay.mp4` que muestra el botón: el cuadro 44 es el que lleva el rótulo
  `IMPACT` (MSE 24 contra 842–875 de sus vecinos), así que los índices cierran
  de punta a punta.

## Queda abierto

- **Esto no mide la bola**, mide cuándo las manos pasan por su posición de
  address —el mismo proxy que ya usaba el cuadro entero—. Con el shaft
  adelantado el contacto real no cae exactamente ahí. Medirlo de verdad pide el
  palo (geometría del shaft, Fase 3, sin hacer).
- **Sin MDC**: descriptivo, procedencia `estimacion`. El arnés puede medirle
  sesgo y MDC con el swing paramétrico; hoy la única verdad es sintética.
- La pose va con huecos rellenados y el cálculo **no distingue** un cuadro
  interpolado de uno medido: con las muñecas perdidas justo en el impacto
  saldría un número igual de confiado.
- El front no se abrió en un navegador (regla de trabajo).
- `explore.py` sigue tomando el `fps_playback` **bruto** y no el efectivo que
  agregó el encargo 03 (`kinelab/explore.py:59` y `:61`). Por eso el original de
  9 s figura a 29,436 fps y sus segundos quedan 1,9 % largos. La `fraction` no
  se ve afectada (va en cuadros); `t_sub_s` sí. No se tocó por el reparto de
  archivos entre los dos encargos.

## Preguntas para el orquestador

1. **El cambio de una línea en `explore.py`** (bruto → efectivo) lo dejaron
   anotado los dos encargos y no lo hizo ninguno. ¿Entra como parte del paso 3 o
   como encargo suyo? Afecta a todos los `t_s` de cualquier clip de Android con
   delta de arranque.
2. **¿El arnés le mide MDC a este instante?** Sería el primer número medido de
   un evento y encaja con el encargo 05 (ganancia en el arnés), que ya va a
   tocar `truth/`.
3. **El paso 3 (`minterpolate`) ahora tiene con qué compararse:** la lámina
   puede mostrar dónde cae 44,44 entre los cuadros interpolados. Si el shaft
   sale fantasma, el sub-cuadro sigue siendo el único número.
4. **¿Se estima también el instante del top?** El top es un cambio de dirección,
   no un cruce: la primitiva de acá no le sirve tal cual (habría que cruzar la
   velocidad proyectada por cero). Hoy no está y el prompt lo prohibía.

## Para que pruebe Hernán

```bash
.venv/bin/python -m service
```

```bash
cd web && pnpm dev
```

Subir `~/Desktop/cortado.mp4` con altura 1,75 y mirar, en este orden:

1. **Debajo del reproductor**: «impacto · entre el cuadro 44 y el 45 (0,44 ±
   0,11) · 1,4814 s ± 3,7 ms», el botón «ver los cuadros 44 y 45» y la aclaración
   de que es cuándo las manos pasan por su posición de address, no el contacto
   con la bola.
2. **El botón**: los dos cuadros lado a lado, el 44 con borde rojo (el instante
   cae más cerca de él), y arriba «entre estos dos cuadros no hay nada filmado:
   a 29,999 fps pasan 33,3 ms entre uno y el otro». Si aparece un aviso ámbar
   «el navegador mostró el cuadro N», decímelo: significa que el seek no cayó
   donde se pidió.
3. **La tabla «En cada evento»**: la columna «impacto» ahora tiene una tercera
   línea con el mismo texto; address y top no la tienen (todavía no se estima).
4. **La foto del impacto**: la misma línea bajo «impacto · cuadro 44 · 1,467 s».
5. Y lo de siempre: que el cuadro a cuadro, el zoom y las tablas sigan igual.
