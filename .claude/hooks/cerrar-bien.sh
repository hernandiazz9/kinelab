#!/bin/bash
# Hook Stop: un encargo no cierra sin commit y sin informe.
#
# Existe porque el método lo pedía y no se cumplía: el 16 terminó sin
# commitear y otra sesión tuvo que hacerlo; la mitad de `padel-coach` se
# perdió igual. Un pedido en un documento depende de que la sesión se acuerde;
# esto no. Sólo actúa si `/encargo` dejó su marcador, así que las sesiones
# normales no lo notan.
set -uo pipefail
entrada=$(cat)
cwd=$(printf '%s' "$entrada" | /usr/bin/python3 -c 'import json,sys; print(json.load(sys.stdin).get("cwd",""))' 2>/dev/null)
[ -n "$cwd" ] && [ -d "$cwd" ] || exit 0
cd "$cwd" 2>/dev/null || exit 0

gitdir=$(git rev-parse --git-dir 2>/dev/null) || exit 0
marca="$gitdir/encargo-en-curso"
[ -f "$marca" ] || exit 0                      # no es un encargo: no me meto
nn=$(tr -dc '0-9' < "$marca" | head -c 2)
[ -n "$nn" ] || exit 0

# Un encargo que frenó a preguntar no está cerrando: no le pidas el informe.
# Sí le pedimos que lo que tenga esté commiteado en su rama, aunque sea un
# WIP: el worktree es suyo y un commit a medias ahí no molesta a nadie,
# mientras que un turno que termina con cambios sueltos los pierde.
esperando=0
grep -qi "esperando" "$marca" && esperando=1

falta=""
sucio=$(git status --porcelain --untracked-files=no)
[ -n "$sucio" ] && falta="Quedan cambios sin commitear:
$sucio"

if [ "$esperando" = 1 ]; then
  if [ -z "$falta" ]; then exit 0; fi
  cat >&2 <<FIN
El encargo $nn frenó a preguntar, pero dejó trabajo suelto:

$falta

Commitealo en tu rama antes de terminar el turno, aunque sea a medias y con el
mensaje empezando por «WIP:». El worktree es tuyo; lo que no se commitea se
pierde cuando te reanuden.
FIN
  exit 2
fi

informe=$(ls docs/informes/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-"$nn"-*.md 2>/dev/null | head -1)
if [ -z "$informe" ]; then
  falta="${falta:+$falta
}No hay informe del encargo $nn en docs/informes/ (AAAA-MM-DD-$nn-<slug>.md)."
elif ! grep -qiE '^#*[[:space:]]*Para (Hernán|Hernan|el dueño)[[:space:]]*:?[[:space:]]*\S' "$informe"; then
  falta="${falta:+$falta
}El informe $informe no tiene la línea «Para Hernán:» arriba. Va siempre, aunque
diga «nada»: es lo que el orquestador lee para saber si tiene que avisarte, y
lo que evita que una pregunta tuya quede enterrada en la línea 287 (pasó en
el 32)."
fi

[ -z "$falta" ] && exit 0

cat >&2 <<FIN
El encargo $nn no está cerrado todavía:

$falta

Cerralo como dice §7 de la skill /encargo: ESTADO.md, el informe, y commit con
rutas explícitas (git commit -m "…" -- ruta1 ruta2). Si de verdad no podés
cerrarlo, commiteá lo que esté entero, dejá dicho en el informe qué quedó
afuera, y borrá el marcador: rm "$marca"
FIN
exit 2
