from database import get_connection

conn = get_connection()
conn.executescript('''
    CREATE TABLE IF NOT EXISTS salidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_documento TEXT UNIQUE NOT NULL,
        obra TEXT,
        destino TEXT,
        observaciones TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS detalle_salidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        salida_id INTEGER REFERENCES salidas(id),
        producto_id INTEGER REFERENCES productos(id),
        cantidad INTEGER NOT NULL,
        serial TEXT,
        modelo TEXT,
        marca TEXT
    );
''')
conn.commit()
print('Listo')