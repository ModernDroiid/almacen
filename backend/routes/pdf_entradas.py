# ============================================================
# pdf_entradas.py
# Genera PDF de una entrada de almacén
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

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.lib.enums import TA_CENTER

import os
from io import BytesIO

from database import get_connection


pdf_entradas_bp = Blueprint(
    "pdf_entradas",
    __name__
)


# ============================================================
# GET /api/pdf/entrada/<id>
# ============================================================

@pdf_entradas_bp.route(
    "/entrada/<int:id>",
    methods=["GET"]
)
@jwt_required()
def generar_pdf_entrada(id):

    claims = get_jwt()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # DATOS DE LA ENTRADA
            # =================================================

            cursor.execute("""
                SELECT
                    e.id,
                    e.numero_documento,
                    e.sede_id,
                    e.proveedor AS origen,
                    e.observaciones,
                    e.estado,
                    e.usuario_id,

                    s.nombre AS sede_nombre,
                    s.ciudad AS sede_ciudad,

                    u.nombre AS usuario_nombre

                FROM entradas e

                LEFT JOIN sedes s
                    ON s.id = e.sede_id

                LEFT JOIN usuarios u
                    ON u.id = e.usuario_id

                WHERE e.id = %s
            """, (
                id,
            ))

            entrada = cursor.fetchone()

            if not entrada:

                return jsonify({
                    "error": "Entrada no encontrada"
                }), 404

            # =================================================
            # RESTRICCIÓN POR SEDE
            # =================================================

            if (
                claims.get("rol") != "admin"
                and entrada.get("sede_id") != claims.get("sede_id")
            ):

                return jsonify({
                    "error": "No tienes permiso para ver esta entrada"
                }), 403


            # =================================================
            # DETALLE DE LA ENTRADA
            # =================================================

            cursor.execute("""
                SELECT
                    d.id,
                    d.producto_id,
                    d.cantidad,
                    d.observaciones,

                    p.codigo,
                    p.nombre AS producto_nombre,
                    p.requiere_serial,

                    un.codigo AS unidad_codigo,
                    un.nombre AS unidad_nombre

                FROM detalle_entradas d

                INNER JOIN productos p
                    ON p.id = d.producto_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                WHERE d.entrada_id = %s

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
            # Cada equipo queda guardado por separado:
            # serial + modelo + marca
            # =================================================

            for item in detalle:

                item["equipos"] = []

                if item.get("requiere_serial"):

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

                        WHERE
                            e.producto_id = %s
                            AND e.sede_id = %s

                        ORDER BY e.id DESC

                        LIMIT %s
                    """, (
                        item["producto_id"],
                        entrada["sede_id"],
                        item["cantidad"]
                    ))

                    equipos = cursor.fetchall()

                    for equipo in equipos:

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
            "ERROR GENERANDO PDF DE ENTRADA:",
            error
        )

        return jsonify({
            "error": (
                "No se pudo generar el PDF de la entrada.",
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
            "ENTRADA ALMACÉN",

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
            f'N° {entrada.get("numero_documento", "")}',

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
        entrada.get("estado")
        or "ACTIVA"
    )


    # ========================================================
    # ORIGEN
    #
    # La BD usa "proveedor" por compatibilidad,
    # pero la aplicación lo muestra como "origen".
    # ========================================================

    origen = (
        entrada.get("origen")
        or entrada.get("proveedor")
        or ""
    )


    # ========================================================
    # DESTINO
    # ========================================================

    destino = "Almacén"


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
                str(
                    origen
                ),
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
                    f'{entrada.get("sede_nombre", "")}'
                    f' - '
                    f'{entrada.get("sede_ciudad", "")}'
                ),
                estilo_valor
            ),

            Paragraph(
                "Documento:",
                estilo_label
            ),

            Paragraph(
                str(
                    entrada.get(
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
                    entrada.get(
                        "usuario_nombre"
                    )
                    or ""
                ),
                estilo_valor
            ),

            Paragraph(
                "Estado:",
                estilo_label
            ),

            Paragraph(
                estado,
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
                    entrada.get(
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
                    "Esta entrada se encuentra anulada.",
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
                    (0, 0),
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
        # PRODUCTO SERIALIZADO SIN EQUIPOS ENCONTRADOS
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
                    entrada.get(
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
            f"entrada_"
            f"{entrada.get('numero_documento', id)}"
            f".pdf"
        )
    )