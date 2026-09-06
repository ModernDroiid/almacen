# ============================================================
# auth.py — Autenticación con JWT
# PostgreSQL
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from database import get_connection
import hashlib

from extensions import limiter


auth_bp = Blueprint('auth', __name__)


# ============================================================
# UTILIDADES
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ============================================================
# POST /api/auth/login
# ============================================================

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():

    datos = request.json or {}

    correo = datos.get('email', '').strip().lower()
    password = datos.get('password', '')

    if not correo or not password:
        return jsonify({
            'error': 'Email y contraseña son obligatorios'
        }), 400

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    u.id,
                    u.nombre,
                    u.correo,
                    u.rol,
                    u.sede_id,
                    s.nombre AS sede_nombre,
                    s.ciudad
                FROM usuarios u
                LEFT JOIN sedes s
                    ON s.id = u.sede_id
                WHERE
                    u.correo = %s
                    AND u.password_hash = %s
                    AND u.activo = TRUE
            ''', (
                correo,
                hash_password(password)
            ))

            usuario = cursor.fetchone()

    finally:
        conn.close()

    if not usuario:
        return jsonify({
            'error': 'Email o contraseña incorrectos'
        }), 401

    token = create_access_token(
        identity=str(usuario['id']),
        additional_claims={
            'rol': usuario['rol'],
            'sede_id': usuario['sede_id'],
            'nombre': usuario['nombre'],
            'sede_nombre': usuario['sede_nombre'],
            'ciudad': usuario['ciudad']
        }
    )

    return jsonify({
        'token': token,
        'nombre': usuario['nombre'],
        'rol': usuario['rol'],
        'sede_id': usuario['sede_id'],
        'sede_nombre': usuario['sede_nombre'],
        'ciudad': usuario['ciudad']
    })


# ============================================================
# GET /api/auth/me
# ============================================================

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():

    claims = get_jwt()

    return jsonify({
        'id': get_jwt_identity(),
        'rol': claims.get('rol'),
        'sede_id': claims.get('sede_id'),
        'nombre': claims.get('nombre'),
        'sede_nombre': claims.get('sede_nombre'),
        'ciudad': claims.get('ciudad')
    })


# ============================================================
# GET /api/auth/sedes
# ============================================================

@auth_bp.route('/sedes', methods=['GET'])
@jwt_required()
def listar_sedes():

    claims = get_jwt()

    # Admin y usuarios de sede pueden consultar las sedes
    if claims.get('rol') not in ('admin', 'sede'):
        return jsonify({
            'error': 'No tienes permisos para consultar las sedes'
        }), 403

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    id,
                    nombre,
                    ciudad,
                    activa
                FROM sedes
                WHERE activa = TRUE
                ORDER BY nombre
            ''')

            sedes = [dict(sede) for sede in cursor.fetchall()]

    finally:
        conn.close()

    return jsonify(sedes)


# ============================================================
# POST /api/auth/sedes
# ============================================================

@auth_bp.route('/sedes', methods=['POST'])
@jwt_required()
def crear_sede():

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede crear sedes'
        }), 403

    datos = request.json or {}

    nombre = datos.get('nombre', '').strip()
    ciudad = datos.get('ciudad', '').strip()

    if not nombre or not ciudad:
        return jsonify({
            'error': 'Nombre y ciudad son obligatorios'
        }), 400

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                INSERT INTO sedes (
                    nombre,
                    ciudad
                )
                VALUES (%s, %s)
                RETURNING id
            ''', (
                nombre,
                ciudad
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
        'mensaje': 'Sede creada',
        'id': nuevo_id
    }), 201


# ============================================================
# GET /api/auth/usuarios
# ============================================================

@auth_bp.route('/usuarios', methods=['GET'])
@jwt_required()
def listar_usuarios():

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede ver usuarios'
        }), 403

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    u.id,
                    u.nombre,
                    u.correo AS email,
                    u.rol,
                    u.activo,
                    s.nombre AS sede_nombre,
                    u.sede_id
                FROM usuarios u
                LEFT JOIN sedes s
                    ON s.id = u.sede_id
                ORDER BY u.nombre
            ''')

            usuarios = [
                dict(usuario)
                for usuario in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(usuarios)


# ============================================================
# POST /api/auth/usuarios
# ============================================================

@auth_bp.route('/usuarios', methods=['POST'])
@jwt_required()
def crear_usuario():

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede crear usuarios'
        }), 403

    datos = request.json or {}

    nombre = datos.get('nombre', '').strip()
    correo = datos.get('email', '').strip().lower()
    password = datos.get('password', '')
    rol = datos.get('rol', 'sede')
    sede_id = datos.get('sede_id')

    if not nombre or not correo or not password:
        return jsonify({
            'error': 'Nombre, email y contraseña son obligatorios'
        }), 400

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                INSERT INTO usuarios (
                    nombre,
                    correo,
                    password_hash,
                    rol,
                    sede_id
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                nombre,
                correo,
                hash_password(password),
                rol,
                sede_id
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
        'mensaje': 'Usuario creado',
        'id': nuevo_id
    }), 201


