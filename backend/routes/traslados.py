from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime, timedelta, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

traslados_bp = Blueprint('traslados', __name__)


# ============================================================
# HORA DE COLOMBIA
# ============================================================

COLOMBIA_TZ = timezone(timedelta(hours=-5))


def fecha_colombia():
    """
    Devuelve la fecha y hora actual de Colombia.
    Formato: YYYY-MM-DD HH:MM:SS
    """
    return datetime.now(COLOMBIA_TZ).strftime('%Y-%m-%d %H:%M:%S')


def obtener_sede_actual():
    claims = get_jwt()

    if claims.get('rol') == 'admin':
        return request.args.get('sede_id', type=int)

    return claims.get('sede_id')


# ============================================================
# GET /api/traslados
# Listar traslados
# ============================================================

@traslados_bp.route('/', methods=['GET'])
@jwt_required()
def listar_traslados():

    claims = get_jwt()
    rol = claims.get('rol')
    sede_id = obtener_sede_actual()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        if rol == 'admin' and sede_id is None:

            cursor.execute('''
                SELECT
                    t.id,
                    t.numero_documento,
                    t.sede_origen_id,
                    t.sede_destino_id,
                    t.observaciones,
                    t.estado,
                    t.creado_por,
                    t.recibido_por,
                    t.fecha_creacion,
                    t.fecha_recepcion,

                    so.nombre AS sede_origen_nombre,
                    so.ciudad AS sede_origen_ciudad,

                    sd.nombre AS sede_destino_nombre,
                    sd.ciudad AS sede_destino_ciudad,

                    uc.nombre AS creado_por_nombre,
                    ur.nombre AS recibido_por_nombre,

                    COUNT(dt.id) AS total_items

                FROM traslados t

                LEFT JOIN detalle_traslados dt
                    ON dt.traslado_id = t.id

                LEFT JOIN sedes so
                    ON so.id = t.sede_origen_id

                LEFT JOIN sedes sd
                    ON sd.id = t.sede_destino_id

                LEFT JOIN usuarios uc
                    ON uc.id = t.creado_por

                LEFT JOIN usuarios ur
                    ON ur.id = t.recibido_por

                GROUP BY t.id

                ORDER BY t.fecha_creacion DESC
            ''')

        else:

            cursor.execute('''
                SELECT
                    t.id,
                    t.numero_documento,
                    t.sede_origen_id,
                    t.sede_destino_id,
                    t.observaciones,
                    t.estado,
                    t.creado_por,
                    t.recibido_por,
                    t.fecha_creacion,
                    t.fecha_recepcion,

                    so.nombre AS sede_origen_nombre,
                    so.ciudad AS sede_origen_ciudad,

                    sd.nombre AS sede_destino_nombre,
                    sd.ciudad AS sede_destino_ciudad,

                    uc.nombre AS creado_por_nombre,
                    ur.nombre AS recibido_por_nombre,

                    COUNT(dt.id) AS total_items

                FROM traslados t

                LEFT JOIN detalle_traslados dt
                    ON dt.traslado_id = t.id

                LEFT JOIN sedes so
                    ON so.id = t.sede_origen_id

                LEFT JOIN sedes sd
                    ON sd.id = t.sede_destino_id

                LEFT JOIN usuarios uc
                    ON uc.id = t.creado_por

                LEFT JOIN usuarios ur
                    ON ur.id = t.recibido_por

                WHERE
                    t.sede_origen_id = ?
                    OR t.sede_destino_id = ?

                GROUP BY t.id

                ORDER BY t.fecha_creacion DESC
            ''', (sede_id, sede_id))

        traslados = [dict(x) for x in cursor.fetchall()]

        return jsonify(traslados)

    finally:
        conn.close()


# ============================================================
# GET /api/traslados/<id>
# Ver detalle
# ============================================================

