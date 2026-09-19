# ============================================================
# perfil.py — Foto de perfil de cada usuario
#
# Cualquier rol (admin, sede/almacenista, porteria, consulta)
# puede ver y cambiar SU PROPIA foto de perfil. Nadie puede ver
# ni cambiar la de otro usuario desde aquí — es autoservicio,
# no un panel de administración de fotos.
#
# La foto se guarda como texto (base64, ya recortado y
# comprimido en el navegador) directamente en la columna
# usuarios.foto_base64, en vez de guardarse como archivo en
# disco: en Render el disco del servicio web NO es permanente
# (se borra en cada despliegue), así que un archivo subido ahí
# se perdería. Guardarla en la base de datos evita ese problema
# sin depender de un servicio externo de almacenamiento.
#
# Requiere la columna usuarios.foto_base64 (ver
# migracion_foto_usuario.sql).
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from database import get_connection


perfil_bp = Blueprint('perfil', __name__)


# Tope de tamaño para el texto base64 recibido (~1.5 MB de foto
# ya comprimida). El navegador ya la recorta/comprime antes de
# enviarla, esto es solo un límite de seguridad adicional.
TAMANO_MAXIMO_FOTO = 2 * 1024 * 1024


# GET /api/perfil/foto
@perfil_bp.route('/foto', methods=['GET'])
@jwt_required()
def obtener_mi_foto():

    usuario_id = int(get_jwt_identity())

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT foto_base64
                FROM usuarios
                WHERE id = %s
            ''', (usuario_id,))

            fila = cursor.fetchone()

    finally:
        conn.close()

    return jsonify({
        'foto_base64': fila['foto_base64'] if fila else None
    })


# PUT /api/perfil/foto
@perfil_bp.route('/foto', methods=['PUT'])
@jwt_required()
def actualizar_mi_foto():

    usuario_id = int(get_jwt_identity())

    datos = request.get_json() or {}

    foto_base64 = datos.get('foto_base64')

    if not foto_base64 or not isinstance(foto_base64, str):
        return jsonify({
            'error': 'Falta la foto'
        }), 400

    if not foto_base64.startswith('data:image/'):
        return jsonify({
            'error': 'La foto debe ser una imagen válida'
        }), 400

    if len(foto_base64) > TAMANO_MAXIMO_FOTO:
        return jsonify({
            'error': 'La imagen es muy pesada. Usa una foto más liviana.'
        }), 400

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                UPDATE usuarios
                SET foto_base64 = %s
                WHERE id = %s
            ''', (
                foto_base64,
                usuario_id
            ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Foto actualizada'
    })


# DELETE /api/perfil/foto — quitar la foto y volver a las iniciales
@perfil_bp.route('/foto', methods=['DELETE'])
@jwt_required()
def eliminar_mi_foto():

    usuario_id = int(get_jwt_identity())

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                UPDATE usuarios
                SET foto_base64 = NULL
                WHERE id = %s
            ''', (usuario_id,))

        conn.commit()

    except Exception as e:

        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 400

    finally:
        conn.close()

    return jsonify({
        'mensaje': 'Foto eliminada'
    })