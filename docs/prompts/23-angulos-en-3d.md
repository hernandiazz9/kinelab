# 23 — Los ángulos en el visor 3D, y la primera medición propia de cuánto se
# equivoca la proyección

Para correr: `/encargo 23` en una sesión nueva. Leé antes los informes del
19 (el visor y el `pose3d.json`), el 07 (el mapeo y el nivel 1) y el 13 (§1,
por qué la ganancia murió) en `docs/informes/`.

## Contexto

El visor 3D del encargo 19 anda y gira, pero dibuja el esqueleto sin los
ángulos que sí muestra el overlay plano. Ponerlos no es decorar: **en el
mocap los ángulos son verdaderos**, calculados con tres puntos 3D reales, sin
error de proyección. Es la primera vez en el proyecto que se puede mostrar un
ángulo articular que no arrastra los 21 a 32 grados de error de la pose
monocular que mide ADR-007.

Y habilita algo que el proyecto necesita y todavía no tiene: **medir, con
datos propios y movimiento humano real, cuánto se equivoca un ángulo cuando
se lo mira desde una cámara en vez de en 3D**. Hoy eso está medido para
desplazamientos en cm (07 y 14) y para la ganancia (13), no para ángulos.
Es ADR-009 nivel 1 aplicado a lo que más se le pregunta a una herramienta de
golf.

**Dónde está el límite, y hay que respetarlo.** `CONTRATO.md` §Niveles pone
los ángulos absolutos de codo, rodilla y muñeca en **nivel 3: no se
construyen** como métrica del producto. Esto no los construye: son del mocap,
son referencia, y van rotulados como tales, igual que la verdad 3D que ya usa
el arnés. Lo que este encargo sí hace es **mostrar por qué** están en nivel 3.
Nada de esto entra al registro de métricas ni a `analysis.json` de un video.

Leer: `truth/kinelab_truth/mocap.py` (el mapeo a Halpe26, `APPROX_NOTES`, el
marco del arnés, cómo se escribe `pose3d.json`), `truth/kinelab_truth/
camera.py` (los extrínsecos de las dos vistas),
`web/src/components/Visor3D.tsx` (cómo dibuja y cómo conmuta capas),
`kinelab/metrics/generic.py` o donde viva el cálculo de ángulos 2D del motor
(para usar **la misma** definición de tres puntos), `kinelab/explore.py`
(qué ángulos dibuja el overlay: codos, rodillas, caderas, hombros, tronco),
`CONTRATO.md` §Niveles y §Registro, `CONTEXTO.md` §Sistemas de coordenadas,
ADR-007, ADR-012.

## Encargo

1. **Ángulos 3D en `pose3d.json`.** Por cuadro, con la **misma definición de
   tres puntos** que usa el motor en 2D, para que la comparación sea justa:
   codo, rodilla, cadera y hombro de los dos lados, y la inclinación de
   tronco. Más las dos que en 2D son imposibles y en 3D son directas: el
   **giro de la línea de caderas** y el de la **línea de hombros** alrededor
   del eje vertical, respecto de la línea de tiro, en grados. Todo con su
   unidad y su marco declarados dentro del archivo.
2. **Los mismos ángulos, proyectados.** Para cada ángulo y cada una de las
   dos vistas del protocolo, el valor que sale de medirlo sobre la proyección
   2D. Es lo que el motor calcularía si ese swing hubiera sido filmado desde
   ahí. Y la diferencia contra el 3D, cuadro por cuadro.
3. **Dibujarlos en el visor.** El número junto a la articulación, siguiendo
   el punto al girar, con la misma estética del overlay plano. Capa propia
   con su interruptor, como las que ya tiene el visor.
4. **La comparación, a la vista.** Cuando el usuario gira la cámara hasta una
   de las dos vistas del protocolo, junto a cada ángulo aparece también el
   valor proyectado y la diferencia. El visor ya muestra el colapso de la
   línea de caderas: esto es lo mismo, en números que un entrenador conoce.
   Una línea de texto explica qué está viendo: el de arriba es el ángulo
   real, el de abajo es lo que una cámara puede ver desde ahí.
5. **La tabla, en el informe.** Sobre los diez trials del sujeto 64, para cada
   ángulo y cada vista: sesgo medio y límites de acuerdo de la proyección
   contra el 3D, en los tres eventos (address, top, impacto) y en el peor
   cuadro de la repetición. Es el entregable de medición de este encargo y el
   número que le faltaba al proyecto. Decilo como lo que es: **un sujeto,
   diez swings**, no una tabla de referencia.
6. **Rótulo, siempre visible en la capa:** estos ángulos son del mocap medido
   con marcadores; un video de celular no los puede dar, y la diferencia que
   se ve al girar es exactamente por qué.

NO: no agregar ninguna métrica al registro ni a `analysis.json`; no tocar
`kinelab/` (si la definición de ángulo que necesitás está ahí, **importala**,
no la copies: duplicar la fórmula es cómo se desincronizan); no tocar
`sports/`, `service/`, `Reproductor.tsx`, `api.ts`, `page.tsx`; no agregar
dependencias; no presentar ningún número como juicio ni como objetivo; no
abrir el navegador.

## Cómo se prueba

- `cd truth && .venv/bin/pytest -q` en verde, con tests nuevos: un ángulo 3D
  construido en el test (una L de 90°, un brazo a 37°) da el valor exacto;
  **el ángulo 3D no cambia al rotar la escena entera** (es lo que lo define,
  y es el test que atrapa un bug de marco); el proyectado sí cambia con la
  vista, y en la vista donde el segmento queda de frente a la cámara la
  diferencia explota; los pares izquierda/derecha no están cruzados.
- `.venv/bin/pytest -q` y `cd web && pnpm lint && pnpm build` limpios.
- Regenerar los dos ejemplos y verificar por `curl` que `pose3d.json` trae
  los ángulos.
- Para Hernán: qué mirar, con el paso de girar hasta `face_on` y ver la
  diferencia entre el ángulo real y el proyectado en el codo y en la línea de
  caderas.

## En paralelo

El 22 toca `web/public/demo/`, `api.ts`, `next.config.ts`, `page.tsx` y
`kinelab/tools/exportar_demo.py`; el 20 mide y quizá toca `explore.py`; el 16
toca `kinelab/` y el contrato; el 18 toca `kinelab/events/`. Vos:
`truth/kinelab_truth/mocap.py`, `truth/tests/`, y
`web/src/components/Visor3D.tsx`. Si el 22 ya exportó la demo, avisá en el
informe que hay que regenerarla para que incluya los ángulos.
