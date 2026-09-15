# ============================================================
# consolidado.py
# Historial por punto / destino / obra
#
# PostgreSQL
#
# Muestra:
#   - Puntos / destinos registrados
#   - Salidas realizadas al punto
#   - Devoluciones realizadas desde el punto
#   - Detalle de productos
#   - Modelo
#   - Marca
#   - Serial
#   - Resumen neto del material que permanece en el punto
#
# ROLES:
#   admin     -> puede consultar cualquier sede
#   sede      -> solamente su sede
#   consulta  -> siempre puede consultar cualquier sede,
#                tenga o no una sede propia asignada
#                (ver obtener_sede_actual)
# ============================================================

import re

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from database import get_connection


consolidado_bp = Blueprint(
    "consolidado",
    __name__
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_sede_actual():

    claims = get_jwt()

    rol = claims.get("rol")

    # ------------------------------------------------------
    # Admin:
    #     Puede consultar una sede específica mediante
    #     ?sede_id=ID. Si no envía sede_id, puede consultar
    #     todas.
    #
    # Consulta:
    #     NO necesita tener sede asignada.
    #     Puede consultar todas las sedes, o filtrar por una
    #     en concreto con ?sede_id, tenga o no una sede propia
    #     asignada en su usuario.
    # ------------------------------------------------------

    if rol == "admin" or rol == "consulta":

        return request.args.get(
            "sede_id",
            type=int
        )

    # ------------------------------------------------------
    # Sede:
    #     Siempre trabaja con su propia sede, sin importar lo
    #     que mande el parámetro sede_id.
    # ------------------------------------------------------

    return claims.get("sede_id")


# ============================================================
# GET /api/consolidado/puntos
#
# LISTAR PUNTOS / DESTINOS
# ============================================================

@consolidado_bp.route(
    "/puntos",
    methods=["GET"]
)
@jwt_required()
def listar_puntos():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # TODAS LAS SEDES
            # =================================================

            if sede_id is None:

                cursor.execute("""
                    SELECT
                        MIN(s.destino) AS destino,
                        s.sede_id,
                        se.nombre AS sede_nombre,
                        se.ciudad,
                        COUNT(s.id) AS total_salidas

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    WHERE s.destino IS NOT NULL
                      AND TRIM(s.destino) <> ''

                    GROUP BY
                        regexp_replace(upper(trim(s.destino)), '\\s+', ' ', 'g'),
                        s.sede_id,
                        se.nombre,
                        se.ciudad

                    ORDER BY
                        MIN(s.destino)
                """)

            # =================================================
            # UNA SEDE
            # =================================================

            else:

                cursor.execute("""
                    SELECT
                        MIN(s.destino) AS destino,
                        s.sede_id,
                        se.nombre AS sede_nombre,
                        se.ciudad,
                        COUNT(s.id) AS total_salidas

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    WHERE s.destino IS NOT NULL
                      AND TRIM(s.destino) <> ''
                      AND s.sede_id = %s

                    GROUP BY
                        regexp_replace(upper(trim(s.destino)), '\\s+', ' ', 'g'),
                        s.sede_id,
                        se.nombre,
                        se.ciudad

                    ORDER BY
                        MIN(s.destino)
                """, (
                    sede_id,
                ))

            puntos = [
                dict(punto)
                for punto in cursor.fetchall()
            ]

    finally:

        conn.close()

    return jsonify(puntos)


# ============================================================
# GET /api/consolidado/punto
#
# HISTORIAL COMPLETO DE UN DESTINO
#
# Ejemplo:
#
# /api/consolidado/punto?destino=Obra%20Norte
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

    # Mismo criterio de normalización que se usa para agrupar
    # los puntos en /puntos: sin importar mayúsculas/minúsculas
    # ni espacios de más, para que coincida con cualquier salida
    # que tenga ese destino escrito de forma un poco distinta.
    destino_normalizado = re.sub(
        r'\s+', ' ', destino
    ).upper()

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # SALIDAS
            # =================================================

            if sede_id is None:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.sede_id,
                        s.observaciones,
                        s.fecha,
                        s.estado,
                        s.usuario_id,
                        s.anulada_por,
                        s.fecha_anulacion,
                        s.motivo_anulacion,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        u.nombre AS usuario_nombre,

                        ua.nombre AS anulada_por_nombre

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = s.usuario_id

                    LEFT JOIN usuarios ua
                        ON ua.id = s.anulada_por

                    WHERE regexp_replace(upper(trim(s.destino)), '\\s+', ' ', 'g') = %s

                    ORDER BY
                        s.fecha DESC
                """, (
                    destino_normalizado,
                ))

            else:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.sede_id,
                        s.observaciones,
                        s.fecha,
                        s.estado,
                        s.usuario_id,
                        s.anulada_por,
                        s.fecha_anulacion,
                        s.motivo_anulacion,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        u.nombre AS usuario_nombre,

                        ua.nombre AS anulada_por_nombre

                    FROM salidas s

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = s.usuario_id

                    LEFT JOIN usuarios ua
                        ON ua.id = s.anulada_por

                    WHERE regexp_replace(upper(trim(s.destino)), '\\s+', ' ', 'g') = %s
                      AND s.sede_id = %s

                    ORDER BY
                        s.fecha DESC
                """, (
                    destino_normalizado,
                    sede_id,
                ))

            salidas = [
                dict(salida)
                for salida in cursor.fetchall()
            ]


            # =================================================
            # DETALLE DE LAS SALIDAS
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
                        p.nombre AS producto_nombre,
                        p.descripcion,
                        p.requiere_serial,

                        un.codigo AS unidad,
                        un.nombre AS unidad_nombre,

                        e.serial,
                        e.condicion AS equipo_condicion,
                        e.estado AS equipo_estado,

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

                    FROM detalle_salidas d

                    INNER JOIN productos p
                        ON p.id = d.producto_id

                    LEFT JOIN unidades un
                        ON un.id = p.unidad_id

                    LEFT JOIN equipos e
                        ON e.id = d.equipo_id

                    LEFT JOIN modelos me
                        ON me.id = e.modelo_id

                    LEFT JOIN marcas mae
                        ON mae.id = me.marca_id

                    LEFT JOIN modelos mp
                        ON mp.id = p.modelo_id

                    LEFT JOIN marcas map
                        ON map.id = mp.marca_id

                    WHERE d.salida_id = %s

                    ORDER BY
                        d.id
                """, (
                    salida["id"],
                ))

                salida["detalle"] = [
                    dict(item)
                    for item in cursor.fetchall()
                ]


            # =================================================
            # DEVOLUCIONES
            # =================================================

            if sede_id is None:

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
                        dv.anulada_por,
                        dv.fecha,
                        dv.fecha_anulacion,
                        dv.motivo_anulacion,

                        s.numero_documento AS salida_numero,
                        s.destino,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        u.nombre AS usuario_nombre,

                        ua.nombre AS anulada_por_nombre

                    FROM devoluciones dv

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = dv.usuario_id

                    LEFT JOIN usuarios ua
                        ON ua.id = dv.anulada_por

                    WHERE regexp_replace(upper(trim(s.destino)), '\\s+', ' ', 'g') = %s

                    ORDER BY
                        dv.fecha DESC
                """, (
                    destino_normalizado,
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
                        dv.anulada_por,
                        dv.fecha,
                        dv.fecha_anulacion,
                        dv.motivo_anulacion,

                        s.numero_documento AS salida_numero,
                        s.destino,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        u.nombre AS usuario_nombre,

                        ua.nombre AS anulada_por_nombre

                    FROM devoluciones dv

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = dv.usuario_id

                    LEFT JOIN usuarios ua
                        ON ua.id = dv.anulada_por

                    WHERE regexp_replace(upper(trim(s.destino)), '\\s+', ' ', 'g') = %s
                      AND dv.sede_id = %s

                    ORDER BY
                        dv.fecha DESC
                """, (
                    destino_normalizado,
                    sede_id,
                ))

            devoluciones = [
                dict(devolucion)
                for devolucion in cursor.fetchall()
            ]


            # =================================================
            # DETALLE DE LAS DEVOLUCIONES
            # =================================================

            for devolucion in devoluciones:

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
                        p.descripcion,
                        p.requiere_serial,

                        un.codigo AS unidad,
                        un.nombre AS unidad_nombre,

                        e.serial,
                        e.condicion AS equipo_condicion,
                        e.estado AS equipo_estado,

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

                    LEFT JOIN equipos e
                        ON e.id = d.equipo_id

                    LEFT JOIN modelos me
                        ON me.id = e.modelo_id

                    LEFT JOIN marcas mae
                        ON mae.id = me.marca_id

                    LEFT JOIN modelos mp
                        ON mp.id = p.modelo_id

                    LEFT JOIN marcas map
                        ON map.id = mp.marca_id

                    WHERE d.devolucion_id = %s

                    ORDER BY
                        d.id
                """, (
                    devolucion["id"],
                ))

                devolucion["detalle"] = [
                    dict(item)
                    for item in cursor.fetchall()
                ]


            # =================================================
            # RESUMEN NETO
            #
            # Salida ACTIVA:
            #     suma material
            #
            # Devolución ACTIVA:
            #     resta material
            #
            # Resultado:
            #     material que permanece en el punto
            # =================================================

            neto = {}


            # =================================================
            # PROCESAR SALIDAS
            # =================================================

            for salida in salidas:

                if salida["estado"] != "ACTIVA":
                    continue

                for item in salida["detalle"]:

                    clave = (
                        item["producto_id"],
                        item.get("modelo_id"),
                        item.get("serial") or ""
                    )

                    if clave not in neto:

                        neto[clave] = {
                            "producto_id":
                                item["producto_id"],

                            "codigo":
                                item["codigo"],

                            "nombre":
                                item["producto_nombre"],

                            "descripcion":
                                item.get("descripcion"),

                            "unidad":
                                item.get("unidad")
                                or "UND",

                            "unidad_nombre":
                                item.get("unidad_nombre"),

                            "modelo_id":
                                item.get("modelo_id"),

                            "modelo":
                                item.get("modelo_nombre")
                                or "—",

                            "marca_id":
                                item.get("marca_id"),

                            "marca":
                                item.get("marca_nombre")
                                or "—",

                            "serial":
                                item.get("serial")
                                or "—",

                            "salidas":
                                0,

                            "devuelto":
                                0,

                            "neto":
                                0
                        }

                    neto[clave]["salidas"] += (
                        item["cantidad"]
                    )

                    neto[clave]["neto"] += (
                        item["cantidad"]
                    )


            # =================================================
            # PROCESAR DEVOLUCIONES
            # =================================================

            for devolucion in devoluciones:

                if devolucion["estado"] != "ACTIVA":
                    continue

                for item in devolucion["detalle"]:

                    clave = (
                        item["producto_id"],
                        item.get("modelo_id"),
                        item.get("serial") or ""
                    )

                    if clave in neto:

                        neto[clave]["devuelto"] += (
                            item["cantidad"]
                        )

                        neto[clave]["neto"] -= (
                            item["cantidad"]
                        )

                    else:

                        neto[clave] = {

                            "producto_id":
                                item["producto_id"],

                            "codigo":
                                item["codigo"],

                            "nombre":
                                item["producto_nombre"],

                            "descripcion":
                                item.get("descripcion"),

                            "unidad":
                                item.get("unidad")
                                or "UND",

                            "unidad_nombre":
                                item.get("unidad_nombre"),

                            "modelo_id":
                                item.get("modelo_id"),

                            "modelo":
                                item.get("modelo_nombre")
                                or "—",

                            "marca_id":
                                item.get("marca_id"),

                            "marca":
                                item.get("marca_nombre")
                                or "—",

                            "serial":
                                item.get("serial")
                                or "—",

                            "salidas":
                                0,

                            "devuelto":
                                item["cantidad"],

                            "neto":
                                -item["cantidad"]
                        }


    except Exception as error:

        # Mostrar el error en la consola durante desarrollo.
        print(
            "ERROR EN CONSOLIDADO:",
            repr(error)
        )

        return jsonify({
            "error": "Error al consultar el consolidado",
            "detalle": str(error)
        }), 500

    finally:

        conn.close()


    # ========================================================
    # RESPUESTA FINAL
    # ========================================================

    return jsonify({

        "destino":
            destino,

        "salidas":
            salidas,

        "devoluciones":
            devoluciones,

        "resumen":
            list(neto.values())
    })