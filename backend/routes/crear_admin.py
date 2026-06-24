from werkzeug.security import generate_password_hash
from database import get_connection, inicializar_db

inicializar_db()  # asegura que la tabla usuarios ya exista

correo = input("Correo del admin: ").strip().lower()
password = input("Contraseña: ").strip()

conn = get_connection()
cursor = conn.cursor()
try:
    cursor.execute(
        'INSERT INTO usuarios (correo, password_hash, rol) VALUES (?, ?, ?)',
        (correo, generate_password_hash(password), 'admin')
    )
    conn.commit()
    print(f"Usuario admin '{correo}' creado correctamente.")
except Exception as e:
    print("Error:", e)
finally:
    conn.close()