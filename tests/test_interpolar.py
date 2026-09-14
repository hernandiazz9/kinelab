"""Cuadros fabricados entre dos medidos: que sean los que se pidieron, que los
medidos sigan intactos debajo del rótulo, y que la marca caiga donde dice.

Todo sobre los clips sintéticos de `conftest.py`. Lo que se verifica es la
mecánica de la herramienta; si la interpolación *sirve* para mirar un swing es
una decisión de quien mira, y está medida en
`docs/informes/2026-09-14-05-lamina-interpolada.md`.
"""

from __future__ import annotations

import numpy as np
import pytest

from kinelab.perception.video import iter_frames
from kinelab.tools.interpolar import (
    COLOR_MARCA,
    COLOR_MEDIDO,
    COLOR_SINTETICO,
    InterpolarError,
    alto_franja,
    correr,
    etiqueta,
    interpolar_cuadros,
    lamina,
    leer_tramo,
    rotular,
)

A, B, FACTOR, CONTEXTO = 10, 11, 4, 2
N_ENTRADA = (B + CONTEXTO) - (A - CONTEXTO) + 1  # 6
N_SALIDA = (N_ENTRADA - 1) * FACTOR + 1  # 21


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    d = a.astype(np.float64) - b.astype(np.float64)
    mse = float(np.mean(d * d))
    return float("inf") if mse == 0 else 10 * np.log10(255.0**2 / mse)


@pytest.fixture(scope="module")
def tramo(clips):
    return leer_tramo(clips["real30_h264"], A - CONTEXTO, B + CONTEXTO)


@pytest.fixture(scope="module")
def interpolados(tramo):
    return list(interpolar_cuadros(tramo.frames, FACTOR))


def test_cuenta_de_cuadros(tramo, interpolados):
    """`(n − 1) · factor + 1`: `minterpolate` se queda sin el último cuadro y la
    herramienta lo compensa duplicando la entrada. Si eso se rompe, la lámina
    pierde el cuadro B, que es justamente uno de los dos medidos."""
    assert len(tramo.frames) == N_ENTRADA
    assert len(interpolados) == N_SALIDA


def test_los_multiplos_de_factor_son_los_medidos(tramo, interpolados):
    """El cuadro de salida `k·factor` tiene que ser el cuadro de entrada `k`.

    No es igualdad exacta: el filtro trabaja en YUV y el ida y vuelta desde BGR
    redondea. Lo que se exige es que no haya movimiento: por debajo de ~35 dB
    ya sería otro cuadro.
    """
    for k in range(0, len(interpolados), FACTOR):
        assert psnr(interpolados[k], tramo.frames[k // FACTOR]) > 35


def test_los_intermedios_van_de_un_medido_al_otro(interpolados):
    """Cada intermedio es distinto de sus dos vecinos medidos, y se va
    pareciendo cada vez menos al de atrás y cada vez más al de adelante.

    Es lo que amarra el índice fraccional al cuadro de salida: si la salida
    saliera corrida, duplicada o al revés, esta progresión se rompe. Medido
    sobre el clip sintético, hueco por hueco: 33,7 → 27,6 → 24,1 dB contra el
    de atrás y 24,1 → 27,7 → 33,7 dB contra el de adelante.
    """
    for base in range(0, len(interpolados) - 1, FACTOR):
        antes, despues = interpolados[base], interpolados[base + FACTOR]
        hacia_atras = [psnr(interpolados[base + j], antes) for j in range(1, FACTOR)]
        hacia_adelante = [psnr(interpolados[base + j], despues) for j in range(1, FACTOR)]
        for j in range(1, FACTOR):
            assert not np.array_equal(interpolados[base + j], antes)
            assert not np.array_equal(interpolados[base + j], despues)
        assert hacia_atras == sorted(hacia_atras, reverse=True)
        assert hacia_adelante == sorted(hacia_adelante)


def test_el_rotulo_no_toca_la_imagen(tramo):
    """Debajo de la franja, un cuadro medido sigue siendo el cuadro medido:
    byte a byte. Es lo que permite mirar la lámina y creerle a los extremos."""
    f = tramo.frames[0]
    h, w = f.shape[:2]
    banda = alto_franja(w, h)
    con_rotulo = rotular(f, 10.0)
    assert np.array_equal(con_rotulo[banda:], f[banda:])
    assert not np.array_equal(con_rotulo[:banda], f[:banda])


def test_etiqueta_distingue_medido_de_fabricado():
    texto, color, medido = etiqueta(44.0)
    assert medido and color == COLOR_MEDIDO and texto == "medido · 44"
    texto, color, medido = etiqueta(44.25)
    assert not medido and color == COLOR_SINTETICO and "no medido" in texto and "44,25" in texto


def test_corrida_completa_deja_los_dos_archivos(clips, tmp_path):
    r = correr(
        clips["real30_h264"], A, B, factor=FACTOR, contexto=CONTEXTO, out_dir=tmp_path,
        marca=10.44, marca_texto="marca de prueba", marca_mas_menos=0.11,
    )
    assert r.video.name == f"interpolado-{A}-{B}-x{FACTOR}.mp4"
    assert r.lamina.name == f"lamina-{A}-{B}-x{FACTOR}.png"
    assert r.video.is_file() and r.lamina.is_file()
    assert r.cuadros_video == N_SALIDA
    assert r.paneles == (B - A) * FACTOR + 1
    assert r.contexto == (CONTEXTO, CONTEXTO)

    escritos = sum(1 for _ in iter_frames(r.video))
    assert escritos == N_SALIDA

    import cv2

    hoja = cv2.imread(str(r.lamina))
    ph, pw = r.recorte[3] - r.recorte[1], r.recorte[2] - r.recorte[0]
    # Una fila de `paneles` recortes, con sus bordes, huecos y márgenes: más
    # ancha que la suma pelada y bastante menos que el doble.
    assert r.paneles * pw < hoja.shape[1] < r.paneles * pw * 1.6 + 4 * pw
    assert hoja.shape[0] > ph


def test_la_marca_cae_en_el_lugar_del_indice():
    """La marca de 44,25 tiene que caer sobre el panel de 44,25, no cerca."""
    pw, ph = 40, 60
    paneles = [(44 + i / 4, np.full((ph, pw, 3), 200, np.uint8)) for i in range(5)]
    hoja = lamina(paneles, cabecera=["x"], marca=44.25, marca_texto="m")
    col = np.where((hoja == np.array(COLOR_MARCA, np.uint8)).all(axis=2).any(axis=0))[0]
    assert col.size, "no se dibujó la marca"
    x = float(np.median(col))
    # El centro del panel i está en margen + i·paso + borde + pw/2.
    borde, hueco = max(2, ph // 250), max(6, pw // 40)
    paso, margen = pw + 2 * borde + hueco, hueco
    esperado = margen + 1 * paso + borde + pw / 2
    assert abs(x - esperado) <= 2


def test_pide_b_mayor_que_a_y_factor_de_dos_para_arriba(clips, tmp_path):
    with pytest.raises(InterpolarError):
        correr(clips["real30_h264"], 11, 10, out_dir=tmp_path)
    with pytest.raises(InterpolarError):
        correr(clips["real30_h264"], 10, 11, factor=1, out_dir=tmp_path)


def test_un_tramo_fuera_del_clip_se_rechaza(clips, tmp_path):
    with pytest.raises(InterpolarError):
        correr(clips["real30_h264"], 5000, 5001, out_dir=tmp_path)
