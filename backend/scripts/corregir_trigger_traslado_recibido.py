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

sql = """
CREATE OR REPLACE FUNCTION procesar_traslado_recibido()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    detalle RECORD;

    producto_origen RECORD;
    producto_destino RECORD;

    nuevo_producto_id INTEGER;

    stock_origen INTEGER;

    estado_anterior_equipo VARCHAR;
    condicion_anterior_equipo VARCHAR;
BEGIN

    -- =========================================================
    -- SOLO EJECUTAR CUANDO:
    -- PENDIENTE -> RECIBIDO
    -- =========================================================

    IF OLD.estado <> 'PENDIENTE'
       OR NEW.estado <> 'RECIBIDO' THEN

        RETURN NEW;

    END IF;


    -- =========================================================
    -- RECORRER LOS DETALLES DEL TRASLADO
    -- =========================================================

    FOR detalle IN
        SELECT
            dt.id,
            dt.producto_id,
            dt.equipo_id,
            dt.cantidad,
            dt.observaciones

        FROM detalle_traslados dt

        WHERE dt.traslado_id = NEW.id

        ORDER BY dt.id

    LOOP

        -- =====================================================
        -- PRODUCTO EN SEDE ORIGEN
        -- =====================================================

        SELECT
            p.id,
            p.codigo,
            p.nombre,
            p.descripcion,
            p.unidad_id,
            p.stock_minimo,
            p.requiere_serial,
            p.modelo_id,
            p.sede_id

        INTO producto_origen

        FROM productos p

        WHERE p.id = detalle.producto_id

        FOR UPDATE;


        IF NOT FOUND THEN

            RAISE EXCEPTION
                'No existe el producto %',
                detalle.producto_id;

        END IF;


        -- =====================================================
        -- STOCK EN ORIGEN
        -- =====================================================

        SELECT
            COALESCE(
                i.cantidad,
                0
            )

        INTO stock_origen

        FROM inventario i

        WHERE
            i.producto_id =
                producto_origen.id

            AND i.sede_id =
                NEW.sede_origen_id

        FOR UPDATE;


        IF stock_origen IS NULL THEN
            stock_origen := 0;
        END IF;


        IF stock_origen < detalle.cantidad THEN

            RAISE EXCEPTION
                'Stock insuficiente para el producto %. Disponible: %, solicitado: %',
                producto_origen.codigo,
                stock_origen,
                detalle.cantidad;

        END IF;


        -- =====================================================
        -- BUSCAR PRODUCTO EN LA SEDE DESTINO
        -- MISMO CÓDIGO
        -- =====================================================

        SELECT
            p.id,
            p.codigo,
            p.nombre,
            p.sede_id

        INTO producto_destino

        FROM productos p

        WHERE
            p.sede_id =
                NEW.sede_destino_id

            AND p.codigo =
                producto_origen.codigo

        LIMIT 1;


        -- =====================================================
        -- CREAR PRODUCTO EN DESTINO SI NO EXISTE
        -- =====================================================

        IF NOT FOUND THEN

            INSERT INTO productos (
                sede_id,
                codigo,
                nombre,
                descripcion,
                stock_minimo,
                requiere_serial,
                modelo_id,
                unidad_id,
                fecha_creacion
            )

            VALUES (
                NEW.sede_destino_id,
                producto_origen.codigo,
                producto_origen.nombre,
                producto_origen.descripcion,
                producto_origen.stock_minimo,
                producto_origen.requiere_serial,
                producto_origen.modelo_id,
                producto_origen.unidad_id,
                CURRENT_TIMESTAMP
            )

            RETURNING id
            INTO nuevo_producto_id;

        ELSE

            nuevo_producto_id =
                producto_destino.id;

        END IF;


        -- =====================================================
        -- DESCONTAR ORIGEN
        -- =====================================================

        UPDATE inventario

        SET
            cantidad =
                cantidad - detalle.cantidad,

            fecha_actualizacion =
                CURRENT_TIMESTAMP

        WHERE
            producto_id =
                producto_origen.id

            AND sede_id =
                NEW.sede_origen_id;


        -- =====================================================
        -- SUMAR DESTINO
        -- =====================================================

        INSERT INTO inventario (
            producto_id,
            sede_id,
            cantidad,
            fecha_actualizacion
        )

        VALUES (
            nuevo_producto_id,
            NEW.sede_destino_id,
            detalle.cantidad,
            CURRENT_TIMESTAMP
        )

        ON CONFLICT (
            producto_id,
            sede_id
        )

        DO UPDATE SET

            cantidad =
                inventario.cantidad +
                EXCLUDED.cantidad,

            fecha_actualizacion =
                CURRENT_TIMESTAMP;


        -- =====================================================
        -- EQUIPO SERIALIZADO
        -- =====================================================

        IF detalle.equipo_id IS NOT NULL THEN

            -- -------------------------------------------------
            -- OBTENER ESTADO/CONDICIÓN ACTUAL
            -- -------------------------------------------------

            SELECT
                estado,
                condicion

            INTO
                estado_anterior_equipo,
                condicion_anterior_equipo

            FROM equipos

            WHERE
                id = detalle.equipo_id

            FOR UPDATE;


            IF NOT FOUND THEN

                RAISE EXCEPTION
                    'No existe el equipo %',
                    detalle.equipo_id;

            END IF;


            -- -------------------------------------------------
            -- VALIDAR QUE PERTENEZCA AL ORIGEN
            -- -------------------------------------------------

            IF NOT EXISTS (
                SELECT 1
                FROM equipos e
                WHERE
                    e.id =
                        detalle.equipo_id

                    AND e.producto_id =
                        producto_origen.id

                    AND e.sede_id =
                        NEW.sede_origen_id
            ) THEN

                RAISE EXCEPTION
                    'El equipo % no pertenece al producto o sede de origen',
                    detalle.equipo_id;

            END IF;


            -- -------------------------------------------------
            -- MOVER EQUIPO AL DESTINO
            -- -------------------------------------------------

            UPDATE equipos

            SET
                producto_id =
                    nuevo_producto_id,

                sede_id =
                    NEW.sede_destino_id,

                estado =
                    'DISPONIBLE'

            WHERE
                id =
                    detalle.equipo_id;


            -- -------------------------------------------------
            -- HISTORIAL DEL EQUIPO
            -- -------------------------------------------------

            INSERT INTO historial_equipos (
                equipo_id,
                usuario_id,
                tipo_movimiento,
                sede_origen_id,
                sede_destino_id,
                estado_anterior,
                estado_nuevo,
                condicion_anterior,
                condicion_nueva,
                observaciones,
                fecha
            )

            VALUES (
                detalle.equipo_id,

                NEW.usuario_recibido_id,

                'TRASLADO',

                NEW.sede_origen_id,

                NEW.sede_destino_id,

                estado_anterior_equipo,

                'DISPONIBLE',

                condicion_anterior_equipo,

                condicion_anterior_equipo,

                COALESCE(
                    detalle.observaciones,
                    'Traslado entre sedes'
                ),

                CURRENT_TIMESTAMP
            );

        END IF;

    END LOOP;


    RETURN NEW;

END;
$$;
"""

try:

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()

    print(
        "✅ Trigger procesar_traslado_recibido() corregido correctamente."
    )

except Exception as e:

    conn.rollback()

    print("❌ Error:")
    print(e)

finally:

    conn.close()