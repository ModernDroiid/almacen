from database import get_connection
import hashlib

conn = get_connection()

# Agregamos las columnas que faltan
for columna, definicion in [
    ('email',   'TEXT'),
    ('sede_id', 'INTEGER'),
    ('activo',  'INTEGER DEFAULT 1'),
    ('password','TEXT'),
]:
    try:
        conn.execute(f'ALTER TABLE usuarios ADD COLUMN {columna} {definicion}')
        print(f'Columna {columna} agregada')
    except Exception as e:
        print(f'{columna}: {e}')

conn.commit()

# Copiamos correo → email y password_hash → password
conn.execute('UPDATE usuarios SET email = correo WHERE email IS NULL')
conn.execute('UPDATE usuarios SET password = password_hash WHERE password IS NULL')
conn.execute('UPDATE usuarios SET activo = 1 WHERE activo IS NULL')
conn.commit()

# Creamos la sede principal si no existe
cursor = conn.cursor()
cursor.execute("INSERT OR IGNORE INTO sedes (id, nombre, ciudad) VALUES (1, 'Sede Principal', 'Bogota')")
conn.commit()

# Actualizamos el admin para que tenga sede_id y rol correcto
conn.execute("UPDATE usuarios SET sede_id = 1, rol = 'admin' WHERE rol = 'admin' OR correo LIKE '%admin%'")
conn.commit()

# Creamos admin por defecto si no existe
password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
cursor.execute("""
    INSERT OR IGNORE INTO usuarios (nombre, email, password, rol, sede_id, activo)
    VALUES ('Administrador', 'admin@occidente.com', ?, 'admin', 1, 1)
""", (password_hash,))
conn.commit()

cursor.execute("SELECT id, nombre, email, rol FROM usuarios")
print("Usuarios actuales:", [dict(u) for u in cursor.fetchall()])

conn.close()
print('Listo')