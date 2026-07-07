# ============================================================
# pdf_consolidado.py — PDF del consolidado por punto
# Muestra salidas y devoluciones de un destino específico
# ============================================================

from flask import Blueprint, request, send_file
from flask_jwt_extended import jwt_required, get_jwt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import os, sys
from io import BytesIO
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

pdf_consolidado_bp = Blueprint('pdf_consolidado', __name__)


@pdf_consolidado_bp.route('/consolidado', methods=['GET'])
@jwt_required()
def generar_pdf_consolidado():
    claims  = get_jwt()
    destino = request.args.get('destino', '').strip()
    sede_id = request.args.get('sede_id', type=int)

    if claims.get('rol') != 'admin':
        sede_id = claims.get('sede_id')

    if not destino:
        return {'error': 'Destino requerido'}, 400

    conn = get_connection()
    cursor = conn.cursor()

    # Salidas hacia ese punto
    if sede_id:
        cursor.execute('''
            SELECT s.id, s.numero_documento, s.fecha, s.observaciones,
                   se.nombre as sede_nombre
            FROM salidas s
            LEFT JOIN sedes se ON se.id = s.sede_id
            WHERE s.destino = ? AND s.sede_id = ?
            ORDER BY s.fecha DESC
        ''', (destino, sede_id))
    else:
        cursor.execute('''
            SELECT s.id, s.numero_documento, s.fecha, s.observaciones,
                   se.nombre as sede_nombre
            FROM salidas s
            LEFT JOIN sedes se ON se.id = s.sede_id
            WHERE s.destino = ?
            ORDER BY s.fecha DESC
        ''', (destino,))

    salidas = [dict(s) for s in cursor.fetchall()]
    for salida in salidas:
        cursor.execute('''
            SELECT p.nombre, p.codigo, d.cantidad, d.unidad,
                   d.modelo, d.marca, d.serial
            FROM detalle_salidas d
            INNER JOIN productos p ON p.id = d.producto_id
            WHERE d.salida_id = ?
        ''', (salida['id'],))
        salida['detalle'] = [dict(d) for d in cursor.fetchall()]

    # Devoluciones desde ese punto
    if sede_id:
        cursor.execute('''
            SELECT dv.id, dv.numero_documento, dv.fecha, dv.motivo,
                   dv.observaciones, s.numero_documento as salida_numero,
                   se.nombre as sede_nombre
            FROM devoluciones dv
            LEFT JOIN salidas s ON s.id = dv.salida_id
            LEFT JOIN sedes se ON se.id = dv.sede_id
            WHERE dv.origen = ? AND dv.sede_id = ?
            ORDER BY dv.fecha DESC
        ''', (destino, sede_id))
    else:
        cursor.execute('''
            SELECT dv.id, dv.numero_documento, dv.fecha, dv.motivo,
                   dv.observaciones, s.numero_documento as salida_numero,
                   se.nombre as sede_nombre
            FROM devoluciones dv
            LEFT JOIN salidas s ON s.id = dv.salida_id
            LEFT JOIN sedes se ON se.id = dv.sede_id
            WHERE dv.origen = ?
            ORDER BY dv.fecha DESC
        ''', (destino,))

    devoluciones = [dict(d) for d in cursor.fetchall()]
    for dev in devoluciones:
        cursor.execute('''
            SELECT p.nombre, p.codigo, d.cantidad, d.unidad,
                   d.modelo, d.marca, d.serial
            FROM detalle_devoluciones d
            INNER JOIN productos p ON p.id = d.producto_id
            WHERE d.devolucion_id = ?
        ''', (dev['id'],))
        dev['detalle'] = [dict(d) for d in cursor.fetchall()]

    conn.close()

    # ── Construir PDF ─────────────────────────────────────────
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
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
    estilo_seccion    = ParagraphStyle('sec', fontSize=11, fontName='Helvetica-Bold',
                                       textColor=colors.HexColor('#0d2137'))
    estilo_sub        = ParagraphStyle('sub', fontSize=9, fontName='Helvetica-Bold',
                                       textColor=colors.HexColor('#1a6fc4'))

    # ── Logo + Título ─────────────────────────────────────────
    logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'img', 'occidente.png')
    logo = Image(logo_path, width=4*cm, height=2.5*cm) if os.path.exists(logo_path) \
           else Paragraph('OCCIDENTE', estilo_titulo)

    bloque_titulo = [
        Paragraph('CONSOLIDADO POR PUNTO', ParagraphStyle(
            'tit', fontSize=16, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0d2137'), alignment=TA_CENTER
        )),
        Spacer(1, 0.2*cm),
        Paragraph(destino, ParagraphStyle(
            'dest', fontSize=11, alignment=TA_CENTER,
            textColor=colors.HexColor('#1a6fc4'), fontName='Helvetica-Bold'
        )),
    ]

    tabla_header = Table([[logo, bloque_titulo]], colWidths=[5*cm, 13*cm])
    tabla_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',  (1,0), (1,0),   'CENTER'),
    ]))
    elementos.append(tabla_header)
    elementos.append(Spacer(1, 0.3*cm))

    # Fecha de generación
    fecha_gen = datetime.now().strftime('%d/%m/%Y %H:%M')
    elementos.append(Paragraph(
        f'Generado el {fecha_gen}',
        ParagraphStyle('gen', fontSize=7, textColor=colors.HexColor('#6b8aab'), alignment=TA_LEFT)
    ))
    elementos.append(Spacer(1, 0.5*cm))

    # ── SALIDAS ───────────────────────────────────────────────
    elementos.append(Paragraph('📤  Equipos en el punto', estilo_seccion))
    elementos.append(Spacer(1, 0.3*cm))

    if not salidas:
        elementos.append(Paragraph('Sin salidas registradas.', estilo_valor))
    else:
        for salida in salidas:
            fecha_str = salida.get('fecha', '')[:10] if salida.get('fecha') else ''
            sede_str  = salida.get('sede_nombre', '')
            elementos.append(Paragraph(
                f"{salida['numero_documento']}  ·  {fecha_str}{('  ·  ' + sede_str) if sede_str else ''}",
                estilo_sub
            ))
            elementos.append(Spacer(1, 0.15*cm))

            encabezados = [
                Paragraph('Descripcion', estilo_encabezado),
                Paragraph('Modelo',      estilo_encabezado),
                Paragraph('N° Serial',   estilo_encabezado),
                Paragraph('Marca',       estilo_encabezado),
                Paragraph('Cant.',       estilo_encabezado),
                Paragraph('Unidad',      estilo_encabezado),
            ]
            filas = [encabezados]
            for item in salida['detalle']:
                filas.append([
                    Paragraph(item.get('nombre', ''), estilo_celda),
                    Paragraph(item.get('modelo', '') or '', estilo_celda),
                    Paragraph(item.get('serial', '') or '', estilo_celda),
                    Paragraph(item.get('marca',  '') or '', estilo_celda),
                    Paragraph(str(item.get('cantidad', '')), estilo_celda),
                    Paragraph(item.get('unidad', '') or '', estilo_celda),
                ])

            tabla = Table(filas, colWidths=[5.5*cm, 3*cm, 3*cm, 2.5*cm, 2*cm, 2*cm])
            tabla.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#0d2137')),
                ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
                ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0), (-1,0),  7),
                ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#dce6f0')),
                ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, colors.HexColor('#f7f9fc')]),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING',       (0,0), (-1,-1), 4),
                ('FONTSIZE',      (0,1), (-1,-1), 7),
            ]))
            elementos.append(tabla)
            elementos.append(Spacer(1, 0.4*cm))

    # ── DEVOLUCIONES ──────────────────────────────────────────
    elementos.append(Spacer(1, 0.2*cm))
    elementos.append(Paragraph('🔄  Devoluciones al almacen', estilo_seccion))
    elementos.append(Spacer(1, 0.3*cm))

    if not devoluciones:
        elementos.append(Paragraph('Sin devoluciones registradas.', estilo_valor))
    else:
        for dev in devoluciones:
            fecha_str  = dev.get('fecha', '')[:10] if dev.get('fecha') else ''
            sede_str   = dev.get('sede_nombre', '')
            motivo_str = dev.get('motivo', '')
            sal_str    = dev.get('salida_numero', '')
            elementos.append(Paragraph(
                f"{dev['numero_documento']}  ·  {fecha_str}{('  ·  ' + sede_str) if sede_str else ''}",
                estilo_sub
            ))
            elementos.append(Paragraph(
                f"Motivo: {motivo_str or '—'}   Salida origen: {sal_str or '—'}",
                ParagraphStyle('mot', fontSize=7, textColor=colors.HexColor('#6b8aab'))
            ))
            elementos.append(Spacer(1, 0.15*cm))

            encabezados = [
                Paragraph('Descripcion', estilo_encabezado),
                Paragraph('Modelo',      estilo_encabezado),
                Paragraph('N° Serial',   estilo_encabezado),
                Paragraph('Marca',       estilo_encabezado),
                Paragraph('Cant.',       estilo_encabezado),
                Paragraph('Unidad',      estilo_encabezado),
            ]
            filas = [encabezados]
            for item in dev['detalle']:
                filas.append([
                    Paragraph(item.get('nombre', ''), estilo_celda),
                    Paragraph(item.get('modelo', '') or '', estilo_celda),
                    Paragraph(item.get('serial', '') or '', estilo_celda),
                    Paragraph(item.get('marca',  '') or '', estilo_celda),
                    Paragraph(str(item.get('cantidad', '')), estilo_celda),
                    Paragraph(item.get('unidad', '') or '', estilo_celda),
                ])

            tabla = Table(filas, colWidths=[5.5*cm, 3*cm, 3*cm, 2.5*cm, 2*cm, 2*cm])
            tabla.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#1a6fc4')),
                ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
                ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0,0), (-1,0),  7),
                ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#dce6f0')),
                ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, colors.HexColor('#f7f9fc')]),
                ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING',       (0,0), (-1,-1), 4),
                ('FONTSIZE',      (0,1), (-1,-1), 7),
            ]))
            elementos.append(tabla)
            elementos.append(Spacer(1, 0.4*cm))

    doc.build(elementos)
    buffer.seek(0)

    nombre_archivo = f'consolidado_{destino.replace(" ", "_")}.pdf'
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=nombre_archivo
    )