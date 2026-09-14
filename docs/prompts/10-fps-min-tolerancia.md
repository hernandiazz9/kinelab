# 10 — `fps_min` con tolerancia: un clip de 29,998 fps es un clip de 30

Para correr: `/encargo 10` en una sesión nueva. Leé antes el informe del 06.

## Contexto

Con ADR-016 el `fps_real` de un camino declarado es el medido del archivo. El
original del S22 da 29,998 fps, y el registro compara `fps_real >= fps_min`
contra `fps_min: 30.0`, escrito por el arnés, que barre en fps enteros: las
métricas de 30 fps mueren por dos milésimas. Va a pasar con todo clip real:
las tasas de video son NTSC (29,97 · 59,94 · 119,88 · 239,76) y la tabla del
arnés es nominal (30 · 60 · 120 · 240).

Decisión del orquestador: la comparación lleva una tolerancia del 0,5 % en
un solo lugar del registro, documentada. La tabla del arnés sigue en fps
nominales enteros; `mdc.yaml` no se toca a mano.

Leer: `kinelab/metrics/registry.py` (`fps_min_met`, `judgment_allowed`),
`sports/golf/metrics.py` y `sports/golf/mdc.yaml` (de dónde sale cada
`fps_min`), `truth/kinelab_truth/harness.py` (sólo para ver que escribe
enteros), `tests/test_fase2.py`, `CONTRATO.md` §sextuplo y §registro.

## Encargo

1. En el registro: `fps_min_met = fps_real >= fps_min · (1 − FPS_MIN_TOL)`
   con `FPS_MIN_TOL = 0.005`, constante nombrada, con el porqué en el
   comentario y en `CONTRATO.md` §sextuplo (una frase: tasas NTSC contra
   nominales enteros). El `null_reason` sigue diciendo los dos números.
2. Tests: 29,998 contra 30 pasa; 29,97 contra 30 pasa; 119,88 contra 120
   pasa; 29,8 contra 30 no; y el swing sintético a 29,97 fps calcula las
   métricas de `fps_min` 30 y deja en `null` las de 60 y 120, con la razón.

NO: no tocar el gate ni `CAPTURA.md` (`fps_min_for_gesture` es otra regla,
con umbral 100 y sin tolerancia: decidirlo es otra conversación); no tocar
`mdc.yaml` ni `truth/`; no tocar `explore.py`, `service/`, `web/`.

## Cómo se prueba

- `.venv/bin/pytest -q` en verde.
- Corrida real, no test: `python -m kinelab datos
  ~/Desktop/20260907_170638.mp4 --altura-m 1.75 --camino
  s22ultra-video-fhd30-cable`. En el informe, cuáles de las 12 métricas
  ahora tienen valor (número, unidad, `sin_verificar`, `judgment_allowed`
  falso) y cuáles siguen en `null` con su razón. Y `cortado.mp4` con
  `desconocido-video`: lo mismo.

## En paralelo

El 07 toca `truth/`, `data/examples/`, `kinelab/explore.py`; el 09 toca
`service/`, `web/` y quizá una línea de `explore.py`. No toques nada de eso.
