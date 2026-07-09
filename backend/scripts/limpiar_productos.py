from database import get_connection

conn = get_connection()
conn.executescript('''
    CREATE TABLE IF NOT EXISTS productos_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        unidad TEXT DEFAULT "UND",
        stock INTEGER DEFAULT 0,
        stock_minimo INTEGER DEFAULT 0,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    INSERT INTO productos_new (id, codigo, nombre, descripcion, unidad, stock, stock_minimo, fecha_creacion)
    SELECT id, codigo, nombre, descripcion, unidad, stock, stock_minimo, fecha_creacion FROM productos;
    DROP TABLE productos;
    ALTER TABLE productos_new RENAME TO productos;
''')
conn.commit()
print('Listo')