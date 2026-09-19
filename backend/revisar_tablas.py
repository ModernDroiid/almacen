from database import get_connection

conn = get_connection()

try:
    with conn.cursor() as cursor:

        cursor.execute("""
            SELECT
                table_name,
                column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN (
                  'salidas',
                  'detalle_salidas',
                  'devoluciones',
                  'detalle_devoluciones',
                  'productos',
                  'unidades',
                  'equipos',
                  'modelos',
                  'marcas'
              )
            ORDER BY
                table_name,
                ordinal_position
        """)

        for fila in cursor.fetchall():
            print(
                fila["table_name"],
                "->",
                fila["column_name"]
            )

finally:
    conn.close()