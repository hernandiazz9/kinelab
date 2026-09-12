# 02 — Impacto entre dos cuadros: el instante sub-cuadro desde la señal

Para correr: `/encargo 02` en una sesión nueva.

## Contexto

En `~/Desktop/cortado.mp4` (30 fps) el cuadro que el motor marca como impacto
(44) es anterior al contacto y el 45 ya pasó la bola. La quinta sesión
(`ESTADO.md`, sección de arriba) hizo el paso 1: entre el 44 y el 45 nunca
hubo cuadros (`cortado.mp4` es copia bit a bit del original Samsung a 30 fps),
así que no hay nada que recuperar, sólo estimar el instante. Este encargo es
el paso 2 tal como quedó definido ahí. El paso 3 (`minterpolate` para mirar)
es otro encargo y viene después de que Hernán vea éste.

Leer: `sports/golf/events.py` (cómo se detecta impact hoy: cuadro más cercano
a la posición de las manos en address dentro de ±0,25 s del pico de
velocidad; la señal maestra es el centro de las dos muñecas),
`kinelab/explore.py` (qué escribe en `datos-eventos.json`),
`tests/helpers/synth_swing.py`, `tests/test_fase2.py`,
`web/src/components/Reproductor.tsx` y `TablaEventos.tsx` (dónde se muestran
los eventos), `web/src/lib/api.ts`, `service/exploracion.py`.

## Qué existe ya

- `.venv/bin/python -m kinelab datos ~/Desktop/cortado.mp4 --altura-m 1.75`
  → `~/Desktop/cortado.kinelab/datos-eventos.json` con address 7, top 39,
  impact 44 y `fps_archivo`. ~10 s.
- El swing sintético de `tests/helpers/synth_swing.py`, con eventos conocidos.
- El reproductor propio en `web/`: seek a `(n + 0,5) / fps` verificado por
  `mediaTime`, marcas de evento en la línea de tiempo, botones "ir a
  address / top / impacto", zoom y paneo.
- La cola de exploración y los endpoints `/api/datos` en `service/`.

## Encargo

1. En `sports/golf/events.py`, además del cuadro entero (que **no cambia** y
   sigue siendo el ancla de todo lo que ya existe): estimar el instante en que
   la trayectoria de las manos cruza su posición de address, interpolando
   entre el cuadro anterior y el posterior al cruce. Sale en el evento como
   `t_sub_s` y `fraccion` (0–1 entre `frame` y `frame + 1`), con su
   incertidumbre propagada desde ±1 cuadro con la velocidad local
   (invariante 8), `method` que diga cómo se calculó y procedencia
   `estimacion`. Si el cruce no es claro (la señal no cruza, o cruza más de
   una vez dentro de la ventana), `fraccion` es `null` con razón; nunca un
   número forzado.
2. Que llegue a `datos-eventos.json` (modo exploración). Si también entra en
   `analysis.json`, es una adición opcional (minor en `schema_version`) con
   test del validador; si preferís dejarlo sólo en exploración por ahora,
   decilo en el informe.
3. Tests: swing sintético con cruce conocido (por ejemplo en 44,6) que falle
   si la fracción se calcula con el cuadro equivocado, con la señal en el eje
   equivocado o con el signo de Y invertido (invariante 15). Y el caso sin
   cruce claro → `null` con razón.
4. Pantalla de exploración, lo mínimo: donde hoy dice "impacto 44", que diga
   "impacto entre el cuadro 44 y el 45 (0,6 ± …)", y un botón que muestre
   los dos cuadros (44 y 45) lado a lado, en el reproductor o debajo. Sin
   rediseño ni otra cosa en el front.

NO: no cambiar el cuadro entero de impact ni los umbrales de detección; no
tocar top ni address; no interpolar video (eso es el paso 3); no agregar
dependencias.

## Cómo se prueba

- `.venv/bin/pytest -q` en verde con los tests nuevos.
- `python -m kinelab datos` sobre `~/Desktop/cortado.mp4` y sobre el original
  `~/Desktop/20260907_170638.mp4` (el impacto debería caer en 147 con la
  misma fracción que en 44 del recorte, salvo por el fps que hoy se calcula
  1,9 % bajo en el original; anotá lo que dé). Los dos `impact` completos
  (frame, fraccion, incertidumbre, method) van en el informe.
- `cd web && pnpm lint && pnpm build` limpios; si tocaste `service/`, el flujo
  por el proxy con `curl` como en la cuarta sesión.
- Para Hernán: qué tiene que ver en la pantalla (el texto del impacto y el
  botón de los dos cuadros) con `cortado.mp4`.

## En paralelo

El encargo 03 (`fps_truth`: falsa alarma de VFR por el primer delta) toca
sólo `kinelab/tools/fps_truth.py` y `tests/test_fps_truth.py`. No toques esos
dos; si `explore.py` necesitara algo de ahí, anotalo en el informe en vez de
hacerlo.
