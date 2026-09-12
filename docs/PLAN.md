# Plan

Última ronda: 2026-09-12 — primer turno del orquestador. Se leyeron los seis
documentos, `ESTADO.md` (quinta sesión en curso: paso 1 hecho, 2 y 3
definidos) y el informe de la cuarta sesión dentro de `ESTADO.md`. Se
escribieron los encargos 02 y 03 para correr en paralelo.

## Backlog, en orden

- [en curso] 02 impacto-subcuadro — instante del impacto entre dos cuadros
  desde la señal de las manos (`t_sub_s`, `fraccion`, incertidumbre) y su
  lectura mínima en la pantalla de exploración. Paso 2 del pedido de Hernán.
- [en curso] 03 fps-truth-primer-delta — `fps_truth` deja de declarar VFR por
  el delta de arranque de la cámara y reporta el fps de reproducción sin él.
  Bug medido; afecta a la calibración con cronómetro cuando llegue.
- [pendiente] 04 lamina-minterpolate — cuadros interpolados con ffmpeg
  (rotulados "interpolados, no medidos", archivo aparte que ninguna métrica
  lee) entre los dos cuadros del impacto, para MIRAR. Paso 3; sólo cuando
  Hernán haya visto el 02.
- [pendiente] 05 ganancia-en-el-arnes — evaluar en `truth/` la ganancia de
  velocidad angular pelvis→tórax→brazo desde `face_on` y `down_the_line` con
  ratios conocidos; decidir si vive (con MDC y vistas) o muere. Fase 3.2 sin
  cerrar; hoy es descriptiva sin validar.
- [pendiente] 06 visor-desde-datos — dibujar el esqueleto desde `pose.npz`
  sobre el video en el reproductor de exploración (ADR-014, invariante 10),
  con `master.mp4` H.264 CFR (4.2) como referencia de cuadros. Cierra la
  desviación anotada en la cuarta sesión.
- [pendiente] 07 cola-con-cancelacion — trabajos cancelables y limpieza de
  `data/exploracion/` (crece ~20 MB por clip); portar el patrón de
  `padel-coach` (4.1). Fotos por evento como JPEG.
- [bloqueado por Hernán] material real — ver Preguntas. Con él: calibrar
  `capture-paths.yaml` (0.7), umbral de encuadre medido (1.3), intrínsecos con
  tablero (`kinelab_truth.calibrate`, 3.1), re-correr el arnés, pasar los clips
  por percepción y análisis.
- [pendiente] 08 golfdb-error-de-eventos — bajar el dataset (CC BY-NC, sólo
  para medir) y correr `kinelab.tools.golfdb_eval`; reporte por evento en
  cuadros (2.5). Después de decidir con Hernán si vale bajar 1400 videos ahora.
- [pendiente] Fase 5: repetibilidad primero, comparación de dos repeticiones
  (`compare.py` de la herencia). No antes de tener clips reales por el gate.

## Preguntas para Hernán

- ¿Qué teléfono va a ser el de captura? `CAPTURA.md` y ADR-003 están escritos
  para iPhone 17 Pro; el único material real es del Galaxy S22 Ultra, que
  ADR-003 deja fuera. Si es el S22: cronómetro de 10 s en cada modo con más de
  30 fps (FHD 60, Slow motion 240, ¿FHD 120?), por cable y por Galería, y con
  esos números se escribe un ADR nuevo que cite al 003. Está detallado en
  `ESTADO.md` §"Lo que le toca filmar a Hernán".
- ¿Qué viste de la pantalla de exploración? La lista de la cuarta sesión en
  `ESTADO.md` §"Para que pruebes vos". Lo que falle entra como encargo.
- GolfDB son 1400 videos de YouTube (CC BY-NC, sólo para medir): ¿bajarlos
  ahora o después del material propio?

## Aparcado

- Pádel: sólo cuando golf tenga MDC medidos (invariante 17).
- SynthPose como segundo estimador (1.5): necesita torch, sólo en `truth/`;
  después de los intrínsecos reales.
- La página vieja del gate en `service/static`: se borra cuando la ingesta
  (4.3) exista en `web/`.
