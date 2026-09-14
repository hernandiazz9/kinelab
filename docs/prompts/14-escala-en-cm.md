# 14 — La escala en cm: el +12,7 % de `px_to_cm`, medido con diez swings de mocap y corregido si hay una convención mejor

Para correr: `/encargo 14` en una sesión nueva. Leé antes el informe del 07
en `docs/informes/` (el nivel 1 y el punto 2 de "queda abierto").

## Contexto

`px_to_cm` divide por la altura cabeza→tobillos en px del cuadro de address
y multiplica por la estatura declarada. En un golfista inclinado en address
esas dos cosas no coinciden: en el mocap 64_01 son 1,4554 m aparentes contra
1,6405 m de estatura, +12,7 % sistemático en toda métrica en cm (el motor
sobre-lee el sway un +10 %: +12,7 % de la convención, −2,4 % de la
proyección). El arnés no lo ve porque su swing sintético usa la misma
convención en la verdad y en la medición. Es el cementerio 6 de
`HERENCIA.md` otra vez: una constante de normalización estimada una vez
devuelve números plausibles multiplicados por un factor. Hay diez swings de
mocap del sujeto 64 (64_01…64_10) para medirlo.

Leer: `kinelab/metrics/core.py` (`px_to_cm` y quién lo llama),
`sports/golf/metrics.py` (sólo lectura: las `definition` de las métricas en
cm), `truth/kinelab_truth/mocap.py` (`--nivel1`, `events_3d`, el mapeo),
`kinelab/perception/` (la escala por cuadro heredada, `body_height_series`),
`data/examples/cmu-mocap/ATRIBUCION.md`, `CONTRATO.md` §registro y
§Desviaciones, `HERENCIA.md` cementerio 6.

## Encargo

1. Bajá `64_03`…`64_10` (a mano, CMU pide no crawlear) a
   `data/examples/cmu-mocap/`, con sus sha256 en `ATRIBUCION.md`. Con los
   diez trials en `face_on`: para cada uno, la relación altura aparente
   cabeza→tobillos en address / estatura del ASF, y el sesgo de las siete
   métricas en cm contra la verdad 3D con la convención actual. Media y
   límites de acuerdo sobre diez swings de **un** sujeto, dicho así.
2. Candidatas, medidas con el mismo procedimiento sobre los diez:
   a. la actual: cabeza→tobillos en address × estatura;
   b. suma de largos de segmentos proyectados en address
      (tobillo→rodilla→cadera→hombro→cabeza) × estatura;
   c. máxima extensión vertical cabeza→tobillos dentro de la repetición
      (address→`follow_end`, o hasta el final del trial) × estatura;
   d. otra que la geometría o el código te sugieran, declarada.
   Tabla: sesgo medio y límites de acuerdo por métrica y candidata.
   **Criterio para implementar:** la que baje el sesgo medio absoluto a
   menos de la mitad del actual sin empeorar ninguna métrica más de 1 cm.
   Si ninguna lo logra, la actual se queda y el sesgo queda anotado como
   desviación con su número en `CONTRATO.md`.
3. Si hay ganadora: implementarla en `kinelab/metrics/core.py`, con la
   `definition` nueva escrita en `CONTRATO.md` §registro (el texto para
   `sports/golf/metrics.py` va en el informe: ese archivo lo toca el 13),
   versionado decidido y justificado (cambiar la convención de escala mueve
   el valor de siete métricas: al menos minor con nota, y decí por qué no
   major), tests con el swing sintético (erguido: la escala no cambia;
   inclinado: cambia lo esperado), y re-correr `datos` sobre
   `~/Desktop/cortado.mp4` y `data/incoming/vid1.mp4` para reportar cómo se
   mueven los siete números.

NO: no tocar `sports/golf/events.py`, `explore.py`, `service/`, `web/`,
`harness.py` ni `swing.py` (el 13 los usa), `sports/golf/metrics.py` (el 13),
`tests/test_fase2.py` (el 15: tus tests van en un archivo nuevo). No fijar
un factor numérico "de golfista" ajustado a este sujeto: la convención tiene
que ser geométrica.

## Cómo se prueba

`cd truth && .venv/bin/pytest -q` y `.venv/bin/pytest -q` en verde; la tabla
de los diez trials por candidata; las dos corridas reales con antes y
después.

## En paralelo

12 (`CAPTURA.md`, `docs/filmacion-s22.md`, `tests/test_service.py`), 13
(`truth/` salvo `mocap.py`, `sports/golf/mdc.yaml`, `sports/golf/metrics.py`,
`kinelab/metrics/` salvo `core.py`), 15 (`sports/golf/events.py`,
`kinelab/events/`, `tests/test_fase2.py`, `DECISIONES.md`). Vos:
`truth/kinelab_truth/mocap.py`, `truth/tests/test_mocap.py`,
`kinelab/metrics/core.py`, `CONTRATO.md`, `data/examples/`, y tu archivo de
test nuevo del motor.
