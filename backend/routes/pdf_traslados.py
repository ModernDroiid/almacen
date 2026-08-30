# ============================================================
# pdf_traslados.py — PDF de traslado entre sedes
# ============================================================

from flask import Blueprint, request, send_file
from flask_jwt_extended import decode_token
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
import sys
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection


pdf_traslados_bp = Blueprint('pdf_traslados', __name__)


# ============================================================
# GET /api/pdf/traslados/<id>
# Generar PDF de traslado
#
# El token se recibe mediante:
# ?token=...
# ============================================================

@pdf_traslados_bp.route('/traslados/<int:id>', methods=['GET'])
def generar_pdf_traslado(id):

    # ========================================================
    # VALIDAR TOKEN
    # ========================================================

    token = request.args.get('token')

    if not token:
        return {
            'error': 'Token requerido'
        }, 401

    try:
        decode_token(token)
    except Exception:
        return {
            'error': 'Token inválido o expirado'
        }, 401

    # ========================================================
    # CONEXIÓN BD
    # ========================================================

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ====================================================
        # INFORMACIÓN DEL TRASLADO
        # ====================================================

        cursor.execute('''
            SELECT
                t.id,
                t.numero_documento,
                t.observaciones,
                t.estado,
                t.fecha_creacion,
                t.fecha_recepcion,

                so.nombre AS sede_origen_nombre,
                so.ciudad AS sede_origen_ciudad,

                sd.nombre AS sede_destino_nombre,
                sd.ciudad AS sede_destino_ciudad,

                uc.nombre AS creado_por_nombre,
                ur.nombre AS recibido_por_nombre

            FROM traslados t

            LEFT JOIN sedes so
                ON so.id = t.sede_origen_id

            LEFT JOIN sedes sd
                ON sd.id = t.sede_destino_id

            LEFT JOIN usuarios uc
                ON uc.id = t.creado_por

            LEFT JOIN usuarios ur
                ON ur.id = t.recibido_por

            WHERE t.id = ?
        ''', (id,))

        traslado = cursor.fetchone()

        if not traslado:
            return {
                'error': 'Traslado no encontrado'
            }, 404

        traslado = dict(traslado)

        # ====================================================
        # DETALLE DE PRODUCTOS
        # ====================================================

        cursor.execute('''
            SELECT
                p.nombre,
                p.codigo,
                dt.modelo,
                dt.marca,
                dt.serial,
                dt.cantidad,
                dt.unidad

            FROM detalle_traslados dt

            INNER JOIN productos p
                ON p.id = dt.producto_origen_id

            WHERE dt.traslado_id = ?

            ORDER BY dt.id
        ''', (id,))

        detalle = [
            dict(x)
            for x in cursor.fetchall()
        ]

    except Exception as e:

        return {
            'error': str(e)
        }, 500

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
        'celda',
        fontSize=8,
        leading=10
    )

    estilo_titulo = ParagraphStyle(
        'titulo',
        fontSize=14,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0d2137')
    )

    estilo_encabezado = ParagraphStyle(
        'encabezado',
        fontSize=7,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=TA_CENTER
    )

    estilo_label = ParagraphStyle(
        'label',
        fontSize=7,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0d2137')
    )

    estilo_valor = ParagraphStyle(
        'valor',
        fontSize=8
    )

    # ========================================================
    # LOGO + TITULO
    # ========================================================

    logo_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        '..',
        'frontend',
        'img',
        'occidente.png'
    )

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=4 * cm,
            height=2.5 * cm
        )

    else:

        logo = Paragraph(
            'OCCIDENTE',
            estilo_titulo
        )

    bloque_titulo = [

        Paragraph(
            'TRASLADO ENTRE SEDES',
            ParagraphStyle(
                'tit',
                fontSize=16,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor('#0d2137'),
                alignment=TA_CENTER
            )
        ),

        Spacer(1, 0.2 * cm),

        Paragraph(
            f'N° {traslado.get("numero_documento", "")}',
            ParagraphStyle(
                'num',
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#1a6fc4')
            )
        )
    ]

    tabla_header = Table(
        [[logo, bloque_titulo]],
        colWidths=[
            5 * cm,
            13 * cm
        ]
    )

    tabla_header.setStyle(TableStyle([
        (
            'VALIGN',
            (0, 0),
            (-1, -1),
            'MIDDLE'
        ),
        (
            'ALIGN',
            (1, 0),
            (1, 0),
            'CENTER'
        ),
    ]))

    elementos.append(tabla_header)
    elementos.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # INFORMACIÓN DEL TRASLADO
    # ========================================================

    fecha_creacion = traslado.get(
        'fecha_creacion'
    ) or ''

    fecha_recepcion = traslado.get(
        'fecha_recepcion'
    ) or ''

    info_data = [

        [
            Paragraph(
                'Sede origen:',
                estilo_label
            ),

            Paragraph(
                f'{traslado.get("sede_origen_nombre", "")} '
                f'— {traslado.get("sede_origen_ciudad", "")}',
                estilo_valor
            ),

            Paragraph(
                'Sede destino:',
                estilo_label
            ),

            Paragraph(
                f'{traslado.get("sede_destino_nombre", "")} '
                f'— {traslado.get("sede_destino_ciudad", "")}',
                estilo_valor
            ),
        ],

        [
            Paragraph(
                'Estado:',
                estilo_label
            ),

            Paragraph(
                traslado.get('estado', ''),
                estilo_valor
            ),

            Paragraph(
                'Documento:',
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    'numero_documento',
                    ''
                ),
                estilo_valor
            ),
        ],

        [
            Paragraph(
                'Inicio traslado:',
                estilo_label
            ),

            Paragraph(
                fecha_creacion,
                estilo_valor
            ),

            Paragraph(
                'Finalización:',
                estilo_label
            ),

            Paragraph(
                fecha_recepcion
                if fecha_recepcion
                else 'Pendiente',
                estilo_valor
            ),
        ],

        [
            Paragraph(
                'Creado por:',
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    'creado_por_nombre'
                ) or '—',
                estilo_valor
            ),

            Paragraph(
                'Recibido por:',
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    'recibido_por_nombre'
                ) or 'Pendiente',
                estilo_valor
            ),
        ],

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

    tabla_info.setStyle(TableStyle([

        (
            'GRID',
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor('#dce6f0')
        ),

        (
            'BACKGROUND',
            (0, 0),
            (0, -1),
            colors.HexColor('#f7f9fc')
        ),

        (
            'BACKGROUND',
            (2, 0),
            (2, -1),
            colors.HexColor('#f7f9fc')
        ),

        (
            'VALIGN',
            (0, 0),
            (-1, -1),
            'MIDDLE'
        ),

        (
            'PADDING',
            (0, 0),
            (-1, -1),
            5
        ),

    ]))

    elementos.append(tabla_info)
    elementos.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # OBSERVACIONES
    # ========================================================

    observaciones = (
        traslado.get('observaciones')
        or 'Sin observaciones'
    )

    tabla_observaciones = Table(
        [[

            Paragraph(
                'Observaciones:',
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

    tabla_observaciones.setStyle(TableStyle([

        (
            'GRID',
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor('#dce6f0')
        ),

        (
            'BACKGROUND',
            (0, 0),
            (0, 0),
            colors.HexColor('#f7f9fc')
        ),

        (
            'VALIGN',
            (0, 0),
            (-1, -1),
            'TOP'
        ),

        (
            'PADDING',
            (0, 0),
            (-1, -1),
            5
        ),

    ]))

    elementos.append(
        tabla_observaciones
    )

    elementos.append(
        Spacer(1, 0.4 * cm)
    )

    # ========================================================
    # TABLA DE PRODUCTOS
    # ========================================================

    encabezados = [

        Paragraph(
            'Descripción del artículo',
            estilo_encabezado
        ),

        Paragraph(
            'Modelo',
            estilo_encabezado
        ),

        Paragraph(
            'Marca',
            estilo_encabezado
        ),

        Paragraph(
            'N° Serial',
            estilo_encabezado
        ),

        Paragraph(
            'Cantidad',
            estilo_encabezado
        ),

        Paragraph(
            'Unidad',
            estilo_encabezado
        ),

    ]

    filas = [encabezados]

    for item in detalle:

        filas.append([

            Paragraph(
                item.get('nombre', ''),
                estilo_celda
            ),

            Paragraph(
                item.get('modelo') or '',
                estilo_celda
            ),

            Paragraph(
                item.get('marca') or '',
                estilo_celda
            ),

            Paragraph(
                item.get('serial') or '',
                estilo_celda
            ),

            Paragraph(
                str(item.get('cantidad', '')),
                estilo_celda
            ),

            Paragraph(
                item.get('unidad') or 'UND',
                estilo_celda
            ),

        ])

    # Mantener espacio visual aunque haya pocos productos

    for _ in range(
        max(0, 10 - len(detalle))
    ):

        filas.append([
            '',
            '',
            '',
            '',
            '',
            ''
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
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor('#0d2137')
            ),

            (
                'TEXTCOLOR',
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                'FONTNAME',
                (0, 0),
                (-1, 0),
                'Helvetica-Bold'
            ),

            (
                'FONTSIZE',
                (0, 0),
                (-1, 0),
                8
            ),

            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor('#dce6f0')
            ),

            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor('#f7f9fc')
                ]
            ),

            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),

            (
                'PADDING',
                (0, 0),
                (-1, -1),
                5
            ),

            (
                'FONTSIZE',
                (0, 1),
                (-1, -1),
                8
            ),

        ])
    )

    elementos.append(
        tabla_productos
    )

    elementos.append(
        Spacer(1, 1 * cm)
    )

    # ========================================================
    # FIRMAS
    # ========================================================

    firmas = Table(
        [[

            Paragraph(
                'Entregado por:',
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    'creado_por_nombre'
                ) or '',
                estilo_valor
            ),

            Paragraph(
                'Recibido por:',
                estilo_label
            ),

            Paragraph(
                traslado.get(
                    'recibido_por_nombre'
                ) or '',
                estilo_valor
            ),

        ]],
        colWidths=[
            3 * cm,
            6.5 * cm,
            3 * cm,
            5.5 * cm
        ]
    )

    firmas.setStyle(TableStyle([

        (
            'GRID',
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor('#dce6f0')
        ),

        (
            'BACKGROUND',
            (0, 0),
            (0, 0),
            colors.HexColor('#f7f9fc')
        ),

        (
            'BACKGROUND',
            (2, 0),
            (2, 0),
            colors.HexColor('#f7f9fc')
        ),

        (
            'PADDING',
            (0, 0),
            (-1, -1),
            8
        ),

    ]))

    elementos.append(firmas)

    # ========================================================
    # GENERAR PDF
    # ========================================================

    doc.build(elementos)

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=(
            f'traslado_'
            f'{traslado.get("numero_documento", id)}.pdf'
        )
    )