# ============================================================
# consolidado.py
# Historial por punto / destino / obra
# PostgreSQL
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from database import get_connection


consolidado_bp = Blueprint(
    "consolidado",
    __name__
)


# ============================================================
# GET /api/consolidado/puntos
# Listar puntos/destinos registrados en salidas
# ============================================================

@consolidado_bp.route(
    "/puntos",
    methods=["GET"]
)
@jwt_required()
def listar_puntos():

    claims = get_jwt()

    rol = claims.get("rol")

    sede_id = request.args.get(
        "sede_id",
        type=int
    )

    # Los usuarios que no sean admin solamente
    # pueden consultar su propia sede.
    if rol != "admin":

        sede_id = claims.get(
            "sede_id"
        )

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            if sede_id is not None:

                cursor.execute("""
                    SELECT
                        s.destino,
                        s.sede_id,

                        se.nombre
                            AS sede_nombre,

                        COUNT(s.id)
                            AS total_salidas

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    WHERE
                        s.destino IS NOT NULL
                        AND TRIM(s.destino) <> ''
                        AND s.sede_id = %s

                    GROUP BY
                        s.destino,
                        s.sede_id,
                        se.nombre

                    ORDER BY
                        s.destino
                """, (
                    sede_id,
                ))

            else:

                cursor.execute("""
                    SELECT
                        s.destino,
                        s.sede_id,

                        se.nombre
                            AS sede_nombre,

                        COUNT(s.id)
                            AS total_salidas

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    WHERE
                        s.destino IS NOT NULL
                        AND TRIM(s.destino) <> ''

                    GROUP BY
                        s.destino,
                        s.sede_id,
                        se.nombre

                    ORDER BY
                        s.destino
                """)

            puntos = [
                dict(p)
                for p in cursor.fetchall()
            ]

    finally:

        conn.close()

    return jsonify(puntos)


# ============================================================
# GET /api/consolidado/punto
#
# Historial completo de un destino:
#
#   - Salidas
#   - Devoluciones
#   - Resumen neto
# ============================================================

