# ============================================================
# auth.py — Autenticacion con JWT
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from database import get_connection
import hashlib

auth_bp = Blueprint('auth', __name__)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ── POST /api/auth/login ─────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    datos = request.json
    correo   = datos.get('email', '').strip().lower()
    password = datos.get('password', '')

    if not correo or not password:
        return jsonify({'error': 'Email y contraseña son obligatorios'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.nombre, u.correo, u.rol, u.sede_id,
               s.nombre as sede_nombre, s.ciudad
        FROM usuarios u
        LEFT JOIN sedes s ON s.id = u.sede_id
        WHERE u.correo = ? AND u.password_hash = ? AND u.activo = 1
    ''', (correo, hash_password(password)))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario:
        return jsonify({'error': 'Email o contraseña incorrectos'}), 401

    usuario = dict(usuario)

    token = create_access_token(
        identity=str(usuario['id']),
        additional_claims={
            'rol':         usuario['rol'],
            'sede_id':     usuario['sede_id'],
            'nombre':      usuario['nombre'],
            'sede_nombre': usuario['sede_nombre'],
            'ciudad':      usuario['ciudad']
        }
    )

    return jsonify({
        'token':       token,
        'nombre':      usuario['nombre'],
        'rol':         usuario['rol'],
        'sede_id':     usuario['sede_id'],
        'sede_nombre': usuario['sede_nombre'],
        'ciudad':      usuario['ciudad']
    })


# ── GET /api/auth/me ─────────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    claims = get_jwt()
    return jsonify({
        'id':          get_jwt_identity(),
        'rol':         claims.get('rol'),
        'sede_id':     claims.get('sede_id'),
        'nombre':      claims.get('nombre'),
        'sede_nombre': claims.get('sede_nombre'),
        'ciudad':      claims.get('ciudad')
    })


# ── GET /api/auth/sedes ──────────────────────────────────────
@auth_bp.route('/sedes', methods=['GET'])
@jwt_required()
def listar_sedes():
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo el admin puede ver las sedes'}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM sedes WHERE activa=1 ORDER BY nombre')
    sedes = [dict(s) for s in cursor.fetchall()]
    conn.close()
    return jsonify(sedes)


# ── POST /api/auth/sedes ─────────────────────────────────────
@auth_bp.route('/sedes', methods=['POST'])
@jwt_required()
def crear_sede():
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo el admin puede crear sedes'}), 403

    datos = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO sedes (nombre, ciudad) VALUES (?, ?)',
        (datos['nombre'], datos['ciudad'])
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return jsonify({'mensaje': 'Sede creada', 'id': nuevo_id}), 201


# ── GET /api/auth/usuarios ───────────────────────────────────
@auth_bp.route('/usuarios', methods=['GET'])
@jwt_required()
def listar_usuarios():
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo el admin puede ver usuarios'}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.id, u.nombre, u.correo as email, u.rol, u.activo,
               s.nombre as sede_nombre, u.sede_id
        FROM usuarios u
        LEFT JOIN sedes s ON s.id = u.sede_id
        ORDER BY u.nombre
    ''')
    usuarios = [dict(u) for u in cursor.fetchall()]
    conn.close()
    return jsonify(usuarios)


# ── POST /api/auth/usuarios ──────────────────────────────────
@auth_bp.route('/usuarios', methods=['POST'])
@jwt_required()
def crear_usuario():
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo el admin puede crear usuarios'}), 403

    datos = request.json
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO usuarios (nombre, correo, password_hash, rol, sede_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datos['nombre'],
            datos['email'].lower(),
            hash_password(datos['password']),
            datos.get('rol', 'sede'),
            datos.get('sede_id')
        ))
        conn.commit()
        nuevo_id = cursor.lastrowid
        conn.close()
        return jsonify({'mensaje': 'Usuario creado', 'id': nuevo_id}), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400


# ── PUT /api/auth/usuarios/<id> ──────────────────────────────
@auth_bp.route('/usuarios/<int:id>', methods=['PUT'])
@jwt_required()
def editar_usuario(id):
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo el admin puede editar usuarios'}), 403

    datos = request.json
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE usuarios
            SET nombre=?, correo=?, rol=?, sede_id=?
            WHERE id=?
        ''', (
            datos['nombre'],
            datos['email'].lower(),
            datos.get('rol', 'sede'),
            datos.get('sede_id'),
            id
        ))

        if datos.get('password'):
            cursor.execute(
                'UPDATE usuarios SET password_hash=? WHERE id=?',
                (hash_password(datos['password']), id)
            )

        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Usuario actualizado'})
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 400


# ── PUT /api/auth/usuarios/<id>/password ─────────────────────
@auth_bp.route('/usuarios/<int:id>/password', methods=['PUT'])
@jwt_required()
def cambiar_password(id):
    claims = get_jwt()
    if claims.get('rol') != 'admin' and int(get_jwt_identity()) != id:
        return jsonify({'error': 'No autorizado'}), 403

    datos = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE usuarios SET password_hash=? WHERE id=?',
        (hash_password(datos['password']), id)
    )
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Contraseña actualizada'})


# ── PUT /api/auth/usuarios/<id>/toggle ───────────────────────
@auth_bp.route('/usuarios/<int:id>/toggle', methods=['PUT'])
@jwt_required()
def toggle_usuario(id):
    claims = get_jwt()
    if claims.get('rol') != 'admin':
        return jsonify({'error': 'Solo el admin puede activar/desactivar usuarios'}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT activo FROM usuarios WHERE id=?', (id,))
    u = cursor.fetchone()
    if not u:
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404

    nuevo_estado = 0 if u['activo'] else 1
    cursor.execute('UPDATE usuarios SET activo=? WHERE id=?', (nuevo_estado, id))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Estado actualizado', 'activo': nuevo_estado})