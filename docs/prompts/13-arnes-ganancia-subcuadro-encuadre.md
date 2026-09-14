# 13 — Arnés: la ganancia vive o muere, el MDC del instante sub-cuadro, y el umbral de encuadre desde el barrido de tamaño

Para correr: `/encargo 13` en una sesión nueva. Leé antes los informes del
02, 07 y 11 en `docs/informes/`.

## Contexto

Tres cosas que sólo el arnés puede contestar:

- La **ganancia** de velocidad angular pelvis→tórax→brazo (`summary.gain`)
  se calcula del giro aparente de las líneas de cadera y hombros en el plano
  de imagen. Desde `face_on` la rotación axial se ve como escorzo. Medido:
  `hip_line_rate_deg_s` llega a 3244 °/s en el mocap y a 3662–3979 en los
  clips del S22, y las ganancias salen menores a 1. No es una métrica
  registrada; hoy es descriptiva y sospechosa (`ESTADO.md`, 07 punto 3, 11).
- El **instante sub-cuadro del impacto** (encargo 02) no tiene MDC.
- El **umbral de encuadre** (`body_height_frac_min`, ESPECIFICACION 1.3)
  sigue en `None`. El barrido de tamaño del sujeto (100–900 px) ya existe en
  el arnés, y hay cuatro clips reales entre 973 y 1132 px de cuerpo.

Leer: `truth/kinelab_truth/harness.py`, `swing.py`, `chain.py`, `camera.py`;
`truth/reports/`; `sports/golf/mdc.yaml` y `sports/golf/metrics.py` (cómo se
calcula la ganancia hoy y dónde vive en `summary`); `kinelab/metrics/`
(repetibilidad y ganancia); `sports/golf/events.py` (el sub-cuadro, sólo
lectura); `CONTRATO.md` §summary, §registro y §Niveles; ESPECIFICACION
3.1–3.3; `truth/kinelab_truth/mocap.py` sólo lectura (si querés contrastar
con un humano real, el 07 dejó cómo).

## Encargo

1. **Ganancia.** Darle al swing paramétrico velocidades angulares 3D
   conocidas de pelvis, tórax y brazo con ratios conocidos (1,5 y 1,5; y
   variantes 1,0 / 2,0), proyectar en `face_on` y `down_the_line` con los
   barridos (azimut, elevación, ruido, tamaño, fps), y medir sesgo y límites
   de acuerdo de las ganancias que calcula el motor contra los ratios
   verdaderos. Veredicto por vista con la regla del arnés (MDC contra un
   ancho de rango declarado `estimacion`, como las demás). Si en ninguna
   vista es defendible, muere: decilo y listá qué archivos la tocan
   (`explore.py`, CSV, `summary`) para el encargo que la borre; **no la
   borres vos**. Si es defendible en alguna vista, entra al registro con sus
   seis cosas (id, unidad `ratio`, nivel, vistas, `fps_min`, MDC) y
   `summary.gain` pasa a alimentarse del registro.
2. **Instante sub-cuadro del impacto.** Sesgo y MDC en cuadros y en ms con
   el swing paramétrico (cruce conocido), barriendo fps (240→30), ruido y
   tamaño. Escribirlo en `mdc.yaml` como entrada del evento, y que
   `datos-eventos.json` y `analysis.json` lo lleven si el registro tiene
   lugar para eventos; si no, en `truth/reports/` y anotado en el informe.
3. **Umbral de encuadre.** Del barrido de tamaño existente, para cada
   métrica de nivel 1 con MDC: a qué altura de cuerpo en px su MDC supera la
   tolerancia (5 cm, 30 ms, 15°). Tabla por métrica, propuesta de
   `body_height_px_min` único para el gate, en px, y cómo caen los cuatro
   clips reales (973, 1083, 1104, 1132 px). **No fijar el umbral en el
   gate**: es decisión del orquestador con `CAPTURA.md`.

NO: no tocar `kinelab/explore.py`, `service/`, `web/`,
`sports/golf/events.py`, `kinelab/metrics/core.py` (lo toca el 14),
`truth/kinelab_truth/mocap.py` (ídem), `CONTRATO.md` (ídem: si el contrato
tiene que cambiar, va en el informe con el texto propuesto),
`tests/test_fase2.py` (lo toca el 15: tus tests van en un archivo nuevo,
`tests/test_arnes_registro.py`, o en `truth/tests/`). `mdc.yaml` lo escribe
el arnés, nunca a mano.

## Cómo se prueba

`cd truth && .venv/bin/pytest -q` en verde; el arnés corre entero y
regenera `sports/golf/mdc.yaml` y `truth/reports/<fecha>.json`;
`.venv/bin/pytest -q` del motor en verde. El informe lleva las tres tablas,
los tres veredictos y el tiempo de la corrida del arnés.

## En paralelo

12 (`CAPTURA.md`, `docs/filmacion-s22.md`, `tests/test_service.py`), 14
(`truth/kinelab_truth/mocap.py`, `kinelab/metrics/core.py`, `CONTRATO.md`,
`data/examples/`), 15 (`sports/golf/events.py`, `kinelab/events/`,
`tests/test_fase2.py`, `DECISIONES.md`). Vos: `truth/` salvo `mocap.py`,
`truth/reports/`, `sports/golf/mdc.yaml`, `sports/golf/metrics.py`,
`kinelab/metrics/` salvo `core.py`, y tus archivos de test nuevos.
