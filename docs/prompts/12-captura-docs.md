# 12 — Lo que midieron el 07 y el 11 entra a los documentos de captura; y un test que caduca

Para correr: `/encargo 12` en una sesión nueva. Leé antes los informes del
07 (punto 6 de "queda abierto") y del 11 en `docs/informes/`.

## Contexto

El 11 midió sobre tres clips reales del S22: 4K no agrega precisión (el
recorte del cuerpo ya se reduce 5,2× hasta los 256 px de entrada del modelo
en FHD) y cuesta 2,15× por cuadro y 3,4× de disco; WhatsApp **como
documento** entrega el archivo intacto (`udta` de Samsung entero, HEVC a
43 Mb/s) mientras el envío **como video** recomprime; el cuerpo salió al
28 % del alto. El 07 midió que el 80 % del alto en vertical exige una focal
de teleobjetivo (3078 px a 3 m): con la lente principal de un teléfono
habría que estar a 0,8 m. Y el 11 dejó un test rojo que caduca por fecha.

Leer: `CAPTURA.md` entero, `docs/filmacion-s22.md`,
`docs/checklist-captura.md`, y en `tests/test_service.py` el test
`test_datos_lista_un_ejemplo_de_otro_proceso`.

## Encargo

1. `CAPTURA.md`:
   - §Presupuesto de datos: fila UHD 60 "desaconsejado, medido", con los
     tres números del 11 y la razón (192×256 de entrada al modelo).
   - §Encuadre: la regla 80–90 % queda como objetivo, con esta nota medida:
     en vertical con la lente principal es inalcanzable a distancia usable
     (07, punto 6); lo que el motor mide es la altura del cuerpo en px, y el
     umbral del gate sale del barrido de tamaño del arnés (encargo 13, en
     curso). Anotar los cuatro valores reales: 28,2 / 28,7 / 29,5 % en UHD y
     41,9 % en FHD. Sin fijar umbral.
   - §Transferencia: fila "WhatsApp como documento" = intacto (medido en
     el 11), "WhatsApp como video" = recomprimido; el cable sigue siendo el
     camino de referencia.
   - §Lo que queda por verificar: con el S22 Ultra, ningún modo Video llega
     a 100 fps; el cronómetro en Slow motion FHD 240 es lo único que puede
     dar un clip que pase el gate.
2. `docs/filmacion-s22.md` (la guía que recibe quien filma): FHD 60, no
   UHD, con el porqué en una línea; WhatsApp: documento sí, video no; el
   cronómetro en Slow motion FHD 240 pasa a ser el paso 1, con su lista
   (10 s de cronómetro, sin editar ni recortar en Galería, el archivo
   entero, por cable o WhatsApp documento) y el de FHD 60 después; encuadre:
   "lo más cerca que permita tener los pies y el palo en el top adentro",
   con el dato de que los tres clips salieron al 28 % y hace falta más.
3. `tests/test_service.py`: la fecha del ejemplo del test relativa a `now`,
   no literal.

NO: no tocar el motor, `service/` ni `web/`; no cambiar umbrales del gate;
no inventar un umbral de encuadre.

## Cómo se prueba

`.venv/bin/pytest -q tests/test_service.py` en verde (hoy tiene ese test en
rojo). Los tres documentos leídos de punta a punta al terminar; en el
informe, qué dice ahora la guía en cinco líneas.

## En paralelo

13 (`truth/` salvo `mocap.py`, `sports/golf/mdc.yaml`,
`sports/golf/metrics.py`), 14 (`truth/kinelab_truth/mocap.py`,
`kinelab/metrics/core.py`, `CONTRATO.md`, `data/examples/`), 15
(`sports/golf/events.py`, `kinelab/events/`, `tests/test_fase2.py`,
`DECISIONES.md`). Vos: `CAPTURA.md`, `docs/filmacion-s22.md`,
`docs/checklist-captura.md`, `tests/test_service.py`. Ningún otro archivo.
