from database import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, nombre, correo, password_hash, rol, sede_id, activo FROM usuarios")
for u in cursor.fetchall():
    print(dict(u))
conn.close()
