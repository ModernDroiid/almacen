# ============================================================
# routes/notificaciones.py — Centro de notificaciones
#
# Reglas de quién ve qué (se generan desde otros módulos con
# utils/notificaciones.crear_notificacion, no aquí):
#
#   - Traslado creado   -> "sede" de la SEDE DESTINO
#   - Solicitud creada  -> todos los "admin"
#   - Salida creada     -> "porteria" de esa SEDE
#
# No hay conexión en tiempo real (no hay websockets todavía):
# el frontend consulta GET /api/notificaciones cada cierto
# tiempo (polling) para enterarse de lo nuevo.
#
# "Vista" vs "no vista":
# Cada usuario tiene un contador (usuarios.notificaciones_vistas_
# hasta) con el id más alto de notificación que ya revisó. Todo
# lo que tenga un id mayor a ese cuenta como "no leída". Al abrir
# el panel de notificaciones se llama a PUT .../marcar-vistas y
# ese contador se pone al día.
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from database import get_connection

notificaciones_bp = Blueprint('notificaciones', __name__)


# ============================================================
# GET /api/notificaciones
# ============================================================

@notificaciones_bp.route('', methods=['GET'])
@jwt_required()
def listar_notificaciones():

    claims = get_jwt()
    rol = claims.get('rol')
    sede_id = claims.get('sede_id')
    usuario_id = int(get_jwt_identity())

    limite = request.args.get('limite', 30, type=int)
    limite = max(1, min(limite, 100))

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT notificaciones_vistas_hasta
                FROM usuarios
                WHERE id = %s
            ''', (usuario_id,))

            fila_usuario = cursor.fetchone()
            vistas_hasta = (
                fila_usuario['notificaciones_vistas_hasta']
                if fila_usuario else 0
            )

            # rol_destino siempre debe coincidir con mi rol.
            # sede_id: si la notificación no tiene sede (NULL),
            # es para todos los de ese rol (ej. admin); si la
            # tiene, solo para los de esa sede exacta.
            cursor.execute('''
                SELECT
                    n.id,
                    n.tipo,
                    n.mensaje,
                    n.entidad_tipo,
                    n.entidad_id,
                    n.fecha_creacion
                FROM notificaciones n
                WHERE
                    n.rol_destino = %s
                    AND (n.sede_id IS NULL OR n.sede_id = %s)
                    AND (n.creado_por IS NULL OR n.creado_por != %s)
                ORDER BY n.fecha_creacion DESC
                LIMIT %s
            ''', (rol, sede_id, usuario_id, limite))

            notificaciones = [dict(fila) for fila in cursor.fetchall()]

    finally:
        conn.close()

    for n in notificaciones:
        n['leida'] = n['id'] <= vistas_hasta
        n['fecha_creacion'] = n['fecha_creacion'].isoformat()

    no_leidas = sum(1 for n in notificaciones if not n['leida'])

    return jsonify({
        'notificaciones': notificaciones,
        'no_leidas': no_leidas
    })


# ============================================================
# PUT /api/notificaciones/marcar-vistas
# ============================================================

@notificaciones_bp.route('/marcar-vistas', methods=['PUT'])
@jwt_required()
def marcar_vistas():

    usuario_id = int(get_jwt_identity())

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                UPDATE usuarios
                SET notificaciones_vistas_hasta = (
                    SELECT COALESCE(MAX(id), 0) FROM notificaciones
                )
                WHERE id = %s
            ''', (usuario_id,))

        conn.commit()

    finally:
        conn.close()

    return jsonify({'mensaje': 'Notificaciones marcadas como vistas'})