# CMU Graphics Lab Motion Capture Database — sujeto 64 (golf)

Captura de movimiento **real** de un golfista, de la base de datos pública de
la Carnegie Mellon University (`mocap.cs.cmu.edu`). Es el nivel 1 de validación
de ADR-009 —movimiento humano real, licencia libre— y la fuente del swing de
muestra que `kinelab_truth.mocap` proyecta con la cámara virtual del arnés.

## Atribución (el texto que pide CMU, textual)

> The data used in this project was obtained from mocap.cs.cmu.edu.
> The database was created with funding from NSF EIA-0196217.

## Licencia, como la declara el sitio

> This data is free for use in research projects. You may include this data in
> commercially-sold products, but you may not resell this data directly, even in
> converted form.

Y en las FAQs: *"The motion capture data may be copied, modified, or
redistributed without permission."* Eso permite que estos archivos viajen en el
repo. Lo único prohibido es **revender los datos en sí**, ni siquiera
convertidos; el `pose.npz` que sale de acá es un derivado dentro de un producto,
no una reventa del dataset.

Las tres preguntas de ADR-010, contestadas por separado:

| | |
|---|---|
| **datos** (estos archivos) | libres, con atribución; sin reventa directa |
| **código** para leerlos | propio, `truth/kinelab_truth/mocap.py`; ninguna dependencia nueva |
| **pesos** | no hay: acá no interviene ningún modelo entrenado |

CMU pide además, si se publican resultados, mandar la cita a
`jkh+mocap@cs.cmu.edu`. Y pide expresamente **no crawlear** la base: de las 30
tomas del sujeto 64 se bajaron a mano, una por una, las diez «Swing», que son
las únicas que el motor puede analizar.

## Los archivos

Bajados a mano de `http://mocap.cs.cmu.edu/subjects/64/`: el ASF, `64_01` y
`64_02` el 14 de septiembre de 2026; `64_03` a `64_10` el 15, para el encargo
14 (la escala en cm). **Los diez «Swing» del sujeto, y ninguno más**: no se
bajó ningún putt ni ninguna maniobra, y no se crawleó la base.

| archivo | bytes | sha256 |
|---|---|---|
| `64.asf` | 7 270 | `931aa1defb080cb8487817b92138cfc042d6bb5c2e84aecc7da0da3af20cd585` |
| `64_01.amc` | 356 466 | `ef1380e6ba40e97ad2b6aa9e1def83767d24f8e2b02d2d59049ad829c19ee23f` |
| `64_02.amc` | 393 045 | `cddcd98c0dde69cf22ec412ff15f9bde8a77168fb605ff32869778e3b8b2785d` |
| `64_03.amc` | 352 883 | `4ed45f30af228cc9a99a2b890fd8babfa1ce7730494ff6ecb5d414d8f365b366` |
| `64_04.amc` | 328 561 | `aa60487c42171358d3e2edf88062f7f3f0156502fd9d9f36c0959c8426467a04` |
| `64_05.amc` | 308 036 | `14c0fab8ecaf19229852ee97ec62c8437aee726a639f718882f2da6a5c7f2beb` |
| `64_06.amc` | 421 654 | `3b3025fc9cf96e69981f3d469eff7b9ad0059d2d7874965bdffbacf208aa0d2f` |
| `64_07.amc` | 299 796 | `fd1cca4dec308cfe200dedb6f26db9dc330729f2912a83b4c3ceec6e34c1296f` |
| `64_08.amc` | 289 725 | `d815e1815bc3d845acde7ca325cbb620eb959efabfa524bacce1ea48034cfc01` |
| `64_09.amc` | 360 687 | `1610ddacf457582c12bef00accc18a926497c7e0e6210cdbfedf5b3d60c5ce17` |
| `64_10.amc` | 447 487 | `2a1e5988512b3f832946c12636f741fb691f79ee2cce48f67b42bf13121ca058` |

El `.asf` es el esqueleto calibrado del sujeto (uno solo, compartido por todas
sus tomas); cada `.amc` es una toma. Los dos `sha256` van también dentro del
`provenance` de cada `pose.npz` que sale de ellos, así que un `pose.npz` siempre
dice de qué archivo exacto salió.

## Por qué el sujeto 64 y por qué los diez

El índice del sitio (`search.php?subjectnumber=64`) titula al sujeto **«golf»** y
lista sus 30 tomas: **1–10 «Swing»**, 11–15 «Putt», 16–20 «Placing Tee», 21–25
«Placing Ball», 26–30 «Picking up Ball». Es el único sujeto de golf de la base.
Todas a **120 Hz**, sistema Vicon de 12 cámaras MX-40, 41 marcadores.

Están los **diez «Swing»** y ninguna de las otras veinte: 11–15 son putt y 16–30
son poner la bola y el tee, que no son el gesto que mide `sports/golf/`.

Los diez tienen el gesto entero: más de medio segundo de quietud antes del
takeaway (el address del motor cae entre el cuadro 67 y el 183, sobre trials de
364 a 562 cuadros), que es lo que el address determinista necesita — se define
como el final de una ventana de quietud, no se detecta (ADR-008).

Por qué diez y no dos. El encargo 07 guardó `64_01` y `64_02` y vio con ellos que
el sesgo de las métricas en cm se repetía. El encargo 14 necesitaba **medir** una
convención de escala, no verla: diez swings dan una media con límites de acuerdo.
Siguen siendo **un solo sujeto**: de acá no sale ningún MDC ni ninguna
referencia. La tabla se rehace con

```bash
cd truth && .venv/bin/python -m kinelab_truth.mocap 64 --escala
```

**64_01 es el ejemplo** que queda en la pantalla, en las dos vistas. Los otros
nueve sólo se leen desde esa tabla.

Lo que estos trials **no** tienen: un finish quieto. Los diez cortan mientras el
golfista todavía se está acomodando, así que `follow_end` queda en `null` con su
razón, y `follow_duration_ms` también.

## Lo que hay que saber del formato

Está en el docstring de `truth/kinelab_truth/mocap.py`. Lo que más muerde: los
largos están en **pulgadas multiplicadas por `:units length` (0,45)**, así que a
metros van `× 0,0254 / 0,45`; vale para los largos de hueso y para la posición
de la raíz. Lo dice la FAQ de CMU y el módulo lo lee del propio archivo en vez
de fijar la constante.
