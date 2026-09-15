# 17 — El gate de encuadre en píxeles, no en fracción del cuadro

Para correr: `/encargo 17` en una sesión nueva, **después de que el 16 haya
cerrado** (los dos tocan `sports/golf/config.py`). Leé antes el informe del
13 (§3) y el del 11.

## Contexto

`body_height_frac_min` sigue en `None` desde la Fase 1. El arnés (13) mostró
que con el ruido relativo de la spec el MDC es invariante al tamaño (álgebra,
no casualidad) y que sólo un ruido absoluto en px da un umbral: con σ = 4,9 px
(el nominal), `head_lift_top_cm` cruza sus 5 cm de tolerancia a **717 px** de
cuerpo; con σ = 2,3 px (la mediana medida en los clips reales), a 345 px. Y
la fracción engaña: en 4K un 28 % del alto son 1104 px, más que el 80 % de un
1080p. Los cuatro clips reales tienen 973–1132 px.

Decisión del orquestador: el gate mide **píxeles**, `body_height_px_min =
717`, procedencia `estimacion` (nivel 0 del arnés, σ nominal, sin
estimador), a revisar cuando `banco/scale_sweep.py` corra sobre los ONNX. La
regla 80–90 % de `CAPTURA.md` queda como objetivo de campo, no como gate.

Leer: `kinelab/ingest/gate.py` (el chequeo `body_height_frac`),
`kinelab/perception/framing.py` (`body_height_px`), `sports/golf/config.py`,
`sports/golf/mdc.yaml` §framing, `tests/test_gate.py`,
`tests/test_perception.py`, `CAPTURA.md` §Encuadre y tabla del gate,
`CONTRATO.md` §capture.json (el chequeo en `gate.checks`).

## Encargo

1. `sports/golf/config.py`: `body_height_px_min: 717` con comentario de
   procedencia y fecha; el nombre viejo desaparece.
2. El chequeo del gate pasa a `body_height_px`: valor = mediana de
   `body_height_px` de la toma, esperado `>= 717`, frase para el entrenador
   con los dos números y qué hacer ("el jugador mide N px en el cuadro; hacen
   falta 717: acercá la cámara o filmá en más resolución"). `passed: null`
   con razón si la percepción todavía no corrió (el gate de ingesta corre
   antes que la pose: decí cómo queda el orden y dónde se evalúa).
3. `CAPTURA.md`: la fila del gate y una frase en §Encuadre con el número y
   su procedencia; `mdc.yaml` §framing deja de decir que nadie lo lee.
4. Tests: una toma sintética a 600 px rechaza con la frase; a 900 px pasa;
   los cuatro clips reales (corrida real, en el informe) pasan con sus px.

NO: no tocar el motor fuera de `gate.py` y `config.py`; no tocar
`CAPTURA.md` fuera de esas dos líneas; no cambiar el 717 "porque parece
mucho": si el código te muestra que el número está mal medido, decilo en el
informe y dejalo.

## Cómo se prueba

`.venv/bin/pytest -q` en verde; ingesta real de `data/incoming/vid1.mp4` y
del original del 7/9 con su camino declarado: el chequeo nuevo con su valor
en el informe.

## En paralelo

Ninguno sobre tus archivos. El 18 puede estar corriendo en `kinelab/events/`
y `sports/golf/events.py`.
