# ============================================================
# solicitudes.py — Solicitudes de compra de equipo
#
# Reemplaza el formato en Excel (FORMATO_REQUISICION_EQUIPOS)
# que se usa para pedir que se le COMPRE equipo a un proveedor
# con destino a un proyecto/constructora.
#
# IMPORTANTE: esto NO es un movimiento de inventario. No toca
# la tabla "inventario" ni genera una salida — el equipo todavía
# no existe en el almacén, se le va a comprar al proveedor.
# Cuando llegue físicamente, se registra aparte como una entrada
# normal (routes/entradas.py).
#
# FLUJO:
#   1) Un usuario (sede o admin) crea la solicitud eligiendo
#      productos ya existentes en el catálogo y la cantidad que
#      necesita. Queda en estado PENDIENTE.
#   2) El admin la revisa y decide:
#        - Aprobarla  (PUT /<id>/aprobar)
#        - Rechazarla (PUT /<id>/rechazar, con motivo)
#
# ROLES:
#   admin     → consultar todas, crear, aprobar y rechazar
#   sede      → consultar y crear (solo de su propia sede)
#   consulta  → solamente consultar
#   porteria  → sin acceso (bloqueado en app.py junto con el
#               resto de rutas que no sean /api/salidas)
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from database import get_connection
from utils.auditoria import registrar_auditoria
from utils.notificaciones import crear_notificacion


solicitudes_bp = Blueprint('solicitudes', __name__)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_sede_actual():
    """
    Admin y consulta:
        Pueden filtrar con ?sede_id=ID, o ver todas si no lo
        envían.

    Sede:
        Siempre trabaja con su propia sede.
    """

    claims = get_jwt()
    rol = claims.get('rol')

    if rol in ('admin', 'consulta'):
        return request.args.get('sede_id', type=int)

    return claims.get('sede_id')


def usuario_puede_ver_solicitud(solicitud):

    claims = get_jwt()

    rol = claims.get('rol')
    sede_id = claims.get('sede_id')

    if rol in ('admin', 'consulta'):
        return True

    return solicitud['sede_id'] == sede_id


# ============================================================
# GET /api/solicitudes/
# LISTAR SOLICITUDES
# ============================================================