@consolidado_bp.route(
    "/punto",
    methods=["GET"]
)
@jwt_required()
def historial_punto():

    destino = request.args.get(
        "destino",
        ""
    ).strip()

    if not destino:

        return jsonify({
            "error": "Destino requerido"
        }), 400

    claims = get_jwt()

    rol = claims.get("rol")

    sede_id = request.args.get(
        "sede_id",
        type=int
    )

    if rol != "admin":

        sede_id = claims.get(
            "sede_id"
        )

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

                        s.destino,
                        s.sede_id,

                        s.observaciones,
                        s.estado,

                        s.usuario_id,

                        s.fecha_creacion,
                        s.fecha_anulacion,

                        se.nombre
                            AS sede_nombre,

                        u.nombre
                            AS usuario_nombre

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = s.usuario_id

                    WHERE
                        s.destino = %s
                        AND s.sede_id = %s

                    ORDER BY
                        s.fecha_creacion DESC
                """, (
                    destino,
                    sede_id
                ))

            else:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,

                        s.destino,
                        s.sede_id,

                        s.observaciones,
                        s.estado,

                        s.usuario_id,

                        s.fecha_creacion,
                        s.fecha_anulacion,

                        se.nombre
                            AS sede_nombre,

                        u.nombre
                            AS usuario_nombre

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = s.usuario_id

                    WHERE
                        s.destino = %s

                    ORDER BY
                        s.fecha_creacion DESC
                """, (
                    destino,
                ))

            salidas = [
                dict(s)
                for s in cursor.fetchall()
            ]

            # =================================================
            # DETALLE DE CADA SALIDA
            # =================================================

            for salida in salidas:

                cursor.execute("""
                    SELECT
                        d.id,
                        d.producto_id,
                        d.equipo_id,
                        d.cantidad,
                        d.observaciones,

                        p.codigo,
                        p.nombre
                            AS producto_nombre,

                        p.requiere_serial,

                        un.codigo
                            AS unidad_codigo,

                        un.nombre
                            AS unidad_nombre,

                        mo.nombre
                            AS modelo_nombre,

                        ma.nombre
                            AS marca_nombre,

                        e.serial

                    FROM detalle_salidas d

                    INNER JOIN productos p
                        ON p.id = d.producto_id

                    LEFT JOIN unidades un
                        ON un.id = p.unidad_id

                    LEFT JOIN modelos mo
                        ON mo.id = p.modelo_id

                    LEFT JOIN marcas ma
                        ON ma.id = mo.marca_id

                    LEFT JOIN equipos e
                        ON e.id = d.equipo_id

                    WHERE
                        d.salida_id = %s

                    ORDER BY
                        d.id
                """, (
                    salida["id"],
                ))

                detalles = [
                    dict(d)
                    for d in cursor.fetchall()
                ]

                # -------------------------------------------------
                # El serial se obtiene mediante el equipo exacto
                # utilizado en detalle_salidas.
                # -------------------------------------------------

                for item in detalles:

                    if item["requiere_serial"]:

                        if item.get("serial"):

                            item["serial"] = item["serial"]

                        else:

                            item["serial"] = None

                    else:

                        item["serial"] = None

                salida["detalle"] = detalles

            # =================================================
            # DEVOLUCIONES
            #
            # El destino se obtiene desde la salida asociada.
            # =================================================

            if sede_id is not None:

                cursor.execute("""
                    SELECT
                        dv.id,
                        dv.numero_documento,

                        dv.sede_id,
                        dv.salida_id,

                        dv.motivo,
                        dv.observaciones,
                        dv.estado,

                        dv.usuario_id,

                        dv.fecha_creacion,
                        dv.fecha_anulacion,

                        s.numero_documento
                            AS salida_numero,

                        s.destino,

                        se.nombre
                            AS sede_nombre,

                        u.nombre
                            AS usuario_nombre

                    FROM devoluciones dv

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = dv.usuario_id

                    WHERE
                        s.destino = %s
                        AND dv.sede_id = %s

                    ORDER BY
                        dv.fecha_creacion DESC
                """, (
                    destino,
                    sede_id
                ))

            else:

                cursor.execute("""
                    SELECT
                        dv.id,
                        dv.numero_documento,

                        dv.sede_id,
                        dv.salida_id,

                        dv.motivo,
                        dv.observaciones,
                        dv.estado,

                        dv.usuario_id,

                        dv.fecha_creacion,
                        dv.fecha_anulacion,

                        s.numero_documento
                            AS salida_numero,

                        s.destino,

                        se.nombre
                            AS sede_nombre,

                        u.nombre
                            AS usuario_nombre

                    FROM devoluciones dv

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = dv.usuario_id

                    WHERE
                        s.destino = %s

                    ORDER BY
                        dv.fecha_creacion DESC
                """, (
                    destino,
                ))

            devoluciones = [
                dict(d)
                for d in cursor.fetchall()
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

                        p.codigo,
                        p.nombre
                            AS producto_nombre,

                        un.codigo
                            AS unidad_codigo,

                        un.nombre
                            AS unidad_nombre,

                        mo.nombre
                            AS modelo_nombre,

                        ma.nombre
                            AS marca_nombre,

                        e.serial

                    FROM detalle_devoluciones d

                    INNER JOIN productos p
                        ON p.id = d.producto_id

                    LEFT JOIN unidades un
                        ON un.id = p.unidad_id

                    LEFT JOIN modelos mo
                        ON mo.id = p.modelo_id

                    LEFT JOIN marcas ma
                        ON ma.id = mo.marca_id

                    LEFT JOIN equipos e
                        ON e.id = d.equipo_id

                    WHERE
                        d.devolucion_id = %s

                    ORDER BY
                        d.id
                """, (
                    dev["id"],
                ))

                dev["detalle"] = [
                    dict(d)
                    for d in cursor.fetchall()
                ]

            # =================================================
            # RESUMEN NETO
            #
            # Solo contamos movimientos ACTIVOS.
            # =================================================

            neto = {}

            for salida in salidas:

                if salida["estado"] != "ACTIVA":

                    continue

                for item in salida["detalle"]:

                    clave = (
                        item["producto_id"],
                        item.get(
                            "modelo_nombre"
                        ) or "",
                        item.get(
                            "serial"
                        ) or ""
                    )

                    if clave not in neto:

                        neto[clave] = {
                            "producto_id":
                                item["producto_id"],

                            "nombre":
                                item[
                                    "producto_nombre"
                                ],

                            "codigo":
                                item["codigo"],

                            "modelo":
                                item.get(
                                    "modelo_nombre"
                                ) or "—",

                            "serial":
                                item.get(
                                    "serial"
                                ) or "—",

                            "unidad":
                                item.get(
                                    "unidad_codigo"
                                ) or "UND",

                            "salidas": 0,
                            "devuelto": 0,
                            "neto": 0
                        }

                    neto[clave]["salidas"] += (
                        item["cantidad"]
                    )

                    neto[clave]["neto"] += (
                        item["cantidad"]
                    )

            # =================================================
            # RESTAR DEVOLUCIONES ACTIVAS
            # =================================================

            for dev in devoluciones:

                if dev["estado"] != "ACTIVA":

                    continue

                for item in dev["detalle"]:

                    clave = (
                        item["producto_id"],
                        item.get(
                            "modelo_nombre"
                        ) or "",
                        item.get(
                            "serial"
                        ) or ""
                    )

                    if clave in neto:

                        neto[clave][
                            "devuelto"
                        ] += item["cantidad"]

                        neto[clave][
                            "neto"
                        ] -= item["cantidad"]

                    else:

                        neto[clave] = {
                            "producto_id":
                                item["producto_id"],

                            "nombre":
                                item[
                                    "producto_nombre"
                                ],

                            "codigo":
                                item["codigo"],

                            "modelo":
                                item.get(
                                    "modelo_nombre"
                                ) or "—",

                            "serial":
                                item.get(
                                    "serial"
                                ) or "—",

                            "unidad":
                                item.get(
                                    "unidad_codigo"
                                ) or "UND",

                            "salidas": 0,

                            "devuelto":
                                item["cantidad"],

                            "neto":
                                -item["cantidad"]
                        }

    finally:

        conn.close()

    return jsonify({
        "destino": destino,
        "salidas": salidas,
        "devoluciones": devoluciones,
        "resumen": list(
            neto.values()
        )
    })
