# ============================================================
# pdf_devoluciones.py
# Genera PDF de una devolución de almacén
# PostgreSQL
# ============================================================

from flask import Blueprint, send_file, jsonify
from flask_jwt_extended import jwt_required, get_jwt

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

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

import os
from io import BytesIO

from database import get_connection
from utils.firmas import imagen_firma


# ============================================================
# BLUEPRINT
# ============================================================

pdf_devoluciones_bp = Blueprint(
    "pdf_devoluciones",
    __name__
)


# ============================================================
# GET /api/pdf/devolucion/<id>
# ============================================================

@pdf_devoluciones_bp.route(
    "/devolucion/<int:id>",
    methods=["GET"]
)
@jwt_required()
def generar_pdf_devolucion(id):

    claims = get_jwt()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # DATOS DE LA DEVOLUCIÓN
            # =================================================

            cursor.execute("""
                SELECT
                    dv.id,
                    dv.numero_documento,

                    dv.sede_id,
                    dv.salida_id,

                    dv.motivo,
                    dv.observaciones,

                    dv.usuario_id,

                    dv.estado,

                    dv.fecha,
                    dv.fecha_anulacion,

                    dv.anulada_por,
                    dv.motivo_anulacion,

                    dv.firma_entrega_base64,
                    dv.firma_recibe_base64,

                    sd.nombre AS sede_nombre,
                    sd.ciudad AS sede_ciudad,

                    u.nombre AS usuario_nombre,

                    ua.nombre AS anulada_por_nombre,

                    s.numero_documento AS salida_numero,
                    s.destino AS salida_destino,

                    c.nombre AS cliente_nombre

                FROM devoluciones dv

                LEFT JOIN sedes sd
                    ON sd.id = dv.sede_id

                LEFT JOIN usuarios u
                    ON u.id = dv.usuario_id

                LEFT JOIN usuarios ua
                    ON ua.id = dv.anulada_por

                LEFT JOIN salidas s
                    ON s.id = dv.salida_id

                LEFT JOIN clientes c
                    ON c.id = s.cliente_id

                WHERE dv.id = %s
            """, (id,))

            devolucion_db = cursor.fetchone()

            if not devolucion_db:

                return jsonify({
                    "error": "Devolución no encontrada"
                }), 404

            devolucion = dict(devolucion_db)

            # =================================================
            # RESTRICCIÓN POR SEDE
            # =================================================

            if (
                claims.get("rol") != "admin"
                and devolucion.get("sede_id") != claims.get("sede_id")
            ):

                return jsonify({
                    "error": "No tienes permiso para ver esta devolución"
                }), 403


            # =================================================
            # DETALLE DE PRODUCTOS
            #
            # MODELO / MARCA:
            #
            # Si es equipo serializado:
            # equipos -> modelos -> marcas
            #
            # Si NO es serializado:
            # productos -> modelos -> marcas
            #
            # COALESCE toma primero el modelo/marca
            # del equipo y, si no existe, usa el del producto.
            # =================================================

            cursor.execute("""
                SELECT
                    d.id,

                    d.producto_id,
                    d.equipo_id,

                    d.cantidad,

                    d.condicion_retorno,
                    d.observaciones,

                    p.codigo,

                    p.nombre AS producto_nombre,

                    p.requiere_serial,

                    un.codigo AS unidad_codigo,

                    un.nombre AS unidad_nombre,

                    eq.serial AS serial,

                    COALESCE(
                        me.id,
                        mp.id
                    ) AS modelo_id,

                    COALESCE(
                        me.nombre,
                        mp.nombre
                    ) AS modelo_nombre,

                    COALESCE(
                        mae.id,
                        map.id
                    ) AS marca_id,

                    COALESCE(
                        mae.nombre,
                        map.nombre
                    ) AS marca_nombre

                FROM detalle_devoluciones d

                INNER JOIN productos p
                    ON p.id = d.producto_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                LEFT JOIN equipos eq
                    ON eq.id = d.equipo_id

                -- Modelo del equipo serializado
                LEFT JOIN modelos me
                    ON me.id = eq.modelo_id

                -- Marca del modelo del equipo
                LEFT JOIN marcas mae
                    ON mae.id = me.marca_id

                -- Modelo del producto no serializado
                LEFT JOIN modelos mp
                    ON mp.id = p.modelo_id

                -- Marca del modelo del producto
                LEFT JOIN marcas map
                    ON map.id = mp.marca_id

                WHERE d.devolucion_id = %s

                ORDER BY d.id
            """, (id,))

            detalle = [
                dict(item)
                for item in cursor.fetchall()
            ]

    except Exception as e:

        return jsonify({
            "error": str(e)
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

        textColor=colors.HexColor(
            "#0d2137"
        )
    )


    estilo_encabezado = ParagraphStyle(
        "enc",

        fontSize=7,

        fontName="Helvetica-Bold",

        textColor=colors.white,

        alignment=TA_CENTER
    )


    estilo_label = ParagraphStyle(
        "label",

        fontSize=7,

        fontName="Helvetica-Bold",

        textColor=colors.HexColor(
            "#0d2137"
        )
    )


    estilo_valor = ParagraphStyle(
        "valor",

        fontSize=8,

        leading=10
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

            "DEVOLUCIÓN ALMACÉN",

            ParagraphStyle(

                "tit",

                fontSize=16,

                fontName="Helvetica-Bold",

                textColor=colors.HexColor(
                    "#0d2137"
                ),

                alignment=TA_CENTER
            )
        ),


        Spacer(
            1,
            0.2 * cm
        ),


        Paragraph(

            f'N° {devolucion.get("numero_documento", "")}',

            ParagraphStyle(

                "num",

                fontSize=9,

                alignment=TA_CENTER,

                textColor=colors.HexColor(
                    "#1a6fc4"
                )
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
    # FECHA
    # ========================================================

    fecha = devolucion.get(
        "fecha"
    )


    if fecha:

        fecha_str = str(fecha)[:19]

    else:

        fecha_str = "—"


    # ========================================================
    # ESTADO
    # ========================================================

    estado = (
        devolucion.get("estado")
        or "ACTIVA"
    )


    # ========================================================
    # INFORMACIÓN GENERAL
    # ========================================================

    info_data = [

        [

            Paragraph(
                "Sede:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "sede_nombre"
                ) or "Almacén",

                estilo_valor
            ),


            Paragraph(
                "Fecha:",
                estilo_label
            ),


            Paragraph(
                fecha_str,
                estilo_valor
            )
        ],


        [

            Paragraph(
                "Procede de:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "salida_destino"
                ) or "—",

                estilo_valor
            ),


            Paragraph(
                "Salida origen:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "salida_numero"
                ) or "—",

                estilo_valor
            )
        ],


        [

            Paragraph(
                "Motivo:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "motivo"
                ) or "—",

                estilo_valor
            ),


            Paragraph(
                "Cliente:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "cliente_nombre"
                ) or "—",

                estilo_valor
            )
        ],


        [

            Paragraph(
                "Registrado por:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "usuario_nombre"
                ) or "—",

                estilo_valor
            ),


            Paragraph(
                "Observaciones:",
                estilo_label
            ),


            Paragraph(

                devolucion.get(
                    "observaciones"
                ) or "—",

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

                colors.HexColor(
                    "#dce6f0"
                )
            ),


            (
                "BACKGROUND",

                (0, 0),

                (0, -1),

                colors.HexColor(
                    "#f7f9fc"
                )
            ),


            (
                "BACKGROUND",

                (2, 0),

                (2, -1),

                colors.HexColor(
                    "#f7f9fc"
                )
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
    # INFORMACIÓN DE ANULACIÓN
    # ========================================================

    if estado == "ANULADA":

        fecha_anulacion = devolucion.get(
            "fecha_anulacion"
        )


        if fecha_anulacion:

            fecha_anulacion_str = str(
                fecha_anulacion
            )[:19]

        else:

            fecha_anulacion_str = "—"


        anulacion_data = [

            [

                Paragraph(
                    "ESTADO:",
                    estilo_label
                ),


                Paragraph(

                    "ANULADA",

                    ParagraphStyle(

                        "anulada",

                        fontSize=9,

                        fontName="Helvetica-Bold",

                        textColor=colors.red
                    )
                )
            ],


            [

                Paragraph(
                    "Anulada por:",
                    estilo_label
                ),


                Paragraph(

                    devolucion.get(
                        "anulada_por_nombre"
                    ) or "—",

                    estilo_valor
                )
            ],


            [

                Paragraph(
                    "Fecha de anulación:",
                    estilo_label
                ),


                Paragraph(
                    fecha_anulacion_str,
                    estilo_valor
                )
            ],


            [

                Paragraph(
                    "Motivo:",
                    estilo_label
                ),


                Paragraph(

                    devolucion.get(
                        "motivo_anulacion"
                    ) or "Sin motivo registrado",

                    estilo_valor
                )
            ]
        ]


        tabla_anulacion = Table(

            anulacion_data,

            colWidths=[

                5 * cm,

                13 * cm
            ]
        )


        tabla_anulacion.setStyle(

            TableStyle([

                (
                    "GRID",

                    (0, 0),

                    (-1, -1),

                    0.5,

                    colors.HexColor(
                        "#dce6f0"
                    )
                ),


                (
                    "BACKGROUND",

                    (0, 0),

                    (0, -1),

                    colors.HexColor(
                        "#fff4f4"
                    )
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
    # PRODUCTOS
    # ========================================================

    for item in detalle:

        serial = (
            item.get("serial")
            or ""
        )


        # Si requiere serial pero no quedó asociado
        # mostramos una advertencia.

        if (
            not serial
            and item.get("requiere_serial")
        ):

            serial = "SIN SERIAL"


        filas.append([

            Paragraph(

                item.get(
                    "producto_nombre"
                ) or "",

                estilo_celda
            ),


            Paragraph(

                item.get(
                    "modelo_nombre"
                ) or "—",

                estilo_celda
            ),


            Paragraph(
                serial,
                estilo_celda
            ),


            Paragraph(

                item.get(
                    "marca_nombre"
                ) or "—",

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

                item.get(
                    "unidad_codigo"
                ) or "UND",

                estilo_celda
            )
        ])


    # ========================================================
    # FILAS VACÍAS
    # ========================================================

    for _ in range(

        max(
            0,
            10 - len(detalle)
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
    # TABLA PRODUCTOS
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
        ],

        repeatRows=1
    )


    tabla_productos.setStyle(

        TableStyle([

            (
                "BACKGROUND",

                (0, 0),

                (-1, 0),

                colors.HexColor(
                    "#0d2137"
                )
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
                "GRID",

                (0, 0),

                (-1, -1),

                0.5,

                colors.HexColor(
                    "#dce6f0"
                )
            ),


            (
                "ROWBACKGROUNDS",

                (0, 1),

                (-1, -1),

                [

                    colors.white,

                    colors.HexColor(
                        "#f7f9fc"
                    )
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
            ),


            (
                "FONTSIZE",

                (0, 1),

                (-1, -1),

                8
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
    #
    # Firma digital de quien entrega (cliente que devuelve) y
    # de quien recibe (almacenista), capturadas al momento de
    # registrar la devolución. Si alguna firma no fue
    # capturada, se deja el espacio en blanco en vez de fallar.
    # ========================================================

    estilo_sin_firma = ParagraphStyle(
        "sinFirma",
        fontSize=7,
        textColor=colors.HexColor("#9aabbd"),
        alignment=TA_CENTER
    )

    ancho_firma = 6 * cm
    alto_firma = 2 * cm

    firma_entrega_img = (
        imagen_firma(
            devolucion.get("firma_entrega_base64"),
            ancho_firma,
            alto_firma
        )
        or Paragraph("(sin firma)", estilo_sin_firma)
    )

    firma_recibe_img = (
        imagen_firma(
            devolucion.get("firma_recibe_base64"),
            ancho_firma,
            alto_firma
        )
        or Paragraph("(sin firma)", estilo_sin_firma)
    )

    firmas = Table(

        [
            [
                Paragraph(
                    "Entregado por:",
                    estilo_label
                ),

                Paragraph(
                    "Recibido por:",
                    estilo_label
                )
            ],

            [
                firma_entrega_img,
                firma_recibe_img
            ],

            [
                Paragraph(
                    str(
                        devolucion.get(
                            "cliente_nombre"
                        )
                        or ""
                    ),
                    estilo_valor
                ),

                Paragraph(
                    str(
                        devolucion.get(
                            "usuario_nombre"
                        )
                        or ""
                    ),
                    estilo_valor
                )
            ]
        ],

        colWidths=[
            9 * cm,
            9 * cm
        ],

        rowHeights=[
            0.7 * cm,
            alto_firma + 0.3 * cm,
            0.7 * cm
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
                (-1, 0),
                colors.HexColor("#f7f9fc")
            ),

            (
                "ALIGN",
                (0, 1),
                (-1, 1),
                "CENTER"
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

    doc.build(
        elementos
    )


    buffer.seek(0)


    return send_file(

        buffer,

        mimetype="application/pdf",

        as_attachment=False,

        download_name=(

            f'devolucion_'

            f'{devolucion.get("numero_documento", id)}'

            f'.pdf'
        )
    )