# ============================================================
# pdf_stock_bajo.py
#
# Genera un PDF con el listado de productos que están por
# debajo de su stock mínimo (o agotados), para saber qué pedir
# más. Es el mismo tipo de reporte que salidas/entradas/etc.,
# pero de una sola pasada con TODOS los productos que necesitan
# reabastecimiento en vez de un solo documento.
#
# GET /api/pdf/stock-bajo?sede_id=<opcional>
#
# Sin sede_id: todas las sedes (se agrega una columna "Sede").
# Con sede_id: solo esa sede.
#
# Un producto se considera "stock bajo" cuando:
#   - está en 0 (agotado), sin importar si tiene mínimo
#     configurado, o
#   - tiene un stock mínimo configurado (> 0) y el stock
#     actual quedó igual o por debajo de ese mínimo.
#
# PostgreSQL
# ============================================================

from flask import Blueprint, request, send_file, jsonify
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
from datetime import datetime
from io import BytesIO

from database import get_connection


pdf_stock_bajo_bp = Blueprint(
    "pdf_stock_bajo",
    __name__
)


# ============================================================
# GET /api/pdf/stock-bajo
# ============================================================

@pdf_stock_bajo_bp.route(
    "/stock-bajo",
    methods=["GET"]
)
@jwt_required()
def generar_pdf_stock_bajo():

    claims = get_jwt()

    sede_id = request.args.get(
        "sede_id",
        type=int
    )

    # ========================================================
    # RESTRICCIÓN POR SEDE
    #
    # Solo el admin puede pedir el reporte de cualquier sede
    # (o de todas). Cualquier otro rol (almacenista, consulta,
    # portería) solo puede ver el de su propia sede, sin
    # importar qué sede_id venga en la URL.
    # ========================================================

    if claims.get("rol") != "admin":
        sede_id = claims.get("sede_id")

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ================================================
            # PRODUCTOS CON STOCK BAJO O AGOTADO
            # ================================================

            condiciones = [
                "("
                "COALESCE(i.cantidad, 0) = 0"
                " OR "
                "(p.stock_minimo > 0 AND COALESCE(i.cantidad, 0) <= p.stock_minimo)"
                ")"
            ]

            parametros = []

            if sede_id:
                condiciones.append("p.sede_id = %s")
                parametros.append(sede_id)

            where_sql = " AND ".join(condiciones)

            cursor.execute(f"""
                SELECT
                    p.codigo,
                    p.nombre,

                    ma.nombre AS marca_nombre,

                    s.nombre AS sede_nombre,

                    p.stock_minimo,

                    COALESCE(i.cantidad, 0) AS stock,

                    u.codigo AS unidad

                FROM productos p

                LEFT JOIN inventario i
                    ON i.producto_id = p.id
                   AND i.sede_id = p.sede_id

                LEFT JOIN sedes s
                    ON s.id = p.sede_id

                LEFT JOIN modelos m
                    ON m.id = p.modelo_id

                LEFT JOIN marcas ma
                    ON ma.id = m.marca_id

                LEFT JOIN unidades u
                    ON u.id = p.unidad_id

                WHERE {where_sql}

                ORDER BY
                    s.nombre,
                    (p.stock_minimo - COALESCE(i.cantidad, 0)) DESC,
                    p.nombre
            """, parametros)

            productos = [
                dict(fila)
                for fila in cursor.fetchall()
            ]

            sede_nombre_filtro = None

            if sede_id:

                cursor.execute("""
                    SELECT nombre
                    FROM sedes
                    WHERE id = %s
                """, (sede_id,))

                fila_sede = cursor.fetchone()

                sede_nombre_filtro = (
                    fila_sede["nombre"]
                    if fila_sede
                    else None
                )

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

    estilo_celda_centrada = ParagraphStyle(
        "celda_c",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER
    )

    estilo_titulo = ParagraphStyle(
        "titulo",
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0d2137")
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

    subtitulo_sede = (
        f"Sede: {sede_nombre_filtro}"
        if sede_nombre_filtro
        else "Todas las sedes"
    )

    fecha_generacion = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    bloque_titulo = [

        Paragraph(
            "PRODUCTOS CON STOCK BAJO",

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
            f"{subtitulo_sede} — Generado: {fecha_generacion}",

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
            0.6 * cm
        )
    )


    # ========================================================
    # SIN RESULTADOS
    # ========================================================

    if not productos:

        elementos.append(
            Paragraph(
                "No hay productos con stock bajo ni agotados "
                "en este momento. Todo está por encima de su "
                "mínimo configurado.",

                ParagraphStyle(
                    "sin_datos",
                    fontSize=11,
                    alignment=TA_CENTER,
                    textColor=colors.HexColor("#1a7a4a"),
                    spaceBefore=30
                )
            )
        )

    else:

        # ====================================================
        # TABLA
        # ====================================================

        mostrar_sede = sede_id is None

        encabezados = [
            "Código",
            "Producto",
            "Marca"
        ]

        if mostrar_sede:
            encabezados.append("Sede")

        encabezados += [
            "Stock actual",
            "Stock mínimo",
            "Sugerido pedir"
        ]

        filas = [encabezados]

        for p in productos:

            stock_actual = p.get("stock") or 0
            stock_minimo = p.get("stock_minimo") or 0

            sugerido = max(
                stock_minimo - stock_actual,
                1 if stock_actual == 0 else 0
            )

            fila = [
                Paragraph(
                    p.get("codigo") or "—",
                    estilo_celda
                ),
                Paragraph(
                    p.get("nombre") or "—",
                    estilo_celda
                ),
                Paragraph(
                    p.get("marca_nombre") or "—",
                    estilo_celda
                )
            ]

            if mostrar_sede:
                fila.append(
                    Paragraph(
                        p.get("sede_nombre") or "—",
                        estilo_celda
                    )
                )

            unidad = p.get("unidad") or "UND"

            fila += [
                Paragraph(
                    f"{stock_actual} {unidad}",
                    estilo_celda_centrada
                ),
                Paragraph(
                    str(stock_minimo) if stock_minimo else "—",
                    estilo_celda_centrada
                ),
                Paragraph(
                    f"{sugerido} {unidad}",
                    estilo_celda_centrada
                )
            ]

            filas.append(fila)

        if mostrar_sede:
            col_widths = [
                2.6 * cm,
                5.2 * cm,
                2.8 * cm,
                2.8 * cm,
                2.2 * cm,
                2.2 * cm,
                2.2 * cm
            ]
        else:
            col_widths = [
                3 * cm,
                6.5 * cm,
                3.5 * cm,
                2.5 * cm,
                2.5 * cm,
                2.5 * cm
            ]

        tabla_productos = Table(
            filas,
            colWidths=col_widths,
            repeatRows=1
        )

        estilo_tabla = [

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
        ]

        # Resaltar en rojo suave las filas de productos
        # agotados (stock = 0), para que salten a la vista.
        for indice, p in enumerate(productos, start=1):
            if (p.get("stock") or 0) == 0:
                estilo_tabla.append((
                    "BACKGROUND",
                    (0, indice),
                    (-1, indice),
                    colors.HexColor("#fdecea")
                ))

        tabla_productos.setStyle(
            TableStyle(estilo_tabla)
        )

        elementos.append(
            tabla_productos
        )

        elementos.append(
            Spacer(
                1,
                0.4 * cm
            )
        )

        elementos.append(
            Paragraph(
                f"Total de productos para reabastecer: {len(productos)}. "
                "Las filas en rojo están agotadas (stock en cero).",

                ParagraphStyle(
                    "nota",
                    fontSize=8,
                    textColor=colors.HexColor("#6b8aab")
                )
            )
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
                "No se pudo construir el documento PDF."
            )
        }), 500

    buffer.seek(0)

    nombre_archivo = "stock_bajo"

    if sede_nombre_filtro:
        nombre_archivo += "_" + (
            sede_nombre_filtro
            .lower()
            .replace(" ", "_")
        )

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{nombre_archivo}.pdf"
    )