from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

productos_bp = Blueprint('productos', __name__)


def obtener_sede_actual():
    claims = get_jwt()
    if claims.get('rol') == 'admin':
        sede_id = request.args.get('sede_id', type=int)  # ← lee del URL
        return sede_id  # ignora lo que viene en el body
    return claims.get('sede_id')

def producto_pertenece_a_sede(producto_id, sede_id):
    """Verifica que el producto exista y sea de la sede indicada."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT sede_id FROM productos WHERE id = ?', (producto_id,))
    fila = cursor.fetchone()
    conn.close()
    if not fila:
        return False
    return fila['sede_id'] == sede_id


@productos_bp.route('/', methods=['GET'])
@jwt_required()
def listar_productos():
    sede_id = obtener_sede_actual()
    conn = get_connection()
    cursor = conn.cursor()
    
    if sede_id is None:
        cursor.execute('''
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.unidad,
                   p.stock, p.stock_minimo, p.sede_id,
                   s.nombre as sede_nombre
            FROM productos p
            LEFT JOIN sedes s ON s.id = p.sede_id
            ORDER BY p.nombre
        ''')
    else:
        cursor.execute('''
            SELECT p.id, p.codigo, p.nombre, p.descripcion, p.unidad,
                   p.stock, p.stock_minimo, p.sede_id,
                   s.nombre as sede_nombre
            FROM productos p
            LEFT JOIN sedes s ON s.id = p.sede_id
            WHERE p.sede_id = ?
            ORDER BY p.nombre
        ''', (sede_id,))
    
    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])

@productos_bp.route('/', methods=['POST'])
@jwt_required()
def crear_producto():
    claims = get_jwt()
    datos  = request.json

    if not datos.get('nombre'):
        return jsonify({'error': 'El nombre es obligatorio'}), 400

    if claims.get('rol') == 'admin':
        sede_id = datos.get('sede_id')
        if not sede_id:
            return jsonify({'error': 'Selecciona una sede para el producto'}), 400
    else:
        sede_id = claims.get('sede_id')

    conn = get_connection()
    cursor = conn.cursor()

    # Verificamos si ya existe un producto con ese codigo en la misma sede
    if datos.get('codigo'):
        cursor.execute('''
            SELECT id FROM productos
            WHERE codigo = ? AND sede_id = ?
        ''', (datos['codigo'], sede_id))
        existente = cursor.fetchone()
        if existente:
            conn.close()
            return jsonify({
                'error': f'Ya existe un producto con el codigo "{datos["codigo"]}" en esta sede'
            }), 400

    cursor.execute('''
        INSERT INTO productos (codigo, nombre, descripcion, unidad, stock, stock_minimo, sede_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        datos.get('codigo', ''),
        datos['nombre'],
        datos.get('descripcion', ''),
        datos.get('unidad', 'UND'),
        datos.get('stock', 0),
        datos.get('stock_minimo', 0),
        sede_id
    ))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return jsonify({'mensaje': 'Producto creado', 'id': nuevo_id}), 201


@productos_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def editar_producto(id):
    claims = get_jwt()
    datos = request.json

    # Solo el almacenista verifica que el producto sea de su sede
    if claims.get('rol') != 'admin':
        sede_id = claims.get('sede_id')
        if not producto_pertenece_a_sede(id, sede_id):
            return jsonify({'error': 'Producto no encontrado en esta sede'}), 404

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
@jwt_required()
def eliminar_producto(id):
    claims = get_jwt()
    
    # Admin puede eliminar cualquier producto
    if claims.get('rol') != 'admin':
        sede_id = claims.get('sede_id')
        if not producto_pertenece_a_sede(id, sede_id):
            return jsonify({'error': 'Producto no encontrado en esta sede'}), 404

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM productos WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Producto eliminado'})