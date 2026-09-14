# ============================================================
# catalogos.py — Marcas, Modelos y Unidades
#
# ROLES:
#   admin     → ver, crear, editar y eliminar
#   sede      → ver, y crear marcas/modelos nuevos "sobre la
#               marcha" (por ejemplo al registrar un equipo
#               serializado con una marca/modelo que aún no
#               existe en el catálogo) — pero NO puede editar
#               ni eliminar
#   consulta  → consultar
#
# PostgreSQL
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt

from database import get_connection


catalogos_bp = Blueprint('catalogos', __name__)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def es_admin():
    claims = get_jwt()
    return claims.get('rol') == 'admin'


def requiere_admin():
    """
    Verifica que el usuario sea administrador.
    Devuelve None si puede continuar.
    Devuelve una respuesta HTTP si no tiene permisos.
    """

    if not es_admin():
        return jsonify({
            'error': 'No tienes permisos para realizar esta acción'
        }), 403

    return None


def requiere_admin_o_sede():
    """
    Verifica que el usuario sea admin O de sede (almacenista).

    Se usa SOLO para crear (POST) marcas/modelos: un almacenista
    necesita poder dar de alta una marca/modelo nuevo al registrar
    un equipo serializado que no coincide con nada del catálogo,
    sin tener que pedirle el favor al admin cada vez.

    Editar y eliminar catálogo sigue siendo exclusivo de admin
    (ver requiere_admin) — esto no le abre esa puerta.

    Devuelve None si puede continuar.
    Devuelve una respuesta HTTP si no tiene permisos.
    """

    claims = get_jwt()

    if claims.get('rol') not in ('admin', 'sede'):
        return jsonify({
            'error': 'No tienes permisos para realizar esta acción'
        }), 403

    return None


# ============================================================
# MARCAS
# ============================================================

# GET /api/catalogos/marcas
@catalogos_bp.route('/marcas', methods=['GET'])
@jwt_required()
def listar_marcas():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    id,
                    nombre,
                    activa,
                    fecha_creacion
                FROM marcas
                WHERE activa = TRUE
                ORDER BY nombre
            ''')

            marcas = [
                dict(marca)
                for marca in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(marcas)


# POST /api/catalogos/marcas
@catalogos_bp.route('/marcas', methods=['POST'])
@jwt_required()
def agregar_marca():

    permiso = requiere_admin_o_sede()

    if permiso:
        return permiso

    datos = request.get_json() or {}

    nombre = datos.get('nombre', '').strip()

    if not nombre:
        return jsonify({
            'error': 'El nombre es obligatorio'
        }), 400

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # Verificar duplicado
            cursor.execute('''
                SELECT id
                FROM marcas
                WHERE LOWER(nombre) = LOWER(%s)
            ''', (nombre,))

            if cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': f'La marca "{nombre}" ya existe'
                }), 400

            cursor.execute('''
                INSERT INTO marcas (
                    nombre
                )
                VALUES (%s)
                RETURNING id
            ''', (nombre,))

            nuevo_id = cursor.fetchone()['id']

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Marca creada',
        'id': nuevo_id
    }), 201


# PUT /api/catalogos/marcas/<id>
@catalogos_bp.route('/marcas/<int:id>', methods=['PUT'])
@jwt_required()
def editar_marca(id):

    permiso = requiere_admin()

    if permiso:
        return permiso

    datos = request.get_json() or {}

    nombre = datos.get('nombre', '').strip()

    if not nombre:
        return jsonify({
            'error': 'El nombre es obligatorio'
        }), 400

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # Verificar que exista
            cursor.execute('''
                SELECT id
                FROM marcas
                WHERE id = %s
            ''', (id,))

            if not cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': 'Marca no encontrada'
                }), 404

            # Verificar duplicado
            cursor.execute('''
                SELECT id
                FROM marcas
                WHERE LOWER(nombre) = LOWER(%s)
                  AND id <> %s
            ''', (
                nombre,
                id
            ))

            if cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': f'La marca "{nombre}" ya existe'
                }), 400

            cursor.execute('''
                UPDATE marcas
                SET nombre = %s
                WHERE id = %s
            ''', (
                nombre,
                id
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
        'mensaje': 'Marca actualizada'
    })


# DELETE /api/catalogos/marcas/<id>
@catalogos_bp.route('/marcas/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_marca(id):

    permiso = requiere_admin()

    if permiso:
        return permiso

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # Verificar existencia
            cursor.execute('''
                SELECT id
                FROM marcas
                WHERE id = %s
            ''', (id,))

            if not cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': 'Marca no encontrada'
                }), 404

            # No hacemos DELETE físico.
            # La desactivamos para conservar historial.
            cursor.execute('''
                UPDATE marcas
                SET activa = FALSE
                WHERE id = %s
            ''', (id,))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': (
                'No se puede eliminar la marca. '
                f'Detalle: {str(e)}'
            )
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Marca desactivada'
    })


# ============================================================
# MODELOS
# ============================================================

# GET /api/catalogos/modelos
@catalogos_bp.route('/modelos', methods=['GET'])
@jwt_required()
def listar_modelos():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    m.id,
                    m.nombre,
                    m.descripcion,
                    m.activo,
                    m.marca_id,
                    ma.nombre AS marca_nombre,
                    m.fecha_creacion
                FROM modelos m

                LEFT JOIN marcas ma
                    ON ma.id = m.marca_id

                WHERE m.activo = TRUE

                ORDER BY ma.nombre, m.nombre
            ''')

            modelos = [
                dict(modelo)
                for modelo in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(modelos)


# POST /api/catalogos/modelos
@catalogos_bp.route('/modelos', methods=['POST'])
@jwt_required()
def agregar_modelo():

    permiso = requiere_admin_o_sede()

    if permiso:
        return permiso

    datos = request.get_json() or {}

    nombre = datos.get('nombre', '').strip()
    marca_id = datos.get('marca_id')
    descripcion = datos.get('descripcion', '').strip()

    if not nombre:
        return jsonify({
            'error': 'El nombre del modelo es obligatorio'
        }), 400

    if not marca_id:
        return jsonify({
            'error': 'La marca es obligatoria'
        }), 400

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # Verificar marca
            cursor.execute('''
                SELECT id
                FROM marcas
                WHERE id = %s
                  AND activa = TRUE
            ''', (marca_id,))

            if not cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': 'La marca seleccionada no existe o está inactiva'
                }), 400

            # Verificar modelo duplicado dentro de la marca
            cursor.execute('''
                SELECT id
                FROM modelos
                WHERE marca_id = %s
                  AND LOWER(nombre) = LOWER(%s)
            ''', (
                marca_id,
                nombre
            ))

            if cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': (
                        f'El modelo "{nombre}" ya existe '
                        'para esta marca'
                    )
                }), 400

            cursor.execute('''
                INSERT INTO modelos (
                    marca_id,
                    nombre,
                    descripcion
                )
                VALUES (%s, %s, %s)
                RETURNING id
            ''', (
                marca_id,
                nombre,
                descripcion
            ))

            nuevo_id = cursor.fetchone()['id']

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Modelo creado',
        'id': nuevo_id
    }), 201


