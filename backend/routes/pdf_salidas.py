# ============================================================
# pdf_salidas.py
# Genera PDF de una salida de almacén
# PostgreSQL
# ============================================================

from flask import Blueprint, send_file, jsonify

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image
)

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.lib.enums import TA_CENTER

import os
from io import BytesIO

from database import get_connection


pdf_salidas_bp = Blueprint(
    "pdf_salidas",
    __name__
)


# ============================================================
# GET /api/pdf/salida/<id>
# ============================================================

@pdf_salidas_bp.route(
    "/salida/<int:id>",
    methods=["GET"]
)
def generar_pdf_salida(id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # DATOS DE LA SALIDA
            # =================================================

            cursor.execute("""
                SELECT
                    s.id,
                    s.numero_documento,
                    s.sede_id,
                    s.destino,
                    s.observaciones,
                    s.estado,
                    s.usuario_id,
                    s.fecha,
                    s.fecha_anulacion,
                    s.anulada_por,
                    s.motivo_anulacion,

                    sd.nombre AS sede_nombre,
                    sd.ciudad AS sede_ciudad,

                    u.nombre AS usuario_nombre,

                    ua.nombre AS anulado_por_nombre,

                    c.nombre AS cliente_nombre

                FROM salidas s

                LEFT JOIN sedes sd
                    ON sd.id = s.sede_id

                LEFT JOIN usuarios u
                    ON u.id = s.usuario_id

                LEFT JOIN usuarios ua
                    ON ua.id = s.anulada_por

                LEFT JOIN clientes c
                    ON c.id = s.cliente_id

                WHERE s.id = %s
            """, (
                id,
            ))

            salida = cursor.fetchone()

            if not salida:

                return jsonify({
                    "error": "Salida no encontrada"
                }), 404


            # =================================================
            # DETALLE DE LA SALIDA
            # =================================================

            cursor.execute("""
                SELECT
                    d.id,
                    d.producto_id,
                    d.equipo_id,
                    d.cantidad,
                    d.observaciones,

                    p.codigo,
                    p.nombre AS producto_nombre,
                    p.requiere_serial,

                    un.codigo AS unidad_codigo,
                    un.nombre AS unidad_nombre

                FROM detalle_salidas d

                INNER JOIN productos p
                    ON p.id = d.producto_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                WHERE d.salida_id = %s

                ORDER BY d.id
            """, (
                id,
            ))

            detalle = [
                dict(item)
                for item in cursor.fetchall()
            ]


            # =================================================
            # EQUIPOS / SERIALES
            #
            # Para salidas serializadas se utiliza equipo_id
            # directamente desde detalle_salidas.
            # =================================================

            for item in detalle:

                item["equipos"] = []

                if item.get("requiere_serial"):

                    # -------------------------------------------------
                    # CASO NORMAL:
                    # cada detalle tiene equipo_id
                    # -------------------------------------------------

                    if item.get("equipo_id"):

                        cursor.execute("""
                            SELECT
                                e.serial,
                                mo.nombre AS modelo_nombre,
                                ma.nombre AS marca_nombre

                            FROM equipos e

                            LEFT JOIN modelos mo
                                ON mo.id = e.modelo_id

                            LEFT JOIN marcas ma
                                ON ma.id = mo.marca_id

                            WHERE e.id = %s

                            LIMIT 1
                        """, (
                            item["equipo_id"],
                        ))

                        equipo = cursor.fetchone()

                        if equipo:

                            item["equipos"].append({
                                "serial": str(
                                    equipo["serial"]
                                    or ""
                                ),

                                "modelo_nombre": str(
                                    equipo["modelo_nombre"]
                                    or ""
                                ),

                                "marca_nombre": str(
                                    equipo["marca_nombre"]
                                    or ""
                                )
                            })


    except Exception as error:

        print(
            "ERROR GENERANDO PDF DE SALIDA:",
            error
        )

        return jsonify({
            "error": (
                "No se pudo generar el PDF de la salida.",
                str(error)
            )
        }), 500

    finally:

        conn.close()


    # ========================================================
    # CREAR PDF EN MEMORIA
    # ========================================================

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,

        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    elementos = []

    estilos = getSampleStyleSheet()


    # ========================================================
    # ESTILOS
    # ========================================================

    estilo_celda = ParagraphStyle(
        "celda",
        fontSize=8,
        leading=10
    )

    estilo_titulo = ParagraphStyle(
        "titulo",
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0d2137")
    )

    estilo_encabezado = ParagraphStyle(
        "enc",
        fontSize=7,
        fontName="Helvetica-Bold",
        textColor=colors.white
    )

    estilo_label = ParagraphStyle(
        "label",
        fontSize=7,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0d2137")
    )

    estilo_valor = ParagraphStyle(
        "valor",
        fontSize=8
    )


    # ========================================================
    # LOGO
    # ========================================================

    logo_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "frontend",
            "img",
            "occidente.png"
        )
    )

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=4 * cm,
            height=2.5 * cm
        )

    else:

        logo = Paragraph(
            "OCCIDENTE",
            estilo_titulo
        )


    # ========================================================
    # TÍTULO
    # ========================================================

    bloque_titulo = [

        Paragraph(
            "SALIDA ALMACÉN",

            ParagraphStyle(
                "tit",
                fontSize=16,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0d2137"),
                alignment=TA_CENTER
            )
        ),

        Spacer(
            1,
            0.2 * cm
        ),

        Paragraph(
            f'N° {salida.get("numero_documento", "")}',

            ParagraphStyle(
                "num",
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1a6fc4")
            )
        )
    ]


    tabla_header = Table(
        [[
            logo,
            bloque_titulo
        ]],

        colWidths=[
            5 * cm,
            13 * cm
        ]
    )


    tabla_header.setStyle(
        TableStyle([

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "ALIGN",
                (1, 0),
                (1, 0),
                "CENTER"
            )
        ])
    )


    elementos.append(
        tabla_header
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm
        )
    )


    # ========================================================
    # ESTADO
    # ========================================================

    estado = (
        salida.get("estado")
        or "ACTIVA"
    )


    # ========================================================
    # ORIGEN
    # ========================================================

    origen = "Almacén"


    # ========================================================
    # DESTINO
    # ========================================================

    destino = (
        salida.get("destino")
        or ""
    )


    # ========================================================
    # INFORMACIÓN
    # ========================================================

    info_data = [

        [
            Paragraph(
                "Origen:",
                estilo_label
            ),

            Paragraph(
                origen,
                estilo_valor
            ),

            Paragraph(
                "Destino:",
                estilo_label
            ),

            Paragraph(
                destino,
                estilo_valor
            )
        ],

        [
            Paragraph(
                "Sede:",
                estilo_label
            ),

            Paragraph(
                (
                    f'{salida.get("sede_nombre", "")}'
                    f' - '
                    f'{salida.get("sede_ciudad", "")}'
                ),
                estilo_valor
            ),

            Paragraph(
                "Documento:",
                estilo_label
            ),

            Paragraph(
                str(
                    salida.get(
                        "numero_documento"
                    )
                    or ""
                ),
                estilo_valor
            )
        ],

        [
            Paragraph(
                "Registrado por:",
                estilo_label
            ),

            Paragraph(
                str(
                    salida.get(
                        "usuario_nombre"
                    )
                    or ""
                ),
                estilo_valor
            ),

            Paragraph(
                "Cliente:",
                estilo_label
            ),

            Paragraph(
                str(
                    salida.get(
                        "cliente_nombre"
                    )
                    or "—"
                ),
                estilo_valor
            )
        ],

        [
            Paragraph(
                "Observaciones:",
                estilo_label
            ),

            Paragraph(
                str(
                    salida.get(
                        "observaciones"
                    )
                    or ""
                ),
                estilo_valor
            ),

            Paragraph(
                "",
                estilo_label
            ),

            Paragraph(
                "",
                estilo_valor
            )
        ]
    ]


    tabla_info = Table(
        info_data,

        colWidths=[
            3.5 * cm,
            7 * cm,
            3 * cm,
            4.5 * cm
        ]
    )


    tabla_info.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#dce6f0")
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor("#f7f9fc")
            ),

            (
                "BACKGROUND",
                (2, 0),
                (2, -1),
                colors.HexColor("#f7f9fc")
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )


    elementos.append(
        tabla_info
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm
        )
    )


    # ========================================================
    # AVISO DE ANULACIÓN
    # ========================================================

    if estado == "ANULADA":

        anulacion_data = [

            [
                Paragraph(
                    "ANULADA",

                    ParagraphStyle(
                        "anulada",
                        fontSize=10,
                        fontName="Helvetica-Bold",
                        textColor=colors.red
                    )
                ),

                Paragraph(
                    "Esta salida se encuentra anulada.",
                    estilo_valor
                )
            ],

            [
                Paragraph(
                    "Anulada por:",
                    estilo_label
                ),

                Paragraph(
                    str(
                        salida.get(
                            "anulado_por_nombre"
                        )
                        or ""
                    ),
                    estilo_valor
                )
            ],

            [
                Paragraph(
                    "Fecha de anulación:",
                    estilo_label
                ),

                Paragraph(
                    (
                        salida["fecha_anulacion"]
                        .strftime(
                            "%d/%m/%Y %H:%M"
                        )
                        if salida.get(
                            "fecha_anulacion"
                        )
                        else ""
                    ),
                    estilo_valor
                )
            ],

            [
                Paragraph(
                    "Motivo:",
                    estilo_label
                ),

                Paragraph(
                    str(
                        salida.get(
                            "motivo_anulacion"
                        )
                        or ""
                    ),
                    estilo_valor
                )
            ]
        ]


        tabla_anulacion = Table(
            anulacion_data,

            colWidths=[
                3.5 * cm,
                14.5 * cm
            ]
        )


        tabla_anulacion.setStyle(
            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#dce6f0")
                ),

                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f7f9fc")
                ),

                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                )
            ])
        )


        elementos.append(
            tabla_anulacion
        )

        elementos.append(
            Spacer(
                1,
                0.4 * cm
            )
        )


    # ========================================================
    # TABLA DE PRODUCTOS
    # ========================================================

    encabezados = [

        Paragraph(
            "Descripción del artículo",
            estilo_encabezado
        ),

        Paragraph(
            "Modelo",
            estilo_encabezado
        ),

        Paragraph(
            "N° Serial",
            estilo_encabezado
        ),

        Paragraph(
            "Marca",
            estilo_encabezado
        ),

        Paragraph(
            "Cantidad",
            estilo_encabezado
        ),

        Paragraph(
            "Unidad",
            estilo_encabezado
        )
    ]


    filas = [
        encabezados
    ]


    # ========================================================
    # CREAR FILAS
    #
    # PRODUCTO SERIALIZADO:
    # una fila por cada equipo
    #
    # PRODUCTO NO SERIALIZADO:
    # una sola fila con la cantidad total
    # ========================================================

    for item in detalle:

        equipos = item.get(
            "equipos",
            []
        )


        # ----------------------------------------------------
        # PRODUCTO SERIALIZADO
        # ----------------------------------------------------

        if item.get("requiere_serial") and equipos:

            for equipo in equipos:

                filas.append([

                    Paragraph(
                        str(
                            item.get(
                                "producto_nombre"
                            )
                            or ""
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        equipo.get(
                            "modelo_nombre",
                            ""
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        equipo.get(
                            "serial",
                            ""
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        equipo.get(
                            "marca_nombre",
                            ""
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        "1",
                        estilo_celda
                    ),

                    Paragraph(
                        str(
                            item.get(
                                "unidad_codigo"
                            )
                            or "UND"
                        ),
                        estilo_celda
                    )
                ])


        # ----------------------------------------------------
        # SERIALIZADO SIN EQUIPO ENCONTRADO
        # ----------------------------------------------------

        elif item.get("requiere_serial"):

            filas.append([

                Paragraph(
                    str(
                        item.get(
                            "producto_nombre"
                        )
                        or ""
                    ),
                    estilo_celda
                ),

                Paragraph(
                    "",
                    estilo_celda
                ),

                Paragraph(
                    "",
                    estilo_celda
                ),

                Paragraph(
                    "",
                    estilo_celda
                ),

                Paragraph(
                    str(
                        item.get(
                            "cantidad",
                            ""
                        )
                    ),
                    estilo_celda
                ),

                Paragraph(
                    str(
                        item.get(
                            "unidad_codigo"
                        )
                        or "UND"
                    ),
                    estilo_celda
                )
            ])


        # ----------------------------------------------------
        # PRODUCTO NO SERIALIZADO
        # ----------------------------------------------------

        else:

            filas.append([

                Paragraph(
                    str(
                        item.get(
                            "producto_nombre"
                        )
                        or ""
                    ),
                    estilo_celda
                ),

                Paragraph(
                    "",
                    estilo_celda
                ),

                Paragraph(
                    "",
                    estilo_celda
                ),

                Paragraph(
                    "",
                    estilo_celda
                ),

                Paragraph(
                    str(
                        item.get(
                            "cantidad",
                            ""
                        )
                    ),
                    estilo_celda
                ),

                Paragraph(
                    str(
                        item.get(
                            "unidad_codigo"
                        )
                        or "UND"
                    ),
                    estilo_celda
                )
            ])


    # ========================================================
    # FILAS VACÍAS
    # ========================================================

    for _ in range(
        max(
            0,
            10 - len(filas) + 1
        )
    ):

        filas.append([
            "",
            "",
            "",
            "",
            "",
            ""
        ])


    # ========================================================
    # TABLA
    # ========================================================

    tabla_productos = Table(
        filas,

        colWidths=[
            5.5 * cm,
            3 * cm,
            3 * cm,
            2.5 * cm,
            2 * cm,
            2 * cm
        ]
    )


    tabla_productos.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#0d2137")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, 0),
                8
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#dce6f0")
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f7f9fc")
                ]
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )


    elementos.append(
        tabla_productos
    )

    elementos.append(
        Spacer(
            1,
            1 * cm
        )
    )


    # ========================================================
    # FIRMAS
    # ========================================================

    firmas = Table(

        [[

            Paragraph(
                "Entregado por:",
                estilo_label
            ),

            Paragraph(
                str(
                    salida.get(
                        "usuario_nombre"
                    )
                    or ""
                ),
                estilo_valor
            ),

            Paragraph(
                "Recibido por:",
                estilo_label
            ),

            Paragraph(
                "",
                estilo_valor
            )
        ]],

        colWidths=[
            3 * cm,
            6.5 * cm,
            3 * cm,
            5.5 * cm
        ]
    )


    firmas.setStyle(
        TableStyle([

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#dce6f0")
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, 0),
                colors.HexColor("#f7f9fc")
            ),

            (
                "BACKGROUND",
                (2, 0),
                (2, 0),
                colors.HexColor("#f7f9fc")
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )


    elementos.append(
        firmas
    )


    # ========================================================
    # GENERAR PDF
    # ========================================================

    try:

        doc.build(
            elementos
        )

    except Exception as error:

        print(
            "ERROR CREANDO DOCUMENTO PDF:",
            error
        )

        return jsonify({
            "error": (
                "No se pudo construir el documento PDF.",
                str(error)
            )
        }), 500


    buffer.seek(0)


    return send_file(

        buffer,

        mimetype="application/pdf",

        as_attachment=False,

        download_name=(
            f"salida_"
            f"{salida.get('numero_documento', id)}"
            f".pdf"
        )
    )