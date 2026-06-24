from flask import Blueprint, request, jsonify
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/', methods=['GET'])
def listar_productos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, codigo, nombre, descripcion, unidad, stock, stock_minimo
        FROM productos ORDER BY nombre
    ''')
    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])

@productos_bp.route('/', methods=['POST'])
def crear_producto():
    datos = request.json
    if not datos.get('nombre'):
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO productos (codigo, nombre, descripcion, unidad, stock, stock_minimo)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datos.get('codigo', ''),
        datos['nombre'],
        datos.get('descripcion', ''),
        datos.get('unidad', 'UND'),
        datos.get('stock', 0),
        datos.get('stock_minimo', 0)
    ))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return jsonify({'mensaje': 'Producto creado', 'id': nuevo_id}), 201

@productos_bp.route('/<int:id>', methods=['PUT'])
def editar_producto(id):
    datos = request.json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE productos
        SET codigo=?, nombre=?, descripcion=?, unidad=?, stock=?, stock_minimo=?
        WHERE id=?
    ''', (
        datos.get('codigo', ''),
        datos['nombre'],
        datos.get('descripcion', ''),
        datos.get('unidad', 'UND'),
        datos.get('stock', 0),
        datos.get('stock_minimo', 0),
        id
    ))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Producto actualizado'})

@productos_bp.route('/<int:id>', methods=['DELETE'])
def eliminar_producto(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM productos WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Producto eliminado'})