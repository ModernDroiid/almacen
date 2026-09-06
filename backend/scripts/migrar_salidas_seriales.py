import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="almacen",
    user="postgres",
    password="1006956507@Andre$"
)

try:
    with conn.cursor() as cur:

        cur.execute("""
            ALTER TABLE detalle_salidas
            ADD COLUMN IF NOT EXISTS equipo_id INTEGER;
        """)

        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_detalle_salidas_equipo'
                ) THEN

                    ALTER TABLE detalle_salidas
                    ADD CONSTRAINT fk_detalle_salidas_equipo
                    FOREIGN KEY (equipo_id)
                    REFERENCES equipos(id)
                    ON DELETE RESTRICT;

                END IF;
            END
            $$;
        """)

        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_detalle_salidas_salida_equipo
            ON detalle_salidas (salida_id, equipo_id)
            WHERE equipo_id IS NOT NULL;
        """)

    conn.commit()

    print("✅ Migración de salidas completada correctamente.")

except Exception as e:

    conn.rollback()

    print("❌ Error durante la migración:")
    print(e)

finally:

    conn.close()