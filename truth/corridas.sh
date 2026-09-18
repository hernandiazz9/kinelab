#!/bin/sh
# Corre N veces la suite del arnés y falla si ALGUNA corrida no sale con exit 0.
#
#     truth/corridas.sh        # 10 corridas
#     truth/corridas.sh 25
#
# Por qué existe: la suite puede terminar con los 43 tests en verde y el
# proceso abortando igual al salir (exit 134, `libc++abi: … recursive_mutex
# lock failed`, la telemetría de onnxruntime; ver kinelab/perception/__init__.py).
# Pasaba en 7 de 10 corridas, así que UNA corrida en verde no probaba nada: es
# intermitente y se lee por exit code, nunca por la palabra «passed»
# (auditoría del 16/9 §7). Este script es lo que lo vuelve a agarrar si vuelve.
#
# Imprime una línea por corrida con su exit y, al final, el conteo. Exit 0 sólo
# si las N dieron 0.

set -u

N=${1:-10}
raiz=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
pytest="$raiz/truth/.venv/bin/pytest"

if [ ! -x "$pytest" ]; then
    echo "no está $pytest — el arnés tiene su propio entorno:" >&2
    echo "  cd truth && python3.12 -m venv .venv && .venv/bin/pip install -e ." >&2
    exit 2
fi

malas=0
i=1
while [ "$i" -le "$N" ]; do
    salida=$(cd "$raiz/truth" && "$pytest" 2>&1)
    codigo=$?
    resumen=$(printf '%s\n' "$salida" | grep -E '^=+ .*(passed|failed|error)' | tail -1)
    printf '%2d/%s  exit %-4s %s\n' "$i" "$N" "$codigo" "$resumen"
    if [ "$codigo" -ne 0 ]; then
        malas=$((malas + 1))
        printf '%s\n' "$salida" | tail -3 | sed 's/^/      /'
    fi
    i=$((i + 1))
done

if [ "$malas" -eq 0 ]; then
    echo "$N corridas, $N con exit 0."
    exit 0
fi
echo "$N corridas, $malas con exit distinto de 0." >&2
exit 1
