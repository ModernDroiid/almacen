# ============================================================
# pdf_salidas.py — Genera el PDF de salida al estilo
# del formato de Occidente Seguridad Privada
# ============================================================

from flask import Blueprint, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import os, sys
from io import BytesIO

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

pdf_salidas_bp = Blueprint('pdf_salidas', __name__)

@pdf_salidas_bp.route('/salida/<int:id>', methods=['GET'])
def generar_pdf_salida(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM salidas WHERE id=?', (id,))
    salida = cursor.fetchone()
    if not salida:
        conn.close()
        return {'error': 'Salida no encontrada'}, 404
    salida = dict(salida)

    cursor.execute('''
        SELECT p.nombre, p.codigo,
               d.modelo, d.marca, d.serial, d.cantidad, d.unidad
        FROM detalle_salidas d
        INNER JOIN productos p ON p.id = d.producto_id
        WHERE d.salida_id = ?
    ''', (id,))
    detalle = [dict(r) for r in cursor.fetchall()]
    conn.close()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )

    elementos = []

    estilo_celda      = ParagraphStyle('celda', fontSize=8, leading=10)
    estilo_titulo     = ParagraphStyle('titulo', fontSize=14, fontName='Helvetica-Bold',
                                       textColor=colors.HexColor('#0d2137'))
    estilo_encabezado = ParagraphStyle('enc', fontSize=7, fontName='Helvetica-Bold',
                                        textColor=colors.white)
    estilo_label      = ParagraphStyle('label', fontSize=7, fontName='Helvetica-Bold',
                                       textColor=colors.HexColor('#0d2137'))
    estilo_valor      = ParagraphStyle('valor', fontSize=8)

    # ── Logo + Título ─────────────────────────────────────────
    logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'img', 'occidente.png')

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=4*cm, height=2.5*cm)
    else:
        logo = Paragraph('OCCIDENTE', estilo_titulo)

    bloque_titulo = [
        Paragraph('SALIDA ALMACEN', ParagraphStyle(
            'tit', fontSize=16, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0d2137'), alignment=TA_CENTER
        )),
        Spacer(1, 0.2*cm),
        Paragraph(f'N° {salida.get("numero_documento", "")}',
            ParagraphStyle('num', fontSize=9, alignment=TA_CENTER,
                           textColor=colors.HexColor('#1a6fc4'))
        ),
    ]

    tabla_header = Table(
        [[logo, bloque_titulo]],
        colWidths=[5*cm, 13*cm]
    )
    tabla_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  (1,0), (1,0),   'CENTER'),
    ]))
    elementos.append(tabla_header)
    elementos.append(Spacer(1, 0.4*cm))

    # ── Info de la salida ──────────────────────────────────────
    fecha_str = salida.get('fecha', '')[:10] if salida.get('fecha') else ''

    info_data = [
        [
            Paragraph('De la seccion:', estilo_label),
            Paragraph(salida.get('obra', 'Almacen'), estilo_valor),
            Paragraph('Fecha:', estilo_label),
            Paragraph(fecha_str, estilo_valor),
        ],
        [
            Paragraph('Con destino a:', estilo_label),
            Paragraph(salida.get('destino', ''), estilo_valor),
            Paragraph('Observaciones:', estilo_label),
            Paragraph(salida.get('observaciones', ''), estilo_valor),
        ],
    ]

    tabla_info = Table(info_data, colWidths=[3.5*cm, 7*cm, 3*cm, 4.5*cm])
    tabla_info.setStyle(TableStyle([
        ('GRID',      (0,0), (-1,-1), 0.5, colors.HexColor('#dce6f0')),
        ('BACKGROUND',(0,0), (0,-1),  colors.HexColor('#f7f9fc')),
        ('BACKGROUND',(2,0), (2,-1),  colors.HexColor('#f7f9fc')),
        ('VALIGN',    (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING',   (0,0), (-1,-1), 5),
    ]))
    elementos.append(tabla_info)
    elementos.append(Spacer(1, 0.4*cm))

    # ── Tabla de productos ──────────────────────────────────────
    encabezados = [
        Paragraph('Descripcion del articulo', estilo_encabezado),
        Paragraph('Modelo',    estilo_encabezado),
        Paragraph('N° Serial', estilo_encabezado),
        Paragraph('Marca',     estilo_encabezado),
        Paragraph('Cantidad',  estilo_encabezado),
        Paragraph('Unidad',    estilo_encabezado),
    ]

    filas = [encabezados]
    for item in detalle:
        filas.append([
            Paragraph(item.get('nombre', ''), estilo_celda),
            Paragraph(item.get('modelo', '') or '', estilo_celda),
            Paragraph(item.get('serial', '') or '', estilo_celda),
            Paragraph(item.get('marca',  '') or '', estilo_celda),
            Paragraph(str(item.get('cantidad', '')), estilo_celda),
            Paragraph(item.get('unidad', '') or '', estilo_celda),
        ])

    for _ in range(max(0, 10 - len(detalle))):
        filas.append(['', '', '', '', '', ''])

    tabla_productos = Table(
        filas,
        colWidths=[5.5*cm, 3*cm, 3*cm, 2.5*cm, 2*cm, 2*cm]
    )
    tabla_productos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0),  colors.HexColor('#0d2137')),
        ('TEXTCOLOR',  (0,0), (-1,0),  colors.white),
        ('FONTNAME',   (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0),  8),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#dce6f0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f7f9fc')]),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('FONTSIZE',   (0,1), (-1,-1), 8),
    ]))
    elementos.append(tabla_productos)
    elementos.append(Spacer(1, 1*cm))

    # ── Firmas ────────────────────────────────────────────────
    firmas = Table(
        [[
            Paragraph('Entregado por:', estilo_label),
            Paragraph('', estilo_valor),
            Paragraph('Recibido por:', estilo_label),
            Paragraph('', estilo_valor),
        ]],
        colWidths=[3*cm, 6.5*cm, 3*cm, 5.5*cm]
    )
    firmas.setStyle(TableStyle([
        ('GRID',      (0,0), (-1,-1), 0.5, colors.HexColor('#dce6f0')),
        ('BACKGROUND',(0,0), (0,0),   colors.HexColor('#f7f9fc')),
        ('BACKGROUND',(2,0), (2,0),   colors.HexColor('#f7f9fc')),
        ('PADDING',   (0,0), (-1,-1), 8),
    ]))
    elementos.append(firmas)

    doc.build(elementos)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f'salida_{salida.get("numero_documento", id)}.pdf'
    )