# Plantilla de un encargo (`docs/prompts/NN-<slug>.md`)

Entre media página y una página. Lo general no va: lo pone la skill
`/encargo` del repo (orden de lectura, reglas de trabajo, restricciones,
cierre). Acá va sólo lo específico de este encargo.

```markdown
# NN — <título en una línea>

Para correr: `/encargo NN` en una sesión nueva. <Si depende de otro: "después
de que cierre el MM". Si puede ir en paralelo: "en paralelo con el MM".>
Leé antes: <informes previos que importan, por nombre>.

## Contexto
<Dos o tres líneas: por qué esto ahora y de qué viene. Con los números que lo
justifican, no con adjetivos. Si hay una decisión del orquestador que la
sesión tiene que aplicar, va acá, con su porqué y con "ajustala sólo si el
código la contradice, y decilo".>

Leer: <los archivos de código y documentos que ESTA tarea necesita, con ruta
y, si se sabe, líneas. Nombrados, no "el módulo de X".>

## Qué existe ya
<Comandos, módulos, datos, y qué producen, para que no lo reinvente. Con las
cifras de hoy si sirven de referencia (tests que pasan, valores actuales).>

## Encargo
1. <Qué construir, medir o escribir, con alcance cerrado.>
2. <…>
<Los tests o comprobaciones que tiene que agregar, incluidos bugs inyectados
si aplica.>

NO: <lo que no hay que hacer, explícito: archivos que no se tocan, decisiones
que no se toman, "no arreglar X aunque lo veas: va en el informe".>

## Cómo se prueba
<Comandos concretos, con qué datos, y qué tiene que dar. Cómo se leen los
resultados (exit code y conteo, no la palabra "passed").>

## Front
<Sólo si el encargo tiene algo que se ve en un navegador: "lo prueba la
sesión" o "lo prueba <dueño>: dejalo listo con los comandos y la lista de qué
mirar". Preguntado al dueño antes de escribir el prompt.>

## En paralelo
<"Ninguno", o: qué encargo corre a la vez y qué archivos toca. Y la lista
cerrada de archivos que ESTE encargo puede tocar.>
```

Checklist antes de entregarlo:

- ¿Una sesión lo cierra entero en una tarde, con commit e informe?
- ¿Cada archivo que nombra existe? (Si el prompt toca el núcleo, verificalo
  con un subagente de sólo lectura.)
- ¿Dice qué NO hacer?
- ¿La prueba tiene comandos y datos, o dice "probalo bien"?
- ¿Las decisiones están tomadas, o le tira preguntas a la sesión?
- ¿Choca en algún archivo con otro encargo en curso?
