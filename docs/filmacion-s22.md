# Cómo filmar los swings (Galaxy S22 Ultra)

Gracias por filmar. Son tres partes: dejar el teléfono configurado (una vez),
filmar un cronómetro (dos clips cortos) y después los swings. Cada paso tiene
su porqué: el programa mide milésimas y centímetros, y si el video viene mal
los números salen mal sin avisar.

**Lo más importante de toda esta hoja es el cronómetro en Cámara lenta**
(sección 2, paso 1). Sin ese clip no hay un solo swing que el programa pueda
medir con los tiempos: hoy rechaza todo lo que se filma en modo Video normal,
porque el teléfono no pasa de 60 cuadros por segundo y hacen falta 100. Si sólo
podés hacer una cosa de esta hoja, hacé esa.

## 1. Configurar el teléfono (una sola vez)

- Abrí la cámara, modo *Video*. Tocá la resolución arriba y elegí *FHD 60*
  (1080p a 60 fps). **No filmes en 4K / UHD**: el programa achica el recorte
  del cuerpo a 256 píxeles de alto igual, así que 4K no agrega nada de
  precisión y sólo hace que el archivo pese más del doble y que la computadora
  tarde más del doble (medido sobre tus tres clips del 14/9: 2,15 veces más de
  proceso por cuadro).
- En Ajustes de la cámara: *Auto FPS* apagado. *Super Steady* apagado.
  *HDR10+* apagado.
- Usá siempre la lente normal, la de *1x*. Nada de gran angular (0.6x) ni
  de zoom.
- No edites ni recortes los videos en Galería después. Se mandan enteros, tal
  como salen.

## 2. El cronómetro (antes de cualquier swing)

Esto sirve para saber a qué velocidad graba de verdad el teléfono. Son dos
clips de 10 a 15 segundos, y el primero es el que desbloquea todo.

En una computadora, abrí un cronómetro con milésimas a pantalla completa
(buscá "online stopwatch milliseconds") y subí el brillo al máximo. Dejalo
corriendo. Filmá la pantalla desde un metro, llenando el cuadro, con el
cronómetro ya andando. Grabá 10 a 15 segundos y cortá. Recién después frená el
cronómetro: así el primer y el último cuadro tienen una lectura.

**Paso 1 — el cronómetro en *Cámara lenta* (Slow motion), FHD 240.** Es el
único modo del teléfono que graba más rápido de lo que el programa exige, y el
programa no puede confiar en él hasta que vea este clip. Es el que hay que
hacer sí o sí.

- [ ] Modo *Cámara lenta*, resolución *FHD*, velocidad *240*.
- [ ] 10 a 15 segundos de cronómetro llenando el cuadro, ya andando antes de
      empezar a grabar.
- [ ] **No lo edites, no lo recortes y no lo "guardes" desde el editor de
      Galería**: la cámara lenta de Samsung se puede editar y eso hornea la
      velocidad en el archivo. Se manda el archivo entero, como salió.
- [ ] Nombre: `crono-fhd240.mp4`.

**Paso 2 — el mismo cronómetro en *Video FHD 60*.**

- [ ] Modo *Video*, *FHD 60*. Mismas 10 a 15 segundos, mismo cronómetro.
- [ ] Sin editar, sin recortar, entero.
- [ ] Nombre: `crono-fhd60.mp4`.

**Cómo mandarlos** (sección 6): por el **mismo camino** por el que después vas
a mandar los swings. El camino es parte de la medición: si el cronómetro va
por cable y los swings por WhatsApp, lo medido no vale para los swings.

Hasta que los dos clips estén medidos, filmá los swings en *Video FHD 60*.

## 3. Dónde poner la cámara

Dos vistas, cada una en su propio video. Teléfono **vertical**, en trípode,
a la altura de la cintura o el pecho.

**Vista de frente (face-on)**
- La cámara mira al pecho del golfista, perpendicular a la línea de tiro.

**Vista desde atrás (down-the-line)**
- La cámara detrás del golfista, sobre la línea de tiro, mirando hacia donde
  va la pelota.

**La regla del encuadre: lo más cerca que permita tener los pies y el palo en
el top adentro del cuadro.** Movés el trípode hacia adelante hasta que esté por
salirse alguna de las dos cosas, y ahí lo dejás.

Esto es lo que más falta hoy. En los tres clips del 14/9 el cuerpo ocupaba
**28 % del alto del cuadro**, y el programa quiere bastante más: cuanto más
chico sale el cuerpo, menos píxeles tiene cada articulación y más se
equivocan los ángulos. Las distancias fijas que decía esta hoja antes —3 y
3,5 metros— dejan el cuerpo demasiado chico con el teléfono vertical; por eso
ahora la regla es la de arriba y no un número de metros. **Acercate todo lo
que puedas sin perder los pies ni el palo.**

Fondo simple. Una sola persona en cuadro: si alguien pasa por atrás, esa
toma no sirve.

## 4. Luz

Al aire libre, de día, sin contraluz: el sol detrás de la cámara o de
costado, nunca de frente. Con poca luz las manos salen borrosas y eso es
peor que cualquier otra cosa. Nada bajo techo. En *Cámara lenta* hace falta
todavía más luz que en Video.

## 5. Los swings

- Un video continuo por vista, con 10 a 20 swings adentro, sin cortar entre
  swing y swing. Primero de frente, después desde atrás.
- Entre swing y swing, quedate quieto un par de segundos en la posición de
  address: el programa usa esa quietud para saber dónde empieza cada uno.
- Nombres: `swings-frente-fhd60.mp4` y `swings-atras-fhd60.mp4` (o `-fhd240`
  si ya se decidió filmar en cámara lenta).

## 6. Cómo mandar los archivos

Por orden de preferencia:

1. **Por cable**, copiando desde la carpeta `DCIM/Camera` del teléfono. Es el
   camino de referencia: llega el archivo exacto.
2. **Por WhatsApp, pero como *documento*.** Adjuntar → **Documento** → buscar
   el archivo. Está medido sobre tus tres clips: así **WhatsApp no toca el
   archivo** — llega con el mismo codec, el mismo bitrate y hasta los datos
   internos de Samsung intactos.

**Nunca por WhatsApp como video** (adjuntar desde Galería o desde la cámara del
chat): eso lo recomprime, le baja la resolución y le borra los datos del
teléfono. Se pierde justo lo que se mide. Lo mismo vale para mandarlo por
Telegram o subirlo a Drive desde la app de fotos.

Y en cualquiera de los dos caminos: **el archivo entero, sin editar ni recortar
en Galería.**

Cualquier duda, preguntá antes de filmar. Es más fácil corregir el trípode
que repetir la sesión.
