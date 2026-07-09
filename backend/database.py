import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'almacen.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''

        CREATE TABLE IF NOT EXISTS sedes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            ciudad TEXT NOT NULL,
            activa INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'consulta',
            sede_id INTEGER REFERENCES sedes(id),
            activo INTEGER DEFAULT 1,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            unidad TEXT DEFAULT 'UND',
            stock INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 0,
            sede_id INTEGER REFERENCES sedes(id),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS catalogos_modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS catalogos_marcas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_documento TEXT UNIQUE NOT NULL,
            obra TEXT,
            destino TEXT,
            observaciones TEXT,
            sede_id INTEGER REFERENCES sedes(id),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS detalle_entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entrada_id INTEGER REFERENCES entradas(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER NOT NULL,
            serial TEXT,
            modelo TEXT,
            marca TEXT,
            unidad TEXT DEFAULT 'UND'
        );

        CREATE TABLE IF NOT EXISTS salidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_documento TEXT UNIQUE NOT NULL,
            obra TEXT,
            destino TEXT,
            observaciones TEXT,
            sede_id INTEGER REFERENCES sedes(id),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS detalle_salidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salida_id INTEGER REFERENCES salidas(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER NOT NULL,
            serial TEXT,
            modelo TEXT,
            marca TEXT,
            unidad TEXT DEFAULT 'UND'
        );

        CREATE TABLE IF NOT EXISTS devoluciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_documento TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            salida_id INTEGER REFERENCES salidas(id),
            origen TEXT,
            destino TEXT,
            motivo TEXT,
            observaciones TEXT,
            sede_id INTEGER REFERENCES sedes(id),
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
            unidad TEXT DEFAULT 'UND'
        );

        CREATE UNIQUE INDEX IF NOT EXISTS ix_productos_codigo_sede
            ON productos(codigo, sede_id);

    ''')

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")