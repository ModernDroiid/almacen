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

from datetime import datetime

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

    rol = claims.get("rol")

    # ------------------------------------------------------
    # Admin y consulta siempre pueden elegir la sede que
    # quieran consultar con ?sede_id (o ninguna, para ver
    # todas), tengan o no una sede propia asignada — igual
    # que en productos.py y consolidado.py.
    # ------------------------------------------------------

    if rol == "admin" or rol == "consulta":

        return request.args.get(
            "sede_id",
            type=int
        )

    # ------------------------------------------------------
    # Sede: siempre trabaja con su propia sede.
    # ------------------------------------------------------

    return claims.get("sede_id")


def usuario_puede_ver_traslado(traslado):

    claims = get_jwt()

    rol = claims.get("rol")

    # ------------------------------------------------------
    # Admin y consulta pueden ver cualquier traslado, tengan
    # o no una sede propia asignada — igual que en
    # obtener_sede_actual(), para que este chequeo y el
    # LISTADO (listar_traslados) se comporten igual y no
    # bloqueen con 403 un traslado que el usuario sí podía
    # ver en la lista.
    # ------------------------------------------------------

    if rol == "admin" or rol == "consulta":
        return True

    sede_id = claims.get("sede_id")

    return (
        traslado["sede_origen_id"] == sede_id
        or traslado["sede_destino_id"] == sede_id
    )


# ============================================================
# GET /api/traslados/
# LISTAR TRASLADOS
# ============================================================

