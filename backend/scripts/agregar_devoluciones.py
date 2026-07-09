from database import get_connection

conn = get_connection()
conn.executescript('''
    CREATE TABLE IF NOT EXISTS devoluciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_documento TEXT UNIQUE NOT NULL,
        salida_id INTEGER REFERENCES salidas(id),
        origen TEXT,
        destino TEXT DEFAULT 'Almacen',
        motivo TEXT,
        observaciones TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS detalle_devoluciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        devolucion_id INTEGER REFERENCES devoluciones(id),
        producto_id INTEGER REFERENCES productos(id),
        cantidad INTEGER NOT NULL,
        serial TEXT,
        modelo TEXT,
        marca TEXT,
        unidad TEXT
    );
''')
conn.commit()
conn.close()
print('Listo')