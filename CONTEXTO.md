# kinelab — CONTEXTO.md

Glosario del dominio y reglas invariantes. Se lee antes de tocar cualquier
módulo. El vocabulario es de metrología antes que de deporte, a propósito: el
producto es un instrumento de medición, y los dos prototipos anteriores
fallaron por tratarlo como una app.

## Vocabulario

- **motor** — el paquete `kinelab/`. Librería Python pura. Entra un video, su
  `capture.json` y una config de deporte; sale `pose.npz` y `analysis.json`. No
  sabe de interfaces, servidores ni usuarios. Si para probar una métrica hay que
  levantar algo, está mal construido.
- **deporte / config de deporte** — `sports/<deporte>/`. Gestos, vistas
  obligatorias, eventos con su definición geométrica, métricas permitidas por
  vista, gates de encuadre y de fps. Todo lo específico del deporte vive ahí y
  en ningún otro lado.
- **gesto** — el movimiento que se analiza: swing de driver, bandeja. Un gesto
  tiene vistas válidas y eventos definidos. No "golpe" (es de pádel), no
  "ejercicio" (es vocabulario del entrenador, no del motor).
- **sesión** — una tanda: un atleta, un gesto, una vista, un clip, N
  repeticiones. La unidad de almacenamiento.
- **repetición** — una ejecución del gesto dentro de una sesión. La unidad de
  análisis. Un clip son N repeticiones comparables entre sí; la variación
  entre ellas es información, no ruido.
- **vista** — posición de cámara con nombre: `face_on`, `down_the_line` en
  golf. Cada métrica declara desde qué vistas es válida; el motor se niega a
  calcularla desde otra.
- **evento** — instante del gesto definido por un criterio geométrico que un
  humano puede verificar en un cuadro (Top: el palo cambia de dirección).
  Lleva su tolerancia en cuadros.
- **address** — el evento cero del golf. Determinista, no detectado: último
  cuadro de una ventana pre-movimiento estable.
- **camino de captura** — combinación de dispositivo, modo de grabación y
  transferencia, con su fps real calibrado. Es configuración
  (`data/capture-paths.yaml`), no metadato del archivo.
- **gate** — validación bloqueante de entrada. Rechaza la sesión con una razón
  legible por el entrenador. Nunca degrada en silencio.
- **piso de ruido** — el error del instrumento para una métrica dada. Si la
  señal es menor que el piso, la métrica no existe, por más que el código la
  calcule.
- **MDC** — mínimo cambio detectable: `1,96 · √2 · SEM`. El número que decide
  si una métrica puede mostrarse como juicio.
- **nivel** de una métrica — 1 defendible, 2 condicional, 3 no se construye.
  Ver `CONTRATO.md` §Niveles.
- **descriptivo / juicio** — un número descriptivo se muestra con unidad y
  confianza; un juicio lo compara contra un rango. Sólo una métrica de nivel 1
  con MDC medido puede ser juicio.
- **repetibilidad** — variación de una métrica entre repeticiones de la misma
  sesión. Desvío estándar absoluto para escalares; DTW normalizado para curvas.
  Siempre con el piso de ruido del propio pipeline restado y declarado.
- **ganancia** — cociente de picos de velocidad angular entre segmentos
  consecutivos (pelvis→tórax→brazo). Es una magnitud. Reemplaza al "orden de
  la secuencia cinemática", que no discrimina nivel ni en tenis ni en golf.
- **arnés de verdad** — `truth/`, con su propio entorno. Esqueleto paramétrico
  proyectado con cámara virtual de intrínsecos medidos, más barridos. Produce
  sesgo, límites de acuerdo y MDC por métrica y por condición.
- **procedencia** — de dónde sale un número: `medido_aqui`, `pares`,
  `fabricante`, `estimacion`, `sin_verificar`. Todo rango de referencia la
  lleva o no entra.
- **master** — `master.mp4`, la transcodificación H.264 CFR de GOP corto que
  ven tanto el motor como el reproductor. Todo índice de cuadro se refiere a
  este archivo, nunca al original.

## Reglas invariantes (no se re-preguntan; se rompen sólo con un ADR nuevo)

1. **La pose cruda es la única fuente de verdad.** Todo lo derivado se recalcula
   desde `pose.npz`. Nunca se vuelve a correr el modelo para cambiar una
   métrica.
2. **El fps real es configuración calibrada con cronómetro.** El motor rechaza
   un clip cuyo camino de captura no está en `capture-paths.yaml`.
3. **Nunca un float solo.** Toda métrica viaja como
   `{value, unit, confidence, view, mdc, level}`.
4. **Sin MDC medido no hay juicio.** Y si el MDC es mayor que el ancho del rango
   de referencia, tampoco. La métrica se muestra, a lo sumo, como descriptiva.
5. **Gate de plausibilidad anatómica antes de cualquier promedio.** Los rechazos
   se cuentan y se muestran; nunca se descartan en silencio.
6. **Cada métrica declara sus vistas válidas.** El motor devuelve `null` con
   razón si se le pide desde otra.
7. **Cada métrica declara su fps mínimo.** Por debajo devuelve `null` con
   razón, no un número calculado mal.
8. **Todo lo anclado a un evento lleva incertidumbre propagada desde ±1
   cuadro**, usando la velocidad local medida.
9. **Address se define, no se detecta.**
10. **Nunca video anotado pre-renderizado como única vista.** Se dibuja desde
    datos, en vivo, sobre el `master`.
11. **Sin puntaje global. Sin texto de veredicto autogenerado en v1.**
12. **Rangos de referencia sólo con procedencia declarada.** Ante la duda, el
    hueco antes que el número inventado.
13. **Lo específico del deporte vive en `sports/`.** El motor no conoce la
    palabra "golf".
14. **El arnés de verdad tiene su propio entorno.** Un validador que comparte
    dependencias con lo que valida no es un validador.
15. **Los tests deben fallar ante cuatro bugs inyectados:** signo de Y,
    grados/radianes, fps ±1, izquierda/derecha. Si ninguno falla, la suite es
    decorativa y hay que escribir el test que falta.
16. **Licencias: código, pesos y datos de entrenamiento son tres preguntas.**
    La lista de prohibidos está en `DECISIONES.md` ADR-010.
17. **Golf primero.** Pádel entra sólo cuando golf v1 tenga MDC medidos para
    todas sus métricas de nivel 1.
18. **Una sola versión de análisis por sesión no alcanza.** Re-analizar escribe
    `analysis.json` nuevo y conserva el anterior con su versión de motor.

## Sistemas de coordenadas (fuente número uno de bugs silenciosos)

- `image_px` — origen arriba a la izquierda, `x` a la derecha, `y` hacia
  **abajo**, en píxeles del `master`. Es el marco de `pose.npz`.
- Cualquier marco de mundo (suelo, cancha) declara origen, ejes, unidades y
  mano, y se guarda como dato en el JSON, no como comentario.
- Toda serie derivada lleva su campo `reference_frame`. Un test metamórfico
  verifica que un cuerpo más erguido dé menos inclinación de tronco.

## Fuera de alcance en v1

Pádel (hasta que golf tenga MDC), detección de pelota, dos personas en cuadro,
clasificación automática del gesto, devolución escrita por IA, acceso del
alumno, nube, multi-entrenador, calibración métrica en metros reales,
cualquier ángulo articular absoluto como juicio, X-factor, orden de la
secuencia cinemática, tempo contra objetivo 3:1.