@solicitudes_bp.route('/', methods=['GET'])
@jwt_required()
def listar_solicitudes():

    sede_id = obtener_sede_actual()

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            condiciones = []
            parametros = []

            if sede_id is not None:
                condiciones.append('sol.sede_id = %s')
                parametros.append(sede_id)

            estado = request.args.get('estado', '').strip().upper()

            if estado:
                condiciones.append('sol.estado = %s')
                parametros.append(estado)

            where_sql = (
                ('WHERE ' + ' AND '.join(condiciones))
                if condiciones
                else ''
            )

            cursor.execute(f'''
                SELECT
                    sol.id,
                    sol.numero_solicitud,
                    sol.sede_id,
                    sol.constructora,
                    sol.proyecto,
                    sol.no_orden_servicio,
                    sol.observaciones,
                    sol.estado,
                    sol.fecha,
                    sol.fecha_aprobacion,
                    sol.motivo_rechazo,

                    s.nombre AS sede_nombre,
                    s.ciudad,

                    u_sol.nombre AS solicitado_por_nombre,
                    u_apr.nombre AS aprobado_por_nombre,

                    COUNT(d.id) AS total_items

                FROM solicitudes sol

                LEFT JOIN sedes s
                    ON s.id = sol.sede_id

                LEFT JOIN usuarios u_sol
                    ON u_sol.id = sol.solicitado_por

                LEFT JOIN usuarios u_apr
                    ON u_apr.id = sol.aprobado_por

                LEFT JOIN detalle_solicitudes d
                    ON d.solicitud_id = sol.id

                {where_sql}

                GROUP BY
                    sol.id, s.nombre, s.ciudad,
                    u_sol.nombre, u_apr.nombre

                ORDER BY sol.fecha DESC
            ''', parametros)

            solicitudes = [
                dict(fila)
                for fila in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(solicitudes)


# ============================================================
# GET /api/solicitudes/pendientes-conteo
#
# Para el aviso/badge del admin: cuántas solicitudes están
# esperando su revisión ahora mismo.
# ============================================================

@solicitudes_bp.route('/pendientes-conteo', methods=['GET'])
@jwt_required()
def contar_pendientes():

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({'pendientes': 0})

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT COUNT(*) AS pendientes
                FROM solicitudes
                WHERE estado = 'PENDIENTE'
            ''')

            fila = cursor.fetchone()

    finally:
        conn.close()

    return jsonify({'pendientes': fila['pendientes'] if fila else 0})


# ============================================================
# GET /api/solicitudes/<id>
# OBTENER SOLICITUD (con su detalle de productos)
# ============================================================

@solicitudes_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def obtener_solicitud(id):

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT
                    sol.*,
                    s.nombre AS sede_nombre,
                    s.ciudad,
                    u_sol.nombre AS solicitado_por_nombre,
                    u_apr.nombre AS aprobado_por_nombre
                FROM solicitudes sol
                LEFT JOIN sedes s
                    ON s.id = sol.sede_id
                LEFT JOIN usuarios u_sol
                    ON u_sol.id = sol.solicitado_por
                LEFT JOIN usuarios u_apr
                    ON u_apr.id = sol.aprobado_por
                WHERE sol.id = %s
            ''', (id,))

            solicitud = cursor.fetchone()

            if not solicitud:
                return jsonify({'error': 'Solicitud no encontrada'}), 404

            solicitud = dict(solicitud)

            if not usuario_puede_ver_solicitud(solicitud):
                return jsonify({'error': 'No autorizado'}), 403

            cursor.execute('''
                SELECT
                    d.id,
                    d.producto_id,
                    d.cantidad_solicitada,
                    d.observaciones,
                    p.codigo,
                    p.nombre,
                    p.descripcion,
                    u.codigo AS unidad
                FROM detalle_solicitudes d
                LEFT JOIN productos p
                    ON p.id = d.producto_id
                LEFT JOIN unidades u
                    ON u.id = p.unidad_id
                WHERE d.solicitud_id = %s
                ORDER BY d.id
            ''', (id,))

            solicitud['detalle'] = [
                dict(fila)
                for fila in cursor.fetchall()
            ]

    finally:
        conn.close()

    return jsonify(solicitud)


# ============================================================
# POST /api/solicitudes/
# CREAR SOLICITUD
# ============================================================

