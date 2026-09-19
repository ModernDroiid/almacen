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
from werkzeug.security import generate_password_hash, check_password_hash
from utils.auditoria import registrar_auditoria
import hashlib

from extensions import limiter


auth_bp = Blueprint('auth', __name__)


# ============================================================
# UTILIDADES DE CONTRASEÑA
#
# Las contraseñas nuevas (o cuando alguien cambia la suya) se
# guardan con werkzeug (pbkdf2 + sal), que es lento a propósito
# y usa una sal distinta por usuario — mucho más seguro que un
# SHA-256 plano.
#
# Las contraseñas viejas de este sistema se guardaron con
# SHA-256 sin sal (siempre 64 caracteres en hexadecimal). Para
# no obligar a resetear la contraseña de todos los usuarios de
# un día para otro, "verificar_password" reconoce ese formato
# viejo, y en cuanto alguien inicia sesión con éxito, "login()"
# la vuelve a guardar ya en el formato nuevo. Con el tiempo,
# todas las contraseñas activas terminan migradas solas.
# ============================================================

def hash_password(password):
    return generate_password_hash(password)


def es_hash_antiguo(hash_guardado):
    return (
        bool(hash_guardado)
        and len(hash_guardado) == 64
        and all(
            c in '0123456789abcdef'
            for c in hash_guardado.lower()
        )
    )


def verificar_password(password, hash_guardado):

    if not hash_guardado:
        return False

    if es_hash_antiguo(hash_guardado):
        return (
            hashlib.sha256(password.encode()).hexdigest()
            == hash_guardado
        )

    return check_password_hash(hash_guardado, password)


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
                    u.password_hash,
                    s.nombre AS sede_nombre,
                    s.ciudad
                FROM usuarios u
                LEFT JOIN sedes s
                    ON s.id = u.sede_id
                WHERE
                    u.correo = %s
                    AND u.activo = TRUE
            ''', (
                correo,
            ))

            usuario = cursor.fetchone()

            if not usuario or not verificar_password(
                password,
                usuario['password_hash']
            ):
                return jsonify({
                    'error': 'Email o contraseña incorrectos'
                }), 401

            # ================================================
            # MIGRACIÓN SILENCIOSA AL HASH SEGURO
            #
            # Si esta contraseña todavía estaba en el formato
            # viejo (SHA-256 sin sal), ya la validamos arriba;
            # ahora la reescribimos con el método seguro para
            # que no se vuelva a comparar con el método viejo.
            # ================================================

            if es_hash_antiguo(usuario['password_hash']):

                cursor.execute('''
                    UPDATE usuarios
                    SET password_hash = %s
                    WHERE id = %s
                ''', (
                    generate_password_hash(password),
                    usuario['id']
                ))

                conn.commit()

    finally:
        conn.close()

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
    if claims.get('rol') not in ('admin', 'sede', 'consulta'):
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

    # La auditoría queda en su propia transacción (así lo maneja
    # registrar_auditoria), así que se registra ya con el usuario
    # creado y confirmado. Si esto llegara a fallar, no se le
    # regresa un error al admin por algo que en realidad sí pasó.
    try:
        registrar_auditoria(
            usuario_id=int(get_jwt_identity()),
            accion="CREAR",
            entidad="USUARIO",
            entidad_id=nuevo_id,
            descripcion=(
                f'Creó al usuario "{nombre}" ({correo}) '
                f'con rol "{rol}"'
            ),
            datos_nuevos={
                'nombre': nombre,
                'correo': correo,
                'rol': rol,
                'sede_id': sede_id
            }
        )
    except Exception:
        pass

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

            # Se guarda cómo estaba el usuario antes del cambio,
            # para que quede en el "datos_anteriores" de la
            # auditoría (además del nombre, que se usa en el
            # mensaje de todas formas).
            cursor.execute('''
                SELECT nombre, correo, rol, sede_id
                FROM usuarios
                WHERE id = %s
            ''', (id,))

            usuario_anterior = cursor.fetchone()

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

            se_cambio_password = bool(datos.get('password'))

            # Si se envió una nueva contraseña,
            # también se actualiza.
            if se_cambio_password:

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

    try:
        registrar_auditoria(
            usuario_id=int(get_jwt_identity()),
            accion="EDITAR",
            entidad="USUARIO",
            entidad_id=id,
            descripcion=(
                f'Editó al usuario "{nombre}" ({correo}), rol "{rol}"'
                + (
                    ' y le cambió la contraseña'
                    if se_cambio_password
                    else ''
                )
            ),
            datos_anteriores=(
                dict(usuario_anterior) if usuario_anterior else None
            ),
            datos_nuevos={
                'nombre': nombre,
                'correo': correo,
                'rol': rol,
                'sede_id': sede_id
            }
        )
    except Exception:
        pass

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

    # Nunca se guardan contraseñas (ni en texto plano ni en hash)
    # en el registro de auditoría, solo el hecho de que se cambió.
    try:
        registrar_auditoria(
            usuario_id=usuario_actual,
            accion="CAMBIAR_PASSWORD",
            entidad="USUARIO",
            entidad_id=id,
            descripcion=(
                'Cambió su propia contraseña'
                if usuario_actual == id
                else f'Cambió la contraseña del usuario id {id}'
            )
        )
    except Exception:
        pass

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

    try:
        registrar_auditoria(
            usuario_id=int(get_jwt_identity()),
            accion="ACTIVAR" if nuevo_estado else "DESACTIVAR",
            entidad="USUARIO",
            entidad_id=id,
            descripcion=(
                f'{"Activó" if nuevo_estado else "Desactivó"} '
                f'al usuario id {id}'
            ),
            datos_anteriores={'activo': usuario['activo']},
            datos_nuevos={'activo': nuevo_estado}
        )
    except Exception:
        pass

    return jsonify({
        'mensaje': 'Estado actualizado',
        'activo': nuevo_estado
    })