# PUT /api/catalogos/modelos/<id>
@catalogos_bp.route('/modelos/<int:id>', methods=['PUT'])
@jwt_required()
def editar_modelo(id):

    permiso = requiere_admin()

    if permiso:
        return permiso

    datos = request.get_json() or {}

    nombre = datos.get('nombre', '').strip()
    marca_id = datos.get('marca_id')
    descripcion = datos.get('descripcion', '').strip()

    if not nombre:
        return jsonify({
            'error': 'El nombre del modelo es obligatorio'
        }), 400

    if not marca_id:
        return jsonify({
            'error': 'La marca es obligatoria'
        }), 400

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            # Verificar modelo
            cursor.execute('''
                SELECT id
                FROM modelos
                WHERE id = %s
            ''', (id,))

            if not cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': 'Modelo no encontrado'
                }), 404

            # Verificar marca
            cursor.execute('''
                SELECT id
                FROM marcas
                WHERE id = %s
                  AND activa = TRUE
            ''', (marca_id,))

            if not cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': 'La marca seleccionada no existe o está inactiva'
                }), 400

            # Verificar duplicado
            cursor.execute('''
                SELECT id
                FROM modelos
                WHERE marca_id = %s
                  AND LOWER(nombre) = LOWER(%s)
                  AND id <> %s
            ''', (
                marca_id,
                nombre,
                id
            ))

            if cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': (
                        f'El modelo "{nombre}" ya existe '
                        'para esta marca'
                    )
                }), 400

            cursor.execute('''
                UPDATE modelos
                SET
                    marca_id = %s,
                    nombre = %s,
                    descripcion = %s
                WHERE id = %s
            ''', (
                marca_id,
                nombre,
                descripcion,
                id
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
        'mensaje': 'Modelo actualizado'
    })


# DELETE /api/catalogos/modelos/<id>
@catalogos_bp.route('/modelos/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_modelo(id):

    permiso = requiere_admin()

    if permiso:
        return permiso

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT id
                FROM modelos
                WHERE id = %s
            ''', (id,))

            if not cursor.fetchone():

                conn.rollback()

                return jsonify({
                    'error': 'Modelo no encontrado'
                }), 404

            # Desactivación lógica.
            # No borramos para conservar historial.
            cursor.execute('''
                UPDATE modelos
                SET activo = FALSE
                WHERE id = %s
            ''', (id,))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': (
                'No se puede eliminar el modelo. '
                f'Detalle: {str(e)}'
            )
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Modelo desactivado'
    })


# ============================================================
# UNIDADES
# ============================================================

# GET /api/catalogos/unidades
@catalogos_bp.route('/unidades', methods=['GET'])
@jwt_required()
def listar_unidades():

    conn = get_connection()

    try:

        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    id,
                    codigo,
                    nombre,
                    activo
                FROM unidades
                WHERE activo = TRUE
                ORDER BY nombre
            ''')

            unidades = [
                dict(unidad)
                for unidad in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(unidades)