@solicitudes_bp.route('/', methods=['POST'])
@jwt_required()
def crear_solicitud():

    claims = get_jwt()
    rol = claims.get('rol')

    if rol == 'consulta':
        return jsonify({
            'error': 'El usuario de consulta no puede crear solicitudes'
        }), 403

    datos = request.get_json(silent=True) or {}

    # ========================================================
    # DATOS PRINCIPALES
    # ========================================================

    numero_solicitud = str(datos.get('numero_solicitud', '')).strip()

    if not numero_solicitud:
        return jsonify({
            'error': 'El número de solicitud es obligatorio'
        }), 400

    proyecto = str(datos.get('proyecto', '')).strip()

    if not proyecto:
        return jsonify({
            'error': 'El proyecto es obligatorio'
        }), 400

    constructora = str(datos.get('constructora', '')).strip()
    no_orden_servicio = str(datos.get('no_orden_servicio', '')).strip()
    observaciones = str(datos.get('observaciones', '')).strip()

    detalle = datos.get('detalle')

    if not isinstance(detalle, list) or len(detalle) == 0:
        return jsonify({
            'error': 'Debe agregar al menos un producto'
        }), 400

    # ========================================================
    # SEDE
    # ========================================================

    if rol == 'admin':
        sede_id = datos.get('sede_id') or claims.get('sede_id')
    else:
        sede_id = claims.get('sede_id')

    if not sede_id:
        return jsonify({'error': 'Debe seleccionar una sede'}), 400

    usuario_id = int(get_jwt_identity())

    firma_solicitante = datos.get('firma_solicitante_base64') or None

    conn = get_connection()

    solicitud_id = None

    try:
        with conn.cursor() as cursor:

            # =================================================
            # VERIFICAR SEDE
            # =================================================

            cursor.execute('''
                SELECT id FROM sedes
                WHERE id = %s AND activa = TRUE
            ''', (sede_id,))

            if not cursor.fetchone():
                raise ValueError('La sede no existe o está inactiva')

            # =================================================
            # VERIFICAR NÚMERO DUPLICADO
            # =================================================

            cursor.execute('''
                SELECT id FROM solicitudes
                WHERE numero_solicitud = %s
            ''', (numero_solicitud,))

            if cursor.fetchone():
                raise ValueError(
                    f'Ya existe una solicitud con el número '
                    f'"{numero_solicitud}"'
                )

            # =================================================
            # CREAR SOLICITUD
            # =================================================

            cursor.execute('''
                INSERT INTO solicitudes (
                    numero_solicitud,
                    sede_id,
                    constructora,
                    proyecto,
                    no_orden_servicio,
                    observaciones,
                    estado,
                    solicitado_por,
                    firma_solicitante_base64
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    'PENDIENTE', %s, %s
                )
                RETURNING id
            ''', (
                numero_solicitud,
                sede_id,
                constructora,
                proyecto,
                no_orden_servicio,
                observaciones,
                usuario_id,
                firma_solicitante
            ))

            solicitud_id = cursor.fetchone()['id']

            # =================================================
            # PROCESAR DETALLE
            # =================================================

            for item in detalle:

                if not isinstance(item, dict):
                    raise ValueError('Cada detalle debe ser un objeto')

                producto_id = item.get('producto_id')

                if not producto_id:
                    raise ValueError('Cada detalle debe tener producto_id')

                cantidad = item.get('cantidad_solicitada')

                try:
                    cantidad = int(cantidad)
                except (TypeError, ValueError):
                    raise ValueError(
                        'La cantidad solicitada debe ser un número entero'
                    )

                if cantidad <= 0:
                    raise ValueError(
                        'La cantidad solicitada debe ser mayor que cero'
                    )

                cursor.execute('''
                    SELECT id, codigo FROM productos
                    WHERE id = %s
                ''', (producto_id,))

                producto = cursor.fetchone()

                if not producto:
                    raise ValueError(f'Producto {producto_id} no encontrado')

                cursor.execute('''
                    INSERT INTO detalle_solicitudes (
                        solicitud_id,
                        producto_id,
                        cantidad_solicitada,
                        observaciones
                    )
                    VALUES (%s, %s, %s, %s)
                ''', (
                    solicitud_id,
                    producto_id,
                    cantidad,
                    str(item.get('observaciones', '')).strip()
                ))

        conn.commit()

    except Exception as e:

        conn.rollback()

        print('ERROR AL CREAR SOLICITUD:', repr(e))

        return jsonify({'error': str(e)}), 400

    finally:
        conn.close()

    # ============================================================
    # AUDITORÍA
    # ============================================================

    try:
        registrar_auditoria(
            usuario_id=usuario_id,
            accion='CREAR',
            entidad='SOLICITUD',
            entidad_id=solicitud_id,
            descripcion=f'Creación de solicitud {numero_solicitud}',
            datos_nuevos={
                'numero_solicitud': numero_solicitud,
                'sede_id': sede_id,
                'proyecto': proyecto,
                'constructora': constructora
            }
        )
    except Exception as e:
        print('ERROR AL REGISTRAR AUDITORIA DE SOLICITUD:', repr(e))

    # ============================================================
    # NOTIFICACIÓN AL ADMIN
    # ============================================================

    try:
        crear_notificacion(
            tipo='solicitud',
            mensaje=f'Nueva solicitud {numero_solicitud} — {proyecto}',
            rol_destino='admin',
            sede_id=None,
            entidad_tipo='solicitud',
            entidad_id=solicitud_id,
            creado_por=usuario_id
        )
    except Exception as e:
        print('ERROR AL CREAR NOTIFICACION DE SOLICITUD:', repr(e))

    return jsonify({
        'mensaje': 'Solicitud registrada',
        'id': solicitud_id
    }), 201


# ============================================================
# PUT /api/solicitudes/<id>/aprobar
#
# SOLO ADMIN
# ============================================================

