from database import get_connection
import hashlib

conn = get_connection()

conn.executescript('''
    -- Tabla de sedes
    CREATE TABLE IF NOT EXISTS sedes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        ciudad TEXT NOT NULL,
        activa INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Tabla de usuarios
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT DEFAULT 'sede',
        sede_id INTEGER REFERENCES sedes(id),
        activo INTEGER DEFAULT 1,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Agregamos sede_id a entradas, salidas y devoluciones
    -- Si ya existen las columnas no falla por el IF NOT EXISTS
''')

# Agregamos sede_id a las tablas de movimientos
for tabla in ['entradas', 'salidas', 'devoluciones']:
    try:
        conn.execute(f'ALTER TABLE {tabla} ADD COLUMN sede_id INTEGER REFERENCES sedes(id)')
        print(f'Columna sede_id agregada a {tabla}')
    except Exception as e:
        print(f'{tabla}: {e}')

conn.commit()

# Creamos la sede y usuario admin por defecto
cursor = conn.cursor()

# Sede principal
cursor.execute("INSERT OR IGNORE INTO sedes (id, nombre, ciudad) VALUES (1, 'Sede Principal', 'Bogota')")

# Admin por defecto — password: admin123
password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
cursor.execute("""
    INSERT OR IGNORE INTO usuarios (nombre, email, password, rol, sede_id)
    VALUES ('Administrador', 'admin@occidente.com', ?, 'admin', 1)
""", (password_hash,))

conn.commit()
conn.close()
print('Listo — usuario admin creado: admin@occidente.com / admin123')