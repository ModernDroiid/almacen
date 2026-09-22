# ============================================================
# pdf_solicitudes.py
# Genera PDF de una solicitud de compra de equipo
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
from utils.firmas import imagen_firma


pdf_solicitudes_bp = Blueprint(
    "pdf_solicitudes",
    __name__
)


# ============================================================
# GET /api/pdf/solicitud/<id>
# ============================================================

@pdf_solicitudes_bp.route(
    "/solicitud/<int:id>",
    methods=["GET"]
)
@jwt_required()
def generar_pdf_solicitud(id):

    claims = get_jwt()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # DATOS DE LA SOLICITUD
            # =================================================

            cursor.execute("""
                SELECT
                    sol.*,
                    s.nombre AS sede_nombre,
                    s.ciudad AS sede_ciudad,
                    u_sol.nombre AS solicitado_por_nombre,
                    u_apr.nombre AS aprobado_por_nombre
                FROM solicitudes sol
                LEFT JOIN sedes s
                    ON s.id = sol.sede_id
                LEFT JOIN usuarios u_sol
                    ON u_sol.id = sol.solicitado_por
                LEFT JOIN usuarios u_apr
                    ON u_apr.id = sol.aprobado_por
                WHERE sol.id = %s
            """, (id,))

            solicitud = cursor.fetchone()

            if not solicitud:
                return jsonify({
                    "error": "Solicitud no encontrada"
                }), 404

            # =================================================
            # RESTRICCIÓN POR SEDE
            # =================================================

            if (
                claims.get("rol") not in ("admin", "consulta")
                and solicitud.get("sede_id") != claims.get("sede_id")
            ):

                return jsonify({
                    "error": "No tienes permiso para ver esta solicitud"
                }), 403

            # =================================================
            # DETALLE DE PRODUCTOS
            # =================================================

            cursor.execute("""
                SELECT
                    d.cantidad_solicitada,
                    d.observaciones,
                    p.codigo,
                    p.nombre AS producto_nombre,
                    u.codigo AS unidad_codigo
                FROM detalle_solicitudes d
                LEFT JOIN productos p
                    ON p.id = d.producto_id
                LEFT JOIN unidades u
                    ON u.id = p.unidad_id
                WHERE d.solicitud_id = %s
                ORDER BY d.id
            """, (id,))

            detalle = [
                dict(fila)
                for fila in cursor.fetchall()
            ]

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

    estilo_sin_firma = ParagraphStyle(
        "sinFirma",
        fontSize=7,
        textColor=colors.HexColor("#9aabbd"),
        alignment=TA_CENTER
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
            "SOLICITUD DE COMPRA DE EQUIPO",

            ParagraphStyle(
                "tit",
                fontSize=15,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor("#0d2137"),
                alignment=TA_CENTER
            )
        ),

        Spacer(1, 0.2 * cm),

        Paragraph(
            f'N° {solicitud.get("numero_solicitud", "")}',

            ParagraphStyle(
                "num",
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1a6fc4")
            )
        )
    ]

    tabla_header = Table(
        [[logo, bloque_titulo]],
        colWidths=[5 * cm, 13 * cm]
    )

    tabla_header.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "CENTER")
        ])
    )

    elementos.append(tabla_header)
    elementos.append(Spacer(1, 0.4 * cm))

    # ========================================================
    # ESTADO
    # ========================================================

    estado = solicitud.get("estado") or "PENDIENTE"

    colores_estado = {
        "PENDIENTE": colors.HexColor("#b8860b"),
        "APROBADA": colors.HexColor("#1e7b45"),
        "RECHAZADA": colors.HexColor("#b23a3a")
    }

    # ========================================================
    # INFORMACIÓN
    # ========================================================

    info_data = [

        [
            Paragraph("Sede:", estilo_label),
            Paragraph(
                f'{solicitud.get("sede_nombre", "")} - '
                f'{solicitud.get("sede_ciudad", "")}',
                estilo_valor
            ),
            Paragraph("Estado:", estilo_label),
            Paragraph(
                estado,
                ParagraphStyle(
                    "estadoVal",
                    fontSize=8,
                    fontName="Helvetica-Bold",
                    textColor=colores_estado.get(estado, colors.black)
                )
            )
        ],

        [
            Paragraph("Constructora:", estilo_label),
            Paragraph(
                str(solicitud.get("constructora") or "—"),
                estilo_valor
            ),
            Paragraph("Proyecto:", estilo_label),
            Paragraph(
                str(solicitud.get("proyecto") or "—"),
                estilo_valor
            )
        ],

        [
            Paragraph("N° Orden de servicio:", estilo_label),
            Paragraph(
                str(solicitud.get("no_orden_servicio") or "—"),
                estilo_valor
            ),
            Paragraph("Fecha:", estilo_label),
            Paragraph(
                str(solicitud.get("fecha") or ""),
                estilo_valor
            )
        ],

        [
            Paragraph("Solicitado por:", estilo_label),
            Paragraph(
                str(solicitud.get("solicitado_por_nombre") or ""),
                estilo_valor
            ),
            Paragraph("Observaciones:", estilo_label),
            Paragraph(
                str(solicitud.get("observaciones") or "—"),
                estilo_valor
            )
        ]
    ]

    tabla_info = Table(
        info_data,
        colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 5 * cm]
    )

    tabla_info.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce6f0")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7f9fc")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f7f9fc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 5)
        ])
    )

    elementos.append(tabla_info)
    elementos.append(Spacer(1, 0.4 * cm))

    # ========================================================
    # AVISO DE RECHAZO
    # ========================================================

    if estado == "RECHAZADA":

        rechazo_data = [
            [
                Paragraph(
                    "RECHAZADA",
                    ParagraphStyle(
                        "rechazada",
                        fontSize=10,
                        fontName="Helvetica-Bold",
                        textColor=colors.red
                    )
                ),
                Paragraph(
                    str(solicitud.get("motivo_rechazo") or ""),
                    estilo_valor
                )
            ]
        ]

        tabla_rechazo = Table(
            rechazo_data,
            colWidths=[3.5 * cm, 14.5 * cm]
        )

        tabla_rechazo.setStyle(
            TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f0d0d0")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf3f3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 6)
            ])
        )

        elementos.append(tabla_rechazo)
        elementos.append(Spacer(1, 0.4 * cm))

    # ========================================================
    # ITEMS SOLICITADOS
    # ========================================================

    encabezados = [
        Paragraph("Código", estilo_encabezado),
        Paragraph("Producto", estilo_encabezado),
        Paragraph("Cantidad", estilo_encabezado),
        Paragraph("Unidad", estilo_encabezado),
        Paragraph("Observaciones", estilo_encabezado)
    ]

    filas = [encabezados]

    for item in detalle:

        filas.append([
            Paragraph(str(item.get("codigo") or ""), estilo_celda),
            Paragraph(str(item.get("producto_nombre") or ""), estilo_celda),
            Paragraph(str(item.get("cantidad_solicitada") or ""), estilo_celda),
            Paragraph(str(item.get("unidad_codigo") or "UND"), estilo_celda),
            Paragraph(str(item.get("observaciones") or ""), estilo_celda)
        ])

    # Filas vacías para que la tabla no se vea tan corta
    for _ in range(max(0, 8 - len(filas) + 1)):
        filas.append(["", "", "", "", ""])

    tabla_items = Table(
        filas,
        colWidths=[2.5 * cm, 6.5 * cm, 2.5 * cm, 2 * cm, 4.5 * cm]
    )

    tabla_items.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d2137")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce6f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 5)
        ])
    )

    elementos.append(tabla_items)
    elementos.append(Spacer(1, 1 * cm))

    # ========================================================
    # FIRMAS
    #
    # Firma de quien solicita (siempre presente) y de quien
    # aprueba (solo si ya fue aprobada). Si la solicitud sigue
    # pendiente, se deja constancia de eso en vez de un espacio
    # en blanco que confunda.
    # ========================================================

    ancho_firma = 6 * cm
    alto_firma = 2 * cm

    firma_solicitante_img = (
        imagen_firma(
            solicitud.get("firma_solicitante_base64"),
            ancho_firma,
            alto_firma
        )
        or Paragraph("(sin firma)", estilo_sin_firma)
    )

    if estado == "PENDIENTE":
        firma_aprobador_img = Paragraph(
            "(pendiente de aprobación)",
            estilo_sin_firma
        )
    else:
        firma_aprobador_img = (
            imagen_firma(
                solicitud.get("firma_aprobador_base64"),
                ancho_firma,
                alto_firma
            )
            or Paragraph("(sin firma)", estilo_sin_firma)
        )

    firmas = Table(

        [
            [
                Paragraph("Solicitado por:", estilo_label),
                Paragraph("Aprobado por:", estilo_label)
            ],
            [
                firma_solicitante_img,
                firma_aprobador_img
            ],
            [
                Paragraph(
                    str(solicitud.get("solicitado_por_nombre") or ""),
                    estilo_valor
                ),
                Paragraph(
                    str(solicitud.get("aprobado_por_nombre") or ""),
                    estilo_valor
                )
            ]
        ],

        colWidths=[9 * cm, 9 * cm],
        rowHeights=[0.7 * cm, alto_firma + 0.3 * cm, 0.7 * cm]
    )

    firmas.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dce6f0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f7f9fc")),
            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ])
    )

    elementos.append(firmas)

    # ========================================================
    # GENERAR PDF
    # ========================================================

    try:
        doc.build(elementos)

    except Exception as error:

        print("ERROR CREANDO DOCUMENTO PDF:", error)

        return jsonify({
            "error": "No se pudo construir el documento PDF."
        }), 500

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f'solicitud_{solicitud.get("numero_solicitud", id)}.pdf'
    )