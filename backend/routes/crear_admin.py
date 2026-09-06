from werkzeug.security import generate_password_hash
from database import get_connection

correo = input("Correo del admin: ").strip().lower()
nombre = input("Nombre completo: ").strip()
password = input("Contraseña: ").strip()

conn = get_connection()

try:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO usuarios
            (correo, nombre, password_hash, rol)
            VALUES
            (%s, %s, %s, %s)
            """,
            (
                correo,
                nombre,
                generate_password_hash(password),
                "admin"
            )
        )

    conn.commit()
    print(f"Usuario admin '{correo}' creado correctamente.")

except Exception as e:
    conn.rollback()
    print("Error:", e)

finally:
    conn.close()