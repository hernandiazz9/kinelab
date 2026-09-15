# Plan

Última ronda: 2026-09-15 (tarde) — leídos los informes del 12, 13, 14 y 15.
Los cuatro cerraron. La ganancia muere en las dos vistas (artefacto de la
proyección, 80×); el instante sub-cuadro tiene MDC (2–3 ms); el umbral de
encuadre sale en px (717); la escala en cm cambió de convención con criterio
medido (sesgo medio 1,04 → 0,49 cm sobre diez swings de mocap); el top desde
`down_the_line` está arreglado (ADR-017) y en `face_on` lo limita la señal de
manos. Escritos 16 (contrato 2.0.0), 17 (gate en px, después del 16) y 18
(señal de manos, en paralelo con el 16). Hernán pregunta qué mostrar a un
cliente: respondido en la sesión y resumido en §Demo.

Regla de numeración: un ítem recibe número cuando se escribe su prompt; los
pendientes van sin número, en orden de ejecución.

## Demo hoy (lo que se puede mostrar sin mentir)

La pantalla de exploración con `vid1.mp4` (el swing con contacto real):
subir, la ficha del archivo, los avisos, los palitos sobre el video con
cámara lenta, cuadro a cuadro y zoom, el impacto entre dos cuadros con el
botón de los dos cuadros, las fotos por evento, la tabla por evento, «con
este archivo» (qué se calcula y qué no, con razón), el ejemplo de mocap
para mostrar que corre sobre otro material, y —cuando cierre el 19— el
swing 3D girable, que es lo único 3D honesto que hay: mocap medido con
marcadores, nunca un clip de celular. Lo que no se muestra: nada como
puntaje; la «rotación aparente» (artefacto, la borra el 16); el ejemplo
`down_the_line` hasta regenerarlo. Antes: re-subir los clips y regenerar los
ejemplos, porque los trabajos viejos tienen el top y la escala anteriores.

## Decisiones del orquestador

- 2026-09-15 · **ADR-018** (lo escribe el 16): la ganancia pelvis→tórax→brazo
  y `sequence_order` mueren; `analysis.json` 2.0.0. Con el schema abierto
  entran `metric_version` por métrica, `quality.scale_px` y el lugar para el
  MDC del sub-cuadro. Evidencia: 13 y 14.
- 2026-09-15 · El gate de encuadre pasa a **píxeles**: `body_height_px_min
  = 717`, procedencia `estimacion` (nivel 0, σ nominal); a revisar con
  `banco/scale_sweep.py` sobre los ONNX. Encargo 17.
- 2026-09-15 · La señal de manos se pesa por confianza con umbral; el top
  lleva banda cuando decide dentro del ruido; el MDC del sub-cuadro entra al
  evento. Encargo 18. ADR-008 recibe una nota: el código detecta el top por
  cambio de sentido (GolfDB), no por inflexión; `d2_inflection` no se usa.
- 2026-09-15 · El 3D girable sale **sólo** del mocap, que está medido con
  marcadores. De un clip monocular no se reconstruye profundidad: nivel 3 del
  contrato y ADR-010. La pantalla lo dice con todas las letras. Encargo 19.
  Camino futuro si se quiere el swing de Hernán en 3D: dos cámaras
  sincronizadas y calibración estéreo, que hoy no está en ninguna fase.
- 2026-09-15 · **Modelos de IA por API para una primera pasada: no.** Tres
  razones, cualquiera alcanza. (1) El producto es "en su Mac, sin nube"
  (`AGENTS.md`): mandar video de un alumno a un tercero rompe el principio y
  abre un problema de datos personales que hoy no existe. (2) No aporta nada
  que no tengamos local: el bbox lo da el detector, el conteo de personas ya
  está en `quality`, la vista se puede derivar de la pose. Un modelo
  multimodal no da posiciones articulares con precisión de píxel, que es lo
  único caro. (3) Rompe el determinismo que el contrato exige: `pose.npz`
  afirma reproducibilidad por checkpoint y proveedor, y una API remota no
  tiene sha256 ni versión estable. Lo que **sí** vale del pedido es la
  primera pasada barata **local**: ver más abajo, en el backlog.
- 2026-09-15 · **Deploy: sólo el visor, nunca el motor.** onnxruntime con
  CoreML, pesos de cientos de MB y 76 s por clip no entran en serverless. Se
  despliega una exportación estática con resultados ya calculados. El repo va
  **privado**: hoy tiene rutas de la máquina de Hernán, su correo en los
  commits y las coordenadas GPS del lugar donde filmó (informe del 11). El
  paso público (conectar Vercel) lo da Hernán, no una sesión.
- 2026-09-15 · Dato para el 20, medido al mirar el disco: el `overlay.mp4`
  de `vid1` pesa **245 MB** contra 93 MB del original, o sea ~115 Mb/s contra
  43. La pérdida de nitidez **no puede venir de falta de bitrate**; quedan el
  re-encode generacional y el obturador. El 20 lo separa igual.
- 2026-09-15 · Anotado, no cerrado: el +4,4 % residual de la escala (cadena
  desde el tobillo, estatura desde el piso). Se cierra sólo con un punto de
  contacto con el suelo validado contra una verdad que no sea nuestro propio
  mapeo. El checklist del iPhone se queda como está; la hoja operativa es
  `docs/filmacion-s22.md`. El 3,4× de disco del 11 es 2,4× (12).

