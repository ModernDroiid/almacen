# ============================================================
# pdf_traslados.py
# PDF de traslado entre sedes
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


pdf_traslados_bp = Blueprint(
    "pdf_traslados",
    __name__
)


# ============================================================
# FORMATEAR FECHA EN ESPAÑOL
# ============================================================

def formatear_fecha_es(fecha):

    if not fecha:
        return ""

    meses = {
        1: "ene",
        2: "feb",
        3: "mar",
        4: "abr",
        5: "may",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "sep",
        10: "oct",
        11: "nov",
        12: "dic"
    }

    dias = {
        0: "lun",
        1: "mar",
        2: "mié",
        3: "jue",
        4: "vie",
        5: "sáb",
        6: "dom"
    }

    return (
        f"{dias[fecha.weekday()]}, "
        f"{fecha.day:02d} "
        f"{meses[fecha.month]} "
        f"{fecha.year} "
        f"{fecha.hour:02d}:"
        f"{fecha.minute:02d}:"
        f"{fecha.second:02d}"
    )


# ============================================================
# GET /api/pdf/traslados/<id>
#
# Antes esta ruta validaba manualmente un ?token=... en la
# URL. Ahora usa el mismo mecanismo de sesión que el resto de
# la API (encabezado Authorization), igual que las demás rutas
# de PDF, y además restringe por sede como corresponde.
# ============================================================

