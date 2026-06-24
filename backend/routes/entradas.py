from flask import Blueprint, request, jsonify
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

entradas_bp = Blueprint('entradas', __name__)

@entradas_bp.route('/', methods=['GET'])
def listar_entradas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, e.numero_documento, e.obra, e.destino,
               e.observaciones, e.fecha,
               COUNT(d.id) as total_items
        FROM entradas e
        LEFT JOIN detalle_entradas d ON d.entrada_id = e.id
        GROUP BY e.id
        ORDER BY e.fecha DESC
    ''')
    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])

@entradas_bp.route('/<int:id>', methods=['GET'])
def obtener_entrada(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM entradas WHERE id=?', (id,))
    entrada = cursor.fetchone()
    if not entrada:
        return jsonify({'error': 'Entrada no encontrada'}), 404
    cursor.execute('''
        SELECT d.cantidad, d.serial, d.modelo, d.marca, d.unidad,
               p.codigo, p.nombre
        FROM detalle_entradas d
        INNER JOIN productos p ON p.id = d.producto_id
        WHERE d.entrada_id = ?
    ''', (id,))
    detalle = cursor.fetchall()
    conn.close()
    return jsonify({**dict(entrada), 'detalle': [dict(d) for d in detalle]})

@entradas_bp.route('/', methods=['POST'])
def crear_entrada():
    datos = request.json

    if not datos.get('numero_documento'):
        return jsonify({'error': 'El numero de documento es obligatorio'}), 400
    if not datos.get('detalle') or len(datos['detalle']) == 0:
        return jsonify({'error': 'Debe agregar al menos un producto'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO entradas (numero_documento, obra, destino, observaciones)
            VALUES (?, ?, ?, ?)
        ''', (
            datos['numero_documento'],
            datos.get('obra', ''),
            datos.get('destino', 'Almacen'),
            datos.get('observaciones', '')
        ))
        entrada_id = cursor.lastrowid

        for item in datos['detalle']:
            cursor.execute('''
                INSERT INTO detalle_entradas
                    (entrada_id, producto_id, cantidad, serial, modelo, marca, unidad)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                entrada_id,
                item['producto_id'],
                item['cantidad'],
                item.get('serial', ''),
                item.get('modelo', ''),
                item.get('marca', ''),
                item.get('unidad', 'UND')
            ))

            # Subimos el stock real del producto
            cursor.execute('''
                UPDATE productos
                SET stock = stock + ?
                WHERE id = ?
            ''', (item['cantidad'], item['producto_id']))

        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Entrada registrada', 'id': entrada_id}), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@entradas_bp.route('/<int:id>', methods=['DELETE'])
def eliminar_entrada(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT producto_id, cantidad FROM detalle_entradas WHERE entrada_id=?', (id,))
        items = cursor.fetchall()

        for item in items:
            cursor.execute('''
                UPDATE productos
                SET stock = stock - ?
                WHERE id = ?
            ''', (item['cantidad'], item['producto_id']))

        cursor.execute('DELETE FROM detalle_entradas WHERE entrada_id=?', (id,))
        cursor.execute('DELETE FROM entradas WHERE id=?', (id,))

        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Entrada eliminada'})

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500