# ============================================================
# salidas.py — Registro de mercancía que sale del almacén
# PostgreSQL
#
# ROLES:
#   admin     → consultar, registrar y anular
#   sede      → consultar y registrar
#   consulta  → solamente consultar
#
# El inventario se actualiza mediante triggers PostgreSQL.
#
# PRODUCTOS SERIALIZADOS:
#   Cada equipo físico se guarda mediante:
#       - equipo_id
#       - serial
#       - modelo
#       - marca
#
# PRODUCTOS NO SERIALIZADOS:
#   Se manejan mediante cantidad.
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt,
    get_jwt_identity
)

from database import get_connection
from utils.auditoria import registrar_auditoria


salidas_bp = Blueprint("salidas", __name__)


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


def usuario_puede_ver_salida(salida):

    claims = get_jwt()

    rol = claims.get("rol")
    sede_id = claims.get("sede_id")

    if rol == "admin":

        return True

    if rol == "consulta":

        return (
            sede_id is None
            or int(salida["sede_id"]) == int(sede_id)
        )

    if rol in ("sede", "porteria"):

        return (
            salida["sede_id"] == sede_id
        )

    return False


def obtener_o_crear_cliente(cursor, nombre):
    """
    Busca un cliente por nombre (sin importar mayúsculas ni
    espacios de más). Si no existe, lo crea. Igual que las
    marcas/modelos "sobre la marcha".

    Devuelve None si no se escribió ningún nombre (el cliente
    es opcional en una salida).
    """

    nombre = (nombre or "").strip()

    if not nombre:
        return None

    cursor.execute("""
        SELECT id
        FROM clientes
        WHERE LOWER(TRIM(nombre)) = LOWER(%s)
    """, (
        nombre,
    ))

    existente = cursor.fetchone()

    if existente:
        return existente["id"]

    cursor.execute("""
        INSERT INTO clientes (
            nombre
        )
        VALUES (%s)
        RETURNING id
    """, (
        nombre,
    ))

    return cursor.fetchone()["id"]


# ============================================================
# GET /api/salidas/
# LISTAR SALIDAS
# ============================================================

@salidas_bp.route("/", methods=["GET"])
@jwt_required()
def listar_salidas():

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
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.observaciones,
                        s.fecha,
                        s.sede_id,
                        s.estado,
                        s.fecha_anulacion,
                        s.motivo_anulacion,
                        s.cliente_id,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        u.nombre AS usuario_nombre,

                        c.nombre AS cliente_nombre,

                        COUNT(
                            DISTINCT d.producto_id
                        ) AS total_items

                    FROM salidas s

                    LEFT JOIN detalle_salidas d
                        ON d.salida_id = s.id

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = s.usuario_id

                    LEFT JOIN clientes c
                        ON c.id = s.cliente_id

                    GROUP BY
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.observaciones,
                        s.fecha,
                        s.sede_id,
                        s.estado,
                        s.fecha_anulacion,
                        s.motivo_anulacion,
                        s.cliente_id,
                        se.nombre,
                        se.ciudad,
                        u.nombre,
                        c.nombre

                    ORDER BY
                        s.fecha DESC
                """)

            # =================================================
            # UNA SEDE
            # =================================================

            else:

                cursor.execute("""
                    SELECT
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.observaciones,
                        s.fecha,
                        s.sede_id,
                        s.estado,
                        s.fecha_anulacion,
                        s.motivo_anulacion,
                        s.cliente_id,

                        se.nombre AS sede_nombre,
                        se.ciudad,

                        u.nombre AS usuario_nombre,

                        c.nombre AS cliente_nombre,

                        COUNT(
                            DISTINCT d.producto_id
                        ) AS total_items

                    FROM salidas s

                    LEFT JOIN detalle_salidas d
                        ON d.salida_id = s.id

                    LEFT JOIN sedes se
                        ON se.id = s.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = s.usuario_id

                    LEFT JOIN clientes c
                        ON c.id = s.cliente_id

                    WHERE s.sede_id = %s

                    GROUP BY
                        s.id,
                        s.numero_documento,
                        s.destino,
                        s.observaciones,
                        s.fecha,
                        s.sede_id,
                        s.estado,
                        s.fecha_anulacion,
                        s.motivo_anulacion,
                        s.cliente_id,
                        se.nombre,
                        se.ciudad,
                        u.nombre,
                        c.nombre

                    ORDER BY
                        s.fecha DESC
                """, (
                    sede_id,
                ))

            salidas = [
                dict(salida)
                for salida in cursor.fetchall()
            ]

    finally:

        conn.close()

    return jsonify(salidas)


# ============================================================
# GET /api/salidas/<id>
# OBTENER SALIDA
# ============================================================

@salidas_bp.route(
    "/<int:id>",
    methods=["GET"]
)
@jwt_required()
def obtener_salida(id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # =================================================
            # CABECERA
            # =================================================

            cursor.execute("""
                SELECT
                    s.id,
                    s.numero_documento,
                    s.destino,
                    s.observaciones,
                    s.fecha,
                    s.sede_id,
                    s.usuario_id,
                    s.estado,
                    s.anulada_por,
                    s.fecha_anulacion,
                    s.motivo_anulacion,
                    s.cliente_id,

                    se.nombre AS sede_nombre,
                    se.ciudad,

                    u.nombre AS usuario_nombre,

                    c.nombre AS cliente_nombre

                FROM salidas s

                LEFT JOIN sedes se
                    ON se.id = s.sede_id

                LEFT JOIN usuarios u
                    ON u.id = s.usuario_id

                LEFT JOIN clientes c
                    ON c.id = s.cliente_id

                WHERE s.id = %s
            """, (
                id,
            ))

            salida = cursor.fetchone()

            if not salida:

                return jsonify({
                    "error": "Salida no encontrada"
                }), 404

            # =================================================
            # PERMISOS
            # =================================================

            if not usuario_puede_ver_salida(
                salida
            ):

                return jsonify({
                    "error": (
                        "No tienes permisos para consultar "
                        "esta salida"
                    )
                }), 403

            # =================================================
            # DETALLE
            # =================================================

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

                    mo.id AS modelo_id,
                    mo.nombre AS modelo_nombre,

                    ma.id AS marca_id,
                    ma.nombre AS marca_nombre

                FROM detalle_salidas d

                INNER JOIN productos p
                    ON p.id = d.producto_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                LEFT JOIN equipos e
                    ON e.id = d.equipo_id

                LEFT JOIN modelos mo
                    ON mo.id = e.modelo_id

                LEFT JOIN marcas ma
                    ON ma.id = mo.marca_id

                WHERE d.salida_id = %s

                ORDER BY
                    d.id
            """, (
                id,
            ))

            detalle = [
                dict(item)
                for item in cursor.fetchall()
            ]

    finally:

        conn.close()

    resultado = dict(salida)

    resultado["detalle"] = detalle

    return jsonify(resultado)


