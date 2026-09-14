# Plan

Última ronda: 2026-09-15 — leídos los informes del 07, 09, 10 y 11. Los
cuatro cerraron. Hallazgos que cambian el plan: el nivel 1 con mocap real
(07) encontró un sesgo sistemático de +12,7 % en toda métrica en cm y una
falla del detector de top desde `down_the_line`; el 11 confirmó que ningún
modo Video del S22 llega a los 100 fps del gate. Escritos 12, 13, 14 y 15,
sin archivos en común. Skill `/encargo` ajustada: el backend se puede
levantar para `curl`; dos sesiones nunca editan el mismo archivo.

Regla de numeración: un ítem recibe número cuando se escribe su prompt; los
pendientes van sin número, en orden de ejecución.

## Decisiones del orquestador

- 2026-09-15 · El `fps_min` del gate de golf (100) **no se baja**. El S22 en
  modo Video da 60 como máximo; el camino a un clip que pase el gate es el
  cronómetro en Slow motion FHD 240. Un clip de 60 fps se mira en
  exploración con sus 8 de 12 métricas descriptivas; no se ingesta.
- 2026-09-15 · 4K desaconsejado por escrito (11: el recorte ya se reduce
  5,2× en FHD; 2,15× de tiempo, 3,4× de disco). WhatsApp como documento es
  un camino limpio, medido; como video, no. Va a `CAPTURA.md` y a la guía
  (encargo 12).
- 2026-09-15 · El top es el cambio de signo de mayor distancia al address,
  no el último (ADR-017, lo escribe el 15). Evidencia: mocap 64_01 desde
  `down_the_line`, 07 punto 1.
- 2026-09-15 · La convención de `px_to_cm` se mide con diez trials de mocap
  y se cambia sólo si una candidata geométrica baja el sesgo a la mitad sin
  empeorar ninguna métrica (14). Nada de factores ajustados a un sujeto.
- 2026-09-15 · El umbral de encuadre del gate sale del barrido de tamaño del
  arnés, en px, no de un porcentaje (13 lo propone; se fija en la ronda
  siguiente). La regla 80–90 % de `CAPTURA.md` queda como objetivo con la
  nota medida de que en vertical no es alcanzable con la lente principal.
- 2026-09-15 · Pantalla (09): los `slomo` sin calibrar se listan
  deshabilitados; el bloque de métricas queda debajo del reproductor; los
  trabajos viejos del 12/9 no se recalculan (borrarlos es de Hernán). El
  ejemplo de mocap se regenera con un comando, no se commitea (07).
- 2026-09-14 · `fps_min` con tolerancia del 0,5 % (hecho, 10). Caminos
  declarados sin calibrar, ADR-016 (hecho, 06). Fps efectivo en gate y motor
  (hecho, 04). Interpolación cerrada, herramienta se queda (05). Silueta
  "ideal": no; ejemplo de mocap, sí, nunca "referencia" (07).

## Backlog, en orden

- [hecho] 02 · 03 · 04 · 05 · 06 · 08 (ver informes).
- [hecho] 07 ejemplo-mocap — `313acd5`, `db9ffad`. Ejemplo en la lista;
  primer nivel 1: desplazamientos con sesgo bajo el MDC, duraciones con el
  error de eventos encima (+41,7 ms backswing).
- [hecho] 09 ficha-y-selector — `b0b46c9`, `fcabfc6`. Hernán prueba.
- [hecho] 10 fps-min-tolerancia — `e2204ee`, `e7d026d`.
- [hecho] 11 diagnostico-vid123 — `6693c84`, `345b340`. Tres swings UHD 60
  por WhatsApp documento; `vid1` con contacto real (impacto 741→742
  verificado contra la pelota); gate: rechazo por fps solamente.
- [en curso] 12 captura-docs — `CAPTURA.md`, la guía de filmación y el test
  que caduca por fecha.
- [en curso] 13 arnes-ganancia-subcuadro-encuadre — la ganancia vive o
  muere; MDC del instante sub-cuadro; umbral de encuadre en px propuesto.
- [en curso] 14 escala-en-cm — el +12,7 % de `px_to_cm` con diez trials;
  convención nueva sólo si gana con criterio.
- [en curso] 15 top-desde-down-the-line — ADR-017.
- [pendiente] fijar el umbral de encuadre en el gate (con la tabla del 13) y
  borrar la ganancia de explore/CSV si el 13 la mata.
- [pendiente] visor-desde-datos — esqueleto desde `pose.npz` sobre el video
  en el reproductor (ADR-014, invariante 10) con `master.mp4` H.264 CFR
  (4.2). Cierra la desviación de la cuarta sesión.
- [pendiente] cola-con-cancelacion — cancelar y borrar trabajos desde la
  pantalla, paginado, fotos como JPEG, limpieza de `data/exploracion/`.
- [bloqueado por Hernán] **cronómetro en Slow motion FHD 240 con el S22** —
  la única llave para que este teléfono produzca un clip que pase el gate.
  Después: FHD 60 también, sesión de swings en el modo aprobado, encuadre
  más cerca. Con eso: `capture-paths.yaml` calibrado, ADR de Android con
  números, intrínsecos con tablero (3.1), re-correr el arnés, percepción y
  análisis sobre clips por el gate.
- [pendiente] golfdb-error-de-eventos (2.5), después de decidir con Hernán.
- [pendiente] Fase 5: repetibilidad; comparación de dos swings filmados con
  el mismo protocolo, sincronizados por evento, lado a lado y silueta
  fantasma; bandas descriptivas con procedencia. No antes de clips por el
  gate y del visor desde datos.

## Preguntas para Hernán

- **El cronómetro en Slow motion FHD 240.** Diez segundos, sin editar en
  Galería, archivo entero por cable o WhatsApp documento. Sin eso el S22 no
  puede pasar el gate en ningún modo. La guía se actualiza en el 12.
- Probar la pantalla del 09 (selector, ficha, avisos, "con este archivo"):
  seis pasos al final de `docs/informes/2026-09-14-09-ficha-y-selector.md`.
  Y el ejemplo de mocap del 07: seis pasos al final de su informe; el de
  `down_the_line` tiene el top mal a propósito hasta que cierre el 15.
- Mirar las láminas del 05 si todavía no: `open ~/Desktop/cortado.kinelab/lamina-44-45-x*.png`.
- Los cinco trabajos del 12/9 en la lista muestran el fps bruto de antes:
  ¿se borran (`rm -rf data/exploracion/<id>`) o se quedan?
- Para la próxima sesión de swings: FHD 60, más cerca. Idea a probar en un
  solo clip, no en la guía todavía: la lente 3× del S22 Ultra a ~3 m daría
  el cuerpo al ~60 % del alto; es otra lente y necesitaría su tablero.
- ¿A quién filmar como referencia para Fase 5? ¿GoPro? ¿GolfDB ahora o
  después?

## Aparcado

- Instante sub-cuadro del top: no pedido; la primitiva de cruce no aplica.
- Lámina interpolada en el front: no; experimento cerrado.
- Pádel (invariante 17). SynthPose (1.5) después de los intrínsecos reales.
- La página vieja del gate en `service/static`: se borra con la ingesta 4.3.
