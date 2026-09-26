# ============================================================
# utils/notificaciones.py
#
# Crea notificaciones para avisar a otros usuarios de la app
# cuando pasa algo que les interesa:
#
#   - Traslado creado   -> avisa a los "sede" de la SEDE DESTINO
#   - Solicitud creada  -> avisa a todos los "admin"
#   - Salida creada     -> avisa a "porteria" de esa SEDE
#
# Se usa de forma "silenciosa", igual que registrar_auditoria:
# si algo falla aquí NO debe tumbar la operación principal (el
# traslado/solicitud/salida ya se guardó bien de todas formas).
# Por eso quien la llama siempre la envuelve en su propio
# try/except.
# ============================================================

from database import get_connection


def crear_notificacion(
    tipo,
    mensaje,
    rol_destino,
    sede_id=None,
    entidad_tipo=None,
    entidad_id=None,
    creado_por=None
):
    """
    tipo:         'traslado' | 'solicitud' | 'salida'
    mensaje:      texto que se muestra en la notificación
    rol_destino:  'admin' | 'sede' | 'porteria' — quién debe verla
    sede_id:      sede a la que va dirigida (None = todas, se usa
                  para 'admin', que ve todo sin importar la sede)
    entidad_tipo: 'traslado' | 'solicitud' | 'salida' (para poder
                  enlazar al detalle desde el frontend)
    entidad_id:   id de esa entidad
    creado_por:   usuario que generó la acción, para que no se
                  auto-notifique a sí mismo
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute('''
                INSERT INTO notificaciones (
                    tipo,
                    mensaje,
                    rol_destino,
                    sede_id,
                    entidad_tipo,
                    entidad_id,
                    creado_por
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                tipo,
                mensaje,
                rol_destino,
                sede_id,
                entidad_tipo,
                entidad_id,
                creado_por
            ))

        conn.commit()

    finally:
        conn.close()