# ============================================================
# POST /api/salidas/
# CREAR SALIDA
# ============================================================

@salidas_bp.route(
    "/",
    methods=["POST"]
)
@jwt_required()
def crear_salida():

    claims = get_jwt()

    rol = claims.get("rol")

    datos = request.get_json(
        silent=True
    ) or {}

    # ========================================================
    # PERMISOS
    # ========================================================

    if rol in ("consulta", "porteria"):

        return jsonify({
            "error": (
                "Este usuario no puede "
                "registrar salidas"
            )
        }), 403

    # ========================================================
    # NÚMERO DE DOCUMENTO
    # ========================================================

    numero_documento = str(
        datos.get(
            "numero_documento",
            ""
        )
    ).strip()

    if not numero_documento:

        return jsonify({
            "error": (
                "El número de documento "
                "es obligatorio"
            )
        }), 400

    # ========================================================
    # DETALLE
    # ========================================================

    detalle = datos.get("detalle")

    if not isinstance(
        detalle,
        list
    ) or not detalle:

        return jsonify({
            "error": (
                "Debe agregar al menos "
                "un producto"
            )
        }), 400

    # ========================================================
    # SEDE
    # ========================================================

    if rol == "admin":

        sede_id = datos.get(
            "sede_id"
        )

        if not sede_id:

            sede_id = claims.get(
                "sede_id"
            )

    else:

        sede_id = claims.get(
            "sede_id"
        )

    if not sede_id:

        return jsonify({
            "error": (
                "Debe seleccionar una sede"
            )
        }), 400

    try:

        sede_id = int(
            sede_id
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "error": "La sede seleccionada no es válida"
        }), 400

    # ========================================================
    # USUARIO
    # ========================================================

    usuario_id = int(
        get_jwt_identity()
    )

    # ========================================================
    # DESTINO
    # ========================================================

    destino = str(
        datos.get(
            "destino",
            ""
        )
    ).strip()

    if not destino:

        return jsonify({
            "error": (
                "El destino es obligatorio"
            )
        }), 400

    # ========================================================
    # CLIENTE (opcional)
    #
    # Se busca o se crea sobre la marcha, igual que
    # marcas/modelos. Si el campo viene vacío, la salida
    # simplemente queda sin cliente asociado.
    # ========================================================

    cliente_nombre = str(
        datos.get(
            "cliente",
            ""
        )
    ).strip()

    # ========================================================
    # OBSERVACIONES
    # ========================================================

    observaciones = str(
        datos.get(
            "observaciones",
            ""
        )
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
            """, (
                sede_id,
            ))

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
                FROM salidas
                WHERE numero_documento = %s
            """, (
                numero_documento,
            ))

            if cursor.fetchone():

                raise ValueError(
                    (
                        f'Ya existe una salida con el '
                        f'número de documento '
                        f'"{numero_documento}"'
                    )
                )

            # =================================================
            # CLIENTE: BUSCAR O CREAR
            # =================================================

            cliente_id = obtener_o_crear_cliente(
                cursor,
                cliente_nombre
            )

            # =================================================
            # VALIDAR DETALLE
            # =================================================

            detalles_normalizados = []

            for item in detalle:

                if not isinstance(
                    item,
                    dict
                ):

                    raise ValueError(
                        "Cada detalle debe ser un objeto"
                    )

                # =================================================
                # PRODUCTO
                # =================================================

                producto_id = item.get(
                    "producto_id"
                )

                if not producto_id:

                    raise ValueError(
                        "Cada detalle debe tener producto_id"
                    )

                try:

                    producto_id = int(
                        producto_id
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    raise ValueError(
                        "producto_id inválido"
                    )

                # =================================================
                # CANTIDAD
                # =================================================

                cantidad = item.get(
                    "cantidad"
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
                        "La cantidad debe ser un número entero"
                    )

                if cantidad <= 0:

                    raise ValueError(
                        "La cantidad debe ser mayor que cero"
                    )

                # =================================================
                # PRODUCTO + STOCK
                # =================================================

                cursor.execute("""
                    SELECT
                        p.id,
                        p.nombre,
                        p.codigo,
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
                """, (
                    producto_id,
                ))

                producto = cursor.fetchone()

                if not producto:

                    raise ValueError(
                        (
                            f"Producto "
                            f"{producto_id} "
                            "no encontrado"
                        )
                    )

                # =================================================
                # SEDE DEL PRODUCTO
                # =================================================

                if int(
                    producto["sede_id"]
                ) != sede_id:

                    raise ValueError(
                        (
                            f'El producto '
                            f'"{producto["nombre"]}" '
                            'no pertenece a la sede '
                            'seleccionada'
                        )
                    )

                # =================================================
                # STOCK
                # =================================================

                if cantidad > int(
                    producto["stock"]
                ):

                    raise ValueError(
                        (
                            f'Stock insuficiente para '
                            f'"{producto["nombre"]}". '
                            f'Disponible: '
                            f'{producto["stock"]}. '
                            f'Solicitado: '
                            f'{cantidad}'
                        )
                    )

                # =================================================
                # PRODUCTO SERIALIZADO
                # =================================================

                if producto["requiere_serial"]:

                    unidades = item.get(
                        "unidades",
                        []
                    )

                    # ------------------------------------------------
                    # Compatibilidad con formato antiguo
                    # ------------------------------------------------

                    if not unidades:

                        equipo_id = item.get(
                            "equipo_id"
                        )

                        serial = item.get(
                            "serial"
                        )

                        if equipo_id or serial:

                            unidades = [
                                {
                                    "equipo_id":
                                        equipo_id,

                                    "serial":
                                        serial
                                }
                            ]

                    if not isinstance(
                        unidades,
                        list
                    ):

                        raise ValueError(
                            (
                                f'Las unidades del producto '
                                f'"{producto["codigo"]}" '
                                'deben ser una lista'
                            )
                        )

                    # ------------------------------------------------
                    # La cantidad debe coincidir
                    # con el número de equipos
                    # ------------------------------------------------

                    if len(unidades) != cantidad:

                        raise ValueError(
                            (
                                f'El producto '
                                f'"{producto["codigo"]}" '
                                f'requiere {cantidad} '
                                f'equipo(s), pero se recibieron '
                                f'{len(unidades)}'
                            )
                        )

                    equipos_validos = []

                    equipos_ids_recibidos = set()

                    for unidad in unidades:

                        if not isinstance(
                            unidad,
                            dict
                        ):

                            raise ValueError(
                                "Cada equipo debe ser un objeto"
                            )

                        equipo_id = unidad.get(
                            "equipo_id"
                        )

                        serial = unidad.get(
                            "serial"
                        )

                        # =============================================
                        # BUSCAR POR ID
                        # =============================================

                        if equipo_id:

                            try:

                                equipo_id = int(
                                    equipo_id
                                )

                            except (
                                TypeError,
                                ValueError
                            ):

                                raise ValueError(
                                    "equipo_id inválido"
                                )

                            cursor.execute("""
                                SELECT
                                    e.id,
                                    e.producto_id,
                                    e.serial,
                                    e.condicion,
                                    e.estado,
                                    e.sede_id,
                                    e.modelo_id

                                FROM equipos e

                                WHERE e.id = %s

                                FOR UPDATE
                            """, (
                                equipo_id,
                            ))

                        # =============================================
                        # BUSCAR POR SERIAL
                        # =============================================

                        elif serial:

                            serial = str(
                                serial
                            ).strip()

                            if not serial:

                                raise ValueError(
                                    (
                                        "El serial del equipo "
                                        "no puede estar vacío"
                                    )
                                )

                            cursor.execute("""
                                SELECT
                                    e.id,
                                    e.producto_id,
                                    e.serial,
                                    e.condicion,
                                    e.estado,
                                    e.sede_id,
                                    e.modelo_id

                                FROM equipos e

                                WHERE e.serial = %s

                                FOR UPDATE
                            """, (
                                serial,
                            ))

                        else:

                            raise ValueError(
                                (
                                    f'El producto '
                                    f'"{producto["codigo"]}" '
                                    'tiene un equipo sin '
                                    'equipo_id ni serial'
                                )
                            )

                        equipo = cursor.fetchone()

                        if not equipo:

                            identificador = (
                                serial
                                or equipo_id
                                or "desconocido"
                            )

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{identificador}" '
                                    'no existe'
                                )
                            )

                        # =============================================
                        # EVITAR EQUIPO REPETIDO
                        # =============================================

                        if equipo["id"] in equipos_ids_recibidos:

                            raise ValueError(
                                (
                                    f'El equipo con serial '
                                    f'"{equipo["serial"]}" '
                                    'está repetido en la salida'
                                )
                            )

                        equipos_ids_recibidos.add(
                            equipo["id"]
                        )

                        # =============================================
                        # PRODUCTO CORRECTO
                        # =============================================

                        if int(
                            equipo["producto_id"]
                        ) != producto_id:

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{equipo["serial"]}" '
                                    'no pertenece al producto '
                                    f'"{producto["codigo"]}"'
                                )
                            )

                        # =============================================
                        # SEDE CORRECTA
                        # =============================================

                        if int(
                            equipo["sede_id"]
                        ) != sede_id:

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{equipo["serial"]}" '
                                    'no pertenece a la sede '
                                    'seleccionada'
                                )
                            )

                        # =============================================
                        # ESTADO DISPONIBLE
                        # =============================================

                        if equipo["estado"] != "DISPONIBLE":

                            raise ValueError(
                                (
                                    f'El equipo '
                                    f'"{equipo["serial"]}" '
                                    f'no está disponible. '
                                    f'Estado actual: '
                                    f'{equipo["estado"]}'
                                )
                            )

                        equipos_validos.append({
                            "equipo_id":
                                equipo["id"],

                            "serial":
                                equipo["serial"]
                        })

                    detalles_normalizados.append({
                        "producto_id":
                            producto_id,

                        "cantidad":
                            cantidad,

                        "observaciones":
                            str(
                                item.get(
                                    "observaciones",
                                    ""
                                )
                            ).strip(),

                        "serializado":
                            True,

                        "equipos":
                            equipos_validos
                    })

                # =================================================
                # PRODUCTO NO SERIALIZADO
                # =================================================

                else:

                    unidades = item.get(
                        "unidades",
                        []
                    )

                    if unidades:

                        raise ValueError(
                            (
                                f'El producto '
                                f'"{producto["codigo"]}" '
                                'no requiere seriales'
                            )
                        )

                    detalles_normalizados.append({
                        "producto_id":
                            producto_id,

                        "cantidad":
                            cantidad,

                        "observaciones":
                            str(
                                item.get(
                                    "observaciones",
                                    ""
                                )
                            ).strip(),

                        "serializado":
                            False,

                        "equipos":
                            []
                    })

            # =================================================
            # CREAR CABECERA DE SALIDA
            # =================================================

            cursor.execute("""
                INSERT INTO salidas (
                    numero_documento,
                    sede_id,
                    destino,
                    observaciones,
                    usuario_id,
                    cliente_id,
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
                destino,
                observaciones,
                usuario_id,
                cliente_id
            ))

            salida_id = cursor.fetchone()["id"]

            # =================================================
            # CREAR DETALLES
            # =================================================

            for item in detalles_normalizados:

                # =================================================
                # NO SERIALIZADO
                # =================================================

                if not item["serializado"]:

                    cursor.execute("""
                        INSERT INTO detalle_salidas (
                            salida_id,
                            producto_id,
                            equipo_id,
                            cantidad,
                            observaciones
                        )
                        VALUES (
                            %s,
                            %s,
                            NULL,
                            %s,
                            %s
                        )
                    """, (
                        salida_id,
                        item["producto_id"],
                        item["cantidad"],
                        item["observaciones"]
                    ))

                # =================================================
                # SERIALIZADO
                #
                # UNA FILA POR CADA EQUIPO
                # =================================================

                else:

                    for equipo in item["equipos"]:

                        cursor.execute("""
                            INSERT INTO detalle_salidas (
                                salida_id,
                                producto_id,
                                equipo_id,
                                cantidad,
                                observaciones
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                1,
                                %s
                            )
                        """, (
                            salida_id,
                            item["producto_id"],
                            equipo["equipo_id"],
                            item["observaciones"]
                        ))

        # ========================================================
        # COMMIT
        # ========================================================

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            "ERROR AL CREAR SALIDA:",
            repr(e)
        )

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
            entidad="SALIDA",
            entidad_id=salida_id,
            descripcion=(
                f"Creación de salida "
                f"{numero_documento}"
            ),
            datos_nuevos={
                "numero_documento":
                    numero_documento,

                "sede_id":
                    sede_id,

                "destino":
                    destino,

                "cliente":
                    cliente_nombre,

                "observaciones":
                    observaciones,

                "detalle":
                    detalles_normalizados
            }
        )

    except Exception as e_auditoria:

        print(
            "ADVERTENCIA AUDITORIA SALIDA:",
            e_auditoria
        )

    return jsonify({
        "mensaje": "Salida registrada",
        "id": salida_id
    }), 201


# ============================================================
# PUT /api/salidas/<id>/anular
# ANULAR SALIDA
#
# SOLO ADMIN
#
# El trigger PostgreSQL:
#   - devuelve cantidades al inventario
#   - devuelve equipos a DISPONIBLE
# ============================================================

@salidas_bp.route(
    "/<int:id>/anular",
    methods=["PUT"]
)
@jwt_required()
def anular_salida(id):

    claims = get_jwt()

    if claims.get("rol") != "admin":

        return jsonify({
            "error": (
                "Solo el admin puede "
                "anular salidas"
            )
        }), 403

    datos = request.get_json(
        silent=True
    ) or {}

    motivo = str(
        datos.get(
            "motivo_anulacion",
            ""
        )
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

    salida = None

    try:

        with conn.cursor() as cursor:

            # =================================================
            # BLOQUEAR SALIDA
            # =================================================

            cursor.execute("""
                SELECT
                    id,
                    numero_documento,
                    sede_id,
                    estado

                FROM salidas

                WHERE id = %s

                FOR UPDATE
            """, (
                id,
            ))

            salida = cursor.fetchone()

            if not salida:

                conn.rollback()

                return jsonify({
                    "error": "Salida no encontrada"
                }), 404

            # =================================================
            # YA ANULADA
            # =================================================

            if salida["estado"] == "ANULADA":

                conn.rollback()

                return jsonify({
                    "error": (
                        "La salida ya está anulada"
                    )
                }), 400

            # =================================================
            # ANULAR
            # =================================================

            cursor.execute("""
                UPDATE salidas

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

        print(
            "ERROR AL ANULAR SALIDA:",
            repr(e)
        )

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
            entidad="SALIDA",
            entidad_id=id,
            descripcion=(
                f'Anulación de salida '
                f'{salida["numero_documento"]}. '
                f'Motivo: {motivo}'
            ),
            datos_anteriores={
                "estado":
                    salida["estado"],

                "numero_documento":
                    salida["numero_documento"],

                "sede_id":
                    salida["sede_id"]
            },
            datos_nuevos={
                "estado":
                    "ANULADA",

                "numero_documento":
                    salida["numero_documento"],

                "sede_id":
                    salida["sede_id"],

                "motivo_anulacion":
                    motivo
            }
        )

    except Exception as e_auditoria:

        print(
            "ADVERTENCIA AUDITORIA "
            "ANULACION SALIDA:",
            e_auditoria
        )

    return jsonify({
        "mensaje": (
            "Salida anulada correctamente"
        )
    })