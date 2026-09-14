# ============================================================
# pdf_consolidado.py
# PDF del consolidado por punto
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

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

import os
from io import BytesIO
from datetime import datetime

from database import get_connection


pdf_consolidado_bp = Blueprint(
    "pdf_consolidado",
    __name__
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def formatear_fecha(fecha):

    if not fecha:
        return "—"

    try:

        if hasattr(fecha, "strftime"):

            return fecha.strftime(
                "%d/%m/%Y %H:%M"
            )

        fecha_texto = str(fecha)

        try:

            fecha_dt = datetime.fromisoformat(
                fecha_texto.replace(
                    "Z",
                    "+00:00"
                )
            )

            return fecha_dt.strftime(
                "%d/%m/%Y %H:%M"
            )

        except Exception:

            return fecha_texto[:16]

    except Exception:

        return str(fecha)


def limpiar_texto(valor):

    if valor is None:
        return "—"

    texto = str(valor).strip()

    if not texto:
        return "—"

    return texto


# ============================================================
# GET /api/pdf/consolidado
# ============================================================

@pdf_consolidado_bp.route(
    "/consolidado",
    methods=["GET"]
)
@jwt_required()
def generar_pdf_consolidado():

    claims = get_jwt()

    destino = (
        request.args.get(
            "destino",
            ""
        )
        .strip()
    )

    sede_id = request.args.get(
        "sede_id",
        type=int
    )

    # ========================================================
    # RESTRICCIÓN POR SEDE
    # ========================================================

    if claims.get("rol") != "admin":

        sede_id = claims.get(
            "sede_id"
        )

    if not destino:

        return jsonify({
            "error": "Destino requerido"
        }), 400

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # SALIDAS
            # =================================================

            if sede_id is not None:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.fecha,
                        s.observaciones,
                        s.destino,
                        s.estado,
                        s.sede_id,

                        se.nombre AS sede_nombre,
                        se.ciudad

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    WHERE s.destino = %s
                      AND s.sede_id = %s
                      AND s.estado = 'ACTIVA'

                    ORDER BY s.fecha DESC
                """, (
                    destino,
                    sede_id
                ))

            else:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.fecha,
                        s.observaciones,
                        s.destino,
                        s.estado,
                        s.sede_id,

                        se.nombre AS sede_nombre,
                        se.ciudad

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    WHERE s.destino = %s
                      AND s.estado = 'ACTIVA'

                    ORDER BY s.fecha DESC
                """, (
                    destino,
                ))

            salidas = [
                dict(row)
                for row in cursor.fetchall()
            ]


            # =================================================
            # DETALLE DE SALIDAS
            # =================================================

            for salida in salidas:

                cursor.execute("""
                    SELECT

                        d.id,
                        d.producto_id,
                        d.equipo_id,
                        d.cantidad,
                        d.observaciones,

                        p.nombre AS nombre,
                        p.codigo,
                        p.descripcion,

                        un.codigo AS unidad_codigo,
                        un.nombre AS unidad_nombre,

                        COALESCE(
                            me.id,
                            mp.id
                        ) AS modelo_id,

                        COALESCE(
                            me.nombre,
                            mp.nombre
                        ) AS modelo,

                        COALESCE(
                            mae.id,
                            map.id
                        ) AS marca_id,

                        COALESCE(
                            mae.nombre,
                            map.nombre
                        ) AS marca,

                        eq.serial,
                        eq.condicion AS equipo_condicion,
                        eq.estado AS equipo_estado

                    FROM detalle_salidas d

                    INNER JOIN productos p
                        ON p.id = d.producto_id

                    LEFT JOIN unidades un
                        ON un.id = p.unidad_id

                    LEFT JOIN equipos eq
                        ON eq.id = d.equipo_id

                    LEFT JOIN modelos me
                        ON me.id = eq.modelo_id

                    LEFT JOIN marcas mae
                        ON mae.id = me.marca_id

                    LEFT JOIN modelos mp
                        ON mp.id = p.modelo_id

                    LEFT JOIN marcas map
                        ON map.id = mp.marca_id

                    WHERE d.salida_id = %s

                    ORDER BY d.id
                """, (
                    salida["id"],
                ))

                salida["detalle"] = [
                    dict(row)
                    for row in cursor.fetchall()
                ]


            # =================================================
            # DEVOLUCIONES
            # =================================================

            if sede_id is not None:

                cursor.execute("""
                    SELECT

                        dv.id,
                        dv.numero_documento,
                        dv.fecha,
                        dv.motivo,
                        dv.observaciones,
                        dv.estado,
                        dv.sede_id,

                        s.numero_documento
                            AS salida_numero,

                        s.destino
                            AS salida_destino,

                        se.nombre
                            AS sede_nombre,

                        se.ciudad

                    FROM devoluciones dv

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    WHERE s.destino = %s
                      AND dv.sede_id = %s
                      AND dv.estado = 'ACTIVA'

                    ORDER BY dv.fecha DESC
                """, (
                    destino,
                    sede_id
                ))

            else:

                cursor.execute("""
                    SELECT

                        dv.id,
                        dv.numero_documento,
                        dv.fecha,
                        dv.motivo,
                        dv.observaciones,
                        dv.estado,
                        dv.sede_id,

                        s.numero_documento
                            AS salida_numero,

                        s.destino
                            AS salida_destino,

                        se.nombre
                            AS sede_nombre,

                        se.ciudad

                    FROM devoluciones dv

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    WHERE s.destino = %s
                      AND dv.estado = 'ACTIVA'

                    ORDER BY dv.fecha DESC
                """, (
                    destino,
                ))

            devoluciones = [
                dict(row)
                for row in cursor.fetchall()
            ]


            # =================================================
            # DETALLE DE DEVOLUCIONES
            # =================================================

            for dev in devoluciones:

                cursor.execute("""
                    SELECT

                        d.id,
                        d.producto_id,
                        d.equipo_id,
                        d.cantidad,
                        d.condicion_retorno,
                        d.observaciones,

                        p.nombre AS nombre,
                        p.codigo,
                        p.descripcion,

                        un.codigo AS unidad_codigo,
                        un.nombre AS unidad_nombre,

                        COALESCE(
                            me.id,
                            mp.id
                        ) AS modelo_id,

                        COALESCE(
                            me.nombre,
                            mp.nombre
                        ) AS modelo,

                        COALESCE(
                            mae.id,
                            map.id
                        ) AS marca_id,

                        COALESCE(
                            mae.nombre,
                            map.nombre
                        ) AS marca,

                        eq.serial,
                        eq.condicion AS equipo_condicion,
                        eq.estado AS equipo_estado

                    FROM detalle_devoluciones d

                    INNER JOIN productos p
                        ON p.id = d.producto_id

                    LEFT JOIN unidades un
                        ON un.id = p.unidad_id

                    LEFT JOIN equipos eq
                        ON eq.id = d.equipo_id

                    LEFT JOIN modelos me
                        ON me.id = eq.modelo_id

                    LEFT JOIN marcas mae
                        ON mae.id = me.marca_id

                    LEFT JOIN modelos mp
                        ON mp.id = p.modelo_id

                    LEFT JOIN marcas map
                        ON map.id = mp.marca_id

                    WHERE d.devolucion_id = %s

                    ORDER BY d.id
                """, (
                    dev["id"],
                ))

                dev["detalle"] = [
                    dict(row)
                    for row in cursor.fetchall()
                ]


    except Exception as e:

        print(
            "ERROR PDF CONSOLIDADO:",
            repr(e)
        )

        return jsonify({
            "error": "Error al generar el PDF",
            "detalle": str(e)
        }), 500

    finally:

        conn.close()


    # ========================================================
    # CALCULAR RESUMEN NETO
    # ========================================================

    neto = {}


    # ========================================================
    # SUMAR SALIDAS
    # ========================================================

    for salida in salidas:

        for item in salida["detalle"]:

            clave = (
                item.get("producto_id"),
                item.get("modelo_id"),
                item.get("serial") or ""
            )

            if clave not in neto:

                neto[clave] = {

                    "nombre":
                        item.get("nombre")
                        or "—",

                    "codigo":
                        item.get("codigo")
                        or "—",

                    "modelo":
                        item.get("modelo")
                        or "—",

                    "serial":
                        item.get("serial")
                        or "—",

                    "marca":
                        item.get("marca")
                        or "—",

                    "unidad":
                        item.get("unidad_codigo")
                        or "UND",

                    "salidas":
                        0,

                    "devuelto":
                        0,

                    "neto":
                        0
                }

            cantidad = (
                item.get("cantidad")
                or 0
            )

            neto[clave]["salidas"] += cantidad

            neto[clave]["neto"] += cantidad


    # ========================================================
    # RESTAR DEVOLUCIONES
    # ========================================================

    for dev in devoluciones:

        for item in dev["detalle"]:

            clave = (
                item.get("producto_id"),
                item.get("modelo_id"),
                item.get("serial") or ""
            )

            cantidad = (
                item.get("cantidad")
                or 0
            )

            if clave in neto:

                neto[clave]["devuelto"] += cantidad

                neto[clave]["neto"] -= cantidad

            else:

                neto[clave] = {

                    "nombre":
                        item.get("nombre")
                        or "—",

                    "codigo":
                        item.get("codigo")
                        or "—",

                    "modelo":
                        item.get("modelo")
                        or "—",

                    "serial":
                        item.get("serial")
                        or "—",

                    "marca":
                        item.get("marca")
                        or "—",

                    "unidad":
                        item.get("unidad_codigo")
                        or "UND",

                    "salidas":
                        0,

                    "devuelto":
                        cantidad,

                    "neto":
                        -cantidad
                }


    resumen = list(
        neto.values()
    )


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
        "enc",
        fontSize=7,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER
    )

    estilo_valor = ParagraphStyle(
        "valor",
        fontSize=8
    )

    estilo_seccion = ParagraphStyle(
        "sec",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(
            "#0d2137"
        )
    )

    estilo_sub = ParagraphStyle(
        "sub",
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(
            "#1a6fc4"
        )
    )


    # ========================================================
    # LOGO
    # ========================================================

    base_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    posibles_logos = [

        os.path.join(
            base_dir,
            "frontend",
            "img",
            "logoocci.png"
        ),

        os.path.join(
            base_dir,
            "frontend",
            "img",
            "occidente.png"
        )
    ]

    logo_path = None

    for ruta in posibles_logos:

        if os.path.exists(ruta):

            logo_path = ruta
            break


    if logo_path:

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
            "CONSOLIDADO POR PUNTO",

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
            limpiar_texto(destino),

            ParagraphStyle(
                "dest",
                fontSize=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor(
                    "#1a6fc4"
                ),
                fontName="Helvetica-Bold"
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
            0.3 * cm
        )
    )


    # ========================================================
    # FECHA DE GENERACIÓN
    # ========================================================

    fecha_gen = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    elementos.append(
        Paragraph(
            f"Generado el {fecha_gen}",

            ParagraphStyle(
                "gen",
                fontSize=7,
                textColor=colors.HexColor(
                    "#6b8aab"
                ),
                alignment=TA_LEFT
            )
        )
    )

    elementos.append(
        Spacer(
            1,
            0.5 * cm
        )
    )


    # ========================================================
    # RESUMEN NETO
    # ========================================================

    elementos.append(
        Paragraph(
            "Equipos en el punto (resumen actual)",
            estilo_seccion
        )
    )

    elementos.append(
        Spacer(
            1,
            0.3 * cm
        )
    )


    if not resumen:

        elementos.append(
            Paragraph(
                "Sin equipos registrados.",
                estilo_valor
            )
        )

    else:

        encabezados_resumen = [

            Paragraph(
                "Descripción",
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
                "Salió",
                estilo_encabezado
            ),

            Paragraph(
                "Devuelto",
                estilo_encabezado
            ),

            Paragraph(
                "En punto",
                estilo_encabezado
            )
        ]

        filas_resumen = [
            encabezados_resumen
        ]


        for r in resumen:

            filas_resumen.append([

                Paragraph(
                    limpiar_texto(
                        r.get("nombre")
                    ),
                    estilo_celda
                ),

                Paragraph(
                    limpiar_texto(
                        r.get("modelo")
                    ),
                    estilo_celda
                ),

                Paragraph(
                    limpiar_texto(
                        r.get("serial")
                    ),
                    estilo_celda
                ),

                Paragraph(
                    limpiar_texto(
                        r.get("marca")
                    ),
                    estilo_celda
                ),

                Paragraph(
                    f'{r["salidas"]} '
                    f'{r["unidad"]}',
                    estilo_celda
                ),

                Paragraph(
                    f'{r["devuelto"]} '
                    f'{r["unidad"]}',

                    ParagraphStyle(
                        "dev_color",
                        fontSize=8,
                        textColor=colors.HexColor(
                            "#c0392b"
                        )
                    )
                ),

                Paragraph(
                    f'{r["neto"]} '
                    f'{r["unidad"]}',

                    ParagraphStyle(
                        "neto_color",
                        fontSize=8,
                        fontName="Helvetica-Bold",
                        textColor=colors.HexColor(
                            "#1a7a4a"
                        )
                    )
                )
            ])


        tabla_resumen = Table(

            filas_resumen,

            colWidths=[
                4.2 * cm,
                2.5 * cm,
                3.0 * cm,
                2.3 * cm,
                2.0 * cm,
                2.2 * cm,
                2.2 * cm
            ]
        )


        tabla_resumen.setStyle(
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
                    "BACKGROUND",
                    (6, 0),
                    (6, 0),
                    colors.HexColor(
                        "#1a7a4a"
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
                    7
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
                    4
                ),

                (
                    "FONTSIZE",
                    (0, 1),
                    (-1, -1),
                    7
                )
            ])
        )


        elementos.append(
            tabla_resumen
        )

        elementos.append(
            Spacer(
                1,
                0.5 * cm
            )
        )


    # ========================================================
    # DEVOLUCIONES
    # ========================================================

    elementos.append(
        Paragraph(
            "Devoluciones al almacén",
            estilo_seccion
        )
    )

    elementos.append(
        Spacer(
            1,
            0.3 * cm
        )
    )


    if not devoluciones:

        elementos.append(
            Paragraph(
                "Sin devoluciones registradas.",
                estilo_valor
            )
        )

    else:

        for dev in devoluciones:

            fecha_str = formatear_fecha(
                dev.get("fecha")
            )

            sede_str = limpiar_texto(
                dev.get("sede_nombre")
            )

            motivo_str = limpiar_texto(
                dev.get("motivo")
            )

            salida_str = limpiar_texto(
                dev.get("salida_numero")
            )


            # =================================================
            # ENCABEZADO DE DEVOLUCIÓN
            # =================================================

            elementos.append(
                Paragraph(

                    (
                        f'{limpiar_texto(dev.get("numero_documento"))}'
                        f' · '
                        f'{fecha_str}'
                        f' · '
                        f'{sede_str}'
                    ),

                    estilo_sub
                )
            )


            # =================================================
            # MOTIVO Y SALIDA ORIGEN
            # =================================================

            elementos.append(
                Paragraph(

                    (
                        f"Motivo: "
                        f"{motivo_str}"
                        f"   "
                        f"Salida origen: "
                        f"{salida_str}"
                    ),

                    ParagraphStyle(
                        "mot",
                        fontSize=7,
                        textColor=colors.HexColor(
                            "#6b8aab"
                        )
                    )
                )
            )


            elementos.append(
                Spacer(
                    1,
                    0.15 * cm
                )
            )


            # =================================================
            # TABLA DE DETALLE
            # =================================================

            encabezados = [

                Paragraph(
                    "Descripción",
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
                    "Cant.",
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


            for item in dev["detalle"]:

                filas.append([

                    Paragraph(
                        limpiar_texto(
                            item.get("nombre")
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        limpiar_texto(
                            item.get("modelo")
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        limpiar_texto(
                            item.get("serial")
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        limpiar_texto(
                            item.get("marca")
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        str(
                            item.get("cantidad")
                            or 0
                        ),
                        estilo_celda
                    ),

                    Paragraph(
                        limpiar_texto(
                            item.get(
                                "unidad_codigo"
                            )
                        ),
                        estilo_celda
                    )
                ])


            tabla = Table(

                filas,

                colWidths=[
                    5.2 * cm,
                    2.7 * cm,
                    3.0 * cm,
                    2.4 * cm,
                    1.8 * cm,
                    2.2 * cm
                ]
            )


            tabla.setStyle(
                TableStyle([

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#1a6fc4"
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
                        7
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
                        4
                    ),

                    (
                        "FONTSIZE",
                        (0, 1),
                        (-1, -1),
                        7
                    )
                ])
            )


            elementos.append(
                tabla
            )

            elementos.append(
                Spacer(
                    1,
                    0.4 * cm
                )
            )


    # ========================================================
    # GENERAR PDF
    # ========================================================

    doc.build(
        elementos
    )

    buffer.seek(0)


    # ========================================================
    # NOMBRE DEL ARCHIVO
    # ========================================================

    nombre_limpio = (
        destino
        .replace(
            " ",
            "_"
        )
        .replace(
            "/",
            "_"
        )
        .replace(
            "\\",
            "_"
        )
    )

    nombre_archivo = (
        "consolidado_"
        f"{nombre_limpio}.pdf"
    )


    # ========================================================
    # RESPUESTA
    # ========================================================

    return send_file(

        buffer,

        mimetype="application/pdf",

        as_attachment=False,

        download_name=nombre_archivo
    )