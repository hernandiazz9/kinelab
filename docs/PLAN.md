# Plan

Última ronda: 2026-09-14 — leídos los informes del 04, 05, 06 y 08. Los
cuatro cerraron. El experimento de interpolación (05) está contestado: no
sirve para ver el contacto; el shaft sale fantasma. Decididas las preguntas
abiertas (abajo). Escritos el 09 (ficha y selector en la pantalla) y el 10
(tolerancia de `fps_min`); el 07 (ejemplo mocap) se actualizó y quedó
destrabado. Los tres corren en paralelo.

Regla de numeración: un ítem recibe número cuando se escribe su prompt; los
pendientes van sin número, en orden de ejecución.

## Decisiones del orquestador

- 2026-09-14 · Un solo delta de PTS de arranque no es tasa variable. El gate
  y el motor usan `vfr_ratio` y `fps_playback` efectivos; los brutos quedan en
  `capture.json`. Hecho en el 04. `duration_playback_s` queda como span
  medido de PTS (es lo que dura el archivo), documentado en `CONTRATO.md`.
- 2026-09-14 · Caminos de captura declarados sin calibrar (ADR-016), hecho en
  el 06. Aprobadas sus dos precisiones: en exploración la procedencia es
  siempre `sin_verificar` (nadie verificó que el archivo vino por el camino),
  y `fps_provenance` es obligatorio en `analysis.json` 1.2.0 aunque el bump
  sea minor (desviación anotada en `CONTRATO.md`: opcional permitiría esconder
  el supuesto).
- 2026-09-14 · `fps_min` se compara con tolerancia del 0,5 % en el registro
  (29,97 · 59,94 · 119,88 son 30 · 60 · 120). La tabla del arnés sigue en
  enteros. Encargo 10. El umbral del gate (100 para golf) no lleva
  tolerancia; si algún día muerde, es otra conversación.
- 2026-09-14 · Interpolación con `minterpolate`: experimento cerrado. No
  reconstruye el palo (barrido completo en el informe del 05, incluida la
  búsqueda exhaustiva). Ver el contacto pide material a 120/240 fps. La
  herramienta `kinelab.tools.interpolar` se queda: es genérica, deja la
  evidencia rotulada y no la lee nadie. Recorte por defecto: el bbox de la
  persona (lo que hay); "manos" es decisión de quien llama.
- 2026-09-14 · Silueta "ideal" con ángulos de internet: no (ADR-007, ADR-012).
  El swing de muestra sale de mocap real (ADR-009 nivel 1) y es un ejemplo y
  un dato de validación, nunca "referencia". Videos de YouTube no son
  material (cementerio 1 y 2); GolfDB sólo para medir.

## Backlog, en orden

- [hecho] 02 impacto-subcuadro — `5ec9c2e`, `4350e08`.
- [hecho] 03 fps-truth-primer-delta — `f1a102e`, `db22fae`.
- [hecho] 04 gate-fps-efectivo — `0cd5716`, `f1fd260`. 197 tests.
- [hecho] 05 lamina-interpolada — `d94dcfd`, `9f3fc0f`, `b7d9b6e`. Contestado:
  fantasma. Hernán mira las láminas cuando quiera.
- [hecho] 06 camino-declarado — `4dc8b7f`, `1297df5`. ADR-016; 240 tests;
  el original del S22 pasa 8 de 9 chequeos, rechazado sólo por 30 < 100 fps.
- [hecho] 08 lista-de-trabajos — `cee7585`, `d5aebbc`, `d127291`. Hernán
  prueba la lista y `?trabajo=`.
- [en curso] 07 ejemplo-mocap — swing real de mocap CMU proyectado con la
  cámara virtual del arnés, corrido por el mismo camino que un video, como
  trabajo de ejemplo en la pantalla; primer número de nivel 1 (sway de
  pelvis y duraciones 2D contra 3D). Borra el ejemplo de mentira del 08.
