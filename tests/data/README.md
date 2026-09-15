# tests/data — fixtures grandes de los tests

Lo que no se puede construir con trigonometría dentro del test. Hoy hay uno
solo.

## `cmu-64_01-face_on/pose.npz` y `cmu-64_01-down_the_line/pose.npz`

Un swing de golf **real** (mocap óptico), proyectado con la cámara virtual del
arnés a 1080×1920 con el cuerpo al 80 % del alto, en las dos vistas. 448
cuadros a 120 fps exactos por construcción. Son `pose.npz` completos, con su
`provenance` adentro: sujeto, trial, sha256 del ASF y del AMC, la cámara
virtual con su focal, y las diez aproximaciones del mapeo a Halpe26.

| | sha256 |
|---|---|
| `cmu-64_01-face_on/pose.npz` | `889416bba4fa40d98069fcf3764e85b359eba912e5e61f693970cb4649c041be` |
| `cmu-64_01-down_the_line/pose.npz` | `c13c5d54aa3320dfc1642a6dd22200a007e0a5dde286687954051632ef759f38` |

**Para qué está.** Es el único material del repo donde la misma ejecución se ve
desde las dos vistas con verdad 3-D al lado, y es lo que hace falta para fijar
ADR-017: desde `down_the_line` el eje principal de las manos queda casi
vertical y aparece un tercer cambio de sentido —el fondo del arco antes del
impacto— que la regla vieja elegía como top. Con un swing sintético no se
reproduce: el arco sintético no vuelve sobre sí mismo.

**Por qué un archivo y no generarlo en el test.** `kinelab_truth.mocap` vive en
`truth/`, que tiene **su propio entorno virtual a propósito** (invariante 14):
un validador que comparte dependencias con lo que valida no es un validador. La
suite del motor corre con `.venv/bin/pytest` y no importa nada de `truth/`.

**Cómo se regenera** (desde `truth/`, con el entorno del arnés):

```bash
cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista face_on \
    --out ../tests/data/cmu-64_01-face_on --solo-pose
cd truth && .venv/bin/python -m kinelab_truth.mocap 64_01 --vista down_the_line \
    --out ../tests/data/cmu-64_01-down_the_line --solo-pose
```

Los ASF/AMC de origen están en `data/examples/cmu-mocap/` (`64.asf`,
`64_01.amc`) con su `ATRIBUCION.md`. Generados el 15 de septiembre de 2026 por
el encargo 15, con `kinelab_truth.mocap` en el commit `d03811e`.

**Atribución (CMU la pide textual, y viaja también dentro del `pose.npz`):**

> The data used in this project was obtained from mocap.cs.cmu.edu. The
> database was created with funding from NSF EIA-0196217.

Licencia y las tres preguntas de ADR-010 (código, pesos, datos), en
`data/examples/cmu-mocap/ATRIBUCION.md`. Acá no interviene ningún modelo: la
pose es geometría, no estimación.
