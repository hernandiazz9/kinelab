# Informes de sesión

Cada sesión de trabajo deja acá un informe corto, `AAAA-MM-DD-NN-<slug>.md`
(NN es el número del encargo en `docs/prompts/`), que el orquestador lee para
decidir el paso siguiente. Formato fijo, para que se pueda leer en un minuto.
Con números: el orquestador no lee código ni CSVs, decide con lo que diga acá.

```
# <slug> — <fecha>
Resumen: <hasta diez líneas, arriba de todo: qué quedó, los tres o cuatro números que importan, qué está abierto y qué hay que decidir o probar. Si el orquestador lee sólo esto, tiene que poder decidir el próximo paso>
Para Hernán: <UNA línea, siempre presente, aunque diga «nada». Qué tiene que
mirar, probar o decidir él, con la ruta o el comando concreto. Va acá arriba y
no enterrada abajo: es lo que dispara el aviso a su teléfono, y si falta, el
hook no te deja cerrar. El campo largo sigue estando más abajo; esta línea es
el índice.>
Encargo: <una línea: qué pedía el prompt>
Hecho: <3–8 líneas; commits con hash>
Probado: <qué se corrió de verdad y qué dio, con números>
Queda abierto: <lo que no se pudo cerrar y por qué>
Para que pruebe Hernán: <comandos y qué esperar; sólo si hay front o algo manual>
Preguntas para el orquestador: <decisiones que no eran de la sesión>
```