@traslados_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_traslado(id):

    claims = get_jwt()
    rol = claims.get('rol')
    sede_id = claims.get('sede_id')

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute('''
            SELECT
                t.*,

                so.nombre AS sede_origen_nombre,
                so.ciudad AS sede_origen_ciudad,

                sd.nombre AS sede_destino_nombre,
                sd.ciudad AS sede_destino_ciudad,

                uc.nombre AS creado_por_nombre,
                ur.nombre AS recibido_por_nombre

            FROM traslados t

            LEFT JOIN sedes so
                ON so.id = t.sede_origen_id

            LEFT JOIN sedes sd
                ON sd.id = t.sede_destino_id

            LEFT JOIN usuarios uc
                ON uc.id = t.creado_por

            LEFT JOIN usuarios ur
                ON ur.id = t.recibido_por

            WHERE t.id = ?
        ''', (id,))

        traslado = cursor.fetchone()

        if not traslado:
            return jsonify({
                'error': 'Traslado no encontrado'
            }), 404

        traslado = dict(traslado)

        # Un usuario que no sea admin solo puede consultar
        # traslados relacionados con su sede.
        if rol != 'admin':

            if (
                traslado['sede_origen_id'] != sede_id
                and traslado['sede_destino_id'] != sede_id
            ):
                return jsonify({
                    'error': 'No autorizado'
                }), 403

        cursor.execute('''
            SELECT
                dt.id,
                dt.producto_origen_id,
                dt.producto_destino_id,
                dt.cantidad,
                dt.serial,
                dt.modelo,
                dt.marca,
                dt.unidad,

                p.codigo,
                p.nombre

            FROM detalle_traslados dt

            INNER JOIN productos p
                ON p.id = dt.producto_origen_id

            WHERE dt.traslado_id = ?

            ORDER BY dt.id
        ''', (id,))

        detalle = [dict(x) for x in cursor.fetchall()]

        traslado['detalle'] = detalle

        return jsonify(traslado)

    finally:
        conn.close()


# ============================================================
# POST /api/traslados
# Crear y enviar traslado
# ============================================================

