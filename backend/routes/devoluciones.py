# ============================================================
# devoluciones.py — Registro de mercancia que regresa al
# almacen, ligada a una salida especifica para trazabilidad
# ============================================================

from flask import Blueprint, request, jsonify
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

devoluciones_bp = Blueprint('devoluciones', __name__)


@devoluciones_bp.route('/', methods=['GET'])
def listar_devoluciones():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT dv.id, dv.numero_documento, dv.salida_id, dv.origen,
               dv.destino, dv.motivo, dv.observaciones, dv.fecha,
               s.numero_documento AS salida_numero,
               COUNT(d.id) as total_items
        FROM devoluciones dv
        LEFT JOIN detalle_devoluciones d ON d.devolucion_id = dv.id
        LEFT JOIN salidas s ON s.id = dv.salida_id
        GROUP BY dv.id
        ORDER BY dv.fecha DESC
    ''')
    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])


@devoluciones_bp.route('/salidas-disponibles', methods=['GET'])
def salidas_disponibles():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, numero_documento, obra, destino, fecha
        FROM salidas
        ORDER BY fecha DESC
    ''')
    salidas = [dict(s) for s in cursor.fetchall()]
    conn.close()
    return jsonify(salidas)


@devoluciones_bp.route('/salida/<int:id>/items', methods=['GET'])
def items_de_salida(id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT d.producto_id, d.cantidad, d.modelo, d.marca, d.serial, d.unidad,
               p.codigo, p.nombre
        FROM detalle_salidas d
        INNER JOIN productos p ON p.id = d.producto_id
        WHERE d.salida_id = ?
    ''', (id,))
    items = [dict(i) for i in cursor.fetchall()]

    for item in items:
        cursor.execute('''
            SELECT COALESCE(SUM(dd.cantidad), 0) as ya_devuelto
            FROM detalle_devoluciones dd
            INNER JOIN devoluciones dv ON dv.id = dd.devolucion_id
            WHERE dv.salida_id = ? AND dd.producto_id = ?
        ''', (id, item['producto_id']))
        ya_devuelto = cursor.fetchone()['ya_devuelto']
        item['cantidad'] = item['cantidad'] - ya_devuelto
        item['ya_devuelto'] = ya_devuelto

    items = [i for i in items if i['cantidad'] > 0]
    conn.close()
    return jsonify(items)


@devoluciones_bp.route('/', methods=['POST'])
def crear_devolucion():
    datos = request.json

    if not datos.get('numero_documento'):
        return jsonify({'error': 'El numero de documento es obligatorio'}), 400
    if not datos.get('detalle') or len(datos['detalle']) == 0:
        return jsonify({'error': 'Debe agregar al menos un producto'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO devoluciones (numero_documento, tipo, salida_id, origen, destino, motivo, observaciones)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos['numero_documento'],
            'DEVOLUCION',
            datos.get('salida_id'),
            datos.get('origen', ''),
            datos.get('destino', 'Almacen'),
            datos.get('motivo', ''),
            datos.get('observaciones', '')
        ))
        devolucion_id = cursor.lastrowid

        for item in datos['detalle']:
            cursor.execute('''
                INSERT INTO detalle_devoluciones
                    (devolucion_id, producto_id, cantidad, serial, modelo, marca, unidad)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                devolucion_id,
                item['producto_id'],
                item['cantidad'],
                item.get('serial', ''),
                item.get('modelo', ''),
                item.get('marca', ''),
                item.get('unidad', 'UND')
            ))

            # Suma stock real de vuelta
            cursor.execute('''
                UPDATE productos
                SET stock = stock + ?
                WHERE id = ?
            ''', (item['cantidad'], item['producto_id']))

        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Devolucion registrada', 'id': devolucion_id}), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500


@devoluciones_bp.route('/<int:id>', methods=['DELETE'])
def eliminar_devolucion(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT producto_id, cantidad FROM detalle_devoluciones WHERE devolucion_id=?', (id,))
        items = cursor.fetchall()

        for item in items:
            cursor.execute('''
                UPDATE productos
                SET stock = stock - ?
                WHERE id = ?
            ''', (item['cantidad'], item['producto_id']))

        cursor.execute('DELETE FROM detalle_devoluciones WHERE devolucion_id=?', (id,))
        cursor.execute('DELETE FROM devoluciones WHERE id=?', (id,))

        conn.commit()
        conn.close()
        return jsonify({'mensaje': 'Devolucion eliminada'})

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': str(e)}), 500