@solicitudes_bp.route('/<int:id>/aprobar', methods=['PUT'])
@jwt_required()
def aprobar_solicitud(id):

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede aprobar solicitudes'
        }), 403

    datos = request.get_json(silent=True) or {}
    firma_aprobador = datos.get('firma_aprobador_base64') or None

    usuario_id = int(get_jwt_identity())

    conn = get_connection()

    numero_solicitud = None

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT id, numero_solicitud, estado
                FROM solicitudes
                WHERE id = %s
                FOR UPDATE
            ''', (id,))

            solicitud = cursor.fetchone()

            if not solicitud:
                conn.rollback()
                return jsonify({'error': 'Solicitud no encontrada'}), 404

            if solicitud['estado'] != 'PENDIENTE':
                conn.rollback()
                return jsonify({
                    'error': (
                        f'La solicitud ya fue procesada '
                        f'(estado actual: {solicitud["estado"]})'
                    )
                }), 400

            numero_solicitud = solicitud['numero_solicitud']

            cursor.execute('''
                UPDATE solicitudes
                SET
                    estado = 'APROBADA',
                    aprobado_por = %s,
                    fecha_aprobacion = CURRENT_TIMESTAMP,
                    firma_aprobador_base64 = %s
                WHERE id = %s
            ''', (usuario_id, firma_aprobador, id))

        conn.commit()

    except Exception as e:

        conn.rollback()
        print('ERROR AL APROBAR SOLICITUD:', repr(e))
        return jsonify({'error': str(e)}), 400

    finally:
        conn.close()

    try:
        registrar_auditoria(
            usuario_id=usuario_id,
            accion='APROBAR',
            entidad='SOLICITUD',
            entidad_id=id,
            descripcion=f'Aprobación de solicitud {numero_solicitud}',
            datos_anteriores={'estado': 'PENDIENTE'},
            datos_nuevos={'estado': 'APROBADA'}
        )
    except Exception as e:
        print('ERROR AL REGISTRAR AUDITORIA DE APROBACION:', repr(e))

    return jsonify({'mensaje': 'Solicitud aprobada'})


# ============================================================
# PUT /api/solicitudes/<id>/rechazar
#
# SOLO ADMIN
# ============================================================

@solicitudes_bp.route('/<int:id>/rechazar', methods=['PUT'])
@jwt_required()
def rechazar_solicitud(id):

    claims = get_jwt()

    if claims.get('rol') != 'admin':
        return jsonify({
            'error': 'Solo el admin puede rechazar solicitudes'
        }), 403

    datos = request.get_json(silent=True) or {}

    motivo = str(datos.get('motivo_rechazo', '')).strip()

    if not motivo:
        return jsonify({
            'error': 'El motivo de rechazo es obligatorio'
        }), 400

    usuario_id = int(get_jwt_identity())

    conn = get_connection()

    numero_solicitud = None

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                SELECT id, numero_solicitud, estado
                FROM solicitudes
                WHERE id = %s
                FOR UPDATE
            ''', (id,))

            solicitud = cursor.fetchone()

            if not solicitud:
                conn.rollback()
                return jsonify({'error': 'Solicitud no encontrada'}), 404

            if solicitud['estado'] != 'PENDIENTE':
                conn.rollback()
                return jsonify({
                    'error': (
                        f'La solicitud ya fue procesada '
                        f'(estado actual: {solicitud["estado"]})'
                    )
                }), 400

            numero_solicitud = solicitud['numero_solicitud']

            cursor.execute('''
                UPDATE solicitudes
                SET
                    estado = 'RECHAZADA',
                    aprobado_por = %s,
                    fecha_aprobacion = CURRENT_TIMESTAMP,
                    motivo_rechazo = %s
                WHERE id = %s
            ''', (usuario_id, motivo, id))

        conn.commit()

    except Exception as e:

        conn.rollback()
        print('ERROR AL RECHAZAR SOLICITUD:', repr(e))
        return jsonify({'error': str(e)}), 400

    finally:
        conn.close()

    try:
        registrar_auditoria(
            usuario_id=usuario_id,
            accion='RECHAZAR',
            entidad='SOLICITUD',
            entidad_id=id,
            descripcion=(
                f'Rechazo de solicitud {numero_solicitud}. '
                f'Motivo: {motivo}'
            ),
            datos_anteriores={'estado': 'PENDIENTE'},
            datos_nuevos={'estado': 'RECHAZADA', 'motivo_rechazo': motivo}
        )
    except Exception as e:
        print('ERROR AL REGISTRAR AUDITORIA DE RECHAZO:', repr(e))

    return jsonify({'mensaje': 'Solicitud rechazada'})