# ============================================================
# entradas.py — Gestión de entradas de inventario
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
#   Cada unidad física puede tener:
#       - serial
#       - modelo
#       - estado
#       - sede
#
# ORIGEN / DESTINO:
#   La columna "proveedor" de la BD se mantiene por compatibilidad.
#   En la API y en la aplicación se maneja como "origen".
#
#   Destino de una entrada normal:
#       Almacén
#
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from database import get_connection
from utils.auditoria import registrar_auditoria


entradas_bp = Blueprint('entradas', __name__)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_sede_actual():

    claims = get_jwt()

    if claims.get('rol') == 'admin':
        return request.args.get('sede_id', type=int)

    return claims.get('sede_id')


def usuario_puede_ver_entrada(entrada):

    claims = get_jwt()

    rol = claims.get('rol')
    sede_id = claims.get('sede_id')

    if rol == 'admin':
        return True

    if rol == 'consulta':
        return (
            sede_id is None
            or entrada['sede_id'] == sede_id
        )

    if rol == 'sede':
        return entrada['sede_id'] == sede_id

    return False


# ============================================================
# GET /api/entradas/
# LISTAR ENTRADAS
# ============================================================

@entradas_bp.route('/', methods=['GET'])
@jwt_required()
def listar_entradas():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            if sede_id is None:

                cursor.execute('''
                    SELECT
                        e.id,
                        e.numero_documento,

                        e.proveedor AS origen,

                        e.observaciones,
                        e.fecha,
                        e.sede_id,
                        e.estado,
                        e.fecha_anulacion,
                        e.motivo_anulacion,

                        'Almacén' AS destino,

                        s.nombre AS sede_nombre,
                        s.ciudad,

                        u.nombre AS usuario_nombre,

                        COUNT(d.id) AS total_items

                    FROM entradas e

                    LEFT JOIN detalle_entradas d
                        ON d.entrada_id = e.id

                    LEFT JOIN sedes s
                        ON s.id = e.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = e.usuario_id

                    GROUP BY
                        e.id,
                        e.numero_documento,
                        e.proveedor,
                        e.observaciones,
                        e.fecha,
                        e.sede_id,
                        e.estado,
                        e.fecha_anulacion,
                        e.motivo_anulacion,
                        s.nombre,
                        s.ciudad,
                        u.nombre

                    ORDER BY e.fecha DESC
                ''')

            else:

                cursor.execute('''
                    SELECT
                        e.id,
                        e.numero_documento,

                        e.proveedor AS origen,

                        e.observaciones,
                        e.fecha,
                        e.sede_id,
                        e.estado,
                        e.fecha_anulacion,
                        e.motivo_anulacion,

                        'Almacén' AS destino,

                        s.nombre AS sede_nombre,
                        s.ciudad,

                        u.nombre AS usuario_nombre,

                        COUNT(d.id) AS total_items

                    FROM entradas e

                    LEFT JOIN detalle_entradas d
                        ON d.entrada_id = e.id

                    LEFT JOIN sedes s
                        ON s.id = e.sede_id

                    LEFT JOIN usuarios u
                        ON u.id = e.usuario_id

                    WHERE e.sede_id = %s

                    GROUP BY
                        e.id,
                        e.numero_documento,
                        e.proveedor,
                        e.observaciones,
                        e.fecha,
                        e.sede_id,
                        e.estado,
                        e.fecha_anulacion,
                        e.motivo_anulacion,
                        s.nombre,
                        s.ciudad,
                        u.nombre

                    ORDER BY e.fecha DESC
                ''', (sede_id,))

            entradas = [
                dict(entrada)
                for entrada in cursor.fetchall()
            ]

    finally:

        conn.close()

    return jsonify(entradas)


# ============================================================
# GET /api/entradas/<id>
# OBTENER ENTRADA
# ============================================================