# ============================================================
# PUT /api/auth/usuarios/<id>
# ============================================================

@auth_bp.route('/usuarios/<int:id>', methods=['PUT'])
@jwt_required()
def editar_usuario(id):

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede editar usuarios'
        }), 403

    datos = request.json or {}

    nombre = datos.get('nombre', '').strip()
    correo = datos.get('email', '').strip().lower()
    rol = datos.get('rol', 'sede')
    sede_id = datos.get('sede_id')

    if not nombre or not correo:
        return jsonify({
            'error': 'Nombre y email son obligatorios'
        }), 400

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                UPDATE usuarios
                SET
                    nombre = %s,
                    correo = %s,
                    rol = %s,
                    sede_id = %s
                WHERE id = %s
            ''', (
                nombre,
                correo,
                rol,
                sede_id,
                id
            ))

            if cursor.rowcount == 0:
                conn.rollback()

                return jsonify({
                    'error': 'Usuario no encontrado'
                }), 404

            # Si se envió una nueva contraseña,
            # también se actualiza.
            if datos.get('password'):

                cursor.execute('''
                    UPDATE usuarios
                    SET password_hash = %s
                    WHERE id = %s
                ''', (
                    hash_password(datos['password']),
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
        'mensaje': 'Usuario actualizado'
    })


# ============================================================
# PUT /api/auth/usuarios/<id>/password
# ============================================================

@auth_bp.route('/usuarios/<int:id>/password', methods=['PUT'])
@jwt_required()
def cambiar_password(id):

    claims = get_jwt()

    usuario_actual = int(get_jwt_identity())

    # Admin puede cambiar cualquier contraseña.
    # Un usuario normal solamente puede cambiar la suya.
    if claims.get('rol') != 'admin' and usuario_actual != id:
        return jsonify({
            'error': 'No autorizado'
        }), 403

    datos = request.json or {}

    password = datos.get('password', '')

    if not password:
        return jsonify({
            'error': 'La contraseña es obligatoria'
        }), 400

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                UPDATE usuarios
                SET password_hash = %s
                WHERE id = %s
            ''', (
                hash_password(password),
                id
            ))

            if cursor.rowcount == 0:
                conn.rollback()

                return jsonify({
                    'error': 'Usuario no encontrado'
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
        'mensaje': 'Contraseña actualizada'
    })


# ============================================================
# PUT /api/auth/usuarios/<id>/toggle
# ============================================================

@auth_bp.route('/usuarios/<int:id>/toggle', methods=['PUT'])
@jwt_required()
def toggle_usuario(id):

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede activar/desactivar usuarios'
        }), 403

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT activo
                FROM usuarios
                WHERE id = %s
            ''', (id,))

            usuario = cursor.fetchone()

            if not usuario:
                conn.rollback()

                return jsonify({
                    'error': 'Usuario no encontrado'
                }), 404

            nuevo_estado = not usuario['activo']

            cursor.execute('''
                UPDATE usuarios
                SET activo = %s
                WHERE id = %s
            ''', (
                nuevo_estado,
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
        'mensaje': 'Estado actualizado',
        'activo': nuevo_estado
    })