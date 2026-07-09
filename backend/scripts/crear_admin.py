from werkzeug.security import generate_password_hash
from database import get_connection, inicializar_db

inicializar_db()

correo   = input("Correo del admin: ").strip().lower()
nombre   = input("Nombre completo: ").strip()
password = input("Contraseña: ").strip()

conn = get_connection()
cursor = conn.cursor()
try:
    cursor.execute(
        'INSERT INTO usuarios (correo, nombre, password_hash, rol) VALUES (?, ?, ?, ?)',
        (correo, nombre, generate_password_hash(password), 'admin')
    )
    conn.commit()
    print(f"Usuario admin '{correo}' creado correctamente.")
except Exception as e:
    print("Error:", e)
finally:
    conn.close()