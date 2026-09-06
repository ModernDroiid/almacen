from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from database import get_connection


productos_bp = Blueprint('productos', __name__)


# ============================================================
# UTILIDADES
# ============================================================

def obtener_sede_actual():
    """
    Admin:
        Puede consultar una sede específica mediante ?sede_id=ID

    Sede:
        Siempre trabaja con su propia sede.

    Consulta:
        Si no tiene sede asignada, puede consultar todas.
        Si tiene sede asignada, consulta solamente esa sede.
    """

    claims = get_jwt()
    rol = claims.get('rol')

    if rol == 'admin':
        return request.args.get('sede_id', type=int)

    return claims.get('sede_id')


def producto_pertenece_a_sede(producto_id, sede_id):
    """
    Verifica que el producto exista y pertenezca a la sede indicada.
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT id
                FROM productos
                WHERE id = %s
                  AND sede_id = %s
            ''', (
                producto_id,
                sede_id
            ))

            return cursor.fetchone() is not None

    finally:
        conn.close()


# ============================================================
# GET /api/productos/
# LISTAR PRODUCTOS
# ============================================================

@productos_bp.route('/', methods=['GET'])
@jwt_required()
def listar_productos():

    claims = get_jwt()
    rol = claims.get('rol')

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            if sede_id is None:

                # Admin sin sede seleccionada o consulta sin sede
                cursor.execute('''
                    SELECT
                        p.id,
                        p.codigo,
                        p.nombre,
                        p.descripcion,
                        u.codigo AS unidad,
                        u.nombre AS unidad_nombre,
                        p.unidad_id,
                        p.stock_minimo,
                        COALESCE(i.cantidad, 0) AS stock,
                        p.sede_id,
                        s.nombre AS sede_nombre,
                        s.ciudad,
                        p.requiere_serial,
                        p.modelo_id,
                        m.nombre AS modelo_nombre,
                        ma.id AS marca_id,
                        ma.nombre AS marca_nombre,
                        p.fecha_creacion
                    FROM productos p

                    LEFT JOIN unidades u
                        ON u.id = p.unidad_id

                    LEFT JOIN inventario i
                        ON i.producto_id = p.id
                       AND i.sede_id = p.sede_id

                    LEFT JOIN sedes s
                        ON s.id = p.sede_id

                    LEFT JOIN modelos m
                        ON m.id = p.modelo_id

                    LEFT JOIN marcas ma
                        ON ma.id = m.marca_id

                    ORDER BY p.nombre
                ''')

            else:

                cursor.execute('''
                    SELECT
                        p.id,
                        p.codigo,
                        p.nombre,
                        p.descripcion,
                        u.codigo AS unidad,
                        u.nombre AS unidad_nombre,
                        p.unidad_id,
                        p.stock_minimo,
                        COALESCE(i.cantidad, 0) AS stock,
                        p.sede_id,
                        s.nombre AS sede_nombre,
                        s.ciudad,
                        p.requiere_serial,
                        p.modelo_id,
                        m.nombre AS modelo_nombre,
                        ma.id AS marca_id,
                        ma.nombre AS marca_nombre,
                        p.fecha_creacion
                    FROM productos p

                    LEFT JOIN unidades u
                        ON u.id = p.unidad_id

                    LEFT JOIN inventario i
                        ON i.producto_id = p.id
                       AND i.sede_id = p.sede_id

                    LEFT JOIN sedes s
                        ON s.id = p.sede_id

                    LEFT JOIN modelos m
                        ON m.id = p.modelo_id

                    LEFT JOIN marcas ma
                        ON ma.id = m.marca_id

                    WHERE p.sede_id = %s

                    ORDER BY p.nombre
                ''', (sede_id,))

            productos = [
                dict(producto)
                for producto in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(productos)

# ============================================================
# GET /api/productos/<id>/equipos
# VER EQUIPOS / SERIALES DE UN PRODUCTO
# ============================================================

@productos_bp.route('/<int:id>/equipos', methods=['GET'])
@jwt_required()
def listar_equipos_producto(id):

    claims = get_jwt()
    rol = claims.get('rol')
    sede_usuario = claims.get('sede_id')

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Buscar producto
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    p.id,
                    p.codigo,
                    p.nombre,
                    p.sede_id,
                    p.requiere_serial,
                    s.nombre AS sede_nombre,
                    s.ciudad
                FROM productos p
                LEFT JOIN sedes s
                    ON s.id = p.sede_id
                WHERE p.id = %s
            ''', (id,))

            producto = cursor.fetchone()

            if not producto:
                return jsonify({
                    'error': 'Producto no encontrado'
                }), 404

            # ------------------------------------------------
            # Verificar permisos por sede
            # ------------------------------------------------

            if rol != 'admin':

                if sede_usuario is None:
                    return jsonify({
                        'error': 'El usuario no tiene una sede asignada'
                    }), 403

                if int(producto['sede_id']) != int(sede_usuario):
                    return jsonify({
                        'error': (
                            'No tienes permisos para consultar '
                            'los equipos de este producto'
                        )
                    }), 403

            # ------------------------------------------------
            # Verificar si el producto es serializado
            # ------------------------------------------------

            if not producto['requiere_serial']:

                return jsonify({
                    'producto': dict(producto),
                    'equipos': []
                })

            # ------------------------------------------------
            # Obtener equipos
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    e.id,
                    e.serial,
                    e.condicion,
                    e.estado,
                    e.sede_id,
                    e.fecha_ingreso,
                    e.observaciones,

                    mo.id AS modelo_id,
                    mo.nombre AS modelo_nombre,

                    ma.id AS marca_id,
                    ma.nombre AS marca_nombre

                FROM equipos e

                LEFT JOIN modelos mo
                    ON mo.id = e.modelo_id

                LEFT JOIN marcas ma
                    ON ma.id = mo.marca_id

                WHERE e.producto_id = %s

                ORDER BY e.id ASC
            ''', (id,))

            equipos = [
                dict(equipo)
                for equipo in cursor.fetchall()
            ]

    finally:

        conn.close()

    return jsonify({
        'producto': dict(producto),
        'equipos': equipos
    })

# ============================================================
# POST /api/productos/
# CREAR PRODUCTO
# ============================================================

@productos_bp.route('/', methods=['POST'])
@jwt_required()
def crear_producto():

    claims = get_jwt()
    rol = claims.get('rol')

    datos = request.json or {}

    # --------------------------------------------------------
    # CONSULTA NO PUEDE CREAR
    # --------------------------------------------------------

    if rol == 'consulta':
        return jsonify({
            'error': 'El usuario de consulta solo tiene permisos de visualización'
        }), 403

    # --------------------------------------------------------
    # DATOS OBLIGATORIOS
    # --------------------------------------------------------

    nombre = datos.get('nombre', '').strip()
    codigo = datos.get('codigo', '').strip()

    if not nombre:
        return jsonify({
            'error': 'El nombre es obligatorio'
        }), 400

    if not codigo:
        return jsonify({
            'error': 'El código es obligatorio'
        }), 400

    # --------------------------------------------------------
    # DETERMINAR SEDE
    # --------------------------------------------------------

    if rol == 'admin':

        sede_id = datos.get('sede_id')

        if not sede_id:
            return jsonify({
                'error': 'Selecciona una sede para el producto'
            }), 400

    else:

        sede_id = claims.get('sede_id')

        if not sede_id:
            return jsonify({
                'error': 'El usuario no tiene una sede asignada'
            }), 400

    # --------------------------------------------------------
    # DATOS DEL PRODUCTO
    # --------------------------------------------------------

    descripcion = datos.get('descripcion', '').strip()

    unidad_id = datos.get('unidad_id')

    # Compatibilidad temporal con el frontend antiguo:
    # si todavía envía "unidad": "UND", buscamos la unidad.
    if not unidad_id:

        unidad_codigo = datos.get('unidad', 'UND')

        conn_temp = get_connection()

        try:
            with conn_temp.cursor() as cursor:

                cursor.execute('''
                    SELECT id
                    FROM unidades
                    WHERE codigo = %s
                      AND activo = TRUE
                ''', (unidad_codigo,))

                unidad = cursor.fetchone()

                if unidad:
                    unidad_id = unidad['id']

        finally:
            conn_temp.close()

    if not unidad_id:
        return jsonify({
            'error': 'La unidad del producto es obligatoria'
        }), 400

    stock_minimo = datos.get('stock_minimo', 0)

    try:
        stock_minimo = int(stock_minimo)

        if stock_minimo < 0:
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({
            'error': 'El stock mínimo debe ser un número entero mayor o igual a 0'
        }), 400

    stock_inicial = datos.get('stock', 0)

    try:
        stock_inicial = int(stock_inicial)

        if stock_inicial < 0:
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({
            'error': 'El stock inicial debe ser un número entero mayor o igual a 0'
        }), 400

    requiere_serial = bool(
        datos.get('requiere_serial', False)
    )

    modelo_id = datos.get('modelo_id')

    # --------------------------------------------------------
    # CREAR PRODUCTO
    # --------------------------------------------------------

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Verificar código duplicado en la misma sede
            # ------------------------------------------------

            cursor.execute('''
                SELECT id
                FROM productos
                WHERE codigo = %s
                  AND sede_id = %s
            ''', (
                codigo,
                sede_id
            ))

            existente = cursor.fetchone()

            if existente:
                conn.rollback()

                return jsonify({
                    'error': (
                        f'Ya existe un producto con el código '
                        f'"{codigo}" en esta sede'
                    )
                }), 400

            # ------------------------------------------------
            # Verificar unidad
            # ------------------------------------------------

            cursor.execute('''
                SELECT id
                FROM unidades
                WHERE id = %s
                  AND activo = TRUE
            ''', (unidad_id,))

            if not cursor.fetchone():
                conn.rollback()

                return jsonify({
                    'error': 'La unidad seleccionada no existe o está inactiva'
                }), 400

            # ------------------------------------------------
            # Verificar modelo si fue enviado
            # ------------------------------------------------

            if modelo_id:

                cursor.execute('''
                    SELECT id
                    FROM modelos
                    WHERE id = %s
                      AND activo = TRUE
                ''', (modelo_id,))

                if not cursor.fetchone():
                    conn.rollback()

                    return jsonify({
                        'error': 'El modelo seleccionado no existe o está inactivo'
                    }), 400

            # ------------------------------------------------
            # Insertar producto
            # ------------------------------------------------

            cursor.execute('''
                INSERT INTO productos (
                    sede_id,
                    codigo,
                    nombre,
                    descripcion,
                    stock_minimo,
                    requiere_serial,
                    modelo_id,
                    unidad_id
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id
            ''', (
                sede_id,
                codigo,
                nombre,
                descripcion,
                stock_minimo,
                requiere_serial,
                modelo_id,
                unidad_id
            ))

            nuevo_id = cursor.fetchone()['id']

            # ------------------------------------------------
            # Crear inventario inicial
            # ------------------------------------------------

            cursor.execute('''
                INSERT INTO inventario (
                    producto_id,
                    sede_id,
                    cantidad,
                    fecha_actualizacion
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT (producto_id, sede_id)
                DO UPDATE SET
                    cantidad = EXCLUDED.cantidad,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            ''', (
                nuevo_id,
                sede_id,
                stock_inicial
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Producto creado',
        'id': nuevo_id
    }), 201


# ============================================================
# PUT /api/productos/<id>
# EDITAR PRODUCTO
# SOLO ADMIN
# ============================================================

@productos_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def editar_producto(id):

    claims = get_jwt()
    rol = claims.get('rol')

    # --------------------------------------------------------
    # SOLO ADMIN PUEDE EDITAR
    # --------------------------------------------------------

    if rol != 'admin':
        return jsonify({
            'error': 'Solo el admin puede editar productos'
        }), 403

    datos = request.json or {}

    nombre = datos.get('nombre', '').strip()
    codigo = datos.get('codigo', '').strip()

    if not nombre:
        return jsonify({
            'error': 'El nombre es obligatorio'
        }), 400

    if not codigo:
        return jsonify({
            'error': 'El código es obligatorio'
        }), 400

    sede_id = datos.get('sede_id')

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Buscar producto actual
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    id,
                    sede_id,
                    codigo
                FROM productos
                WHERE id = %s
            ''', (id,))

            producto = cursor.fetchone()

            if not producto:
                conn.rollback()

                return jsonify({
                    'error': 'Producto no encontrado'
                }), 404

            sede_producto = sede_id or producto['sede_id']

            # ------------------------------------------------
            # Verificar código duplicado
            # ------------------------------------------------

            cursor.execute('''
                SELECT id
                FROM productos
                WHERE codigo = %s
                  AND sede_id = %s
                  AND id <> %s
            ''', (
                codigo,
                sede_producto,
                id
            ))

            if cursor.fetchone():
                conn.rollback()

                return jsonify({
                    'error': (
                        f'Ya existe un producto con el código '
                        f'"{codigo}" en esta sede'
                    )
                }), 400

            # ------------------------------------------------
            # Unidad
            # ------------------------------------------------

            unidad_id = datos.get('unidad_id')

            if not unidad_id:

                unidad_codigo = datos.get('unidad', 'UND')

                cursor.execute('''
                    SELECT id
                    FROM unidades
                    WHERE codigo = %s
                      AND activo = TRUE
                ''', (unidad_codigo,))

                unidad = cursor.fetchone()

                if unidad:
                    unidad_id = unidad['id']

            if not unidad_id:
                conn.rollback()

                return jsonify({
                    'error': 'La unidad del producto es obligatoria'
                }), 400

            # ------------------------------------------------
            # Modelo
            # ------------------------------------------------

            modelo_id = datos.get('modelo_id')

            if modelo_id:

                cursor.execute('''
                    SELECT id
                    FROM modelos
                    WHERE id = %s
                      AND activo = TRUE
                ''', (modelo_id,))

                if not cursor.fetchone():
                    conn.rollback()

                    return jsonify({
                        'error': 'El modelo seleccionado no existe o está inactivo'
                    }), 400

            # ------------------------------------------------
            # Datos
            # ------------------------------------------------

            descripcion = datos.get('descripcion', '').strip()

            stock_minimo = datos.get('stock_minimo', 0)

            try:
                stock_minimo = int(stock_minimo)

                if stock_minimo < 0:
                    raise ValueError

            except (TypeError, ValueError):

                conn.rollback()

                return jsonify({
                    'error': 'El stock mínimo debe ser un número entero mayor o igual a 0'
                }), 400

            requiere_serial = bool(
                datos.get('requiere_serial', False)
            )

            # ------------------------------------------------
            # IMPORTANTE:
            # No permitimos modificar stock desde esta ruta.
            #
            # El stock debe cambiar únicamente mediante:
            # entradas, salidas, devoluciones y traslados.
            # ------------------------------------------------

            cursor.execute('''
                UPDATE productos
                SET
                    sede_id = %s,
                    codigo = %s,
                    nombre = %s,
                    descripcion = %s,
                    stock_minimo = %s,
                    requiere_serial = %s,
                    modelo_id = %s,
                    unidad_id = %s
                WHERE id = %s
            ''', (
                sede_producto,
                codigo,
                nombre,
                descripcion,
                stock_minimo,
                requiere_serial,
                modelo_id,
                unidad_id,
                id
            ))

            if cursor.rowcount == 0:
                conn.rollback()

                return jsonify({
                    'error': 'Producto no encontrado'
                }), 404

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Producto actualizado'
    })


# ============================================================
# DELETE /api/productos/<id>
# ELIMINAR PRODUCTO
# SOLO ADMIN
# ============================================================

@productos_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_producto(id):

    claims = get_jwt()

    # --------------------------------------------------------
    # SOLO ADMIN
    # --------------------------------------------------------

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede eliminar productos'
        }), 403

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Verificar que exista
            # ------------------------------------------------

            cursor.execute('''
                SELECT
                    id,
                    nombre,
                    sede_id
                FROM productos
                WHERE id = %s
            ''', (id,))

            producto = cursor.fetchone()

            if not producto:
                conn.rollback()

                return jsonify({
                    'error': 'Producto no encontrado'
                }), 404

            # ------------------------------------------------
            # ELIMINAR EQUIPOS ASOCIADOS
            #
            # Solo aplica al producto que estamos eliminando.
            # ------------------------------------------------

            cursor.execute('''
                DELETE FROM equipos
                WHERE producto_id = %s
            ''', (id,))

            # ------------------------------------------------
            # ELIMINAR INVENTARIO
            # ------------------------------------------------

            cursor.execute('''
                DELETE FROM inventario
                WHERE producto_id = %s
            ''', (id,))

            # ------------------------------------------------
            # ELIMINAR PRODUCTO
            # ------------------------------------------------

            cursor.execute('''
                DELETE FROM productos
                WHERE id = %s
            ''', (id,))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': (
                'No se pudo eliminar el producto. '
                'Puede tener movimientos o registros históricos asociados. '
                f'Detalle: {str(e)}'
            )
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Producto eliminado correctamente'
    })