@entradas_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_entrada(id):

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Entrada
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    e.id,
                    e.numero_documento,

                    e.proveedor AS origen,

                    e.observaciones,
                    e.fecha,
                    e.sede_id,
                    e.usuario_id,
                    e.estado,
                    e.anulada_por,
                    e.fecha_anulacion,
                    e.motivo_anulacion,

                    'Almacén' AS destino,

                    s.nombre AS sede_nombre,
                    s.ciudad,

                    u.nombre AS usuario_nombre

                FROM entradas e

                LEFT JOIN sedes s
                    ON s.id = e.sede_id

                LEFT JOIN usuarios u
                    ON u.id = e.usuario_id

                WHERE e.id = %s

            ''', (id,))

            entrada = cursor.fetchone()

            if not entrada:

                return jsonify({
                    'error': 'Entrada no encontrada'
                }), 404

            if not usuario_puede_ver_entrada(entrada):

                return jsonify({
                    'error': (
                        'No tienes permisos para '
                        'consultar esta entrada'
                    )
                }), 403

            # ------------------------------------------------
            # Detalle
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    d.id,
                    d.producto_id,
                    d.cantidad,
                    d.observaciones,

                    p.codigo,
                    p.nombre AS producto_nombre,
                    p.descripcion,
                    p.requiere_serial,

                    un.codigo AS unidad,
                    un.nombre AS unidad_nombre

                FROM detalle_entradas d

                INNER JOIN productos p
                    ON p.id = d.producto_id

                LEFT JOIN unidades un
                    ON un.id = p.unidad_id

                WHERE d.entrada_id = %s

                ORDER BY d.id

            ''', (id,))

            detalle = [
                dict(item)
                for item in cursor.fetchall()
            ]

            # ------------------------------------------------
            # Equipos / seriales relacionados
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    e.id,
                    e.producto_id,
                    e.serial,
                    e.condicion,
                    e.estado,
                    e.sede_id,
                    e.fecha_ingreso,
                    e.observaciones,

                    p.codigo,
                    p.nombre AS producto_nombre,

                    mo.id AS modelo_id,
                    mo.nombre AS modelo_nombre,

                    ma.id AS marca_id,
                    ma.nombre AS marca_nombre

                FROM equipos e

                INNER JOIN productos p
                    ON p.id = e.producto_id

                LEFT JOIN modelos mo
                    ON mo.id = e.modelo_id

                LEFT JOIN marcas ma
                    ON ma.id = mo.marca_id

                INNER JOIN detalle_entradas d
                    ON d.producto_id = e.producto_id

                WHERE d.entrada_id = %s

                ORDER BY e.id

            ''', (id,))

            equipos = [
                dict(item)
                for item in cursor.fetchall()
            ]

    finally:

        conn.close()

    resultado = dict(entrada)

    resultado['detalle'] = detalle
    resultado['equipos'] = equipos

    return jsonify(resultado)


# ============================================================
# POST /api/entradas/
# CREAR ENTRADA
# ============================================================

@entradas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_entrada():

    claims = get_jwt()

    rol = claims.get('rol')

    datos = request.get_json(silent=True) or {}

    # ========================================================
    # PERMISOS
    # ========================================================

    if rol == 'consulta':

        return jsonify({
            'error': (
                'El usuario de consulta no puede '
                'registrar entradas'
            )
        }), 403

    # ========================================================
    # DATOS PRINCIPALES
    # ========================================================

    numero_documento = datos.get(
        'numero_documento',
        ''
    )

    numero_documento = str(
        numero_documento
    ).strip()

    if not numero_documento:

        return jsonify({
            'error': (
                'El número de documento '
                'es obligatorio'
            )
        }), 400

    detalle = datos.get('detalle')

    if not isinstance(detalle, list) or len(detalle) == 0:

        return jsonify({
            'error': (
                'Debe agregar al menos '
                'un producto'
            )
        }), 400

    # ========================================================
    # SEDE
    # ========================================================

    if rol == 'admin':

        sede_id = datos.get('sede_id')

        if not sede_id:

            sede_id = claims.get('sede_id')

    else:

        sede_id = claims.get('sede_id')

    if not sede_id:

        return jsonify({
            'error': 'Debe seleccionar una sede'
        }), 400

    usuario_id = int(
        get_jwt_identity()
    )

    # ========================================================
    # ORIGEN
    #
    # La BD continúa usando la columna "proveedor".
    # La aplicación puede enviar "origen".
    #
    # También aceptamos "proveedor" para compatibilidad
    # con versiones anteriores del frontend.
    # ========================================================

    origen = datos.get(
        'origen',
        datos.get('proveedor', '')
    )

    origen = str(
        origen
    ).strip()

    # ========================================================
    # DESTINO
    #
    # Las entradas normales tienen como destino Almacén.
    # Actualmente no se guarda en una columna porque la tabla
    # entradas no tiene campo destino.
    # ========================================================

    destino = 'Almacén'

    # ========================================================
    # OBSERVACIONES
    # ========================================================

    observaciones = datos.get(
        'observaciones',
        ''
    )

    observaciones = str(
        observaciones
    ).strip()

    conn = get_connection()

    entrada_id = None

    try:

        with conn.cursor() as cursor:

            # =================================================
            # VERIFICAR SEDE
            # =================================================

            cursor.execute('''
                SELECT
                    id
                FROM sedes
                WHERE id = %s
                  AND activa = TRUE
            ''', (sede_id,))

            if not cursor.fetchone():

                raise ValueError(
                    'La sede no existe o está inactiva'
                )

            # =================================================
            # VERIFICAR DOCUMENTO DUPLICADO
            # =================================================

            cursor.execute('''
                SELECT
                    id
                FROM entradas
                WHERE numero_documento = %s
            ''', (numero_documento,))

            if cursor.fetchone():

                raise ValueError(
                    (
                        f'Ya existe una entrada con el '
                        f'número de documento '
                        f'"{numero_documento}"'
                    )
                )

            # =================================================
            # CREAR ENTRADA
            #
            # "proveedor" es la columna existente en BD,
            # pero representa el ORIGEN.
            # =================================================

            cursor.execute('''
                INSERT INTO entradas (
                    numero_documento,
                    sede_id,
                    proveedor,
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
                    'ACTIVA'
                )

                RETURNING id

            ''', (
                numero_documento,
                sede_id,
                origen,
                observaciones,
                usuario_id
            ))

            entrada_id = cursor.fetchone()['id']

            # =================================================
            # PROCESAR DETALLE
            # =================================================

            for item in detalle:

                if not isinstance(item, dict):

                    raise ValueError(
                        'Cada detalle debe ser un objeto'
                    )

                # ------------------------------------------------
                # Producto
                # ------------------------------------------------

                producto_id = item.get(
                    'producto_id'
                )

                if not producto_id:

                    raise ValueError(
                        'Cada detalle debe tener producto_id'
                    )

                # ------------------------------------------------
                # Cantidad
                # ------------------------------------------------

                cantidad = item.get(
                    'cantidad'
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
                        'La cantidad debe ser un número entero'
                    )

                if cantidad <= 0:

                    raise ValueError(
                        'La cantidad debe ser mayor que cero'
                    )

                # =================================================
                # BUSCAR PRODUCTO
                # =================================================

                cursor.execute('''
                    SELECT
                        id,
                        sede_id,
                        codigo,
                        nombre,
                        requiere_serial
                    FROM productos
                    WHERE id = %s
                    FOR UPDATE
                ''', (producto_id,))

                producto = cursor.fetchone()

                if not producto:

                    raise ValueError(
                        f'Producto {producto_id} no encontrado'
                    )

                # =================================================
                # VERIFICAR SEDE DEL PRODUCTO
                # =================================================

                if producto['sede_id'] != sede_id:

                    raise ValueError(
                        (
                            f'El producto '
                            f'{producto["codigo"]} '
                            'no pertenece a la sede '
                            'seleccionada'
                        )
                    )

                # =================================================
                # INFORMACIÓN DE UNIDADES
                # =================================================

                unidades = item.get(
                    'unidades',
                    []
                )

                if unidades is None:

                    unidades = []

                if not isinstance(
                    unidades,
                    list
                ):

                    raise ValueError(
                        (
                            f'Las unidades del producto '
                            f'{producto["codigo"]} '
                            'deben ser una lista'
                        )
                    )

                # =================================================
                # PRODUCTO SERIALIZADO
                # =================================================

                if producto['requiere_serial']:

                    if len(unidades) != cantidad:

                        raise ValueError(
                            (
                                f'El producto '
                                f'{producto["codigo"]} '
                                f'requiere {cantidad} '
                                f'unidad(es) serializada(s), '
                                f'pero se recibieron '
                                f'{len(unidades)}'
                            )
                        )

                    seriales_recibidos = []

                    # =============================================
                    # PROCESAR CADA UNIDAD
                    # =============================================

                    for unidad in unidades:

                        if not isinstance(
                            unidad,
                            dict
                        ):

                            raise ValueError(
                                (
                                    'Cada unidad '
                                    'debe ser un objeto'
                                )
                            )

                        serial = unidad.get(
                            'serial'
                        )

                        if serial is None:

                            raise ValueError(
                                (
                                    f'El producto '
                                    f'{producto["codigo"]} '
                                    'requiere serial'
                                )
                            )

                        serial = str(
                            serial
                        ).strip()

                        if not serial:

                            raise ValueError(
                                (
                                    f'El producto '
                                    f'{producto["codigo"]} '
                                    'tiene una unidad '
                                    'sin serial'
                                )
                            )

                        # -----------------------------------------
                        # Serial duplicado dentro de la entrada
                        # -----------------------------------------

                        if serial in seriales_recibidos:

                            raise ValueError(
                                (
                                    f'El serial '
                                    f'"{serial}" '
                                    'está repetido '
                                    'en la entrada'
                                )
                            )

                        seriales_recibidos.append(
                            serial
                        )

                        # -----------------------------------------
                        # Modelo de ESTA unidad
                        # -----------------------------------------

                        modelo_id = unidad.get(
                            'modelo_id'
                        )

                        if not modelo_id:

                            raise ValueError(
                                (
                                    f'La unidad '
                                    f'"{serial}" '
                                    'debe tener un modelo'
                                )
                            )

                        # -----------------------------------------
                        # Verificar modelo
                        # -----------------------------------------

                        cursor.execute('''
                            SELECT
                                id,
                                marca_id,
                                nombre,
                                activo
                            FROM modelos
                            WHERE id = %s
                        ''', (modelo_id,))

                        modelo = cursor.fetchone()

                        if not modelo:

                            raise ValueError(
                                (
                                    f'El modelo '
                                    f'{modelo_id} '
                                    'no existe'
                                )
                            )

                        if not modelo['activo']:

                            raise ValueError(
                                (
                                    f'El modelo '
                                    f'{modelo["nombre"]} '
                                    'está inactivo'
                                )
                            )

                        # -----------------------------------------
                        # Verificar serial global
                        # -----------------------------------------

                        cursor.execute('''
                            SELECT
                                id
                            FROM equipos
                            WHERE serial = %s
                        ''', (serial,))

                        if cursor.fetchone():

                            raise ValueError(
                                (
                                    f'El serial '
                                    f'"{serial}" '
                                    'ya existe'
                                )
                            )

                    # =================================================
                    # INSERTAR DETALLE
                    # =================================================

                    cursor.execute('''
                        INSERT INTO detalle_entradas (
                            entrada_id,
                            producto_id,
                            cantidad,
                            observaciones
                        )

                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s
                        )

                    ''', (
                        entrada_id,
                        producto_id,
                        cantidad,
                        str(
                            item.get(
                                'observaciones',
                                ''
                            )
                        ).strip()
                    ))

                    # =================================================
                    # CREAR EQUIPOS
                    # =================================================

                    for unidad in unidades:

                        serial = str(
                            unidad['serial']
                        ).strip()

                        modelo_id = unidad.get(
                            'modelo_id'
                        )

                        cursor.execute('''
                            INSERT INTO equipos (
                                producto_id,
                                serial,
                                modelo_id,
                                condicion,
                                estado,
                                sede_id,
                                observaciones
                            )

                            VALUES (
                                %s,
                                %s,
                                %s,
                                'NUEVO',
                                'DISPONIBLE',
                                %s,
                                %s
                            )

                        ''', (
                            producto_id,
                            serial,
                            modelo_id,
                            sede_id,
                            str(
                                unidad.get(
                                    'observaciones',
                                    item.get(
                                        'observaciones',
                                        ''
                                    )
                                )
                            ).strip()
                        ))

                # =================================================
                # PRODUCTO NO SERIALIZADO
                # =================================================

                else:

                    # ---------------------------------------------
                    # No debe recibir unidades serializadas
                    # ---------------------------------------------

                    if len(unidades) > 0:

                        raise ValueError(
                            (
                                f'El producto '
                                f'{producto["codigo"]} '
                                'no requiere seriales'
                            )
                        )

                    # ---------------------------------------------
                    # Insertar detalle
                    # ---------------------------------------------

                    cursor.execute('''
                        INSERT INTO detalle_entradas (
                            entrada_id,
                            producto_id,
                            cantidad,
                            observaciones
                        )

                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s
                        )

                    ''', (
                        entrada_id,
                        producto_id,
                        cantidad,
                        str(
                            item.get(
                                'observaciones',
                                ''
                            )
                        ).strip()
                    ))

        # ========================================================
        # COMMIT
        # ========================================================

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            'ERROR AL CREAR ENTRADA:',
            repr(e)
        )

        return jsonify({
            'error': str(e)
        }), 400

    finally:

        conn.close()

    # ============================================================
    # AUDITORÍA
    # ============================================================

    try:

        registrar_auditoria(
            usuario_id=usuario_id,
            accion='CREAR',
            entidad='ENTRADA',
            entidad_id=entrada_id,
            descripcion=(
                f'Creación de entrada '
                f'{numero_documento}'
            ),
            datos_nuevos={
                'numero_documento': numero_documento,
                'sede_id': sede_id,
                'origen': origen,
                'destino': destino,
                'observaciones': observaciones
            }
        )

    except Exception as e:

        print(
            'ERROR AL REGISTRAR AUDITORIA '
            'DE ENTRADA:',
            repr(e)
        )

    return jsonify({
        'mensaje': 'Entrada registrada',
        'id': entrada_id,
        'origen': origen,
        'destino': destino
    }), 201


# ============================================================
# PUT /api/entradas/<id>/anular
# ANULAR ENTRADA
#
# SOLO ADMIN
#
# El trigger PostgreSQL revierte el inventario.
# ============================================================

@entradas_bp.route(
    '/<int:id>/anular',
    methods=['PUT']
)
@jwt_required()
def anular_entrada(id):

    claims = get_jwt()

    if claims.get('rol') != 'admin':

        return jsonify({
            'error': (
                'Solo el admin puede '
                'anular entradas'
            )
        }), 403

    datos = request.get_json(
        silent=True
    ) or {}

    motivo = datos.get(
        'motivo_anulacion',
        ''
    )

    motivo = str(
        motivo
    ).strip()

    if not motivo:

        return jsonify({
            'error': (
                'El motivo de anulación '
                'es obligatorio'
            )
        }), 400

    usuario_id = int(
        get_jwt_identity()
    )

    conn = get_connection()

    numero_documento = None
    sede_id = None

    try:

        with conn.cursor() as cursor:

            # =================================================
            # BUSCAR ENTRADA
            # =================================================

            cursor.execute('''
                SELECT
                    id,
                    numero_documento,
                    sede_id,
                    estado
                FROM entradas
                WHERE id = %s
                FOR UPDATE
            ''', (id,))

            entrada = cursor.fetchone()

            if not entrada:

                conn.rollback()

                return jsonify({
                    'error': 'Entrada no encontrada'
                }), 404

            if entrada['estado'] == 'ANULADA':

                conn.rollback()

                return jsonify({
                    'error': (
                        'La entrada '
                        'ya está anulada'
                    )
                }), 400

            numero_documento = (
                entrada['numero_documento']
            )

            sede_id = (
                entrada['sede_id']
            )

            # =================================================
            # ANULAR
            #
            # El trigger PostgreSQL
            # revierte el inventario.
            # =================================================

            cursor.execute('''
                UPDATE entradas

                SET
                    estado = 'ANULADA',
                    anulada_por = %s,
                    fecha_anulacion = CURRENT_TIMESTAMP,
                    motivo_anulacion = %s

                WHERE id = %s

            ''', (
                usuario_id,
                motivo,
                id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        print(
            'ERROR AL ANULAR ENTRADA:',
            repr(e)
        )

        return jsonify({
            'error': str(e)
        }), 400

    finally:

        conn.close()

    # ============================================================
    # AUDITORÍA
    # ============================================================

    try:

        registrar_auditoria(
            usuario_id=usuario_id,
            accion='ANULAR',
            entidad='ENTRADA',
            entidad_id=id,
            descripcion=(
                f'Anulación de entrada '
                f'{numero_documento}. '
                f'Motivo: {motivo}'
            ),
            datos_anteriores={
                'estado': 'ACTIVA',
                'sede_id': sede_id
            },
            datos_nuevos={
                'estado': 'ANULADA',
                'sede_id': sede_id,
                'motivo_anulacion': motivo
            }
        )

    except Exception as e:

        print(
            'ERROR AL REGISTRAR AUDITORIA '
            'DE ANULACION:',
            repr(e)
        )

    return jsonify({
        'mensaje': (
            'Entrada anulada correctamente'
        )
    })