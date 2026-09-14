"""Cuadros fabricados entre dos cuadros medidos, para MIRAR. No para medir.

Entre dos cuadros consecutivos de un clip no hay nada: lo que pasó ahí no se
grabó. `minterpolate` de ffmpeg puede fabricar cuadros intermedios estimando el
movimiento; esta herramienta los escribe en un archivo **aparte**, con el
rótulo "cuadro interpolado, no medido" quemado en cada uno, y una lámina en
fila para poder decidir de un vistazo si sirven o si el implemento sale
fantasma.

Es un experimento etiquetado, no una medición:

- ninguna métrica, ningún evento y ninguna pose leen lo que sale de acá;
- los nombres de archivo (`interpolado-*.mp4`, `lamina-*.png`) no están en la
  lista blanca de `service/` ni los mira `explore.py`;
- sin modelos de interpolación (RIFE, FILM y compañía quedan fuera por
  ADR-010): sólo ffmpeg, que ya está en el stack (ADR-015).

La herramienta es agnóstica al deporte: recibe **índices de cuadro**, no
"impacto", y el texto de la marca vertical lo pone quien la llama.

Uso:
    python -m kinelab.tools.interpolar VIDEO --entre 44 45 --factor 4 \
        --marca 44.44 --marca-mas-menos 0.11 \
        --marca-texto "estimación del encargo 02: 44,44 ± 0,11"

Deja en `<video>.kinelab/` (o en `--out`):
    interpolado-A-B-x<factor>.mp4   el tramo [A−contexto, B+contexto] interpolado, con rótulo por cuadro
    lamina-A-B-x<factor>.png        A, los intermedios y B en fila, recortados, con la marca

### Los índices son los del motor

Los cuadros se leen con el mismo `iter_frames` que usa la percepción, así que
el cuadro 44 de acá es el cuadro 44 de `pose.npz`, de `datos-por-cuadro.csv` y
del `overlay.mp4`. No se usa `select=between(n,…)` de ffmpeg: una edit list
(la que dejó el recorte de `cortado.mp4`, por ejemplo) corre los índices.

### Alineación exacta

A `minterpolate` se le entra a **1 fps** y se le pide `fps=factor`: así el
cuadro de salida `k` cae exactamente en el índice de entrada `k/factor`, sin
error de redondeo del time base. La tasa real del clip sólo se usa para
escribir el mp4. Medido sobre `cortado.mp4`: los cuadros de salida en
posiciones múltiplo de `factor` dan PSNR 52,4 dB contra los originales — la
pérdida del ida y vuelta BGR↔YUV del filtro, nada más.

Y `minterpolate` emite `(n−1)·factor` cuadros para `n` de entrada: se queda sin
el último. Por eso se le entrega el último cuadro **duplicado**, y la salida
tiene `(n−1)·factor + 1` cuadros, que es el tramo entero.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from kinelab.perception.video import ffmpeg_bin, iter_frames
from kinelab.tools.fps_truth import FfprobeError
from kinelab.tools.fps_truth import analyze as fps_analyze

# El filtro por defecto. Medido sobre este material (informe del encargo 05):
# `mc_mode` (obmc/aobmc) y `vsbmc` (0/1) dan la salida **byte a byte idéntica**
# en ffmpeg 9.0.1 — no hacen nada. El que mueve la aguja es `me_mode`: `bidir`
# reconstruye mejor que `bilat`, que es el default del filtro. Se deja el juego
# completo escrito igual, explícito, para que se vea qué se pidió; cambiarlo es
# `--filtro`.
FILTRO_DEFECTO = "mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"

AVISO = "INTERPOLADO: cuadros fabricados por ffmpeg minterpolate. No son medidos y ninguna métrica los lee."
TEXTO_MEDIDO = "medido"
TEXTO_SINTETICO = "cuadro interpolado, no medido"
FONT = cv2.FONT_HERSHEY_SIMPLEX
# Las dos leyendas más anchas que puede haber: la escala de la fuente se fija
# con ellas y no con el texto de cada cuadro, para que no cambie entre cuadros.
_PLANTILLAS = (f"{TEXTO_SINTETICO} · 9999,99", f"{TEXTO_MEDIDO} · 9999")
COLOR_MEDIDO = (120, 240, 120)      # BGR: verde
COLOR_SINTETICO = (60, 170, 255)    # BGR: naranja
COLOR_MARCA = (255, 80, 255)        # BGR: magenta
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)


class InterpolarError(RuntimeError):
    """El tramo pedido no existe, ffmpeg falló, o el clip no se puede leer."""


def _coma(x: float, decimales: int) -> str:
    """Número con coma decimal: los rótulos son prosa y la prosa va en español."""
    return f"{x:.{decimales}f}".replace(".", ",")


# `cv2.putText` dibuja con las fuentes Hershey, que sólo tienen ASCII: una "é"
# sale como dos signos de pregunta, sin aviso. Pillow no está en el entorno y
# ADR-015 cierra el stack, así que el texto se translitera **al quemarlo**; en
# el código y en la salida de consola sigue escrito en español como corresponde.
_ASCII = str.maketrans({
    "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
    "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N",
    "·": "|", "±": "+/-", "–": "-", "—": "-", "×": "x", "°": " grados",
    "“": '"', "”": '"', "‘": "'", "’": "'", "…": "...",
})


def _ascii(texto: str) -> str:
    return texto.translate(_ASCII).encode("ascii", "replace").decode("ascii")


def _medir(texto: str, fs: float, grosor: int) -> tuple[int, int]:
    (w, h), _ = cv2.getTextSize(_ascii(texto), FONT, fs, grosor)
    return w, h


def etiqueta(indice: float) -> tuple[str, tuple[int, int, int], bool]:
    """Rótulo, color y si el cuadro es medido, para el índice fraccional dado."""
    entero = abs(indice - round(indice)) < 1e-9
    if entero:
        return f"{TEXTO_MEDIDO} · {round(indice)}", COLOR_MEDIDO, True
    return f"{TEXTO_SINTETICO} · {_coma(indice, 2)}", COLOR_SINTETICO, False


def alto_franja(w: int, h: int) -> int:
    """Alto en píxeles de la franja del rótulo, arriba de todo.

    Está acá afuera porque el test lo necesita: debajo de la franja, un cuadro
    medido tiene que ser el original (PSNR alto), y para comprobarlo hay que
    saber dónde termina el rótulo.
    """
    return max(24, int(round(h * 0.045)))


def _escala_fuente(w: int, h: int, alto: int, grosor: int) -> float:
    ancho_max = max(_medir(t, 1.0, grosor)[0] for t in _PLANTILLAS)
    margen = max(6, w // 100)
    por_ancho = (w - 2 * margen) / ancho_max if ancho_max else 1.0
    por_alto = (alto * 0.55) / _medir("Hg", 1.0, grosor)[1]
    return float(max(0.25, min(por_ancho, por_alto)))


def _ajustar(lineas: list[str], ancho: int, grosor: int, techo: float) -> float:
    """La escala más grande, hasta `techo`, con la que la línea más larga entra en `ancho`.

    El 0,96 es el contorno negro: `_texto` lo dibuja con `grosor + 2` y sale
    unos píxeles más ancho que lo que mide `getTextSize` con `grosor`.
    """
    largo = max((_medir(t, 1.0, grosor)[0] for t in lineas if t), default=1)
    return float(max(0.25, min(techo, ancho * 0.96 / largo if largo else techo)))


def _texto(img: np.ndarray, texto: str, x: int, y: int, fs: float, grosor: int, color) -> None:
    t = _ascii(texto)
    cv2.putText(img, t, (int(x), int(y)), FONT, fs, NEGRO, grosor + 2, cv2.LINE_AA)
    cv2.putText(img, t, (int(x), int(y)), FONT, fs, color, grosor, cv2.LINE_AA)


def rotular(frame: np.ndarray, indice: float) -> np.ndarray:
    """Quema el rótulo en una franja negra arriba. Debajo de la franja el cuadro
    no se toca: un cuadro medido sigue siendo el cuadro medido."""
    img = frame.copy()
    h, w = img.shape[:2]
    banda = alto_franja(w, h)
    grosor = max(1, h // 600)
    fs = _escala_fuente(w, h, banda, grosor)
    texto, color, _ = etiqueta(indice)
    img[:banda] = NEGRO
    margen = max(6, w // 100)
    _texto(img, texto, margen, int(banda * 0.72), fs, grosor, color)
    return img


@dataclass(frozen=True)
class Fuente:
    """El clip y su tramo, ya leído."""

    path: Path
    fps: float
    width: int
    height: int
    rotation_deg: int
    frames_total: int
    inicio: int  # índice del primer cuadro leído
    frames: list[np.ndarray]

    @property
    def fin(self) -> int:
        return self.inicio + len(self.frames) - 1


def leer_tramo(video: Path, desde: int, hasta: int) -> Fuente:
    """Decodifica `[desde, hasta]` con la rotación aplicada, como lo ve el motor."""
    try:
        t = fps_analyze(video)
    except FfprobeError as e:
        raise InterpolarError(str(e)) from e
    d, c = t.declared, t.counted
    w, h = d.display_size
    total = c.frames_decoded
    desde, hasta = max(0, desde), min(total - 1, hasta)
    if hasta < desde:
        raise InterpolarError(f"{video}: el tramo pedido queda fuera de los {total} cuadros del clip")
    frames: list[np.ndarray] = []
    for i, f in iter_frames(video, rotation_deg=d.rotation_deg, display_size=(w, h)):
        if desde <= i <= hasta:
            frames.append(f)
        if i >= hasta:
            break
    if len(frames) < 2:
        raise InterpolarError(f"{video}: el tramo tiene {len(frames)} cuadro(s); hacen falta al menos 2")
    return Fuente(
        path=video, fps=c.fps_playback_effective, width=w, height=h, rotation_deg=d.rotation_deg,
        frames_total=total, inicio=desde, frames=frames,
    )


def interpolar_cuadros(
    frames: list[np.ndarray], factor: int, *, filtro: str = FILTRO_DEFECTO
) -> Iterator[np.ndarray]:
    """Produce `(n−1)·factor + 1` cuadros: los `n` de entrada y los sintéticos entre ellos.

    Entra y sale rawvideo por un pipe (HERENCIA §Se porta: escritura de video
    por pipe a ffmpeg). El último cuadro se duplica porque `minterpolate` no
    emite el suyo.
    """
    if factor < 2:
        raise InterpolarError("el factor tiene que ser 2 o más")
    h, w = frames[0].shape[:2]
    entrada = list(frames) + [frames[-1]]
    cmd = [
        ffmpeg_bin(), "-y", "-v", "error", "-nostdin",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", "1", "-i", "-",
        "-vf", f"minterpolate=fps={factor}:{filtro}",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-",
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def alimentar() -> None:
        try:
            for f in entrada:
                p.stdin.write(np.ascontiguousarray(f).tobytes())
            p.stdin.close()
        except (BrokenPipeError, ValueError):
            pass

    hilo = threading.Thread(target=alimentar, daemon=True)
    hilo.start()
    esperados = (len(frames) - 1) * factor + 1
    n_bytes = w * h * 3
    salidos = 0
    try:
        while salidos < esperados:
            buf = p.stdout.read(n_bytes)
            if len(buf) < n_bytes:
                break
            salidos += 1
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    finally:
        p.stdout.close()
        err = p.stderr.read().decode("utf-8", "replace")
        p.stderr.close()
        p.wait(timeout=600)
        hilo.join(timeout=5)
    if salidos < esperados:
        raise InterpolarError(
            f"minterpolate devolvió {salidos} cuadros y se esperaban {esperados}. ffmpeg dijo: {err.strip() or '(nada)'}"
        )


def _bbox_pose(out_dir: Path, desde: int, hasta: int) -> tuple[int, int, int, int] | None:
    """Caja de la persona en `pose.npz`, unión sobre el tramo. `None` si no hay."""
    p = out_dir / "pose.npz"
    if not p.is_file():
        return None
    try:
        with np.load(p, allow_pickle=True) as z:
            bbox = np.asarray(z["bbox"], dtype=float)
    except (OSError, KeyError, ValueError):
        return None
    tramo = bbox[max(0, desde): hasta + 1]
    tramo = tramo[np.isfinite(tramo).all(axis=1)] if tramo.size else tramo
    if tramo.size == 0:
        return None
    return (
        int(np.floor(tramo[:, 0].min())), int(np.floor(tramo[:, 1].min())),
        int(np.ceil(tramo[:, 2].max())), int(np.ceil(tramo[:, 3].max())),
    )


def _recorte(
    spec: str, out_dir: Path, w: int, h: int, desde: int, hasta: int
) -> tuple[tuple[int, int, int, int], str]:
    """`persona` (bbox de pose.npz, con margen), `completo`, o `x0,y0,x1,y1`."""
    if spec == "completo":
        return (0, 0, w, h), "cuadro entero"
    if spec != "persona":
        try:
            x0, y0, x1, y1 = (int(float(v)) for v in spec.replace(" ", "").split(","))
        except ValueError as e:
            raise InterpolarError(f"--recorte: '{spec}' no es 'persona', 'completo' ni 'x0,y0,x1,y1'") from e
        caja, origen = (x0, y0, x1, y1), "recorte pedido a mano"
    else:
        b = _bbox_pose(out_dir, desde, hasta)
        if b is None:
            return (0, 0, w, h), "cuadro entero (no hay pose.npz para recortar a la persona)"
        pad_x, pad_y = int((b[2] - b[0]) * 0.10), int((b[3] - b[1]) * 0.06)
        caja = (b[0] - pad_x, b[1] - pad_y, b[2] + pad_x, b[3] + pad_y)
        origen = "bbox de la persona en pose.npz, con margen"
    x0, y0, x1, y1 = (max(0, caja[0]), max(0, caja[1]), min(w, caja[2]), min(h, caja[3]))
    if x1 - x0 < 16 or y1 - y0 < 16:
        raise InterpolarError(f"el recorte {caja} queda vacío dentro de {w}x{h}")
    return (x0, y0, x1, y1), origen


def lamina(
    paneles: list[tuple[float, np.ndarray]],
    *,
    cabecera: list[str],
    marca: float | None = None,
    marca_texto: str | None = None,
    marca_mas_menos: float | None = None,
) -> np.ndarray:
    """Los cuadros en fila, cada uno con su rótulo, y la marca vertical.

    `paneles` son `(índice fraccional, imagen ya recortada)`, en orden. La marca
    se ubica interpolando entre los centros de los paneles, así que cae en el
    mismo lugar en que caería el cuadro de ese índice. La banda de ±
    incertidumbre se dibuja **arriba y abajo** de las imágenes y no encima:
    la lámina existe para mirar el implemento, y un velo de color justo ahí
    tapa lo único que hay que juzgar.
    """
    if not paneles:
        raise InterpolarError("no hay paneles para la lámina")
    ph, pw = paneles[0][1].shape[:2]
    n = len(paneles)
    grosor = max(1, ph // 400)
    borde = max(2, ph // 250)
    hueco = max(6, pw // 40)
    margen = hueco
    paso = pw + 2 * borde + hueco
    ancho = margen * 2 + paso * n - hueco

    pies = [list(etiqueta(i)[0].split(" · ")) for i, _ in paneles]
    fs_pie = _ajustar([t for par in pies for t in par], pw, grosor, ph / 700.0)
    alto_linea = int(_medir("Hg", fs_pie, grosor)[1] * 1.7)
    pie = alto_linea * 2 + alto_linea // 2

    fs_cab = _ajustar(cabecera, ancho - 2 * margen, grosor, ph / 620.0)
    alto_cab_linea = int(_medir("Hg", fs_cab, grosor)[1] * 2.0)
    alto_cab = alto_cab_linea * len(cabecera) + margen
    alto_marca = int(alto_cab_linea * 1.3) if marca is not None else 0

    alto = alto_cab + alto_marca + ph + 2 * borde + pie + margen
    hoja = np.zeros((alto, ancho, 3), np.uint8)
    hoja[:] = (24, 24, 24)
    for i, linea in enumerate(cabecera):
        _texto(hoja, linea, margen, int(margen * 0.5 + alto_cab_linea * (i + 0.8)), fs_cab, grosor, BLANCO)

    y_panel = alto_cab + alto_marca
    y_pie = y_panel + ph + 2 * borde

    if marca is not None:
        i0, i1 = paneles[0][0], paneles[-1][0]
        p = (marca - i0) / (i1 - i0) * (n - 1) if i1 > i0 else 0.0

        def x_de(pos: float) -> int:
            return int(round(margen + pos * paso + borde + pw / 2))

        if marca_mas_menos:
            dp = marca_mas_menos / (i1 - i0) * (n - 1) if i1 > i0 else 0.0
            xa, xb = max(0, x_de(p - dp)), min(ancho, x_de(p + dp) + 1)
            for y0, y1 in ((alto_cab, y_panel), (y_pie, y_pie + pie)):
                franja = hoja[y0:y1, xa:xb]
                if franja.size:
                    franja[:] = (franja.astype(np.uint16) // 2 + np.array(COLOR_MARCA, np.uint16) // 2).astype(np.uint8)
        cv2.line(hoja, (x_de(p), alto_cab), (x_de(p), y_pie + pie), COLOR_MARCA, max(3, 2 * grosor), cv2.LINE_AA)
        if marca_texto:
            tmw = _medir(marca_texto, fs_cab, grosor)[0]
            x_txt = int(min(max(margen, x_de(p) - tmw / 2), ancho - margen - tmw))
            # En blanco: el texto cae dentro de la banda de ±, que ya es magenta.
            _texto(hoja, marca_texto, x_txt, alto_cab + int(alto_cab_linea * 0.95), fs_cab, grosor, BLANCO)

    for i, (indice, img) in enumerate(paneles):
        x = margen + i * paso
        color = etiqueta(indice)[1]
        cv2.rectangle(hoja, (x, y_panel), (x + pw + 2 * borde - 1, y_panel + ph + 2 * borde - 1), color, -1)
        hoja[y_panel + borde: y_panel + borde + ph, x + borde: x + borde + pw] = img
        for j, linea in enumerate(pies[i]):
            _texto(hoja, linea, x + borde, y_pie + alto_linea * (j + 1), fs_pie, grosor, color)
    return hoja


@dataclass(frozen=True)
class Resultado:
    video: Path
    lamina: Path
    a: int
    b: int
    factor: int
    contexto: tuple[int, int]
    cuadros_video: int
    paneles: int
    recorte: tuple[int, int, int, int]
    recorte_origen: str
    filtro: str
    fps_fuente: float
    fps_salida: float
    segundos: float


def correr(
    video: Path,
    a: int,
    b: int,
    *,
    factor: int = 4,
    contexto: int = 2,
    out_dir: Path | None = None,
    filtro: str = FILTRO_DEFECTO,
    recorte: str = "persona",
    marca: float | None = None,
    marca_texto: str | None = None,
    marca_mas_menos: float | None = None,
    fps_salida: float | None = None,
    progreso=None,
) -> Resultado:
    if b <= a:
        raise InterpolarError(f"--entre A B necesita B > A (llegó {a} {b})")
    out_dir = out_dir or video.with_name(video.stem + ".kinelab")
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fuente = leer_tramo(video, a - contexto, b + contexto)
    if fuente.inicio > a or fuente.fin < b:
        raise InterpolarError(f"{video}: el tramo {a}–{b} no entra en los {fuente.frames_total} cuadros del clip")
    n = len(fuente.frames)
    esperados = (n - 1) * factor + 1
    fps_out = fps_salida if fps_salida else fuente.fps * factor
    caja, origen = _recorte(recorte, out_dir, fuente.width, fuente.height, a, b)
    x0, y0, x1, y1 = caja

    destino_mp4 = out_dir / f"interpolado-{a}-{b}-x{factor}.mp4"
    destino_png = out_dir / f"lamina-{a}-{b}-x{factor}.png"
    cmd = [
        ffmpeg_bin(), "-y", "-v", "error", "-nostdin",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{fuente.width}x{fuente.height}", "-r", f"{fps_out:.4f}", "-i", "-",
        # `-g 12` como el master.mp4 de la Fase 4: retroceder un cuadro en el
        # navegador no decodifica 250.
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-g", "12", "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-movflags", "+faststart", str(destino_mp4),
    ]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    paneles: list[tuple[float, np.ndarray]] = []
    escritos = 0
    try:
        for k, cuadro in enumerate(interpolar_cuadros(fuente.frames, factor, filtro=filtro)):
            indice = fuente.inicio + k / factor
            rotulado = rotular(cuadro, indice)
            enc.stdin.write(np.ascontiguousarray(rotulado).tobytes())
            escritos += 1
            if a - 1e-9 <= indice <= b + 1e-9:
                paneles.append((indice, cuadro[y0:y1, x0:x1].copy()))
            if progreso is not None:
                progreso(escritos, esperados)
    finally:
        if enc.stdin:
            enc.stdin.close()
        err = enc.stderr.read().decode("utf-8", "replace")
        enc.stderr.close()
        enc.wait(timeout=600)
    if enc.returncode != 0:
        raise InterpolarError(f"ffmpeg no pudo escribir {destino_mp4}: {err.strip() or '(sin mensaje)'}")

    cabecera = [
        AVISO,
        f"{video.name} · cuadros {a}–{b} a x{factor} ({factor - 1} intermedios por hueco) · tramo del video: {fuente.inicio}–{fuente.fin}",
        f"minterpolate={filtro} · recorte {caja} ({origen}) · clip a {_coma(fuente.fps, 3)} fps",
    ]
    hoja = lamina(paneles, cabecera=cabecera, marca=marca, marca_texto=marca_texto, marca_mas_menos=marca_mas_menos)
    if not cv2.imwrite(str(destino_png), hoja):
        raise InterpolarError(f"no se pudo escribir {destino_png}")
    return Resultado(
        video=destino_mp4, lamina=destino_png, a=a, b=b, factor=factor,
        contexto=(a - fuente.inicio, fuente.fin - b), cuadros_video=escritos, paneles=len(paneles),
        recorte=caja, recorte_origen=origen, filtro=filtro, fps_fuente=fuente.fps, fps_salida=fps_out,
        segundos=time.time() - t0,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m kinelab.tools.interpolar",
        description="Cuadros fabricados entre dos cuadros medidos, etiquetados, para mirar. Ninguna métrica los lee.",
    )
    ap.add_argument("video", type=Path)
    ap.add_argument("--entre", type=int, nargs=2, required=True, metavar=("A", "B"), help="índices de cuadro (los del motor), B > A")
    ap.add_argument("--factor", type=int, default=4, help="cuántos huecos por intervalo: 4 = 3 intermedios (por defecto 4)")
    ap.add_argument("--contexto", type=int, default=2, help="cuadros extra a cada lado para que la estimación de movimiento tenga con qué (por defecto 2)")
    ap.add_argument("--out", type=Path, default=None, help="carpeta de salida (por defecto <video>.kinelab/)")
    ap.add_argument("--filtro", default=FILTRO_DEFECTO, help=f"opciones de minterpolate (por defecto {FILTRO_DEFECTO})")
    ap.add_argument("--recorte", default="persona", help="'persona' (bbox de pose.npz), 'completo', o 'x0,y0,x1,y1'")
    ap.add_argument("--marca", type=float, default=None, help="índice fraccional donde dibujar la marca vertical en la lámina")
    ap.add_argument("--marca-texto", default=None, help="texto de la marca")
    ap.add_argument("--marca-mas-menos", type=float, default=None, help="semiancho de la banda de la marca, en cuadros")
    ap.add_argument("--fps-reproduccion", type=float, default=None, help="fps del mp4 de salida (por defecto fps del clip × factor, que a 120 o 240 dura décimas de segundo)")
    args = ap.parse_args(argv)

    if not args.video.exists():
        print(f"no existe: {args.video}", file=sys.stderr)
        return 2
    a, b = args.entre

    def progreso(i: int, total: int) -> None:
        print(f"\r  cuadro {i}/{total}", end="", flush=True)

    try:
        r = correr(
            args.video, a, b, factor=args.factor, contexto=args.contexto, out_dir=args.out,
            filtro=args.filtro, recorte=args.recorte, marca=args.marca, marca_texto=args.marca_texto,
            marca_mas_menos=args.marca_mas_menos, fps_salida=args.fps_reproduccion, progreso=progreso,
        )
    except (InterpolarError, FileNotFoundError, BrokenPipeError, subprocess.TimeoutExpired) as e:
        print(f"\nerror: {e}", file=sys.stderr)
        return 2
    print(
        f"\r  {r.cuadros_video} cuadros escritos en {_coma(r.segundos, 1)} s"
        f"\n  {r.video}   ({_coma(r.fps_salida, 2)} fps, contexto {r.contexto[0]}+{r.contexto[1]})"
        f"\n  {r.lamina}   ({r.paneles} paneles, recorte {r.recorte}: {r.recorte_origen})"
        f"\n  {AVISO}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
