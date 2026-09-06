# ============================================================
# traslados.py — Traslados entre sedes
# PostgreSQL
#
# ROLES:
#   admin     → crear, consultar, recibir y anular
#   sede      → crear desde su sede, consultar y recibir
#               traslados destinados a su sede
#   consulta  → solamente consultar
#
# IMPORTANTE:
# El inventario NO se modifica directamente desde Flask.
#
# Al CREAR:
#   PENDIENTE
#
# Al RECIBIR:
#   PostgreSQL ejecuta el trigger:
#   procesar_traslado_recibido()
#
# Al ANULAR:
#   PostgreSQL ejecuta el trigger:
#   revertir_traslado_anulado()
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt,
    get_jwt_identity
)

from database import get_connection


traslados_bp = Blueprint(
    "traslados",
    __name__
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_sede_actual():

    claims = get_jwt()

    if claims.get("rol") == "admin":

        return request.args.get(
            "sede_id",
            type=int
        )

    return claims.get("sede_id")


def usuario_puede_ver_traslado(traslado):

    claims = get_jwt()

    rol = claims.get("rol")
    sede_id = claims.get("sede_id")

    if rol == "admin":
        return True

    if sede_id is None:
        return False

    return (
        traslado["sede_origen_id"] == sede_id
        or traslado["sede_destino_id"] == sede_id
    )


# ============================================================
# GET /api/traslados/
# LISTAR TRASLADOS
# ============================================================

@traslados_bp.route("/", methods=["GET"])
@jwt_required()
def listar_traslados():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            if sede_id is None:

                cursor.execute("""
                    SELECT
                        t.id,
                        t.numero_documento,

                        t.sede_origen_id,
                        t.sede_destino_id,

                        t.observaciones,
                        t.estado,

                        t.usuario_creador_id,
                        t.usuario_recibido_id,

                        t.fecha_creacion,
                        t.fecha_recepcion,

                        t.fecha_anulacion,
                        t.anulado_por,
                        t.motivo_anulacion,

                        so.nombre
                            AS sede_origen_nombre,

                        so.ciudad
                            AS sede_origen_ciudad,

                        sd.nombre
                            AS sede_destino_nombre,

                        sd.ciudad
                            AS sede_destino_ciudad,

                        uc.nombre
                            AS creador_nombre,

                        ur.nombre
                            AS recibido_nombre,

                        COUNT(dt.id)
                            AS total_items

                    FROM traslados t

                    LEFT JOIN detalle_traslados dt
                        ON dt.traslado_id = t.id

                    LEFT JOIN sedes so
                        ON so.id = t.sede_origen_id

                    LEFT JOIN sedes sd
                        ON sd.id = t.sede_destino_id

                    LEFT JOIN usuarios uc
                        ON uc.id = t.usuario_creador_id

                    LEFT JOIN usuarios ur
                        ON ur.id = t.usuario_recibido_id

                    GROUP BY
                        t.id,
                        so.nombre,
                        so.ciudad,
                        sd.nombre,
                        sd.ciudad,
                        uc.nombre,
                        ur.nombre

                    ORDER BY
                        t.fecha_creacion DESC
                """)

            else:

                cursor.execute("""
                    SELECT
                        t.id,
                        t.numero_documento,

                        t.sede_origen_id,
                        t.sede_destino_id,

                        t.observaciones,
                        t.estado,

                        t.usuario_creador_id,
                        t.usuario_recibido_id,

                        t.fecha_creacion,
                        t.fecha_recepcion,

                        t.fecha_anulacion,
                        t.anulado_por,
                        t.motivo_anulacion,

                        so.nombre
                            AS sede_origen_nombre,

                        so.ciudad
                            AS sede_origen_ciudad,

                        sd.nombre
                            AS sede_destino_nombre,

                        sd.ciudad
                            AS sede_destino_ciudad,

                        uc.nombre
                            AS creador_nombre,

                        ur.nombre
                            AS recibido_nombre,

                        COUNT(dt.id)
                            AS total_items

                    FROM traslados t

                    LEFT JOIN detalle_traslados dt
                        ON dt.traslado_id = t.id

                    LEFT JOIN sedes so
                        ON so.id = t.sede_origen_id

                    LEFT JOIN sedes sd
                        ON sd.id = t.sede_destino_id

                    LEFT JOIN usuarios uc
                        ON uc.id = t.usuario_creador_id

                    LEFT JOIN usuarios ur
                        ON ur.id = t.usuario_recibido_id

                    WHERE
                        t.sede_origen_id = %s
                        OR t.sede_destino_id = %s

                    GROUP BY
                        t.id,
                        so.nombre,
                        so.ciudad,
                        sd.nombre,
                        sd.ciudad,
                        uc.nombre,
                        ur.nombre

                    ORDER BY
                        t.fecha_creacion DESC
                """, (
                    sede_id,
                    sede_id
                ))

            traslados = [
                dict(item)
                for item in cursor.fetchall()
            ]

    finally:

        conn.close()

    return jsonify(traslados)


# ============================================================
# GET /api/traslados/<id>
# DETALLE DEL TRASLADO
# ============================================================

@traslados_bp.route(
    "/<int:id>",
    methods=["GET"]
)
@jwt_required()
def obtener_traslado(id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

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

                    t.fecha_anulacion,
                    t.anulado_por,
                    t.motivo_anulacion,

                    so.nombre
                        AS sede_origen_nombre,

                    so.ciudad
                        AS sede_origen_ciudad,

                    sd.nombre
                        AS sede_destino_nombre,

                    sd.ciudad
                        AS sede_destino_ciudad,

                    uc.nombre
                        AS creador_nombre,

                    ur.nombre
                        AS recibido_nombre,

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
            """, (id,))

            traslado = cursor.fetchone()

            if not traslado:

                return jsonify({
                    "error": "Traslado no encontrado"
                }), 404

            if not usuario_puede_ver_traslado(
                traslado
            ):

                return jsonify({
                    "error": "No autorizado"
                }), 403

            # ------------------------------------------------
            # Detalle
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    dt.id,
                    dt.producto_id,
                    dt.equipo_id,
                    dt.cantidad,
                    dt.observaciones,

                    p.codigo,
                    p.nombre AS producto_nombre,
                    p.descripcion,

                    un.codigo AS unidad,
                    un.nombre AS unidad_nombre,

                    p.requiere_serial,

                    mo.nombre
                        AS modelo_nombre,

                    ma.id
                        AS marca_id,

                    ma.nombre
                        AS marca_nombre,

                    e.serial
                        AS equipo_serial,

                    e.estado
                        AS equipo_estado,

                    e.condicion
                        AS equipo_condicion

                FROM detalle_traslados dt

                INNER JOIN productos p
                    ON p.id = dt.producto_id

                LEFT JOIN equipos e
                    ON e.id = dt.equipo_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                LEFT JOIN modelos mo
                    ON mo.id = p.modelo_id

                LEFT JOIN marcas ma
                    ON ma.id = mo.marca_id

                WHERE dt.traslado_id = %s

                ORDER BY dt.id
            """, (id,))

            detalle = [
                dict(item)
                for item in cursor.fetchall()
            ]

    finally:

        conn.close()

    resultado = dict(traslado)

    resultado["detalle"] = detalle

    return jsonify(resultado)


# ============================================================
# POST /api/traslados/
# CREAR TRASLADO
# ============================================================

@traslados_bp.route(
    "/",
    methods=["POST"]
)
@jwt_required()
def crear_traslado():

    claims = get_jwt()

    rol = claims.get("rol")
    sede_usuario_id = claims.get("sede_id")

    datos = request.json or {}

    # --------------------------------------------------------
    # PERMISOS
    # --------------------------------------------------------

    if rol not in (
        "admin",
        "sede"
    ):

        return jsonify({
            "error": (
                "No tienes permisos para crear traslados"
            )
        }), 403

    sede_origen_id = datos.get(
        "sede_origen_id"
    )

    sede_destino_id = datos.get(
        "sede_destino_id"
    )

    detalle = datos.get(
        "detalle"
    )

    # --------------------------------------------------------
    # SEDE ORIGEN
    # --------------------------------------------------------

    if rol == "sede":

        if not sede_usuario_id:

            return jsonify({
                "error": (
                    "El usuario no tiene una sede asignada"
                )
            }), 403

        if not sede_origen_id:

            sede_origen_id = sede_usuario_id

        if int(sede_origen_id) != int(
            sede_usuario_id
        ):

            return jsonify({
                "error": (
                    "Solo puedes crear traslados "
                    "desde tu propia sede"
                )
            }), 403

    # --------------------------------------------------------
    # VALIDACIONES
    # --------------------------------------------------------

    if not sede_origen_id or not sede_destino_id:

        return jsonify({
            "error": (
                "Debe seleccionar sede de origen "
                "y sede de destino"
            )
        }), 400

    sede_origen_id = int(
        sede_origen_id
    )

    sede_destino_id = int(
        sede_destino_id
    )

    if sede_origen_id == sede_destino_id:

        return jsonify({
            "error": (
                "La sede de origen y destino "
                "no pueden ser iguales"
            )
        }), 400

    if not detalle or len(detalle) == 0:

        return jsonify({
            "error": (
                "Debe agregar al menos un producto"
            )
        }), 400

    usuario_id = int(
        get_jwt_identity()
    )

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Verificar sedes
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    nombre,
                    ciudad
                FROM sedes
                WHERE id = %s
                  AND activa = TRUE
            """, (sede_origen_id,))

            sede_origen = cursor.fetchone()

            if not sede_origen:

                raise ValueError(
                    (
                        "La sede de origen "
                        "no existe o está inactiva"
                    )
                )

            cursor.execute("""
                SELECT
                    id,
                    nombre,
                    ciudad
                FROM sedes
                WHERE id = %s
                  AND activa = TRUE
            """, (sede_destino_id,))

            sede_destino = cursor.fetchone()

            if not sede_destino:

                raise ValueError(
                    (
                        "La sede de destino "
                        "no existe o está inactiva"
                    )
                )

            # ------------------------------------------------
            # Generar documento
            #
            # Se genera dentro de la aplicación.
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    COUNT(*) AS cantidad
                FROM traslados
                WHERE fecha_creacion::date =
                      CURRENT_DATE
            """)

            consecutivo = (
                cursor.fetchone()["cantidad"]
                + 1
            )

            numero_documento = (
                f"TR-"
                f"{__import__('datetime').datetime.now().strftime('%Y%m%d')}"
                f"-{consecutivo:04d}"
            )

            # ------------------------------------------------
            # Validar productos
            # ------------------------------------------------

            productos_validos = []

            for item in detalle:

                producto_id = item.get(
                    "producto_id"
                )

                cantidad = item.get(
                    "cantidad"
                )

                equipo_id = item.get(
                    "equipo_id"
                )

                if not producto_id:

                    raise ValueError(
                        (
                            "Cada detalle debe tener "
                            "producto_id"
                        )
                    )

                try:

                    cantidad = int(
                        cantidad
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    raise ValueError(
                        (
                            "La cantidad debe ser "
                            "un número entero"
                        )
                    )

                if cantidad <= 0:

                    raise ValueError(
                        (
                            "La cantidad debe ser "
                            "mayor que cero"
                        )
                    )

                # --------------------------------------------
                # Producto
                # --------------------------------------------

                cursor.execute("""
                    SELECT
                        p.id,
                        p.codigo,
                        p.nombre,
                        p.sede_id,
                        p.requiere_serial,

                        COALESCE(
                            i.cantidad,
                            0
                        ) AS stock

                    FROM productos p

                    LEFT JOIN inventario i
                        ON i.producto_id = p.id
                       AND i.sede_id = p.sede_id

                    WHERE p.id = %s
                    FOR UPDATE OF p
                """, (producto_id,))

                producto = cursor.fetchone()

                if not producto:

                    raise ValueError(
                        (
                            f"Producto {producto_id} "
                            "no encontrado"
                        )
                    )

                if producto["sede_id"] != (
                    sede_origen_id
                ):

                    raise ValueError(
                        (
                            f'El producto '
                            f'"{producto["nombre"]}" '
                            "no pertenece a la "
                            "sede de origen"
                        )
                    )

                # --------------------------------------------
                # Verificar inventario disponible
                #
                # NO se modifica aquí.
                # --------------------------------------------

                if producto["stock"] < cantidad:

                    raise ValueError(
                        (
                            f'Stock insuficiente para '
                            f'"{producto["nombre"]}". '
                            f'Disponible: '
                            f'{producto["stock"]}. '
                            f'Solicitado: '
                            f'{cantidad}.'
                        )
                    )

                # --------------------------------------------
                # Producto serializado
                # --------------------------------------------

                if (
                    producto["requiere_serial"]
                    and not equipo_id
                ):

                    raise ValueError(
                        (
                            f'El producto '
                            f'"{producto["nombre"]}" '
                            "requiere número de serie"
                        )
                    )

                # --------------------------------------------
                # Equipo / serial
                # --------------------------------------------

                if equipo_id:

                    cursor.execute("""
                        SELECT
                            id,
                            producto_id,
                            sede_id,
                            serial,
                            estado,
                            condicion

                        FROM equipos

                        WHERE id = %s

                        FOR UPDATE
                    """, (equipo_id,))

                    equipo = cursor.fetchone()

                    if not equipo:

                        raise ValueError(
                            (
                                f"Equipo {equipo_id} "
                                "no encontrado"
                            )
                        )

                    if equipo["producto_id"] != (
                        producto_id
                    ):

                        raise ValueError(
                            (
                                "El equipo no pertenece "
                                "al producto seleccionado"
                            )
                        )

                    if equipo["sede_id"] != (
                        sede_origen_id
                    ):

                        raise ValueError(
                            (
                                "El equipo no pertenece "
                                "a la sede de origen"
                            )
                        )

                    if equipo["estado"] in (
                        "EN_TRANSITO",
                        "MANTENIMIENTO",
                        "DADO_DE_BAJA"
                    ):

                        raise ValueError(
                            (
                                f'El equipo con serial '
                                f'"{equipo["serial"]}" '
                                f'no puede trasladarse '
                                f'porque está en estado '
                                f'{equipo["estado"]}'
                            )
                        )

                productos_validos.append({
                    "producto_id": producto_id,
                    "cantidad": cantidad,
                    "equipo_id": equipo_id,
                    "observaciones": item.get(
                        "observaciones",
                        ""
                    ).strip()
                })

            # ------------------------------------------------
            # Crear traslado
            #
            # IMPORTANTE:
            # El inventario NO cambia aquí.
            # ------------------------------------------------

            cursor.execute("""
                INSERT INTO traslados (
                    numero_documento,
                    sede_origen_id,
                    sede_destino_id,
                    usuario_creador_id,
                    estado,
                    observaciones
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    'PENDIENTE',
                    %s
                )
                RETURNING id
            """, (
                numero_documento,
                sede_origen_id,
                sede_destino_id,
                usuario_id,
                datos.get(
                    "observaciones",
                    ""
                ).strip()
            ))

            traslado_id = cursor.fetchone()["id"]

            # ------------------------------------------------
            # Detalles
            # ------------------------------------------------

            for item in productos_validos:

                cursor.execute("""
                    INSERT INTO detalle_traslados (
                        traslado_id,
                        producto_id,
                        equipo_id,
                        cantidad,
                        observaciones
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    traslado_id,
                    item["producto_id"],
                    item["equipo_id"],
                    item["cantidad"],
                    item["observaciones"]
                ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:

        conn.close()

    return jsonify({
        "mensaje": (
            "Traslado creado correctamente"
        ),
        "id": traslado_id,
        "numero_documento": numero_documento,
        "estado": "PENDIENTE"
    }), 201


# ============================================================
# PUT /api/traslados/<id>/recibir
#
# RECIBIR TRASLADO
#
# El trigger PostgreSQL hará el trabajo de inventario,
# producto destino, equipo e historial.
# ============================================================

@traslados_bp.route(
    "/<int:id>/recibir",
    methods=["PUT"]
)
@jwt_required()
def recibir_traslado(id):

    claims = get_jwt()

    rol = claims.get("rol")
    sede_usuario_id = claims.get(
        "sede_id"
    )

    usuario_id = int(
        get_jwt_identity()
    )

    # --------------------------------------------------------
    # Consulta no puede recibir
    # --------------------------------------------------------

    if rol == "consulta":

        return jsonify({
            "error": (
                "El usuario de consulta "
                "no puede recibir traslados"
            )
        }), 403

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Bloquear traslado
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    sede_origen_id,
                    sede_destino_id,
                    estado

                FROM traslados

                WHERE id = %s

                FOR UPDATE
            """, (id,))

            traslado = cursor.fetchone()

            if not traslado:

                return jsonify({
                    "error": "Traslado no encontrado"
                }), 404

            # ------------------------------------------------
            # Solo la sede destino puede recibir
            # Admin puede recibir cualquiera.
            # ------------------------------------------------

            if rol != "admin":

                if (
                    not sede_usuario_id
                    or int(sede_usuario_id)
                    != int(
                        traslado[
                            "sede_destino_id"
                        ]
                    )
                ):

                    return jsonify({
                        "error": (
                            "Solo la sede de destino "
                            "puede recibir este traslado"
                        )
                    }), 403

            # ------------------------------------------------
            # Estado
            # ------------------------------------------------

            if traslado["estado"] != "PENDIENTE":

                return jsonify({
                    "error": (
                        "El traslado no está pendiente. "
                        f"Estado actual: "
                        f"{traslado['estado']}"
                    )
                }), 400

            # ------------------------------------------------
            # Verificar que tenga detalles
            # ------------------------------------------------

            cursor.execute("""
                SELECT COUNT(*) AS cantidad
                FROM detalle_traslados
                WHERE traslado_id = %s
            """, (id,))

            cantidad_items = cursor.fetchone()[
                "cantidad"
            ]

            if cantidad_items == 0:

                return jsonify({
                    "error": (
                        "El traslado no tiene productos"
                    )
                }), 400

            # ------------------------------------------------
            # Cambiar estado
            #
            # AQUÍ SE DISPARA EL TRIGGER:
            #
            # procesar_traslado_recibido()
            #
            # El trigger:
            #   - descuenta origen
            #   - suma destino
            #   - mueve equipos
            #   - registra historial
            #   - establece fecha_recepcion
            # ------------------------------------------------

            cursor.execute("""
                UPDATE traslados
                SET
                    estado = 'RECIBIDO',
                    usuario_recibido_id = %s,
                    fecha_recepcion =
                        CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                usuario_id,
                id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:

        conn.close()

    return jsonify({
        "mensaje": (
            "Traslado recibido correctamente"
        ),
        "estado": "RECIBIDO"
    })


# ============================================================
# PUT /api/traslados/<id>/anular
#
# SOLO ADMIN
#
# El trigger PostgreSQL revierte:
#   destino → origen
#   equipo → origen
#   historial
# ============================================================

@traslados_bp.route(
    "/<int:id>/anular",
    methods=["PUT"]
)
@jwt_required()
def anular_traslado(id):

    claims = get_jwt()

    if claims.get("rol") != "admin":

        return jsonify({
            "error": (
                "Solo el administrador "
                "puede anular traslados"
            )
        }), 403

    datos = request.json or {}

    motivo = datos.get(
        "motivo_anulacion",
        ""
    ).strip()

    if not motivo:

        return jsonify({
            "error": (
                "El motivo de anulación "
                "es obligatorio"
            )
        }), 400

    usuario_id = int(
        get_jwt_identity()
    )

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    sede_origen_id,
                    sede_destino_id,
                    estado

                FROM traslados

                WHERE id = %s

                FOR UPDATE
            """, (id,))

            traslado = cursor.fetchone()

            if not traslado:

                return jsonify({
                    "error": (
                        "Traslado no encontrado"
                    )
                }), 404

            if traslado["estado"] == "ANULADO":

                return jsonify({
                    "error": (
                        "El traslado ya está anulado"
                    )
                }), 400

            # ------------------------------------------------
            # Solo se permite anular un traslado que ya fue
            # recibido o que está pendiente.
            #
            # El trigger se encargará de actuar según estado.
            # ------------------------------------------------

            if traslado["estado"] not in (
                "PENDIENTE",
                "RECIBIDO"
            ):

                return jsonify({
                    "error": (
                        "El traslado no puede ser anulado "
                        f"desde el estado "
                        f"{traslado['estado']}"
                    )
                }), 400

            # ------------------------------------------------
            # Anular
            # ------------------------------------------------

            cursor.execute("""
                UPDATE traslados
                SET
                    estado = 'ANULADO',
                    anulado_por = %s,
                    fecha_anulacion =
                        CURRENT_TIMESTAMP,
                    motivo_anulacion = %s
                WHERE id = %s
            """, (
                usuario_id,
                motivo,
                id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:

        conn.close()

    return jsonify({
        "mensaje": (
            "Traslado anulado correctamente"
        ),
        "estado": "ANULADO"
    })