- 2026-09-15 · El `fps_min` del gate de golf (100) **no se baja**. El S22 en
  modo Video da 60 como máximo; el camino a un clip que pase el gate es el
  cronómetro en Slow motion FHD 240. Un clip de 60 fps se mira en
  exploración con sus 8 de 12 métricas descriptivas; no se ingesta.
- 2026-09-15 · 4K desaconsejado por escrito (11: el recorte ya se reduce
  5,2× en FHD; 2,15× de tiempo, 2,4× de disco). WhatsApp como documento es
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
- [hecho] 12 captura-docs — `9f44eb5`…`840fc86`. Guía reescrita; 2,4× no 3,4×.
- [hecho] 13 arnes-ganancia-subcuadro-encuadre — `4342073`, `5373b2e`. La
  ganancia muere; sub-cuadro MDC 2,0–2,9 ms; encuadre 717 px propuesto.
- [hecho] 14 escala-en-cm — `5991922`, `9cf32ad`. Escala = máximo de la
  cadena proyectada en la repetición; sesgo 1,04 → 0,49 cm.
- [hecho] 15 top-desde-down-the-line — `0f8f18e`, `e909b2f`. ADR-017; en
  `down_the_line` el error del top pasa de +58 a −6 cuadros.
- [en curso] 16 contrato-2-0-0 — ADR-018, sin ganancia ni orden;
  `metric_version`, `scale_px`, lugar para el MDC del sub-cuadro; bumps del
  14; CSV y front sin «rotación aparente».
- [en curso] 18 senal-de-manos — centro de manos pesado por confianza, banda
  del top, MDC del sub-cuadro en el evento. Paralelo al 16.
- [en curso] 19 visor-3d-del-mocap — el swing del mocap, que es 3D medido,
  girable en la pantalla, con el colapso de la línea de caderas visible al
  girar hacia `down_the_line`. Sin dependencias nuevas. Pedido de Hernán.
- [en curso] 20 por-que-se-ve-borroso — medir de dónde viene el borrón de
  las manos (obturador contra nuestra recompresión) antes de tocar nada; el
  arreglo del overlay sólo si es nuestro y sólo cuando el 16 libere
  `explore.py`. Pedido de Hernán. Prompt escrito.
- [en curso] 22 github-y-demo-estatica — repo privado en GitHub, exportador
  de demo (recorte al sujeto, video liviano, JPEG, transformación afín
  declarada) y modo estático del front para desplegar en Vercel. El motor no
  se despliega: es un visor de resultados ya calculados. Prompt escrito.
- [pendiente] 21 visor-desde-datos — el esqueleto dibujado en canvas desde
  `pose.npz` sobre el video, con capas conmutables (el switch que pidió
  Hernán) y sin recompresión. Cierra la desviación de la invariante 10 y
  cumple ADR-014. Después del 16, 19 y 20. Prompt escrito.
- [pendiente] 17 gate-encuadre-en-px — después del 16. Prompt escrito.
- [pendiente] re-analizar desde `pose.npz` los trabajos de `data/exploracion/`
  (invariante 18) desde la pantalla, y que `mdc.yaml` lleve el `code_sha` de
  `kinelab/metrics/` para avisar cuando la tabla quedó vieja (13, pregunta 5).
- [pendiente] cola-con-cancelacion — cancelar y borrar trabajos desde la
  pantalla, paginado, fotos como JPEG, limpieza de `data/exploracion/`.
- [bloqueado por Hernán] **cronómetro en Slow motion FHD 240 con el S22** —
  la única llave para que este teléfono produzca un clip que pase el gate.
  Después: FHD 60 también, sesión de swings en el modo aprobado, encuadre
  más cerca. Con eso: `capture-paths.yaml` calibrado, ADR de Android con
  números, intrínsecos con tablero (3.1), re-correr el arnés, percepción y
  análisis sobre clips por el gate.
- [pendiente] pasada-barata-local — correr el detector en baja resolución
  cada N cuadros para encontrar el tramo del gesto y correr la pose completa
  sólo ahí. En `vid1` son 1066 cuadros de los cuales el swing son ~170: el
  ahorro es del orden de 5×. Local, determinista, dentro del stack. Es la
  versión sana de la idea de Hernán de "una primera pasada que dé parámetros
  a la pasada cara".
- [pendiente] golfdb-error-de-eventos (2.5), después de decidir con Hernán.
- [pendiente] Fase 5: repetibilidad; comparación de dos swings filmados con
  el mismo protocolo, sincronizados por evento, lado a lado y silueta
  fantasma; bandas descriptivas con procedencia. No antes de clips por el
  gate y del visor desde datos.

## Preguntas para Hernán

- **El cronómetro en Slow motion FHD 240.** Diez segundos, sin editar en
  Galería, archivo entero por cable o WhatsApp documento. Sin eso el S22 no
  puede pasar el gate en ningún modo. La guía se actualiza en el 12.
- Antes de la demo: re-subir `vid1.mp4` y `cortado.mp4` desde la pantalla
  (los trabajos viejos tienen el top y la escala anteriores) y regenerar los
  dos ejemplos de mocap con el comando del informe del 07.
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
