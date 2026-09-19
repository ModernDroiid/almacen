# ============================================================
# utils/firmas.py
#
# Ayudante para incrustar firmas digitales en los PDF de
# entradas, salidas, traslados y devoluciones.
#
# La firma se captura en el navegador con un lienzo (canvas) al
# que se le puede dibujar con el dedo, el mouse o una tablet /
# lápiz de firma, y se envía al backend como una imagen PNG en
# base64 (normalmente con el prefijo
# "data:image/png;base64,...."). Este archivo se encarga de
# convertir ese texto de vuelta en una imagen que reportlab
# pueda insertar en el PDF.
# ============================================================

import base64
import re
from io import BytesIO

from reportlab.platypus import Image


def imagen_firma(firma_base64, width, height):
    """
    Convierte una firma en base64 en una imagen lista para
    insertar en un PDF con reportlab.

    - width / height se usan como un recuadro máximo: la firma
      se escala PROPORCIONALMENTE dentro de ese recuadro, para
      que no se vea estirada ni deformada.
    - Si no hay firma, o el dato no se puede leer (por ejemplo,
      quedó corrupto o no es una imagen), devuelve None en vez
      de lanzar un error, para que el PDF se genere igual, sin
      la firma, en lugar de fallar por completo.
    """

    if not firma_base64 or not isinstance(firma_base64, str):
        return None

    try:

        datos = firma_base64.strip()

        # ----------------------------------------------------
        # Quita el prefijo "data:image/png;base64," si viene
        # incluido (así llega normalmente desde el navegador).
        # ----------------------------------------------------

        coincidencia = re.match(
            r'^data:image/\w+;base64,(.+)$',
            datos
        )

        if coincidencia:
            datos = coincidencia.group(1)

        binario = base64.b64decode(datos)

        if not binario:
            return None

        return Image(
            BytesIO(binario),
            width=width,
            height=height,
            kind='proportional'
        )

    except Exception as error:

        print(
            'ERROR AL DECODIFICAR FIRMA PARA PDF:',
            error
        )

        return None