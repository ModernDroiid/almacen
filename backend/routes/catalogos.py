# ============================================================
# catalogos.py — Maneja las listas de Marcas y Modelos
#
# ROLES:
#   admin     → puede ver, crear, editar y eliminar
#   sede      → puede consultar
#   consulta  → puede consultar
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

catalogos_bp = Blueprint('catalogos', __name__)


# ============================================================
# FUNCION AUXILIAR
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


# ============================================================
# MARCAS
# ============================================================

@catalogos_bp.route('/marcas', methods=['GET'])
@jwt_required()
def listar_marcas():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT id, nombre FROM marcas ORDER BY nombre'
    )

    filas = cursor.fetchall()
    conn.close()

    return jsonify([dict(f) for f in filas])


@catalogos_bp.route('/marcas', methods=['POST'])
@jwt_required()
def agregar_marca():

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
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT OR IGNORE INTO marcas (nombre) VALUES (?)',
            (nombre,)
        )

        conn.commit()

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Marca creada'
    }), 201


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
    cursor = conn.cursor()

    cursor.execute(
        'UPDATE marcas SET nombre=? WHERE id=?',
        (nombre, id)
    )

    if cursor.rowcount == 0:
        conn.close()

        return jsonify({
            'error': 'Marca no encontrada'
        }), 404

    conn.commit()
    conn.close()

    return jsonify({
        'mensaje': 'Marca actualizada'
    })


@catalogos_bp.route('/marcas/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_marca(id):

    permiso = requiere_admin()
    if permiso:
        return permiso

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM marcas WHERE id=?',
        (id,)
    )

    if cursor.rowcount == 0:
        conn.close()

        return jsonify({
            'error': 'Marca no encontrada'
        }), 404

    conn.commit()
    conn.close()

    return jsonify({
        'mensaje': 'Marca eliminada'
    })


# ============================================================
# MODELOS
# ============================================================

@catalogos_bp.route('/modelos', methods=['GET'])
@jwt_required()
def listar_modelos():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        'SELECT id, nombre FROM modelos ORDER BY nombre'
    )

    filas = cursor.fetchall()
    conn.close()

    return jsonify([dict(f) for f in filas])


@catalogos_bp.route('/modelos', methods=['POST'])
@jwt_required()
def agregar_modelo():

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
    cursor = conn.cursor()

    try:
        cursor.execute(
            'INSERT OR IGNORE INTO modelos (nombre) VALUES (?)',
            (nombre,)
        )

        conn.commit()

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Modelo creado'
    }), 201


@catalogos_bp.route('/modelos/<int:id>', methods=['PUT'])
@jwt_required()
def editar_modelo(id):

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
    cursor = conn.cursor()

    cursor.execute(
        'UPDATE modelos SET nombre=? WHERE id=?',
        (nombre, id)
    )

    if cursor.rowcount == 0:
        conn.close()

        return jsonify({
            'error': 'Modelo no encontrado'
        }), 404

    conn.commit()
    conn.close()

    return jsonify({
        'mensaje': 'Modelo actualizado'
    })


@catalogos_bp.route('/modelos/<int:id>', methods=['DELETE'])
@jwt_required()
def eliminar_modelo(id):

    permiso = requiere_admin()
    if permiso:
        return permiso

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        'DELETE FROM modelos WHERE id=?',
        (id,)
    )

    if cursor.rowcount == 0:
        conn.close()

        return jsonify({
            'error': 'Modelo no encontrado'
        }), 404

    conn.commit()
    conn.close()

    return jsonify({
        'mensaje': 'Modelo eliminado'
    })
