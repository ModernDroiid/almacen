from database import get_connection
from psycopg.types.json import Jsonb


def registrar_auditoria(
    usuario_id,
    accion,
    entidad,
    entidad_id=None,
    descripcion=None,
    datos_anteriores=None,
    datos_nuevos=None
):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO auditoria (
                    usuario_id,
                    accion,
                    entidad,
                    entidad_id,
                    descripcion,
                    datos_anteriores,
                    datos_nuevos
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                usuario_id,
                accion,
                entidad,
                entidad_id,
                descripcion,
                Jsonb(datos_anteriores) if datos_anteriores is not None else None,
                Jsonb(datos_nuevos) if datos_nuevos is not None else None
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()