- [en curso] 09 ficha-y-selector — selector de camino antes de subir, la
  ficha del archivo como primera etapa del trabajo, los avisos (camino
  declarado y fps corregido) antes de cualquier número, y el bloque de las
  12 métricas calculada / no calculada con razón.
- [en curso] 10 fps-min-tolerancia — 0,5 % en el registro; a 29,998 fps las
  métricas de 30 vuelven a calcularse (sin juicio).
- [pendiente] arnes-ganancia-y-subcuadro — en `truth/`: ganancia de
  velocidad angular pelvis→tórax→brazo con ratios conocidos desde las dos
  vistas (vive con MDC y vistas, o muere), y sesgo/MDC del instante
  sub-cuadro del impacto. Fase 3.2/3.3 sin cerrar.
- [pendiente] visor-desde-datos — esqueleto desde `pose.npz` sobre el video
  en el reproductor (ADR-014, invariante 10) con `master.mp4` H.264 CFR
  (4.2). Cierra la desviación de la cuarta sesión.
- [pendiente] cola-con-cancelacion — cancelar y borrar trabajos desde la
  pantalla, paginado de la lista, fotos por evento como JPEG (hoy ~20 MB por
  clip de 3 s, 3,7 MB por PNG), limpieza de `data/exploracion/` (4.1).
- [bloqueado por Hernán] cronómetro y sesión con el S22 — ver Preguntas.
  Con eso: calibrar los caminos del S22 en `capture-paths.yaml` (0.7), un
  ADR que cierre lo de Android con números, umbral de encuadre medido (1.3),
  intrínsecos con tablero (3.1), re-correr el arnés, pasar los clips por
  percepción y análisis. Anotar el primer delta de cada modo (el 03 lo midió
  en uno solo: 0,2015 s) y el codec de FHD 60 (`s22ultra-video-fhd60-cable`
  no lo declara).
- [pendiente] golfdb-error-de-eventos — bajar el dataset (CC BY-NC, sólo
  para medir) y correr `kinelab.tools.golfdb_eval` (2.5). Después de decidir
  con Hernán si vale bajar 1400 videos ahora.
- [pendiente] Fase 5: repetibilidad primero; comparación de dos repeticiones
  o de dos atletas filmados con el mismo protocolo, sincronizados por evento
  y normalizados por altura, lado a lado y como silueta fantasma
  (`compare.py` de la herencia); bandas descriptivas con procedencia para las
  métricas de nivel 1, nunca veredicto. No antes de clips reales por el gate
  y del visor desde datos.

## Preguntas para Hernán

- Mirar las dos láminas del 05: `open ~/Desktop/cortado.kinelab/lamina-44-45-x*.png`.
  La sesión dice fantasma; si vos ves otra cosa, se reabre.
- Probar la pantalla del 08 (lista de trabajos, `?trabajo=`): la lista de
  seis pasos está al final de `docs/informes/2026-09-14-08-lista-de-trabajos.md`.
  Y la del 02 si todavía no (texto del impacto y botón de los dos cuadros).
- Filmar el cronómetro con el S22 Ultra: guía en `docs/filmacion-s22.md`. Es
  lo único que puede hacer que ese teléfono pase el gate (240 fps en slow
  motion) y lo único que da métricas con juicio.
- ¿A quién filmar como referencia para Fase 5? Alguien que juegue claramente
  mejor, misma cámara, misma distancia, mismas vistas.
- ¿Tenés o podés conseguir una GoPro? Camino de 240 fps real; entra con
  cronómetro y tablero.
- GolfDB: ¿bajar los 1400 videos ahora o después del material propio?

## Aparcado

- Instante sub-cuadro del top: no pedido; la primitiva de cruce no aplica.
- Lámina interpolada en el front: no; el experimento está cerrado.
- Pádel: sólo cuando golf tenga MDC medidos (invariante 17).
- SynthPose como segundo estimador (1.5): necesita torch, sólo en `truth/`;
  después de los intrínsecos reales.
- La página vieja del gate en `service/static`: se borra cuando la ingesta
  (4.3) exista en `web/`.