@traslados_bp.route('/', methods=['POST'])
@jwt_required()
def crear_traslado():

    claims = get_jwt()
    rol = claims.get('rol')
    sede_usuario_id = claims.get('sede_id')

    datos = request.json or {}

    # Hora de Colombia
    ahora_colombia = datetime.now(COLOMBIA_TZ)

    # Número del documento
    numero_documento = (
        f"TR-{ahora_colombia.strftime('%Y%m%d-%H%M%S')}"
    )

    # Fecha de creación en Colombia
    fecha_creacion = ahora_colombia.strftime(
        '%Y-%m-%d %H:%M:%S'
    )

    sede_origen_id = datos.get('sede_origen_id')
    sede_destino_id = datos.get('sede_destino_id')
    detalle = datos.get('detalle')

    # ----------------------------------------------------
    # Validar permisos de origen
    # ----------------------------------------------------

    if rol not in ('admin', 'sede'):

        return jsonify({
            'error': 'No tienes permisos para crear traslados'
        }), 403

    # El almacenista SOLO puede enviar desde su propia sede
    if rol == 'sede':

        if not sede_usuario_id:

            return jsonify({
                'error': 'El usuario no tiene una sede asignada'
            }), 403

        if not sede_origen_id:
            sede_origen_id = sede_usuario_id

        if int(sede_origen_id) != int(sede_usuario_id):

            return jsonify({
                'error':
                    'Solo puedes crear traslados desde tu propia sede'
            }), 403

    if not sede_origen_id or not sede_destino_id:

        return jsonify({
            'error':
                'Debe seleccionar sede de origen y sede de destino'
        }), 400

    if int(sede_origen_id) == int(sede_destino_id):

        return jsonify({
            'error':
                'La sede de origen y destino no pueden ser iguales'
        }), 400

    if not detalle or len(detalle) == 0:

        return jsonify({
            'error':
                'Debe agregar al menos un producto'
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # ----------------------------------------------------
        # Verificar sedes
        # ----------------------------------------------------

        cursor.execute(
            '''
            SELECT id
            FROM sedes
            WHERE id=? AND activa=1
            ''',
            (sede_origen_id,)
        )

        if not cursor.fetchone():

            return jsonify({
                'error':
                    'La sede de origen no existe o está inactiva'
            }), 400

        cursor.execute(
            '''
            SELECT id
            FROM sedes
            WHERE id=? AND activa=1
            ''',
            (sede_destino_id,)
        )

        if not cursor.fetchone():

            return jsonify({
                'error':
                    'La sede de destino no existe o está inactiva'
            }), 400

        # ----------------------------------------------------
        # Verificar documento duplicado
        # ----------------------------------------------------

        cursor.execute(
            '''
            SELECT id
            FROM traslados
            WHERE numero_documento=?
            ''',
            (numero_documento,)
        )

        if cursor.fetchone():

            return jsonify({
                'error':
                    'Ya existe un traslado con ese numero de documento'
            }), 400

        # ----------------------------------------------------
        # Validar productos y stock
        # ----------------------------------------------------

        productos_validos = []

        for item in detalle:

            producto_id = item.get('producto_id')
            cantidad = item.get('cantidad')

            if not producto_id or not cantidad:

                return jsonify({
                    'error':
                        'Cada producto debe tener producto_id y cantidad'
                }), 400

            cantidad = int(cantidad)

            if cantidad <= 0:

                return jsonify({
                    'error':
                        'La cantidad debe ser mayor que cero'
                }), 400

            cursor.execute('''
                SELECT
                    id,
                    codigo,
                    nombre,
                    stock,
                    sede_id,
                    unidad
                FROM productos
                WHERE id=?
            ''', (producto_id,))

            producto = cursor.fetchone()

            if not producto:

                return jsonify({
                    'error':
                        f'Producto {producto_id} no encontrado'
                }), 400

            if producto['sede_id'] != int(sede_origen_id):

                return jsonify({
                    'error':
                        f'El producto "{producto["nombre"]}" '
                        'no pertenece a la sede de origen'
                }), 400

            if producto['stock'] < cantidad:

                return jsonify({
                    'error':
                        f'Stock insuficiente para '
                        f'"{producto["nombre"]}". '
                        f'Disponible: {producto["stock"]}. '
                        f'Solicitado: {cantidad}.'
                }), 400

            productos_validos.append({
                'producto': producto,
                'cantidad': cantidad,
                'item': item
            })

        # ----------------------------------------------------
        # Crear traslado
        # ----------------------------------------------------

        cursor.execute('''
            INSERT INTO traslados
                (
                    numero_documento,
                    sede_origen_id,
                    sede_destino_id,
                    observaciones,
                    estado,
                    creado_por,
                    fecha_creacion
                )
            VALUES (?, ?, ?, ?, 'PENDIENTE', ?, ?)
        ''', (
            numero_documento,
            sede_origen_id,
            sede_destino_id,
            datos.get('observaciones', ''),
            int(get_jwt_identity()),
            fecha_creacion
        ))

        traslado_id = cursor.lastrowid

        # ----------------------------------------------------
        # Detalle + descuento de stock
        # ----------------------------------------------------

        for item in productos_validos:

            producto = item['producto']
            datos_item = item['item']
            cantidad = item['cantidad']

            cursor.execute('''
                INSERT INTO detalle_traslados
                    (
                        traslado_id,
                        producto_origen_id,
                        producto_destino_id,
                        cantidad,
                        serial,
                        modelo,
                        marca,
                        unidad
                    )
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?)
            ''', (
                traslado_id,
                producto['id'],
                cantidad,
                datos_item.get('serial', ''),
                datos_item.get('modelo', ''),
                datos_item.get('marca', ''),
                datos_item.get(
                    'unidad',
                    producto['unidad'] or 'UND'
                )
            ))

            cursor.execute('''
                UPDATE productos
                SET stock = stock - ?
                WHERE id = ?
            ''', (
                cantidad,
                producto['id']
            ))

        conn.commit()

        return jsonify({
            'mensaje':
                'Traslado creado y enviado correctamente',
            'id': traslado_id,
            'estado': 'PENDIENTE'
        }), 201

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 500

    finally:
        conn.close()


# ============================================================
# PUT /api/traslados/<id>/recibir
# Recibir traslado
# ============================================================

@traslados_bp.route('/<int:id>/recibir', methods=['PUT'])
@jwt_required()
def recibir_traslado(id):

    claims = get_jwt()

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute('''
            SELECT
                id,
                sede_origen_id,
                sede_destino_id,
                estado
            FROM traslados
            WHERE id=?
        ''', (id,))

        traslado = cursor.fetchone()

        if not traslado:

            return jsonify({
                'error': 'Traslado no encontrado'
            }), 404

        # ----------------------------------------------------
        # Solo admin puede recibir
        # ----------------------------------------------------

        if claims.get('rol') != 'admin':

            return jsonify({
                'error':
                    'Solo el administrador puede recibir traslados'
            }), 403

        # ----------------------------------------------------
        # Verificar estado
        # ----------------------------------------------------

        if traslado['estado'] != 'PENDIENTE':

            return jsonify({
                'error':
                    f'El traslado ya está en estado '
                    f'{traslado["estado"]}'
            }), 400

        sede_destino_id = traslado['sede_destino_id']

        # ----------------------------------------------------
        # Obtener productos
        # ----------------------------------------------------

        cursor.execute('''
            SELECT
                id,
                producto_origen_id,
                cantidad,
                serial,
                modelo,
                marca,
                unidad
            FROM detalle_traslados
            WHERE traslado_id=?
        ''', (id,))

        items = cursor.fetchall()

        if not items:

            return jsonify({
                'error':
                    'El traslado no tiene productos'
            }), 400

        # ----------------------------------------------------
        # Pasar productos a sede destino
        # ----------------------------------------------------

        for item in items:

            producto_origen_id = item['producto_origen_id']

            cursor.execute('''
                SELECT
                    codigo,
                    nombre,
                    descripcion,
                    unidad
                FROM productos
                WHERE id=?
            ''', (producto_origen_id,))

            producto = cursor.fetchone()

            if not producto:

                return jsonify({
                    'error':
                        f'Producto origen '
                        f'{producto_origen_id} no encontrado'
                }), 400

            codigo = producto['codigo']

            # Buscar producto equivalente en la sede destino
            cursor.execute('''
                SELECT id
                FROM productos
                WHERE codigo=?
                  AND sede_id=?
            ''', (
                codigo,
                sede_destino_id
            ))

            producto_destino = cursor.fetchone()

            if producto_destino:

                destino_id = producto_destino['id']

                cursor.execute('''
                    UPDATE productos
                    SET stock = stock + ?
                    WHERE id=?
                ''', (
                    item['cantidad'],
                    destino_id
                ))

            else:

                cursor.execute('''
                    INSERT INTO productos
                        (
                            codigo,
                            nombre,
                            descripcion,
                            unidad,
                            stock,
                            stock_minimo,
                            sede_id
                        )
                    SELECT
                        codigo,
                        nombre,
                        descripcion,
                        unidad,
                        ?,
                        stock_minimo,
                        ?
                    FROM productos
                    WHERE id=?
                ''', (
                    item['cantidad'],
                    sede_destino_id,
                    producto_origen_id
                ))

                destino_id = cursor.lastrowid

            # Guardamos qué producto terminó en destino
            cursor.execute('''
                UPDATE detalle_traslados
                SET producto_destino_id=?
                WHERE id=?
            ''', (
                destino_id,
                item['id']
            ))

        # ----------------------------------------------------
        # Marcar recibido
        # ----------------------------------------------------

        fecha_recepcion = fecha_colombia()

        cursor.execute('''
            UPDATE traslados
            SET
                estado='RECIBIDO',
                recibido_por=?,
                fecha_recepcion=?
            WHERE id=?
        ''', (
            int(get_jwt_identity()),
            fecha_recepcion,
            id
        ))

        conn.commit()

        return jsonify({
            'mensaje':
                'Traslado recibido correctamente',
            'estado':
                'RECIBIDO'
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 500

    finally:
        conn.close()