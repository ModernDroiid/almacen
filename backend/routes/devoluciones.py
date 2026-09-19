# ============================================================
# devoluciones.py — Registro de mercancía que regresa
# al almacén
#
# PostgreSQL
#
# ROLES:
#   admin     → consultar, registrar y anular
#   sede      → consultar y registrar
#   consulta  → solamente consultar
#
# El inventario y los equipos son actualizados mediante
# triggers PostgreSQL.
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt,
    get_jwt_identity
)

from database import get_connection
from utils.auditoria import registrar_auditoria


devoluciones_bp = Blueprint(
    "devoluciones",
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


def usuario_puede_ver_devolucion(devolucion):

    claims = get_jwt()

    rol = claims.get("rol")
    sede_id = claims.get("sede_id")

    if rol == "admin":
        return True

    if rol == "consulta":
        return (
            sede_id is None
            or devolucion["sede_id"] == sede_id
        )

    if rol == "sede":
        return devolucion["sede_id"] == sede_id

    return False


# ============================================================
# GET /api/devoluciones/
# LISTAR DEVOLUCIONES
# ============================================================

@devoluciones_bp.route("/", methods=["GET"])
@jwt_required()
def listar_devoluciones():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            if sede_id is None:

                cursor.execute("""
                    SELECT
                        dv.id,
                        dv.numero_documento,
                        dv.salida_id,
                        dv.motivo,
                        dv.observaciones,
                        dv.fecha,
                        dv.sede_id,
                        dv.estado,
                        dv.fecha_anulacion,
                        dv.motivo_anulacion,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        s.numero_documento AS salida_numero,

                        u.nombre AS usuario_nombre,

                        COUNT(d.id) AS total_items

                    FROM devoluciones dv

                    LEFT JOIN detalle_devoluciones d
                        ON d.devolucion_id = dv.id

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = dv.usuario_id

                    GROUP BY
                        dv.id,
                        dv.numero_documento,
                        dv.salida_id,
                        dv.motivo,
                        dv.observaciones,
                        dv.fecha,
                        dv.sede_id,
                        dv.estado,
                        dv.fecha_anulacion,
                        dv.motivo_anulacion,
                        se.nombre,
                        se.ciudad,
                        s.numero_documento,
                        u.nombre

                    ORDER BY dv.fecha DESC
                """)

            else:

                cursor.execute("""
                    SELECT
                        dv.id,
                        dv.numero_documento,
                        dv.salida_id,
                        dv.motivo,
                        dv.observaciones,
                        dv.fecha,
                        dv.sede_id,
                        dv.estado,
                        dv.fecha_anulacion,
                        dv.motivo_anulacion,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        s.numero_documento AS salida_numero,

                        u.nombre AS usuario_nombre,

                        COUNT(d.id) AS total_items

                    FROM devoluciones dv

                    LEFT JOIN detalle_devoluciones d
                        ON d.devolucion_id = dv.id

                    LEFT JOIN salidas s
                        ON s.id = dv.salida_id

                    LEFT JOIN sedes se
                        ON se.id = dv.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = dv.usuario_id

                    WHERE dv.sede_id = %s

                    GROUP BY
                        dv.id,
                        dv.numero_documento,
                        dv.salida_id,
                        dv.motivo,
                        dv.observaciones,
                        dv.fecha,
                        dv.sede_id,
                        dv.estado,
                        dv.fecha_anulacion,
                        dv.motivo_anulacion,
                        se.nombre,
                        se.ciudad,
                        s.numero_documento,
                        u.nombre

                    ORDER BY dv.fecha DESC
                """, (sede_id,))

            devoluciones = [
                dict(item)
                for item in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(devoluciones)


# ============================================================
# GET /api/devoluciones/<id>
# OBTENER DEVOLUCIÓN
# ============================================================

@devoluciones_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def obtener_devolucion(id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # DATOS PRINCIPALES
            # =================================================

            cursor.execute("""
                SELECT
                    dv.id,
                    dv.numero_documento,
                    dv.salida_id,
                    dv.motivo,
                    dv.observaciones,
                    dv.fecha,
                    dv.sede_id,
                    dv.usuario_id,
                    dv.estado,
                    dv.anulada_por,
                    dv.fecha_anulacion,
                    dv.motivo_anulacion,

                    se.nombre AS sede_nombre,
                    se.ciudad,

                    s.numero_documento AS salida_numero,
                    s.cliente_id,

                    c.nombre AS cliente_nombre,

                    u.nombre AS usuario_nombre,

                    ua.nombre AS anulada_por_nombre

                FROM devoluciones dv

                LEFT JOIN sedes se
                    ON se.id = dv.sede_id

                LEFT JOIN salidas s
                    ON s.id = dv.salida_id

                LEFT JOIN clientes c
                    ON c.id = s.cliente_id

                LEFT JOIN usuarios u
                    ON u.id = dv.usuario_id

                LEFT JOIN usuarios ua
                    ON ua.id = dv.anulada_por

                WHERE dv.id = %s
            """, (id,))

            devolucion = cursor.fetchone()

            if not devolucion:

                return jsonify({
                    "error": "Devolución no encontrada"
                }), 404

            if not usuario_puede_ver_devolucion(
                devolucion
            ):

                return jsonify({
                    "error": (
                        "No tienes permisos para consultar "
                        "esta devolución"
                    )
                }), 403

            # =================================================
            # DETALLE
            #
            # El modelo puede estar en:
            # 1. equipos.modelo_id
            # 2. productos.modelo_id
            #
            # COALESCE toma primero el modelo del equipo.
            # =================================================

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
                    p.requiere_serial,

                    e.serial,
                    e.estado AS equipo_estado,
                    e.condicion AS equipo_condicion,

                    un.codigo AS unidad,
                    un.nombre AS unidad_nombre,

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

                LEFT JOIN equipos e
                    ON e.id = d.equipo_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                LEFT JOIN modelos me
                    ON me.id = e.modelo_id

                LEFT JOIN marcas mae
                    ON mae.id = me.marca_id

                LEFT JOIN modelos mp
                    ON mp.id = p.modelo_id

                LEFT JOIN marcas map
                    ON map.id = mp.marca_id

                WHERE d.devolucion_id = %s

                ORDER BY d.id
            """, (id,))

            detalle = [
                dict(item)
                for item in cursor.fetchall()
            ]

    finally:
        conn.close()

    resultado = dict(devolucion)
    resultado["detalle"] = detalle

    return jsonify(resultado)


# ============================================================
# GET /api/devoluciones/salidas-disponibles
# Salidas que pueden utilizarse para registrar devoluciones.
# ============================================================

@devoluciones_bp.route(
    "/salidas-disponibles",
    methods=["GET"]
)
@jwt_required()
def salidas_disponibles():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            if sede_id is None:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.fecha,
                        s.sede_id,
                        s.estado,
                        s.cliente_id,

                        c.nombre AS cliente_nombre

                    FROM salidas s

                    LEFT JOIN clientes c
                        ON c.id = s.cliente_id

                    WHERE s.estado = 'ACTIVA'

                    ORDER BY s.fecha DESC
                """)

            else:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.fecha,
                        s.sede_id,
                        s.estado,
                        s.cliente_id,

                        c.nombre AS cliente_nombre

                    FROM salidas s

                    LEFT JOIN clientes c
                        ON c.id = s.cliente_id

                    WHERE s.sede_id = %s
                      AND s.estado = 'ACTIVA'

                    ORDER BY s.fecha DESC
                """, (sede_id,))

            salidas = [
                dict(salida)
                for salida in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(salidas)


# ============================================================
# GET /api/devoluciones/salida/<id>/items
# Productos que todavía tienen cantidades pendientes
# por devolver.
# ============================================================

@devoluciones_bp.route(
    "/salida/<int:id>/items",
    methods=["GET"]
)
@jwt_required()
def items_de_salida(id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # VERIFICAR SALIDA
            # =================================================

            cursor.execute("""
                SELECT
                    id,
                    sede_id,
                    estado

                FROM salidas

                WHERE id = %s
            """, (id,))

            salida = cursor.fetchone()

            if not salida:

                return jsonify({
                    "error": "Salida no encontrada"
                }), 404

            # =================================================
            # PERMISOS
            # =================================================

            claims = get_jwt()

            if claims.get("rol") != "admin":

                usuario_sede = claims.get("sede_id")

                if (
                    usuario_sede is not None
                    and int(usuario_sede)
                    != int(salida["sede_id"])
                ):

                    return jsonify({
                        "error": (
                            "No tienes permisos para "
                            "consultar esta salida"
                        )
                    }), 403

            # =================================================
            # ITEMS DE LA SALIDA
            # =================================================

            cursor.execute("""
                SELECT
                    d.id AS detalle_salida_id,

                    d.producto_id,
                    d.equipo_id,
                    d.cantidad,

                    p.codigo,
                    p.nombre,

                    p.requiere_serial,

                    un.codigo AS unidad,
                    un.nombre AS unidad_nombre,

                    e.serial,

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

                ORDER BY d.id
            """, (id,))

            items_salida = cursor.fetchall()

            resultado = []

            for item in items_salida:

                # =============================================
                # PRODUCTO SERIALIZADO
                # =============================================

                if item["requiere_serial"]:

                    if not item["equipo_id"]:
                        continue

                    cursor.execute("""
                        SELECT
                            COALESCE(
                                SUM(dd.cantidad),
                                0
                            ) AS ya_devuelto

                        FROM detalle_devoluciones dd

                        INNER JOIN devoluciones dv
                            ON dv.id = dd.devolucion_id

                        WHERE dv.salida_id = %s
                          AND dd.equipo_id = %s
                          AND dv.estado = 'ACTIVA'
                    """, (
                        id,
                        item["equipo_id"]
                    ))

                    ya_devuelto = cursor.fetchone()[
                        "ya_devuelto"
                    ]

                    if ya_devuelto >= item["cantidad"]:
                        continue

                    fila = dict(item)

                    fila["cantidad_original"] = (
                        item["cantidad"]
                    )

                    fila["ya_devuelto"] = (
                        ya_devuelto
                    )

                    fila["cantidad"] = (
                        item["cantidad"]
                        - ya_devuelto
                    )

                    resultado.append(fila)

                # =============================================
                # PRODUCTO NO SERIALIZADO
                # =============================================

                else:

                    cursor.execute("""
                        SELECT
                            COALESCE(
                                SUM(dd.cantidad),
                                0
                            ) AS ya_devuelto

                        FROM detalle_devoluciones dd

                        INNER JOIN devoluciones dv
                            ON dv.id = dd.devolucion_id

                        WHERE dv.salida_id = %s
                          AND dd.producto_id = %s
                          AND dd.equipo_id IS NULL
                          AND dv.estado = 'ACTIVA'
                    """, (
                        id,
                        item["producto_id"]
                    ))

                    ya_devuelto = cursor.fetchone()[
                        "ya_devuelto"
                    ]

                    pendiente = (
                        item["cantidad"]
                        - ya_devuelto
                    )

                    if pendiente <= 0:
                        continue

                    fila = dict(item)

                    fila["cantidad_original"] = (
                        item["cantidad"]
                    )

                    fila["ya_devuelto"] = (
                        ya_devuelto
                    )

                    fila["cantidad"] = pendiente

                    resultado.append(fila)

    finally:
        conn.close()

    return jsonify(resultado)


# ============================================================
# POST /api/devoluciones/
# CREAR DEVOLUCIÓN
# ============================================================

@devoluciones_bp.route(
    "/",
    methods=["POST"]
)
@jwt_required()
def crear_devolucion():

    claims = get_jwt()
    rol = claims.get("rol")

    datos = request.get_json(silent=True) or {}

    # ========================================================
    # CONSULTA NO PUEDE REGISTRAR
    # ========================================================

    if rol == "consulta":

        return jsonify({
            "error": (
                "El usuario de consulta no puede "
                "registrar devoluciones"
            )
        }), 403

    # ========================================================
    # VALIDACIONES
    # ========================================================

    numero_documento = datos.get(
        "numero_documento",
        ""
    ).strip()

    if not numero_documento:

        return jsonify({
            "error": (
                "El número de documento es obligatorio"
            )
        }), 400

    detalle = datos.get("detalle")

    if not detalle or len(detalle) == 0:

        return jsonify({
            "error": (
                "Debe agregar al menos un producto"
            )
        }), 400

    # ========================================================
    # SEDE
    # ========================================================

    if rol == "admin":

        sede_id = datos.get("sede_id")

        if not sede_id:
            sede_id = claims.get("sede_id")

    else:

        sede_id = claims.get("sede_id")

    if not sede_id:

        return jsonify({
            "error": "Debe seleccionar una sede"
        }), 400

    # ========================================================
    # USUARIO
    # ========================================================

    usuario_id = int(
        get_jwt_identity()
    )

    salida_id = datos.get("salida_id")

    motivo = datos.get(
        "motivo",
        ""
    ).strip()

    observaciones = datos.get(
        "observaciones",
        ""
    ).strip()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # VERIFICAR SEDE
            # =================================================

            cursor.execute("""
                SELECT
                    id,
                    nombre,
                    ciudad

                FROM sedes

                WHERE id = %s
                  AND activa = TRUE
            """, (sede_id,))

            sede = cursor.fetchone()

            if not sede:

                raise ValueError(
                    "La sede no existe o está inactiva"
                )

            # =================================================
            # DOCUMENTO DUPLICADO
            # =================================================

            cursor.execute("""
                SELECT id

                FROM devoluciones

                WHERE numero_documento = %s
            """, (numero_documento,))

            if cursor.fetchone():

                raise ValueError(
                    f'Ya existe una devolución con '
                    f'el número de documento '
                    f'"{numero_documento}"'
                )

            # =================================================
            # VERIFICAR SALIDA
            # =================================================

            if salida_id:

                cursor.execute("""
                    SELECT
                        id,
                        sede_id,
                        estado

                    FROM salidas

                    WHERE id = %s
                """, (salida_id,))

                salida = cursor.fetchone()

                if not salida:

                    raise ValueError(
                        "La salida indicada no existe"
                    )

                if salida["sede_id"] != sede_id:

                    raise ValueError(
                        "La salida no pertenece "
                        "a la sede seleccionada"
                    )

                if salida["estado"] != "ACTIVA":

                    raise ValueError(
                        "Solo se pueden devolver "
                        "productos de una salida activa"
                    )

            # =================================================
            # CREAR DEVOLUCIÓN
            # =================================================

            cursor.execute("""
                INSERT INTO devoluciones (
                    numero_documento,
                    sede_id,
                    salida_id,
                    motivo,
                    observaciones,
                    usuario_id,
                    estado
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    'ACTIVA'
                )
                RETURNING id
            """, (
                numero_documento,
                sede_id,
                salida_id,
                motivo,
                observaciones,
                usuario_id
            ))

            devolucion_id = cursor.fetchone()["id"]

            # =================================================
            # PROCESAR DETALLES
            # =================================================

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

                condicion_retorno = item.get(
                    "condicion_retorno",
                    "BUEN_ESTADO"
                )

                if not producto_id:

                    raise ValueError(
                        "Cada detalle debe tener producto_id"
                    )

                try:

                    cantidad = int(cantidad)

                except (
                    TypeError,
                    ValueError
                ):

                    raise ValueError(
                        "La cantidad debe ser un número entero"
                    )

                if cantidad <= 0:

                    raise ValueError(
                        "La cantidad debe ser mayor que cero"
                    )

                # =============================================
                # PRODUCTO
                # =============================================

                cursor.execute("""
                    SELECT
                        id,
                        sede_id,
                        codigo,
                        nombre,
                        requiere_serial

                    FROM productos

                    WHERE id = %s
                """, (producto_id,))

                producto = cursor.fetchone()

                if not producto:

                    raise ValueError(
                        f"Producto {producto_id} no encontrado"
                    )

                if producto["sede_id"] != sede_id:

                    raise ValueError(
                        f'El producto '
                        f'"{producto["nombre"]}" '
                        "no pertenece a la sede"
                    )

                # =============================================
                # PRODUCTO SERIALIZADO
                # =============================================

                if (
                    producto["requiere_serial"]
                    and not equipo_id
                ):

                    raise ValueError(
                        f'El producto '
                        f'"{producto["nombre"]}" '
                        "requiere número de serie"
                    )

                # =============================================
                # VERIFICAR EQUIPO
                # =============================================

                if equipo_id:

                    cursor.execute("""
                        SELECT
                            id,
                            producto_id,
                            sede_id,
                            serial,
                            estado,
                            modelo_id

                        FROM equipos

                        WHERE id = %s

                        FOR UPDATE
                    """, (equipo_id,))

                    equipo = cursor.fetchone()

                    if not equipo:

                        raise ValueError(
                            f"Equipo {equipo_id} no encontrado"
                        )

                    if equipo["producto_id"] != producto_id:

                        raise ValueError(
                            "El equipo no pertenece "
                            "al producto seleccionado"
                        )

                    if equipo["sede_id"] != sede_id:

                        raise ValueError(
                            "El equipo no pertenece "
                            "a la sede de la devolución"
                        )

                    if equipo["estado"] == "DADO_DE_BAJA":

                        raise ValueError(
                            "El equipo está dado de baja"
                        )

                # =============================================
                # VERIFICAR DEVOLUCIÓN CONTRA LA SALIDA
                # =============================================

                if salida_id:

                    # =========================================
                    # PRODUCTO SERIALIZADO
                    # =========================================

                    if producto["requiere_serial"]:

                        cursor.execute("""
                            SELECT
                                cantidad

                            FROM detalle_salidas

                            WHERE salida_id = %s
                              AND producto_id = %s
                              AND equipo_id = %s
                        """, (
                            salida_id,
                            producto_id,
                            equipo_id
                        ))

                        detalle_salida = cursor.fetchone()

                        if not detalle_salida:

                            raise ValueError(
                                f'El equipo con serial '
                                f'"{equipo["serial"]}" '
                                "no pertenece a esta salida"
                            )

                        cursor.execute("""
                            SELECT
                                COALESCE(
                                    SUM(dd.cantidad),
                                    0
                                ) AS cantidad_devuelta

                            FROM detalle_devoluciones dd

                            INNER JOIN devoluciones dv
                                ON dv.id = dd.devolucion_id

                            WHERE dv.salida_id = %s
                              AND dd.equipo_id = %s
                              AND dv.estado = 'ACTIVA'
                        """, (
                            salida_id,
                            equipo_id
                        ))

                        cantidad_devuelta = (
                            cursor.fetchone()[
                                "cantidad_devuelta"
                            ]
                        )

                        pendiente = (
                            detalle_salida["cantidad"]
                            - cantidad_devuelta
                        )

                    # =========================================
                    # PRODUCTO NO SERIALIZADO
                    # =========================================

                    else:

                        cursor.execute("""
                            SELECT
                                COALESCE(
                                    SUM(ds.cantidad),
                                    0
                                ) AS cantidad_salida

                            FROM detalle_salidas ds

                            WHERE ds.salida_id = %s
                              AND ds.producto_id = %s
                              AND ds.equipo_id IS NULL
                        """, (
                            salida_id,
                            producto_id
                        ))

                        cantidad_salida = (
                            cursor.fetchone()[
                                "cantidad_salida"
                            ]
                        )

                        cursor.execute("""
                            SELECT
                                COALESCE(
                                    SUM(dd.cantidad),
                                    0
                                ) AS cantidad_devuelta

                            FROM detalle_devoluciones dd

                            INNER JOIN devoluciones dv
                                ON dv.id = dd.devolucion_id

                            WHERE dv.salida_id = %s
                              AND dd.producto_id = %s
                              AND dd.equipo_id IS NULL
                              AND dv.estado = 'ACTIVA'
                        """, (
                            salida_id,
                            producto_id
                        ))

                        cantidad_devuelta = (
                            cursor.fetchone()[
                                "cantidad_devuelta"
                            ]
                        )

                        pendiente = (
                            cantidad_salida
                            - cantidad_devuelta
                        )

                    if cantidad > pendiente:

                        raise ValueError(
                            f"Cantidad a devolver inválida "
                            f"para '{producto['nombre']}'. "
                            f"Pendiente: {pendiente}, "
                            f"solicitado: {cantidad}"
                        )

                # =============================================
                # INSERTAR DETALLE
                # =============================================

                cursor.execute("""
                    INSERT INTO detalle_devoluciones (
                        devolucion_id,
                        producto_id,
                        equipo_id,
                        cantidad,
                        condicion_retorno,
                        observaciones
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    devolucion_id,
                    producto_id,
                    equipo_id,
                    cantidad,
                    condicion_retorno,
                    item.get(
                        "observaciones",
                        ""
                    ).strip()
                ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:
        conn.close()

    # ========================================================
    # AUDITORÍA
    # ========================================================

    try:

        registrar_auditoria(
            usuario_id=usuario_id,
            accion="CREAR",
            entidad="DEVOLUCION",
            entidad_id=devolucion_id,
            descripcion=(
                f"Creación de devolución "
                f"{numero_documento}"
            ),
            datos_nuevos={
                "numero_documento": numero_documento,
                "sede_id": sede_id,
                "salida_id": salida_id,
                "motivo": motivo,
                "observaciones": observaciones,
                "detalle": detalle
            }
        )

    except Exception as e_auditoria:

        print(
            f"ADVERTENCIA AUDITORIA DEVOLUCION: "
            f"{e_auditoria}"
        )

    return jsonify({
        "mensaje": "Devolución registrada",
        "id": devolucion_id
    }), 201


# ============================================================
# PUT /api/devoluciones/<id>/anular
#
# SOLO ADMIN
# ============================================================

@devoluciones_bp.route(
    "/<int:id>/anular",
    methods=["PUT"]
)
@jwt_required()
def anular_devolucion(id):

    claims = get_jwt()

    if claims.get("rol") != "admin":

        return jsonify({
            "error": (
                "Solo el admin puede anular devoluciones"
            )
        }), 403

    datos = request.get_json(silent=True) or {}

    motivo = datos.get(
        "motivo_anulacion",
        ""
    ).strip()

    if not motivo:

        return jsonify({
            "error": (
                "El motivo de anulación es obligatorio"
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
                    numero_documento,
                    sede_id,
                    estado

                FROM devoluciones

                WHERE id = %s

                FOR UPDATE
            """, (id,))

            devolucion = cursor.fetchone()

            if not devolucion:

                conn.rollback()

                return jsonify({
                    "error": (
                        "Devolución no encontrada"
                    )
                }), 404

            if devolucion["estado"] == "ANULADA":

                conn.rollback()

                return jsonify({
                    "error": (
                        "La devolución ya está anulada"
                    )
                }), 400

            cursor.execute("""
                UPDATE devoluciones

                SET
                    estado = 'ANULADA',
                    anulada_por = %s,
                    fecha_anulacion = CURRENT_TIMESTAMP,
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

    # ========================================================
    # AUDITORÍA
    # ========================================================

    try:

        registrar_auditoria(
            usuario_id=usuario_id,
            accion="ANULAR",
            entidad="DEVOLUCION",
            entidad_id=id,
            descripcion=(
                f'Anulación de devolución '
                f'{devolucion["numero_documento"]}. '
                f'Motivo: {motivo}'
            ),
            datos_anteriores={
                "estado": devolucion["estado"],
                "numero_documento": (
                    devolucion["numero_documento"]
                ),
                "sede_id": devolucion["sede_id"]
            },
            datos_nuevos={
                "estado": "ANULADA",
                "numero_documento": (
                    devolucion["numero_documento"]
                ),
                "sede_id": devolucion["sede_id"],
                "motivo_anulacion": motivo
            }
        )

    except Exception as e_auditoria:

        print(
            f"ADVERTENCIA AUDITORIA "
            f"ANULACION DEVOLUCION: "
            f"{e_auditoria}"
        )

    return jsonify({
        "mensaje": (
            "Devolución anulada correctamente"
        )
    })