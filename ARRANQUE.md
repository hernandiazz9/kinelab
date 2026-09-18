# Cómo arrancar `kinelab`

## 1. El repo

Ya existe en `/Users/heralc/Desktop/HDDev/kinelab`, sembrado y con sus
primeros commits. **Para retomar trabajo empezado, el mensaje de arranque es el
de `ESTADO.md`, no el de abajo**: el de abajo asume que no hay nada construido.

`CLAUDE.md` contiene sólo `@AGENTS.md`, igual que en BMPadel: el agente lee
`AGENTS.md` en cada sesión y ese archivo lo manda a los otros seis.

## 2. El mensaje de arranque

Pegar esto en una sesión nueva de Claude Code, dentro del repo. Está pensado
para que la primera respuesta sea comprensión, no código.

---

> Vamos a construir `kinelab` desde cero en este repo. Antes de escribir una
> sola línea, leé en este orden y completos: `AGENTS.md`, `CONTEXTO.md`,
> `DECISIONES.md`, `ESPECIFICACION.md`, `CONTRATO.md`, `CAPTURA.md`,
> `HERENCIA.md`. Son la fuente de verdad. No los relitigues; si encontrás algo
> inviable o contradictorio, decímelo antes de seguir.
>
> Cuando termines de leer, respondé **sólo con esto** y esperá mi confirmación:
>
> 1. En diez líneas, qué entendiste que vamos a construir y por qué el orden
>    de las fases es el que es.
> 2. Las tres reglas que más te sorprendieron y qué falla evitan.
> 3. Cualquier contradicción o hueco que hayas encontrado entre los siete
>    documentos.
> 4. Qué hay en `HERENCIA.md` §Se porta que vas a necesitar leer en su repo de
>    origen antes de la Fase 1, y confirmá que los dos repos están accesibles
>    en las rutas que indica.
>
> Recién después de mi confirmación arrancamos la **Fase 0**, y sólo su parte
> de agente (0.1 a 0.5). Lo que la Fase 0 pide es casi todo mío — filmar un
> cronómetro y una sesión real — y tu trabajo es darme las herramientas para
> hacerlo bien y después **parar**:
>
> - `kinelab/tools/fps_truth.py`, con sus tests sobre tres clips que el propio
>   test fabrica con ffmpeg. El test tiene que demostrar que los campos
>   declarados no distinguen "estirado" de "remuestreado" y que el conteo sí.
> - `data/capture-paths.yaml` con schema y ejemplo comentado.
> - `docs/checklist-captura.md`, imprimible, derivado de `CAPTURA.md`.
> - `kinelab/ingest/gate.py` con los chequeos de Fase 0 y sus tests, incluido
>   uno que rechaza con razón legible.
> - Commit.
>
> Al terminar, decime exactamente qué tengo que filmar, con qué ajustes, cómo
> lo transfiero y qué comando corro para verificar cada clip. No escribas nada
> de pose, métricas ni interfaz hasta que existan clips reales que pasen el
> gate.
>
> Dos reglas de cómo trabajar conmigo: cuando algo de los documentos no se
> pueda cumplir, parás y avisás, no rodeás. Y cuando termines un bloque,
> commit con mensaje en español que diga qué cambió y por qué.

---

## 3. Qué esperar

La primera respuesta buena es la que encuentra al menos un hueco en los
documentos. Los hay: el umbral de encuadre se fijó midiendo (717 px de cuerpo,
`body_height_px_min`), el nombre del proyecto es provisorio, y los bitrates de
`CAPTURA.md` vienen de un sitio comercial. Un agente que dice "todo claro,
arranco" no leyó.

La Fase 0 de agente debería cerrar en una sesión. La Fase 0 de humano depende
de tener un golfista, un trípode, un cronómetro con milisegundos y una mañana
al aire libre.

## 4. Lo que el humano tiene que decidir antes del primer clip

- **Qué teléfono es.** El protocolo asume iPhone 17 Pro o 18 Pro (video normal
  a 1080p120). Con otro modelo, el cronómetro decide qué modos sirven, y quizás
  haga falta Slo-Mo calibrado o Blackmagic Camera.
- **A quién se filma.** Un golfista dispuesto a pegar 10–20 swings por vista,
  dos vistas, al aire libre, de día.
- **Dónde.** Driving range o cancha con espacio para el trípode a 3,5 m detrás
  (down-the-line) y perpendicular a la línea de tiro (face-on).
