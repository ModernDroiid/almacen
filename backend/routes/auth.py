from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
import jwt
import datetime
from database import get_connection

auth_bp = Blueprint('auth', __name__)

SECRET_KEY = "cambia-esto-por-una-clave-larga-y-secreta"

@auth_bp.route('/login', methods=['POST'])
def login():
    datos = request.get_json()

    if not datos or 'correo' not in datos or 'password' not in datos:
        return jsonify({'error': 'Correo y contraseña son requeridos'}), 400

    correo = datos['correo'].strip().lower()
    password = datos['password']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE correo = ?', (correo,))
    usuario = cursor.fetchone()
    conn.close()

    if not usuario or not check_password_hash(usuario['password_hash'], password):
        return jsonify({'error': 'Correo o contraseña incorrectos'}), 401

    payload = {
        'usuario_id': usuario['id'],
        'correo': usuario['correo'],
        'nombre': usuario['nombre'],
        'rol': usuario['rol'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    return jsonify({
        'token': token,
        'correo': usuario['correo'],
        'nombre': usuario['nombre'],
        'rol': usuario['rol']
    })