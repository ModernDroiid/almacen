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
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_name = 'detalle_salidas'
            ORDER BY ordinal_position
        """)

        for fila in cur.fetchall():
            print(fila)

finally:
    conn.close()