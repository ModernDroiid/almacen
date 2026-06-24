import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'almacen.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            unidad TEXT DEFAULT 'unidad',
            stock INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 0,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
                         
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'consulta',
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_documento TEXT UNIQUE NOT NULL,
            obra TEXT,
            proveedor TEXT,
            observaciones TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS detalle_entradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entrada_id INTEGER REFERENCES entradas(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER NOT NULL,
            precio_unitario REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS salidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_documento TEXT UNIQUE NOT NULL,
            destinatario TEXT,
            observaciones TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS detalle_salidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salida_id INTEGER REFERENCES salidas(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS devoluciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_documento TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            documento_origen TEXT,
            motivo TEXT,
            observaciones TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS detalle_devoluciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devolucion_id INTEGER REFERENCES devoluciones(id),
            producto_id INTEGER REFERENCES productos(id),
            cantidad INTEGER NOT NULL
        );
    ''')

    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")