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
tomas del sujeto 64 se bajaron a mano las tres que se iban a mirar, y quedaron
las dos elegidas.

## Los archivos

Bajados el 14 de septiembre de 2026 de `http://mocap.cs.cmu.edu/subjects/64/`.

| archivo | bytes | sha256 |
|---|---|---|
| `64.asf` | 7 270 | `931aa1defb080cb8487817b92138cfc042d6bb5c2e84aecc7da0da3af20cd585` |
| `64_01.amc` | 356 466 | `ef1380e6ba40e97ad2b6aa9e1def83767d24f8e2b02d2d59049ad829c19ee23f` |
| `64_02.amc` | 393 045 | `cddcd98c0dde69cf22ec412ff15f9bde8a77168fb605ff32869778e3b8b2785d` |

El `.asf` es el esqueleto calibrado del sujeto (uno solo, compartido por todas
sus tomas); cada `.amc` es una toma. Los dos `sha256` van también dentro del
`provenance` de cada `pose.npz` que sale de ellos, así que un `pose.npz` siempre
dice de qué archivo exacto salió.

## Por qué el sujeto 64 y por qué estos dos trials

El índice del sitio (`search.php?subjectnumber=64`) titula al sujeto **«golf»** y
lista sus 30 tomas: **1–10 «Swing»**, 11–15 «Putt», 16–20 «Placing Tee», 21–25
«Placing Ball», 26–30 «Picking up Ball». Es el único sujeto de golf de la base.
Todas a **120 Hz**, sistema Vicon de 12 cámaras MX-40, 41 marcadores.

De los diez «Swing» se miraron los tres primeros y quedaron **64_01** y
**64_02**, por tres razones:

1. **Son el gesto entero.** Los dos tienen más de un segundo de quietud antes
   del takeaway (address 145 y 182, sobre 448 y 493 cuadros), que es lo que el
   address determinista necesita: se define como el final de una ventana de
   quietud, no se detecta (ADR-008).
2. **No son putts ni maniobras.** 11–15 son putt y 16–30 son poner la bola y el
   tee: no son el gesto que mide `sports/golf/`.
3. **Son dos y no uno** para que el número de nivel 1 no dependa de una sola
   toma. 64_03 se miró y da la misma lectura, pero no se guardó: con dos alcanza
   para ver si el sesgo se repite, y la base pide no acumular copias.

**64_01 es el ejemplo** que queda en la pantalla, en las dos vistas. 64_02 es la
segunda lectura del número de nivel 1.

Lo que estos trials **no** tienen: un finish quieto. Los dos cortan mientras el
golfista todavía se está acomodando, así que `follow_end` queda en `null` con su
razón, y `follow_duration_ms` también.

## Lo que hay que saber del formato

Está en el docstring de `truth/kinelab_truth/mocap.py`. Lo que más muerde: los
largos están en **pulgadas multiplicadas por `:units length` (0,45)**, así que a
metros van `× 0,0254 / 0,45`; vale para los largos de hueso y para la posición
de la raíz. Lo dice la FAQ de CMU y el módulo lo lee del propio archivo en vez
de fijar la constante.
