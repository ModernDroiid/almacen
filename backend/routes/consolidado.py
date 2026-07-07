# ============================================================
# consolidado.py — Historial por punto (destino/obra)
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_connection

consolidado_bp = Blueprint('consolidado', __name__)


# ── GET /api/consolidado/puntos ──────────────────────────────
@consolidado_bp.route('/puntos', methods=['GET'])
@jwt_required()
def listar_puntos():
    claims = get_jwt()
    sede_id = request.args.get('sede_id', type=int)
    if claims.get('rol') != 'admin':
        sede_id = claims.get('sede_id')

    conn = get_connection()
    cursor = conn.cursor()

    if sede_id:
        cursor.execute('''
            SELECT DISTINCT destino, sede_id,
                   COUNT(id) as total_salidas
            FROM salidas
            WHERE destino IS NOT NULL AND destino != ''
              AND sede_id = ?
            GROUP BY destino
            ORDER BY destino
        ''', (sede_id,))
    else:
        cursor.execute('''
            SELECT DISTINCT s.destino, s.sede_id,
                   se.nombre as sede_nombre,
                   COUNT(s.id) as total_salidas
            FROM salidas s
            LEFT JOIN sedes se ON se.id = s.sede_id
            WHERE s.destino IS NOT NULL AND s.destino != ''
            GROUP BY s.destino
            ORDER BY s.destino
        ''')

    puntos = [dict(p) for p in cursor.fetchall()]
    conn.close()
    return jsonify(puntos)


# ── GET /api/consolidado/punto ───────────────────────────────
@consolidado_bp.route('/punto', methods=['GET'])
@jwt_required()
def historial_punto():
    destino = request.args.get('destino', '').strip()
    if not destino:
        return jsonify({'error': 'Destino requerido'}), 400

    claims = get_jwt()
    sede_id = request.args.get('sede_id', type=int)
    if claims.get('rol') != 'admin':
        sede_id = claims.get('sede_id')

    conn = get_connection()
    cursor = conn.cursor()

    # ── Salidas hacia ese punto ──────────────────────────────
    if sede_id:
        cursor.execute('''
            SELECT s.id, s.numero_documento, s.fecha, s.observaciones,
                   se.nombre as sede_nombre
            FROM salidas s
            LEFT JOIN sedes se ON se.id = s.sede_id
            WHERE s.destino = ? AND s.sede_id = ?
            ORDER BY s.fecha DESC
        ''', (destino, sede_id))
    else:
        cursor.execute('''
            SELECT s.id, s.numero_documento, s.fecha, s.observaciones,
                   se.nombre as sede_nombre
            FROM salidas s
            LEFT JOIN sedes se ON se.id = s.sede_id
            WHERE s.destino = ?
            ORDER BY s.fecha DESC
        ''', (destino,))

    salidas = [dict(s) for s in cursor.fetchall()]

    for salida in salidas:
        cursor.execute('''
            SELECT p.nombre, p.codigo, d.cantidad, d.unidad,
                   d.modelo, d.marca, d.serial
            FROM detalle_salidas d
            INNER JOIN productos p ON p.id = d.producto_id
            WHERE d.salida_id = ?
        ''', (salida['id'],))
        salida['detalle'] = [dict(d) for d in cursor.fetchall()]

    # ── Devoluciones desde ese punto ─────────────────────────
    if sede_id:
        cursor.execute('''
            SELECT dv.id, dv.numero_documento, dv.fecha, dv.motivo,
                   dv.observaciones, s.numero_documento as salida_numero,
                   se.nombre as sede_nombre
            FROM devoluciones dv
            LEFT JOIN salidas s ON s.id = dv.salida_id
            LEFT JOIN sedes se ON se.id = dv.sede_id
            WHERE dv.origen = ? AND dv.sede_id = ?
            ORDER BY dv.fecha DESC
        ''', (destino, sede_id))
    else:
        cursor.execute('''
            SELECT dv.id, dv.numero_documento, dv.fecha, dv.motivo,
                   dv.observaciones, s.numero_documento as salida_numero,
                   se.nombre as sede_nombre
            FROM devoluciones dv
            LEFT JOIN salidas s ON s.id = dv.salida_id
            LEFT JOIN sedes se ON se.id = dv.sede_id
            WHERE dv.origen = ?
            ORDER BY dv.fecha DESC
        ''', (destino,))

    devoluciones = [dict(d) for d in cursor.fetchall()]

    for dev in devoluciones:
        cursor.execute('''
            SELECT p.nombre, p.codigo, d.cantidad, d.unidad,
                   d.modelo, d.marca, d.serial
            FROM detalle_devoluciones d
            INNER JOIN productos p ON p.id = d.producto_id
            WHERE d.devolucion_id = ?
        ''', (dev['id'],))
        dev['detalle'] = [dict(d) for d in cursor.fetchall()]

    # ── Resumen neto por producto ─────────────────────────────
    # Suma todo lo que salió y resta lo que devolvió
    neto = {}
    for salida in salidas:
        for item in salida['detalle']:
            clave = (item['nombre'], item['modelo'] or '', item['serial'] or '')
            if clave not in neto:
                neto[clave] = {
                    'nombre':   item['nombre'],
                    'codigo':   item['codigo'],
                    'modelo':   item['modelo'] or '—',
                    'serial':   item['serial'] or '—',
                    'unidad':   item['unidad'],
                    'salidas':  0,
                    'devuelto': 0,
                    'neto':     0
                }
            neto[clave]['salidas']  += item['cantidad']
            neto[clave]['neto']     += item['cantidad']

    for dev in devoluciones:
        for item in dev['detalle']:
            clave = (item['nombre'], item['modelo'] or '', item['serial'] or '')
            if clave in neto:
                neto[clave]['devuelto'] += item['cantidad']
                neto[clave]['neto']     -= item['cantidad']

    conn.close()
    return jsonify({
        'destino':     destino,
        'salidas':     salidas,
        'devoluciones': devoluciones,
        'resumen':     list(neto.values())
    })