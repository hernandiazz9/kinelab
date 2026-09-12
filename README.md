# kinelab

Motor de medición del movimiento humano a partir de video de celular. Para un
entrenador, en su Mac, sin nube. Agnóstico al deporte; golf primero.

**Empezá por [`AGENTS.md`](AGENTS.md).** Dice qué leer, en qué orden, y cuáles
son las reglas de trabajo. Los seis documentos que enumera son la fuente de
verdad; `ESTADO.md` dice dónde quedó el trabajo.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
```

Nombre provisorio. Cambiarlo es un `sed`.
