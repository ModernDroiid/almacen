import psycopg

try:
    conn = psycopg.connect(
        host="localhost",
        port=5432,
        dbname="almacen",
        user="postgres",
        password="1006956507@Andre$"
    )

    print("✅ Conexión exitosa a PostgreSQL")

    conn.close()

except Exception as e:
    print("❌ Error:")
    print(e)