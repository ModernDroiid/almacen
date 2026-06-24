# ============================================================
# catalogos.py — Maneja las listas de Marcas y Modelos
# Esta seccion es administrable: el admin puede ver, crear,
# editar y eliminar marcas/modelos directamente desde el menu
# ============================================================

from flask import Blueprint, request, jsonify
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

catalogos_bp = Blueprint('catalogos', __name__)


# ── MARCAS ────────────────────────────────────────────────────

@catalogos_bp.route('/marcas', methods=['GET'])
def listar_marcas():
    conn = get_connection()
    cursor = conn.cursor()
    # Ahora devolvemos id + nombre, no solo el nombre,
    # porque necesitamos el id para editar/eliminar
    cursor.execute('SELECT id, nombre FROM marcas ORDER BY nombre')
    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])


@catalogos_bp.route('/marcas', methods=['POST'])
def agregar_marca():
    nombre = request.json.get('nombre', '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO marcas (nombre) VALUES (?)', (nombre,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'mensaje': 'ok'}), 201


@catalogos_bp.route('/marcas/<int:id>', methods=['PUT'])
def editar_marca(id):
    nombre = request.json.get('nombre', '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE marcas SET nombre=? WHERE id=?', (nombre, id))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Marca actualizada'})


@catalogos_bp.route('/marcas/<int:id>', methods=['DELETE'])
def eliminar_marca(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM marcas WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Marca eliminada'})


# ── MODELOS ───────────────────────────────────────────────────

@catalogos_bp.route('/modelos', methods=['GET'])
def listar_modelos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, nombre FROM modelos ORDER BY nombre')
    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])


@catalogos_bp.route('/modelos', methods=['POST'])
def agregar_modelo():
    nombre = request.json.get('nombre', '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT OR IGNORE INTO modelos (nombre) VALUES (?)', (nombre,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({'mensaje': 'ok'}), 201


@catalogos_bp.route('/modelos/<int:id>', methods=['PUT'])
def editar_modelo(id):
    nombre = request.json.get('nombre', '').strip()
    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE modelos SET nombre=? WHERE id=?', (nombre, id))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Modelo actualizado'})


@catalogos_bp.route('/modelos/<int:id>', methods=['DELETE'])
def eliminar_modelo(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM modelos WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Modelo eliminado'})