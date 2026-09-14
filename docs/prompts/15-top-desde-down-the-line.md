# 15 — El top desde `down_the_line`: el cambio de signo que importa no es el último (ADR-017)

Para correr: `/encargo 15` en una sesión nueva. Leé antes el informe del 07
en `docs/informes/` (punto 1 de "queda abierto").

## Contexto

ADR-008 fija el top por inflexión; el código lo implementa como el
**último** cambio de signo de la velocidad de las manos proyectada sobre el
eje principal address→impact. Medido sobre el mocap 64_01: en `face_on` hay
dos cambios (145, 270) y el último es el top; en `down_the_line` el eje
queda casi vertical, hay tres (158, **263**, 328), gana 328 —el fondo del
arco justo antes del impacto— y el downswing sale de 5 cuadros. El top
verdadero está en la señal; lo pierde la regla. Mientras tanto
`down_the_line` no sirve para medir duraciones.

Decisión del orquestador, a escribir como **ADR-017** en `DECISIONES.md`
citando ADR-008: entre address e impacto, el top es el cambio de signo de la
velocidad proyectada en el que las manos están **más lejos** de su posición
de address (distancia proyectada en el plano de imagen), no el último. Es la
versión continua de "el palo cambia de dirección en lo más alto", vale en
las dos vistas, y coincide con el criterio `events_3d` que el 07 dejó en
código. Ajustá el texto si el código te muestra algo que lo contradiga, y
decilo en el informe.

Leer: `sports/golf/events.py`, `kinelab/events/primitives.py`,
`tests/test_fase2.py`, `tests/helpers/synth_swing.py`,
`truth/kinelab_truth/mocap.py` (`events_3d`, sólo lectura), ADR-008 en
`DECISIONES.md`, `CONTRATO.md` §events[].

## Encargo

1. Implementar la regla en `sports/golf/events.py` (o como primitiva en
   `kinelab/events/primitives.py` si es genérica: "cambio de signo de mayor
   excursión"). El `method` del evento top nombra la regla nueva.
2. Tests: mocap 64_01 en `down_the_line` da top 263 ± 2 y en `face_on`
   sigue en 270 (generá el `pose.npz` en el test con `kinelab_truth.mocap`
   si el entorno lo permite, o guardá un fixture chico en `tests/data/`:
   elegí y decilo); el swing sintético no cambia; un caso construido con
   tres cambios de signo donde el último no es el más lejano; y un bug
   inyectado (elegir el más cercano) tiene que hacer fallar un test.
3. ADR-017 en `DECISIONES.md`. `ESTADO.md` con tu sección. Los eventos ya
   calculados no se recalculan solos (invariante 18).

NO: no tocar address ni impact ni sus umbrales; no tocar el filtrado; no
tocar `explore.py`, `service/`, `web/`, `truth/` (salvo leer),
`kinelab/metrics/`, `CONTRATO.md` (si hace falta una línea ahí, va en el
informe: lo toca el 14).

## Cómo se prueba

`.venv/bin/pytest -q` en verde. Corridas reales, tabla antes/después en el
informe: mocap 64_01 y 64_02 en las dos vistas (top y duraciones),
`~/Desktop/cortado.mp4` (top 39), `data/incoming/vid1.mp4` (726),
`data/incoming/vid2.mp4` (115), `~/Desktop/20260907_170638.mp4` (141). Los
de `face_on` no deberían moverse; si alguno se mueve, explicá por qué con
la señal.

## En paralelo

12 (`CAPTURA.md`, `docs/filmacion-s22.md`, `tests/test_service.py`), 13
(`truth/`, `sports/golf/mdc.yaml`, `sports/golf/metrics.py`,
`kinelab/metrics/`), 14 (`truth/kinelab_truth/mocap.py`,
`kinelab/metrics/core.py`, `CONTRATO.md`, `data/examples/`). Vos:
`sports/golf/events.py`, `kinelab/events/`, `tests/test_fase2.py`,
`tests/data/` si lo creás, `DECISIONES.md`.
