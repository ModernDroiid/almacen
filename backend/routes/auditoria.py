# ============================================================
# routes/auditoria.py
#
# Consulta del registro de auditoría — quién hizo qué y cuándo.
# Solo el admin puede verlo.
#
# Usa la tabla "auditoria" que ya existía en la base de datos
# (columnas: usuario_id, accion, entidad, entidad_id, descripcion,
# datos_anteriores, datos_nuevos, fecha), y la función
# registrar_auditoria(...) que ya existía en utils/auditoria.py.
#
# GET /api/auditoria?limite=100&usuario_id=&accion=
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from database import get_connection

auditoria_bp = Blueprint('auditoria', __name__)


@auditoria_bp.route('', methods=['GET'])
@jwt_required()
def listar_auditoria():

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede ver el registro de auditoría'
        }), 403

    limite = request.args.get('limite', 100, type=int)
    limite = max(1, min(limite, 500))

    usuario_id = request.args.get('usuario_id', type=int)
    accion = request.args.get('accion', '').strip()

    condiciones = []
    parametros = []

    if usuario_id:
        condiciones.append('a.usuario_id = %s')
        parametros.append(usuario_id)

    if accion:
        condiciones.append('a.accion = %s')
        parametros.append(accion)

    where_sql = (
        ('WHERE ' + ' AND '.join(condiciones))
        if condiciones
        else ''
    )

    parametros.append(limite)

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # La tabla no guarda el nombre del usuario directamente
            # (solo el id), así que lo traemos con un JOIN para que
            # el registro sea legible en pantalla.
            cursor.execute(f'''
                SELECT
                    a.id,
                    a.usuario_id,
                    u.nombre AS usuario_nombre,
                    a.accion,
                    a.entidad,
                    a.entidad_id,
                    a.descripcion,
                    a.datos_anteriores,
                    a.datos_nuevos,
                    a.fecha
                FROM auditoria a
                LEFT JOIN usuarios u
                    ON u.id = a.usuario_id
                {where_sql}
                ORDER BY a.fecha DESC
                LIMIT %s
            ''', parametros)

            registros = [
                dict(fila)
                for fila in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(registros)