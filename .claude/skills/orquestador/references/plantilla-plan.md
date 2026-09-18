# Formato de `docs/PLAN.md`

Es la memoria del orquestador. Al día y commiteado al final de cada ronda.
Un orquestador nuevo arranca de acá.

```markdown
# Plan

Última ronda: <fecha> — <qué informe se leyó, qué se decidió, qué encargos
se escribieron; cuatro o cinco líneas>.
Ronda anterior: <fecha> — <lo mismo, más corto>.

Regla de numeración: un ítem recibe número cuando se escribe su prompt; los
pendientes van sin número, en orden de ejecución.

## Dónde está el proyecto, sin optimismo
<Tres a seis líneas. Qué fase, qué está validado y qué no, qué es lo que
destraba lo demás.>

## Congelado hasta <condición>
- <lo que no se hace hasta que pase algo, y por qué>

## Decisiones del orquestador
- <fecha> · <qué se decidió>. Evidencia: <informe o medición>. <Qué encargo
  lo aplica.>
- Anteriores, vigentes: <una línea por decisión vieja que sigue valiendo>.

## Backlog, en rondas
<Máximo dos sesiones a la vez, sin archivos compartidos.>
- **R1** · [hecho] **NN** <slug> — <hashes>. <una línea de resultado>.
- **R2** · [en curso] **NN** <slug> ∥ [en curso] **MM** <slug>.
- **R3** · [pendiente] <slug sin número> — <qué es, en una línea>.
- [bloqueado por <dueño>] <qué, y qué destraba>.

## Preguntas para <dueño>
- <pregunta, y qué traba mientras no se conteste>

## Aparcado
- <qué, y por qué>
```

Estados: `pendiente | en curso | hecho | bloqueado por <dueño>`.
