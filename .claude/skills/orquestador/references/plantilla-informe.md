# Formato del informe de una sesión (`docs/informes/AAAA-MM-DD-NN-<slug>.md`)

Lo escribe la sesión de trabajo al cerrar. Lo lee el orquestador, que no lee
código ni datos: decide sólo con lo que diga acá. Por eso: números, no
adjetivos; comandos al lado de cada número; y el resumen arriba, porque el
cuerpo puede crecer y el orquestador tiene que poder parar en la línea diez.

```markdown
# <slug> — <fecha>

## Resumen
<Hasta diez líneas. Qué se pidió, qué quedó, los tres o cuatro números que
importan, qué quedó abierto, y qué tiene que decidir o probar alguien. Si el
orquestador lee sólo esto, tiene que poder decidir el próximo paso.>

## Encargo
<Una línea: qué pedía el prompt.>

## Hecho
<Qué existe ahora que antes no. Commits con hash. Qué NO se tocó, si el
prompt lo prohibía o si se decidió no tocarlo.>

## Probado
<Qué se corrió de verdad y qué dio: suites con pasados, fallados y exit code;
corridas reales con sus comandos y sus números; mutación manual si hubo (qué
se rompió a propósito y qué test lo vio). Tablas antes/después cuando algo
cambia un valor.>

## Queda abierto
<Lo que no se pudo cerrar y por qué. Lo que se vio y no era de este encargo,
con el archivo y la línea. Deuda nueva.>

## Para que pruebe <dueño>
<Sólo si hay front o algo manual: comandos y qué tiene que ver en cada paso.
Si no hay nada: "Nada de front."; no se inventa.>

## Preguntas para el orquestador
<Decisiones que no eran de la sesión, con las opciones y lo que cuesta cada
una. Numeradas, para que el orquestador las conteste por número.>
```

Reglas:

- Todo número con su unidad y su comando al lado.
- Los tests se reportan por exit code y conteo. "En verde" sin conteo no vale.
- Si algo se hizo distinto de lo que pedía el prompt, se dice acá y en el
  archivo de estado, con la razón.
- Nada de "debería funcionar": o se corrió, o se dice que no se corrió.
