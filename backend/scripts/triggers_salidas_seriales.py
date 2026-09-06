import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

conn = psycopg.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "almacen"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD")
)

try:
    with conn.cursor() as cur:

        # ============================================================
        # 1. Al registrar una salida de un equipo serializado:
        #    DISPONIBLE -> INSTALADO
        # ============================================================

        cur.execute("""
            CREATE OR REPLACE FUNCTION actualizar_estado_equipo_salida()
            RETURNS TRIGGER
            AS $$
            BEGIN

                IF NEW.equipo_id IS NOT NULL THEN

                    UPDATE equipos
                    SET estado = 'INSTALADO'
                    WHERE id = NEW.equipo_id
                      AND estado = 'DISPONIBLE';

                    IF NOT FOUND THEN
                        RAISE EXCEPTION
                        'El equipo % no está disponible para salida.',
                        NEW.equipo_id;
                    END IF;

                END IF;

                RETURN NEW;

            END;
            $$
            LANGUAGE plpgsql;
        """)

        cur.execute("""
            DROP TRIGGER IF EXISTS trg_detalle_salidas_equipo
            ON detalle_salidas;
        """)

        cur.execute("""
            CREATE TRIGGER trg_detalle_salidas_equipo
            AFTER INSERT
            ON detalle_salidas
            FOR EACH ROW
            EXECUTE FUNCTION actualizar_estado_equipo_salida();
        """)

        # ============================================================
        # 2. Al anular una salida:
        #    INSTALADO -> DISPONIBLE
        #
        #    Solo vuelve a disponible si ese equipo no pertenece
        #    a otra salida activa.
        # ============================================================

        cur.execute("""
            CREATE OR REPLACE FUNCTION revertir_equipos_salida_anulada()
            RETURNS TRIGGER
            AS $$
            BEGIN

                IF OLD.estado = 'ACTIVA'
                   AND NEW.estado = 'ANULADA' THEN

                    UPDATE equipos e
                    SET estado = 'DISPONIBLE'
                    WHERE e.id IN (
                        SELECT ds.equipo_id
                        FROM detalle_salidas ds
                        WHERE ds.salida_id = NEW.id
                          AND ds.equipo_id IS NOT NULL
                    )
                    AND NOT EXISTS (
                        SELECT 1
                        FROM detalle_salidas ds2
                        JOIN salidas s2
                          ON s2.id = ds2.salida_id
                        WHERE ds2.equipo_id = e.id
                          AND s2.id <> NEW.id
                          AND s2.estado = 'ACTIVA'
                    );

                END IF;

                RETURN NEW;

            END;
            $$
            LANGUAGE plpgsql;
        """)

        cur.execute("""
            DROP TRIGGER IF EXISTS trg_salidas_anulada_equipos
            ON salidas;
        """)

        cur.execute("""
            CREATE TRIGGER trg_salidas_anulada_equipos
            AFTER UPDATE OF estado
            ON salidas
            FOR EACH ROW
            EXECUTE FUNCTION revertir_equipos_salida_anulada();
        """)

    conn.commit()

    print("✅ Triggers de salidas serializadas creados correctamente.")

except Exception as e:

    conn.rollback()

    print("❌ Error:")
    print(e)

finally:
    conn.close()