# ============================================================
# salidas.py — Registro de mercancía que sale del almacén
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

salidas_bp = Blueprint("salidas", __name__)


def obtener_sede_actual():
    claims = get_jwt()
    if claims.get('rol') == 'admin':
        return request.args.get('sede_id', type=int)  # None = todas
    return claims.get('sede_id')


@salidas_bp.route("/", methods=["GET"])
@jwt_required()
def listar_salidas():
    sede_id = obtener_sede_actual()
    conn = get_connection()
    cursor = conn.cursor()

    if sede_id is None:
        cursor.execute("""
            SELECT s.id, s.numero_documento, s.obra, s.destino,
                   s.observaciones, s.fecha, s.sede_id,
                   se.nombre as sede_nombre,
                   COUNT(d.id) AS total_items
            FROM salidas s
            LEFT JOIN detalle_salidas d ON d.salida_id = s.id
            LEFT JOIN sedes se ON se.id = s.sede_id
            GROUP BY s.id
            ORDER BY s.fecha DESC
        """)
    else:
        cursor.execute("""
            SELECT s.id, s.numero_documento, s.obra, s.destino,
                   s.observaciones, s.fecha, s.sede_id,
                   se.nombre as sede_nombre,
                   COUNT(d.id) AS total_items
            FROM salidas s
            LEFT JOIN detalle_salidas d ON d.salida_id = s.id
            LEFT JOIN sedes se ON se.id = s.sede_id
            WHERE s.sede_id = ?
            GROUP BY s.id
            ORDER BY s.fecha DESC
        """, (sede_id,))

    filas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in filas])


@salidas_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def obtener_salida(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM salidas WHERE id=?", (id,))
    salida = cursor.fetchone()
    if not salida:
        conn.close()
        return jsonify({"error": "Salida no encontrada"}), 404
    cursor.execute("""
        SELECT d.cantidad, d.serial, d.modelo, d.marca, d.unidad,
               p.codigo, p.nombre
        FROM detalle_salidas d
        INNER JOIN productos p ON p.id = d.producto_id
        WHERE d.salida_id = ?
    """, (id,))
    detalle = cursor.fetchall()
    conn.close()
    return jsonify({**dict(salida), "detalle": [dict(x) for x in detalle]})


@salidas_bp.route("/", methods=["POST"])
@jwt_required()
def crear_salida():
    claims = get_jwt()
    datos = request.json

    if not datos.get("numero_documento"):
        return jsonify({"error": "El número de documento es obligatorio"}), 400
    if not datos.get("detalle") or len(datos["detalle"]) == 0:
        return jsonify({"error": "Debe agregar al menos un producto"}), 400

    if claims.get('rol') == 'admin':
        sede_id = datos.get('sede_id') or claims.get('sede_id')
    else:
        sede_id = claims.get('sede_id')

    conn = get_connection()
    cursor = conn.cursor()

    try:
        for item in datos["detalle"]:
            cursor.execute("SELECT nombre, stock FROM productos WHERE id=?",
                         (item["producto_id"],))
            producto = cursor.fetchone()
            if not producto:
                conn.close()
                return jsonify({"error": "Producto no encontrado"}), 400
            if item["cantidad"] > producto["stock"]:
                conn.close()
                return jsonify({
                    "error": f'Stock insuficiente para "{producto["nombre"]}". '
                             f'Disponible: {producto["stock"]} '
                             f'Solicitado: {item["cantidad"]}'
                }), 400

        cursor.execute("""
            INSERT INTO salidas (numero_documento, obra, destino, observaciones, sede_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datos["numero_documento"],
            datos.get("obra", ""),
            datos.get("destino", ""),
            datos.get("observaciones", ""),
            sede_id
        ))
        salida_id = cursor.lastrowid

        for item in datos["detalle"]:
            cursor.execute("""
                INSERT INTO detalle_salidas
                    (salida_id, producto_id, cantidad, serial, modelo, marca, unidad)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                salida_id,
                item["producto_id"],
                item["cantidad"],
                item.get("serial", ""),
                item.get("modelo", ""),
                item.get("marca", ""),
                item.get("unidad", "UND")
            ))
            cursor.execute("""
                UPDATE productos SET stock = stock - ? WHERE id = ?
            """, (item["cantidad"], item["producto_id"]))

        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Salida registrada", "id": salida_id}), 201

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 500


@salidas_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar_salida(id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT producto_id, cantidad FROM detalle_salidas WHERE salida_id=?", (id,))
        items = cursor.fetchall()

        for item in items:
            cursor.execute("UPDATE productos SET stock = stock + ? WHERE id = ?",
                         (item["cantidad"], item["producto_id"]))

        cursor.execute("DELETE FROM detalle_salidas WHERE salida_id=?", (id,))
        cursor.execute("DELETE FROM salidas WHERE id=?", (id,))

        conn.commit()
        conn.close()
        return jsonify({"mensaje": "Salida eliminada"})

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"error": str(e)}), 500