@pdf_traslados_bp.route(
    "/traslados/<int:id>",
    methods=["GET"]
)
@jwt_required()
def generar_pdf_traslado(id):

    claims = get_jwt()

    # ========================================================
    # CONEXIÓN BD
    # ========================================================

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # INFORMACIÓN DEL TRASLADO
            # =================================================

            cursor.execute("""
                SELECT

                    t.id,
                    t.numero_documento,

                    t.sede_origen_id,
                    t.sede_destino_id,

                    t.usuario_creador_id,
                    t.usuario_recibido_id,

                    t.estado,

                    t.observaciones,

                    t.fecha_creacion,
                    t.fecha_recepcion,

                    t.anulado_por,
                    t.fecha_anulacion,
                    t.motivo_anulacion,

                    t.firma_entrega_base64,
                    t.firma_recibe_base64,

                    so.nombre
                        AS sede_origen_nombre,

                    so.ciudad
                        AS sede_origen_ciudad,

                    sd.nombre
                        AS sede_destino_nombre,

                    sd.ciudad
                        AS sede_destino_ciudad,

                    uc.nombre
                        AS creado_por_nombre,

                    ur.nombre
                        AS recibido_por_nombre,

                    ua.nombre
                        AS anulado_por_nombre

                FROM traslados t

                LEFT JOIN sedes so
                    ON so.id = t.sede_origen_id

                LEFT JOIN sedes sd
                    ON sd.id = t.sede_destino_id

                LEFT JOIN usuarios uc
                    ON uc.id = t.usuario_creador_id

                LEFT JOIN usuarios ur
                    ON ur.id = t.usuario_recibido_id

                LEFT JOIN usuarios ua
                    ON ua.id = t.anulado_por

                WHERE t.id = %s
            """, (
                id,
            ))

            traslado = cursor.fetchone()

            if not traslado:

                return jsonify({
                    "error": "Traslado no encontrado"
                }), 404

            # =================================================
            # RESTRICCIÓN POR SEDE
            #
            # El admin ve cualquier traslado. Cualquier otro rol
            # solo puede ver traslados donde su propia sede sea
            # el origen o el destino.
            # =================================================

            if claims.get("rol") != "admin":

                sede_usuario = claims.get("sede_id")

                if sede_usuario not in (
                    traslado.get("sede_origen_id"),
                    traslado.get("sede_destino_id")
                ):

                    return jsonify({
                        "error": "No tienes permiso para ver este traslado"
                    }), 403

            # =================================================
            # DETALLE
            # =================================================

            cursor.execute("""
                SELECT

                    dt.id,

                    dt.producto_id,
                    dt.equipo_id,

                    dt.cantidad,

                    dt.observaciones
                        AS detalle_observaciones,

                    p.codigo,

                    p.nombre
                        AS producto_nombre,

                    p.requiere_serial,

                    un.codigo
                        AS unidad_codigo,

                    un.nombre
                        AS unidad_nombre,

                    eq.serial
                        AS serial,

                    mo.nombre
                        AS modelo_nombre,

                    ma.nombre
                        AS marca_nombre

                FROM detalle_traslados dt

                INNER JOIN productos p
                    ON p.id = dt.producto_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                LEFT JOIN equipos eq
                    ON eq.id = dt.equipo_id

                LEFT JOIN modelos mo
                    ON mo.id = COALESCE(
                        eq.modelo_id,
                        p.modelo_id
                    )

                LEFT JOIN marcas ma
                    ON ma.id = mo.marca_id

                WHERE dt.traslado_id = %s

                ORDER BY dt.id
            """, (
                id,
            ))

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
    # CREAR PDF
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
        "encabezado",
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
        fontSize=8
    )

    # ========================================================
    # LOGO
    # ========================================================

    logo_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "frontend",
        "img",
        "occidente.png"
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
            "TRASLADO ENTRE SEDES",

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
            f'N° {traslado.get("numero_documento", "")}',

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
    # FECHAS
    # ========================================================

    fecha_creacion = formatear_fecha_es(
        traslado.get("fecha_creacion")
    )

    fecha_recepcion = formatear_fecha_es(
        traslado.get("fecha_recepcion")
    )

    # ========================================================
    # ESTADO
    # ========================================================

    estado = (
        traslado.get(
            "estado"
        )
        or "PENDIENTE"
    )

    # ========================================================
    # INFORMACIÓN DEL TRASLADO
    # ========================================================

    info_data = [

        [
            Paragraph(
                "Sede origen:",
                estilo_label
            ),

            Paragraph(
                (
                    f'{traslado.get("sede_origen_nombre", "")} '
                    f'— '
                    f'{traslado.get("sede_origen_ciudad", "")}'
                ),
                estilo_valor
            ),

            Paragraph(
                "Sede destino:",
                estilo_label
            ),

            Paragraph(
                (
                    f'{traslado.get("sede_destino_nombre", "")} '
                    f'— '
                    f'{traslado.get("sede_destino_ciudad", "")}'
                ),
                estilo_valor
            )
        ],

        [
            Paragraph(
                "Estado:",
                estilo_label
            ),

            Paragraph(
                estado,
                estilo_valor
            ),

            Paragraph(
                "Documento:",
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    "numero_documento"
                ) or "",
                estilo_valor
            )
        ],

        [
            Paragraph(
                "Inicio traslado:",
                estilo_label
            ),

            Paragraph(
                fecha_creacion,
                estilo_valor
            ),

            Paragraph(
                "Finalización:",
                estilo_label
            ),

            Paragraph(
                fecha_recepcion
                if fecha_recepcion
                else "Pendiente",
                estilo_valor
            )
        ],

        [
            Paragraph(
                "Creado por:",
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    "creado_por_nombre"
                ) or "—",
                estilo_valor
            ),

            Paragraph(
                "Recibido por:",
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    "recibido_por_nombre"
                ) or "Pendiente",
                estilo_valor
            )
        ]
    ]

    tabla_info = Table(
        info_data,

        colWidths=[
            3.5 * cm,
            6.0 * cm,
            3.5 * cm,
            4.0 * cm
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
    # ANULACIÓN
    # ========================================================

    if estado == "ANULADA":

        anulacion_data = [

            [
                Paragraph(
                    "ANULADO",

                    ParagraphStyle(
                        "anulado",
                        fontSize=10,
                        fontName="Helvetica-Bold",
                        textColor=colors.red
                    )
                ),

                Paragraph(
                    traslado.get(
                        "motivo_anulacion"
                    )
                    or
                    "Sin motivo registrado",

                    estilo_valor
                )
            ],

            [
                Paragraph(
                    "Anulado por:",
                    estilo_label
                ),

                Paragraph(
                    traslado.get(
                        "anulado_por_nombre"
                    )
                    or "",
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
                    colors.HexColor(
                        "#dce6f0"
                    )
                ),

                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 1),
                    colors.HexColor(
                        "#f7f9fc"
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
    # OBSERVACIONES
    # ========================================================

    observaciones = (
        traslado.get(
            "observaciones"
        )
        or "Sin observaciones"
    )

    tabla_observaciones = Table(
        [[

            Paragraph(
                "Observaciones:",
                estilo_label
            ),

            Paragraph(
                observaciones,
                estilo_valor
            )
        ]],

        colWidths=[
            3.5 * cm,
            13.5 * cm
        ]
    )

    tabla_observaciones.setStyle(
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
                (0, 0),
                colors.HexColor(
                    "#f7f9fc"
                )
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
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
        tabla_observaciones
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
            "Marca",
            estilo_encabezado
        ),

        Paragraph(
            "N° Serial",
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

    for item in detalle:

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
                ) or "",
                estilo_celda
            ),

            Paragraph(
                item.get(
                    "marca_nombre"
                ) or "",
                estilo_celda
            ),

            Paragraph(
                item.get(
                    "serial"
                ) or "",
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

    tabla_productos = Table(
        filas,

        colWidths=[
            5.0 * cm,
            3.0 * cm,
            2.5 * cm,
            3.0 * cm,
            2.0 * cm,
            2.0 * cm
        ]
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
    # Firma digital de quien despacha en la sede origen (al
    # crear el traslado) y de quien recibe en la sede destino
    # (al confirmar la recepción). Mientras el traslado esté
    # PENDIENTE todavía no habrá firma de quien recibe — se deja
    # el espacio en blanco en vez de fallar.
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
            traslado.get("firma_entrega_base64"),
            ancho_firma,
            alto_firma
        )
        or Paragraph("(sin firma)", estilo_sin_firma)
    )

    firma_recibe_img = (
        imagen_firma(
            traslado.get("firma_recibe_base64"),
            ancho_firma,
            alto_firma
        )
        or Paragraph(
            (
                "(pendiente de recibir)"
                if traslado.get("estado") == "PENDIENTE"
                else "(sin firma)"
            ),
            estilo_sin_firma
        )
    )

    firmas = Table(

        [
            [
                Paragraph(
                    "Despachado por (origen):",
                    estilo_label
                ),

                Paragraph(
                    "Recibido por (destino):",
                    estilo_label
                )
            ],

            [
                firma_entrega_img,
                firma_recibe_img
            ],

            [
                Paragraph(
                    traslado.get(
                        "creado_por_nombre"
                    ) or "",
                    estilo_valor
                ),

                Paragraph(
                    traslado.get(
                        "recibido_por_nombre"
                    ) or "",
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
            f'traslado_'
            f'{traslado.get("numero_documento", id)}'
            f'.pdf'
        )
    )