@traslados_bp.route(
    "/",
    methods=["GET"]
)
@jwt_required()
def listar_traslados():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            if sede_id is None:

                # ------------------------------------------------
                # ADMIN → ve todos
                # ------------------------------------------------

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

                        so.nombre AS sede_origen_nombre,
                        so.ciudad AS sede_origen_ciudad,

                        sd.nombre AS sede_destino_nombre,
                        sd.ciudad AS sede_destino_ciudad,

                        uc.nombre AS creador_nombre,
                        ur.nombre AS recibido_nombre,

                        COUNT(dt.id) AS total_items

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

                # ------------------------------------------------
                # SEDE → ve traslados donde participa
                # ------------------------------------------------

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

                        so.nombre AS sede_origen_nombre,
                        so.ciudad AS sede_origen_ciudad,

                        sd.nombre AS sede_destino_nombre,
                        sd.ciudad AS sede_destino_ciudad,

                        uc.nombre AS creador_nombre,
                        ur.nombre AS recibido_nombre,

                        COUNT(dt.id) AS total_items

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

            # ------------------------------------------------
            # CABECERA
            # ------------------------------------------------

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

                    t.firma_entrega_base64,
                    t.firma_recibe_base64,

                    so.nombre AS sede_origen_nombre,
                    so.ciudad AS sede_origen_ciudad,

                    sd.nombre AS sede_destino_nombre,
                    sd.ciudad AS sede_destino_ciudad,

                    uc.nombre AS creador_nombre,
                    ur.nombre AS recibido_nombre,

                    ua.nombre AS anulado_por_nombre

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

                WHERE
                    t.id = %s
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
            # DETALLE
            #
            # Para equipos serializados, el modelo real se
            # obtiene desde equipos.modelo_id.
            # La marca se obtiene desde modelos → marcas.
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

                    e.serial AS equipo_serial,
                    e.estado AS equipo_estado,
                    e.condicion AS equipo_condicion,

                    e.modelo_id AS equipo_modelo_id,

                    mo.nombre AS modelo_nombre,

                    ma.id AS marca_id,
                    ma.nombre AS marca_nombre

                FROM detalle_traslados dt

                INNER JOIN productos p
                    ON p.id = dt.producto_id

                LEFT JOIN equipos e
                    ON e.id = dt.equipo_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                LEFT JOIN modelos mo
                    ON mo.id = COALESCE(
                        e.modelo_id,
                        p.modelo_id
                    )

                LEFT JOIN marcas ma
                    ON ma.id = mo.marca_id

                WHERE
                    dt.traslado_id = %s

                ORDER BY
                    dt.id
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

    if not detalle:

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
            # VERIFICAR SEDE ORIGEN
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    nombre,
                    ciudad
                FROM sedes
                WHERE
                    id = %s
                    AND activa = TRUE
            """, (
                sede_origen_id,
            ))

            sede_origen = cursor.fetchone()

            if not sede_origen:

                raise ValueError(
                    "La sede de origen no existe o está inactiva"
                )

            # ------------------------------------------------
            # VERIFICAR SEDE DESTINO
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    nombre,
                    ciudad
                FROM sedes
                WHERE
                    id = %s
                    AND activa = TRUE
            """, (
                sede_destino_id,
            ))

            sede_destino = cursor.fetchone()

            if not sede_destino:

                raise ValueError(
                    "La sede de destino no existe o está inactiva"
                )

            # ------------------------------------------------
            # GENERAR DOCUMENTO
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    COUNT(*) AS cantidad
                FROM traslados
                WHERE
                    fecha_creacion::date =
                    CURRENT_DATE
            """)

            consecutivo = (
                cursor.fetchone()["cantidad"]
                + 1
            )

            numero_documento = (
                f"TR-"
                f"{datetime.now().strftime('%Y%m%d')}-"
                f"{consecutivo:04d}"
            )

            detalles_finales = []

            # =================================================
            # VALIDAR PRODUCTOS
            # =================================================

            for item in detalle:

                producto_id = item.get(
                    "producto_id"
                )

                if not producto_id:

                    raise ValueError(
                        "Cada detalle debe tener producto_id"
                    )

                # ------------------------------------------------
                # BUSCAR PRODUCTO
                # ------------------------------------------------

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

                    WHERE
                        p.id = %s

                    FOR UPDATE OF p
                """, (
                    producto_id,
                ))

                producto = cursor.fetchone()

                if not producto:

                    raise ValueError(
                        (
                            f"Producto {producto_id} "
                            "no encontrado"
                        )
                    )

                # ------------------------------------------------
                # VERIFICAR SEDE
                # ------------------------------------------------

                if producto["sede_id"] != (
                    sede_origen_id
                ):

                    raise ValueError(
                        (
                            f'El producto '
                            f'"{producto["nombre"]}" '
                            "no pertenece a la sede de origen"
                        )
                    )

                # =================================================
                # PRODUCTO SERIALIZADO
                # =================================================

                if producto["requiere_serial"]:

                    unidades = (
                        item.get("unidades")
                        or []
                    )

                    if not unidades:

                        raise ValueError(
                            (
                                f'El producto '
                                f'"{producto["nombre"]}" '
                                "requiere seleccionar "
                                "los equipos serializados"
                            )
                        )

                    if len(unidades) > (
                        producto["stock"]
                    ):

                        raise ValueError(
                            (
                                f'No hay suficientes '
                                f'unidades de '
                                f'"{producto["nombre"]}"'
                            )
                        )

                    equipos_usados = set()

                    for unidad_item in unidades:

                        # ------------------------------------------------
                        # ID DEL EQUIPO
                        # ------------------------------------------------

                        equipo_id = unidad_item.get(
                            "equipo_id"
                        )

                        if not equipo_id:

                            raise ValueError(
                                (
                                    f'Debe seleccionar '
                                    f'un equipo para '
                                    f'"{producto["nombre"]}"'
                                )
                            )

                        equipo_id = int(
                            equipo_id
                        )

                        # ------------------------------------------------
                        # EVITAR EQUIPO REPETIDO
                        # ------------------------------------------------

                        if (
                            equipo_id
                            in equipos_usados
                        ):

                            raise ValueError(
                                (
                                    "No puedes seleccionar "
                                    "el mismo equipo más "
                                    "de una vez."
                                )
                            )

                        equipos_usados.add(
                            equipo_id
                        )

                        # ------------------------------------------------
                        # BUSCAR EQUIPO
                        # ------------------------------------------------

                        cursor.execute("""
                            SELECT
                                id,
                                producto_id,
                                sede_id,
                                serial,
                                estado,
                                condicion,
                                modelo_id

                            FROM equipos

                            WHERE
                                id = %s

                            FOR UPDATE
                        """, (
                            equipo_id,
                        ))

                        equipo = cursor.fetchone()

                        if not equipo:

                            raise ValueError(
                                (
                                    f"Equipo {equipo_id} "
                                    "no encontrado"
                                )
                            )

                        # ------------------------------------------------
                        # VALIDAR PRODUCTO
                        # ------------------------------------------------

                        if equipo["producto_id"] != (
                            producto_id
                        ):

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{equipo["serial"]}" '
                                    "no pertenece al "
                                    "producto seleccionado"
                                )
                            )

                        # ------------------------------------------------
                        # VALIDAR SEDE
                        # ------------------------------------------------

                        if equipo["sede_id"] != (
                            sede_origen_id
                        ):

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{equipo["serial"]}" '
                                    "no pertenece a la "
                                    "sede de origen"
                                )
                            )

                        # ------------------------------------------------
                        # VALIDAR ESTADO
                        # ------------------------------------------------

                        if equipo["estado"] != (
                            "DISPONIBLE"
                        ):

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{equipo["serial"]}" '
                                    "no está disponible. "
                                    f'Estado actual: '
                                    f'{equipo["estado"]}'
                                )
                            )

                        # ------------------------------------------------
                        # AGREGAR DETALLE
                        # ------------------------------------------------

                        detalles_finales.append({
                            "producto_id":
                                producto_id,

                            "equipo_id":
                                equipo_id,

                            "cantidad":
                                1,

                            "observaciones":
                                item.get(
                                    "observaciones",
                                    ""
                                ).strip()
                        })

                # =================================================
                # PRODUCTO NORMAL
                # =================================================

                else:

                    try:

                        cantidad = int(
                            item.get(
                                "cantidad"
                            )
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

                    if cantidad > (
                        producto["stock"]
                    ):

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

                    detalles_finales.append({
                        "producto_id":
                            producto_id,

                        "equipo_id":
                            None,

                        "cantidad":
                            cantidad,

                        "observaciones":
                            item.get(
                                "observaciones",
                                ""
                            ).strip()
                    })

            # =================================================
            # CREAR CABECERA
            # =================================================

            cursor.execute("""
                INSERT INTO traslados (
                    numero_documento,
                    sede_origen_id,
                    sede_destino_id,
                    usuario_creador_id,
                    estado,
                    observaciones,
                    firma_entrega_base64
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    'PENDIENTE',
                    %s,
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
                ).strip(),
                datos.get("firma_entrega_base64") or None
            ))

            traslado_id = (
                cursor.fetchone()["id"]
            )

            # =================================================
            # INSERTAR DETALLES
            # =================================================

            for item in detalles_finales:

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
        "mensaje":
            "Traslado creado correctamente",

        "id":
            traslado_id,

        "numero_documento":
            numero_documento,

        "estado":
            "PENDIENTE"
    }), 201


# ============================================================
# PUT /api/traslados/<id>/recibir
# RECIBIR TRASLADO
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

    # ------------------------------------------------
    # CONSULTA NO PUEDE RECIBIR
    # ------------------------------------------------

    if rol == "consulta":

        return jsonify({
            "error": (
                "El usuario de consulta "
                "no puede recibir traslados"
            )
        }), 403

    # ------------------------------------------------
    # FIRMA DE QUIEN RECIBE
    #
    # Firma digital de quien recibe el traslado en la
    # sede destino, capturada al momento de confirmar
    # la recepción. Se guarda como imagen PNG en base64.
    # Es opcional: si el dispositivo de firma no está
    # disponible, el traslado se recibe igual sin firma.
    # ------------------------------------------------

    datos = request.get_json(silent=True) or {}

    firma_recibe = datos.get("firma_recibe_base64") or None

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # BLOQUEAR TRASLADO
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    sede_origen_id,
                    sede_destino_id,
                    estado

                FROM traslados

                WHERE
                    id = %s

                FOR UPDATE
            """, (
                id,
            ))

            traslado = cursor.fetchone()

            if not traslado:

                return jsonify({
                    "error":
                        "Traslado no encontrado"
                }), 404

            # ------------------------------------------------
            # PERMISOS DE RECEPCIÓN
            # ------------------------------------------------

            if rol != "admin":

                if (
                    not sede_usuario_id
                    or
                    int(sede_usuario_id)
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
            # ESTADO
            # ------------------------------------------------

            if traslado["estado"] != (
                "PENDIENTE"
            ):

                return jsonify({
                    "error": (
                        "El traslado no está pendiente. "
                        f"Estado actual: "
                        f'{traslado["estado"]}'
                    )
                }), 400

            # ------------------------------------------------
            # VERIFICAR DETALLES
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    COUNT(*) AS cantidad

                FROM detalle_traslados

                WHERE
                    traslado_id = %s
            """, (
                id,
            ))

            cantidad_items = (
                cursor.fetchone()["cantidad"]
            )

            if cantidad_items == 0:

                return jsonify({
                    "error": (
                        "El traslado no tiene productos"
                    )
                }), 400

            # ------------------------------------------------
            # RECIBIR
            #
            # El trigger de PostgreSQL realiza:
            #
            # - descuento de origen
            # - aumento de destino
            # - movimiento de equipos
            # - historial
            # ------------------------------------------------

            cursor.execute("""
                UPDATE traslados
                SET
                    estado = 'RECIBIDO',
                    usuario_recibido_id = %s,
                    fecha_recepcion =
                        CURRENT_TIMESTAMP,
                    firma_recibe_base64 = %s
                WHERE
                    id = %s
            """, (
                usuario_id,
                firma_recibe,
                id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error":
                str(e)
        }), 400

    finally:

        conn.close()

    return jsonify({
        "mensaje":
            "Traslado recibido correctamente",

        "estado":
            "RECIBIDO"
    })


# ============================================================
# PUT /api/traslados/<id>/anular
# SOLO ADMIN
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

                WHERE
                    id = %s

                FOR UPDATE
            """, (
                id,
            ))

            traslado = cursor.fetchone()

            if not traslado:

                return jsonify({
                    "error":
                        "Traslado no encontrado"
                }), 404

            if traslado["estado"] == (
                "ANULADO"
            ):

                return jsonify({
                    "error":
                        "El traslado ya está anulado"
                }), 400

            if traslado["estado"] not in (
                "PENDIENTE",
                "RECIBIDO"
            ):

                return jsonify({
                    "error": (
                        "El traslado no puede ser "
                        "anulado desde el estado "
                        f'{traslado["estado"]}'
                    )
                }), 400

            # ------------------------------------------------
            # ANULAR
            #
            # PostgreSQL ejecutará el trigger
            # correspondiente.
            # ------------------------------------------------

            cursor.execute("""
                UPDATE traslados
                SET
                    estado = 'ANULADO',
                    anulado_por = %s,
                    fecha_anulacion =
                        CURRENT_TIMESTAMP,
                    motivo_anulacion = %s
                WHERE
                    id = %s
            """, (
                usuario_id,
                motivo,
                id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error":
                str(e)
        }), 400

    finally:

        conn.close()

    return jsonify({
        "mensaje":
            "Traslado anulado correctamente",

        "estado":
            "ANULADO"
    })